"""KickTip v6 modeler (Phase 0): data loading across seasons, rating components, walk-forward (expanding window) state at every ET Saturday cutoff.
Never imports anything from private/. Protocol: PROTOCOL.md (pre-registered). ratings.py (MSM v3) is used unchanged (only its module constant RIDGE is varied for the ridge-tuning component).
Team index convention is the same as ratings.fit(): sorted FBS ids + 'FCS' pseudo-team."""
import json, math, os, sys, datetime as dt, collections, zoneinfo
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ratings as R
ROOT = R.ROOT
ET = zoneinfo.ZoneInfo("America/New_York")
CONF = json.load(open(f"{ROOT}/data/ref/conf_2026.json")); FBS = {v["id"]: k for k, v in CONF.items()}
TEAMS = sorted(FBS) + ["FCS"]; IX = {t: i for i, t in enumerate(TEAMS)}; N = len(TEAMS); FIDX = [IX[t] for t in FBS]
key = lambda i: i if i in FBS else "FCS"
sig = lambda x: 1 / (1 + np.exp(-x))
LAMBDAS = (0.3, 1.0, 3.0, 10.0)
SEASONS = (2021, 2022, 2023, 2024, 2025, 2026)
DEV = (2021, 2022); TEST = (2023, 2024, 2025, 2026)
FADE_G = 4.0

# ---------------------------------------------------------------- data
def block_start(d):
    """Saturday on or before ET date d (ET Saturday-to-Friday weeks)."""
    return d - dt.timedelta(days=(d.weekday() - 5) % 7)

def _prior_status(y, root):
    """{game_id: (status name, completed)} from the cached ESPN scoreboards of season y (written by src/prior_pull.py); the evidence for the FINAL assert."""
    st = {}
    for wk in range(1, 16):
        for pre in ("sb", "sbx"):       # sbx_* = weeks that contain a postponed/canceled game (sb_* is only written for weeks where every event is completed); pulled once for the FINAL assert
            p = f"{root}/data/cache/prior/{pre}_{y}_w{wk:02d}.json"
            if os.path.exists(p):
                for e in json.load(open(p)): st[e["id"]] = (e["status"], e["completed"])
    return st

def load_all(root=ROOT, strict_live=True):
    """All final regular-season games with an FBS team, seasons 2021-2026, with ET kickoff, season and week-block k (k=1 = block of the season's first game).
    HARD ASSERT (QA fix 1): every game of every season must be STATUS_FINAL and completed. Prior seasons are checked against the cached scoreboards; a game missing from the cache
    or not final raises AssertionError. 2026: a game in games_rated.json whose schedule row is not STATUS_FINAL raises too (strict_live=True, the Phase 0 harness); the live site
    refresh (src/calibrate.py) passes strict_live=False, which drops such a row and counts it in the returned dict as live_not_final instead of stopping the refresh."""
    out = []; dropped = collections.Counter()
    for y in SEASONS[:-1]:
        st = _prior_status(y, root); rows_y = json.load(open(f"{root}/data/store/prior/games_{y}.json"))
        bad = [g["id"] for g in rows_y if st.get(g["id"]) != ("STATUS_FINAL", True)]
        assert not bad, f"season {y}: {len(bad)} games not STATUS_FINAL/completed in the cached scoreboards, e.g. {bad[:5]}"
        for g in rows_y:
            g = dict(g); g["season"] = y; out.append(g)
    sched = {g["id"]: g for g in json.load(open(f"{root}/data/store/schedule.json"))}
    for g in json.load(open(f"{root}/data/store/games_rated.json")):
        s = sched.get(g["id"])
        if s is None or s.get("status") != "STATUS_FINAL" or not s.get("done"):
            assert not strict_live, f"2026 game {g['id']} is in games_rated.json but its schedule row is not STATUS_FINAL"
            dropped["live_not_final"] += 1; continue
        g = dict(g); g["season"] = 2026; g["ts"] = s["date"]; g["week"] = s["week"]; g["cc"] = s["espn_conf"]; out.append(g)
    seen = set(); res = []
    for g in out:
        if g["id"] in seen: dropped["dup"] += 1; continue
        seen.add(g["id"])
        if g["hs"] == g["as_"]: dropped["tie"] += 1; continue
        if g["home"] not in FBS and g["away"] not in FBS: dropped["no_fbs"] += 1; continue
        t = dt.datetime.fromisoformat(g["ts"].replace("Z", "+00:00")).astimezone(ET); g["et"] = t; g["ed"] = t.date(); res.append(g)
    first = {}
    for g in res: first[g["season"]] = min(first.get(g["season"], g["ed"]), g["ed"])
    for g in res:
        g["bstart"] = block_start(g["ed"]); g["k"] = (g["bstart"] - block_start(first[g["season"]])).days // 7 + 1
    res.sort(key=lambda g: (g["et"], g["id"]))
    return res, dict(dropped)

# ---------------------------------------------------------------- Elo (logit scale)
def elo_snapshots(games, K, hfa, rho, mov):
    """Continuous Elo over all seasons. Returns {(season,k): dict(r=array(N), r0=array(N), g=array(N))} = state at that block's cutoff,
    plus the virtual next block (kmax+1) of each season (state after the last game). step = 4*K*(ln(|margin|+1)+1 if mov else 1)*(result - p)."""
    r = np.zeros(N); snaps = {}
    by = collections.defaultdict(list)
    for g in games: by[(g["season"], g["k"])].append(g)
    for s in SEASONS:
        ks = sorted(k for (ss, k) in by if ss == s)
        if not ks: continue
        r = r * rho; r0 = r.copy(); cnt = np.zeros(N)
        for k in range(1, ks[-1] + 2):
            snaps[(s, k)] = dict(r=r.copy(), r0=r0.copy(), g=cnt.copy())
            for g in by.get((s, k), []):
                h, a = IX[key(g["home"])], IX[key(g["away"])]
                p = sig(r[h] - r[a] + (0 if g["neutral"] else hfa)); m = g["hs"] - g["as_"]
                step = 4 * K * ((math.log(abs(m) + 1) + 1) if mov else 1) * ((1 if m > 0 else 0) - p)
                r[h] += step; r[a] -= step; cnt[h] += 1; cnt[a] += 1
    return snaps

def elo_untuned(train, K=0.035, hfa=0.35):
    """Creative's prelim Elo, verbatim logic: in-season games only, from zero, margin multiplier, no carry-over."""
    r = collections.defaultdict(float)
    for g in train:
        h, a = key(g["home"]), key(g["away"]); d = r[h] - r[a] + (0 if g["neutral"] else hfa)
        p = 1 / (1 + math.exp(-d)); m = g["hs"] - g["as_"]; res = 1 if m > 0 else 0; mult = math.log(abs(m) + 1) + 1
        r[h] += K * mult * (res - p) * 4; r[a] -= K * mult * (res - p) * 4
    return r

# ---------------------------------------------------------------- Efficiency (same construction as MSM's eff, standalone)
def eff_rating(G, lam):
    """Opponent-adjusted yards/play and points/drive (offense + defense terms, home field, intercept), ridge lam, recency weights as in ratings.fit(); returns mean of the two FBS z-scores per team (index TEAMS)."""
    D = lambda s: dt.date.fromisoformat(s)
    dates = sorted(set(g["date"] for g in G)); d0, d1 = dates[0], dates[-1]; span = max(1, (D(d1) - D(d0)).days)
    n = N
    def adj(statfn):
        rows = []; y = []; w = []
        for g in G:
            wt = R.REC_MIN + (1 - R.REC_MIN) * (D(g["date"]) - D(d0)).days / span
            bx = g.get("box", {})
            for o, d, home in ((g["home"], g["away"], 1), (g["away"], g["home"], -1)):
                v = statfn(g, o, bx)
                if v is None: continue
                r = np.zeros(2 * n + 2); r[IX[key(o)]] = 1; r[n + IX[key(d)]] = -1; r[2 * n] = 0 if g["neutral"] else home; r[2 * n + 1] = 1
                rows.append(r); y.append(v); w.append(wt)
        if len(rows) < 20: return np.zeros(n)
        X = np.array(rows); y = np.array(y); Wt = np.array(w); P = np.eye(2 * n + 2) * lam; P[-1, -1] = 0; P[-2, -2] = 0
        b = np.linalg.solve(X.T @ (X * Wt[:, None]) + P, X.T @ (Wt * y)); return b[:n] + b[n:2 * n]
    ypp = lambda g, o, bx: bx[o]["yds"] / bx[o]["plays"] if o in bx and bx[o]["plays"] > 20 else None
    ppd = lambda g, o, bx: (g["hs"] if o == g["home"] else g["as_"]) / bx[o]["drives"] if o in bx and bx[o].get("drives", 0) >= 5 else None
    def zf(v):
        sd = v[FIDX].std(); return (v - v[FIDX].mean()) / sd if sd > 0 else v * 0
    return (zf(adj(ypp)) + zf(adj(ppd))) / 2

# ---------------------------------------------------------------- per-cutoff state and per-game rows
def msm_fit(train, lam):
    old = R.RIDGE; R.RIDGE = lam
    try: m = R.fit([dict(g) for g in train], CONF)
    finally: R.RIDGE = old
    assert m["teams"] == TEAMS
    return m

def build(games, elo_params, verbose=False):
    """For every (season,k) cutoff with in-season data (k>=2) plus the virtual next block of the current season, fit all components using only earlier games.
    Returns (rows, states). rows: one dict per game in blocks k>=2 with raw component values (differences home minus away) for every lambda; states: team vectors per cutoff."""
    snaps = elo_snapshots(games, **elo_params)
    by = collections.defaultdict(list)
    for g in games: by[(g["season"], g["k"])].append(g)
    rows = []; states = {}
    for s in SEASONS:
        ks = sorted(k for (ss, k) in by if ss == s)
        kend = ks[-1] + 1 if s == SEASONS[-1] else ks[-1]
        for k in range(2, kend + 1):
            cut = block_start_of(s, k, games)
            train = [g for g in games if g["season"] == s and g["ed"] < cut]
            if len(train) < 30: continue
            gcount = np.zeros(N)
            for g in train: gcount[IX[key(g["home"])]] += 1; gcount[IX[key(g["away"])]] += 1
            f = 1 / (1 + gcount / FADE_G); f[IX["FCS"]] = 0.0
            ms = {l: msm_fit(train, l) for l in LAMBDAS}; es = {l: eff_rating(train, l) for l in LAMBDAS}
            sn = snaps[(s, k)]; ub = elo_untuned(train)
            st = dict(season=s, k=k, cut=cut.isoformat(), f=f, g=gcount, elo=sn["r"], prior=sn["r0"], n_train=len(train),
                      msm={l: ms[l]["strength"].copy() for l in LAMBDAS}, hfa={l: ms[l]["hfa"] for l in LAMBDAS}, sigma={l: ms[l]["sigma"] for l in LAMBDAS}, eff={l: es[l] for l in LAMBDAS})
            states[(s, k)] = st
            for g in by.get((s, k), []):
                h, a = IX[key(g["home"])], IX[key(g["away"])]; home = 0 if g["neutral"] else 1
                row = dict(id=g["id"], season=s, k=k, date=g["ed"].isoformat(), y=1 if g["hs"] > g["as_"] else 0, home=home,
                           fcs=int(g["home"] not in FBS or g["away"] not in FBS), margin=g["hs"] - g["as_"],
                           elo=sn["r"][h] - sn["r"][a], prior=sn["r0"][h] - sn["r0"][a], prior_f=sn["r0"][h] * f[h] - sn["r0"][a] * f[a],
                           p_b4=float(1 / (1 + math.exp(-(ub[key(g["home"])] - ub[key(g["away"])] + (0 if g["neutral"] else 0.35))))))
                for l in LAMBDAS:
                    sv = ms[l]["strength"]; ev = es[l]
                    row[f"msm{l}"] = sv[h] - sv[a]; row[f"msm_f{l}"] = sv[h] * f[h] - sv[a] * f[a]
                    row[f"eff{l}"] = ev[h] - ev[a]; row[f"eff_f{l}"] = ev[h] * f[h] - ev[a] * f[a]
                    row[f"pmsm_raw{l}"] = float(1 / (1 + math.exp(-(sv[h] - sv[a] + ms[l]["hfa"] * home) / ms[l]["sigma"])))
                rows.append(row)
        if verbose: print("season", s, "built", flush=True)
    return rows, states

def block_start_of(season, k, games):
    first = min(g["ed"] for g in games if g["season"] == season)
    return block_start(first) + dt.timedelta(days=7 * (k - 1))
