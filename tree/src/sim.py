"""Monte Carlo season simulator + standings/paths output. Seeded and reproducible.
Everything here is the KickTip MODEL. No outside lines, no sportsbook data.
  P(home win) = 1/(1+exp(-(s_h - s_a + hfa*(not neutral))/sigma))     s = MSM v3 ridge strength, hfa and sigma fitted (src/ratings.py)
  final rating = rating_now + 10*0.6/resume_sd * (0.7*dSOR/sd_SOR + 0.3*dColley/sd_Colley)   (linearised update of the MSM composite)
  rank by final rating = committee proxy; conference tiebreaks via src/tiebreak.py + src/rules.py; CFP field via src/cfp.py."""
import json, os, sys, time, math, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ratings, tiebreak, rules, cfp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{ROOT}/data/out"
CONFS = ["acc", "big10", "big12", "sec", "American", "usa", "midam", "mwest", "pac12", "belt", "ind"]
sig = lambda x: 1 / (1 + np.exp(-x))
import models_registry
DEFAULT_MODEL = os.environ.get("KT_MODEL", models_registry.DEFAULT_ID)   # the KickTip blend (src/models_registry.py); KT_MODEL=elo etc. only for tests
def games_sha12(): return __import__("hashlib").sha256(open(f"{ROOT}/data/store/games_rated.json", "rb").read()).hexdigest()[:12]

class Season:
    def __init__(self, model="default"):
        """model: "default" = the registry default, the KickTip blend (data/out/models/blend.json, written by src/calibrate.py; env KT_MODEL overrides, e.g. elo, for tests only).
        model in ("raw", None) = MSM v3 exactly as before the calibration build (used only for the before/after comparison and the regression tests).
        Any other id = data/out/models/<id>.json. The model drives GAME win probabilities only (s_g, hfa_g, SIG_g); the committee-proxy rating update
        (SOR/Colley, pbench) stays the MSM v3 composite for every model."""
        self.m = m = ratings.fit()
        self.conf = json.load(open(f"{ROOT}/data/ref/conf_2026.json"))
        self.ix = m["ix"]; self.n = m["n"]; self.FCS = self.ix["FCS"]
        self.name = {self.ix[v["id"]]: k for k, v in self.conf.items()}
        self.cof = {self.ix[v["id"]]: v["conf"] for v in self.conf.values()}
        self.sched = json.load(open(f"{ROOT}/data/store/schedule.json"))
        self.s = np.array(m["strength"]); self.hfa = m["hfa"]; self.SIG = m["sigma"]; self.bench = m["bench"]
        self.rating = np.array(m["rating"])
        if model == "default": model = DEFAULT_MODEL
        if model in ("raw", None, ""): model = None
        self.model = model; self.s_g, self.hfa_g, self.SIG_g = self.s, self.hfa, self.SIG
        if model:
            mm = json.load(open(f"{ROOT}/data/out/models/{model}.json"))
            assert mm["teams"] == m["teams"], "team index mismatch"
            # fail closed: a calibration file fitted on different games than the ones being simulated must never be used (run src/calibrate.py after every refresh)
            assert mm.get("n_games") == m["n_games"] and mm.get("games_sha12") == games_sha12(), \
                "calibration file is stale (data changed since src/calibrate.py ran): run `python3 src/calibrate.py` first"
            self.s_g = np.array(mm["s"]); self.hfa_g = float(mm["hfa"]); self.SIG_g = float(mm["sigma"])
        self._games()
        self._confs()
    def tid(self, i):
        if i in self.ix and i != "FCS": return self.ix[i]
        return self.FCS if not i.startswith("-") else None
    def _games(self):
        self.done = []; self.rem = []
        for g in self.sched:
            h, a = self.tid(g["home"]), self.tid(g["away"])
            if h is None or a is None or (h == self.FCS and a == self.FCS): continue
            rec = dict(id=g["id"], status=g.get("status", ""), live=g.get("live"), h=h, a=a, neutral=bool(g["neutral"]), week=g["week"], conf=bool(g["espn_conf"]), date=g["date"], hs=g["hs"], as_=g["as_"])
            (self.done if g["done"] else self.rem).append(rec)
        n = self.n
        self.wins = np.zeros(n); self.gms = np.zeros(n); self.fcs_w = np.zeros(n); self.fcs_g = np.zeros(n); self.fbs_w = np.zeros(n); self.fbs_g = np.zeros(n)
        def add(h, a, hw, done):
            for t, o, w in ((h, a, hw), (a, h, 1 - hw)):
                if t == self.FCS: continue
                self.gms[t] += 1; self.wins[t] += w
                if o == self.FCS: self.fcs_g[t] += 1; self.fcs_w[t] += w
                else: self.fbs_g[t] += 1; self.fbs_w[t] += w
        self.games_now = np.zeros(n)
        for g in self.done:
            add(g["h"], g["a"], 1 if g["hs"] > g["as_"] else 0, True)
        self.w_now = self.wins.copy(); self.g_now = self.gms.copy(); self.fcsw_now = self.fcs_w.copy(); self.fcsg_now = self.fcs_g.copy()
        self.fbsw_now = self.fbs_w.copy(); self.fbsg_now = self.fbs_g.copy()
        # totals of games still to play (denominators for season-end percentages)
        self.g_rem = np.zeros(n); self.fcsg_rem = np.zeros(n); self.fbsg_rem = np.zeros(n)
        for g in self.rem:
            for t, o in ((g["h"], g["a"]), (g["a"], g["h"])):
                if t == self.FCS: continue
                self.g_rem[t] += 1
                if o == self.FCS: self.fcsg_rem[t] += 1
                else: self.fbsg_rem[t] += 1
        self.colley_games = np.zeros(self.n)
        for g in self.m["games"]:
            for t in (g["home"], g["away"]):
                self.colley_games[self.tid(t)] += 1
    def counts(self, g, code):
        cut = rules.RULES[code].get("standings_max_week", 13)
        return g["conf"] and g["week"] <= cut and self.cof.get(g["h"]) == code and self.cof.get(g["a"]) == code
    def _confs(self):
        self.members = {c: sorted(t for t, cc in self.cof.items() if cc == c) for c in CONFS}
        self.cgames_done = {c: [g for g in self.done if self.counts(g, c)] for c in CONFS}
        self.cgames_rem = {c: [g for g in self.rem if self.counts(g, c)] for c in CONFS}

    # ---------- per-team update from one set of results ----------
    def pbench(self, o, side, neutral):
        return sig((self.bench - self.s[o] + (0 if neutral else side * self.hfa)) / self.SIG)

def sample(S, N, seed, forced=None):
    """forced: optional {game_id: 1 (home wins) | 0 (away wins)} -> those columns are fixed in every simulated season.
    The uniform draws are still consumed, so a forced run with the same seed is a common-random-numbers twin of the base run."""
    rng = np.random.default_rng(seed)
    n = S.n; G = len(S.rem)
    h = np.array([g["h"] for g in S.rem]); a = np.array([g["a"] for g in S.rem]); neu = np.array([g["neutral"] for g in S.rem])
    p = sig((S.s_g[h] - S.s_g[a] + np.where(neu, 0, S.hfa_g)) / S.SIG_g)
    hw = rng.random((N, G)) < p
    if forced:
        col = {g["id"]: k for k, g in enumerate(S.rem)}
        for gid, v in forced.items(): hw[:, col[gid]] = bool(v)
    return rng, h, a, neu, p, hw

def tot_arrays(S, N, h, a, neu, hw):
    """per-sim season-to-date arrays (N, n): wins, fcs wins, fbs wins, dSOR, dColley."""
    n = S.n
    wins = np.tile(S.w_now, (N, 1)); fcsw = np.tile(S.fcsw_now, (N, 1)); fbsw = np.tile(S.fbsw_now, (N, 1))
    dsor = np.zeros((N, n)); dcol = np.zeros((N, n))
    col = np.array(S.m["colley"])
    for k in range(len(h)):
        hk, ak = h[k], a[k]; w = hw[:, k]
        for t, o, win, side in ((hk, ak, w, 1), (ak, hk, ~w, -1)):
            if t == S.FCS: continue
            wf = win.astype(float)
            wins[:, t] += wf
            if o == S.FCS: fcsw[:, t] += wf
            else: fbsw[:, t] += wf
            dsor[:, t] += wf - S.pbench(o, side, neu[k])
            dcol[:, t] += ((wf - 0.5) + col[o] - col[t]) / (3 + S.colley_games[t])
    return wins, fcsw, fbsw, dsor, dcol

def rating_update(S, dsor, dcol):
    m = S.m
    return S.rating[None, :] + 10 * 0.6 / m["resume_sd"] * (0.7 * dsor / m["sor_sd"] + 0.3 * dcol / m["colley_sd"])

def run(N=10000, seed=2026, verbose=True, forced=None, S=None):
    t0 = time.time(); S = S or Season(); m = S.m
    rng, h, a, neu, p, hw = sample(S, N, seed, forced)
    wins, fcsw, fbsw, dsor, dcol = tot_arrays(S, N, h, a, neu, hw)
    r_reg = rating_update(S, dsor, dcol)               # rating after regular season (pre title games)
    draw = rng.random((N, S.n))
    gcol = {g["id"]: k for k, g in enumerate(S.rem)}
    # season-end percentages (<=1 FCS win counts)
    capw = wins - np.maximum(0, fcsw - 1)
    games_tot = (S.g_now + S.g_rem)[None, :]
    fcs_games = (S.fcsg_now + S.fcsg_rem)[None, :]
    capg = games_tot - np.maximum(0, fcs_games - 1) * (fcsw >= 1)  # if >=1 FCS win, other FCS games dropped from the denominator only when they were wins
    ovp = capw / np.maximum(capg, 1)
    fbsp = fbsw / np.maximum((S.fbsg_now + S.fbsg_rem)[None, :], 1)
    champ = {c: np.full(N, -1) for c in CONFS}; ccg_in = {c: np.zeros((N, S.n), bool) for c in CONFS}
    seeds1 = {}; trace_ct = {c: {} for c in CONFS}
    dsor2 = dsor.copy(); dcol2 = dcol.copy(); col = np.array(m["colley"])
    ccg_teams = {}; cwins = {}; hosts = {}
    U2 = rng.random((N, len(CONFS)))
    for ci, c in enumerate(CONFS):
        R = rules.RULES[c]
        if R["fmt"] == "none": continue
        mem = S.members[c]; pos = {t: i for i, t in enumerate(mem)}; k = len(mem)
        base = np.zeros((k, k), dtype=np.int16)
        for g in S.cgames_done[c]:
            w, l = (g["h"], g["a"]) if g["hs"] > g["as_"] else (g["a"], g["h"]); base[pos[w], pos[l]] += 1
        Hs = np.tile(base, (N, 1, 1))
        for g in S.cgames_rem[c]:
            kk = gcol[g["id"]]; i, j = pos[g["h"]], pos[g["a"]]
            Hs[:, i, j] += hw[:, kk]; Hs[:, j, i] += ~hw[:, kk]
        cwins[c] = Hs.sum(axis=2)
        div = None
        if R["fmt"] == "div":
            nm = {t: S.name[t] for t in mem}; dmap = {}
            for dn, lst in R["divisions"].items():
                for x in lst: dmap[x] = dn
            div = [dmap[nm[t]] for t in mem]
        memarr = np.array(mem)
        sel = np.zeros((N, 2), int)
        for s in range(N):
            ctx = tiebreak.Ctx(Hs[s].tolist(), r_reg[s, memarr].tolist(), draw[s, memarr].tolist(), ovp[s, memarr].tolist(), capw[s, memarr].tolist(), fbsp[s, memarr].tolist(), div)
            tr = []
            top = tiebreak.select_ccg(ctx, R, tr)
            sel[s] = top
            if tr:
                key = tr[-1]; trace_ct[c][key] = trace_ct[c].get(key, 0) + 1
        g1 = memarr[sel[:, 0]]; g2 = memarr[sel[:, 1]]
        pw1 = sig((S.s_g[g1] - S.s_g[g2] + (0 if R["neutral"] else S.hfa_g)) / S.SIG_g)
        w1 = U2[:, ci] < pw1
        champ[c] = np.where(w1, g1, g2)
        idx = np.arange(N)
        ccg_in[c][idx, g1] = True; ccg_in[c][idx, g2] = True
        ccg_teams[c] = (g1, g2); hosts[c] = g1
        for t, o, win, side in ((g1, g2, w1, 1), (g2, g1, ~w1, -1)):
            wf = win.astype(float)
            neu_c = R["neutral"]
            pb = sig((S.bench - S.s[o] + (0 if neu_c else side * S.hfa)) / S.SIG)
            dsor2[idx, t] += wf - pb
            dcol2[idx, t] += ((wf - 0.5) + col[o] - col[t]) / (3 + S.colley_games[t])
    r_fin = rating_update(S, dsor2, dcol2)
    # CFP
    F = np.array(S.m["F"]); nd = S.ix[S.conf["Notre Dame Fighting Irish"]["id"]] if "Notre Dame Fighting Irish" in S.conf else None
    order_all = F[np.argsort(-r_fin[:, F], axis=1)]
    cfp_site = np.zeros((N, S.n), bool); bye_site = np.zeros((N, S.n), bool); top4rank = np.zeros((N, S.n), bool)
    rank_sum = np.zeros(S.n)
    g6 = [t for t in F.tolist() if S.cof.get(t) in cfp.G6]
    for s in range(N):
        order = order_all[s].tolist(); rank = np.empty(S.n, int); rank[order_all[s]] = np.arange(1, len(order) + 1)
        rk = rank.tolist()
        rank_sum += rank
        champs = {c: (int(champ[c][s]) if champ[c][s] >= 0 else None) for c in CONFS}
        f1 = cfp.field(rk, champs, order, nd, g6)
        cfp_site[s, f1] = True; bye_site[s, f1[:4]] = True
        top4rank[s, order[:4]] = True
    runtime = time.time() - t0
    return dict(S=S, N=N, seed=seed, wins=wins, hw=hw, p=p, h=h, a=a, neu=neu, ccg_in=ccg_in, champ=champ, cfp_site=cfp_site, cfp_off=cfp_site,  # cfp_off: legacy alias (same single rule) kept for tests/web/py_ref.py
                bye=bye_site,
                top4=top4rank, cwins=cwins, ccg_teams=ccg_teams, r_fin=r_fin, r_reg=r_reg, rank_mean=rank_sum / N, trace=trace_ct, runtime=runtime, Hs_conf=None)

def write_outputs(R, outdir=OUT, asof=None):
    S = R["S"]; N = R["N"]; m = S.m; os.makedirs(outdir, exist_ok=True)
    asof = asof or dt.datetime.now(__import__("zoneinfo").ZoneInfo("America/Denver")).strftime("%Y-%m-%d %H:%M MT")
    # conference records now
    teams = []
    for c in CONFS:
        mem = S.members[c]; pos = {t: i for i, t in enumerate(mem)}
        cw = {t: 0 for t in mem}; cl = {t: 0 for t in mem}
        for g in S.cgames_done[c]:
            w, l = (g["h"], g["a"]) if g["hs"] > g["as_"] else (g["a"], g["h"]); cw[w] += 1; cl[l] += 1
        crem = {t: 0 for t in mem}
        for g in S.cgames_rem[c]: crem[g["h"]] += 1; crem[g["a"]] += 1
        rank_now = {t: i + 1 for i, t in enumerate(m["ix"][x] for x in m["order"])}
        for t in mem:
            R_ = rules.RULES[c]
            teams.append(dict(team=S.name[t], conf=c, conf_name=R_["name"], rating=round(float(S.rating[t]), 1), rank_now=rank_now[t],
                  conf_w=cw[t], conf_l=cl[t], conf_remaining=crem[t], overall_w=int(S.w_now[t]), overall_l=int(S.g_now[t] - S.w_now[t]),
                  p_ccg=round(float(R["ccg_in"][c][:, t].mean()), 4) if R_["fmt"] != "none" else None,
                  p_conf_title=round(float((R["champ"][c] == t).mean()), 4) if R_["fmt"] != "none" else None,
                  p_cfp_12=round(float(R["cfp_site"][:, t].mean()), 4),
                  p_cfp_bye=round(float(R["bye"][:, t].mean()), 4), p_top4_rank=round(float(R["top4"][:, t].mean()), 4), mean_final_rank=round(float(R["rank_mean"][t]), 1),
                  exp_wins=round(float(R["wins"][:, t].mean()), 2)))
    teams.sort(key=lambda x: -x["p_cfp_12"])
    json.dump(dict(label="MODEL output - KickTip analysis, not betting advice", model=S.model, as_of=asof, seasons=N, seed=R["seed"], teams=teams), open(f"{outdir}/sim_teams.json", "w"), indent=1)
    # games
    k = fit_spread_scale(S)
    games = []
    for i, g in enumerate(S.rem):
        if g["h"] == S.FCS or g["a"] == S.FCS and False: pass
        d = S.s_g[g["h"]] - S.s_g[g["a"]] + (0 if g["neutral"] else S.hfa_g)      # same basis as the win probability, so the favourite always agrees
        spread = -round(k * d * 2) / 2
        nm = lambda t: "FCS opponent" if t == S.FCS else S.name[t]
        games.append(dict(id=g["id"], status=g["status"], live=g["live"], week=g["week"], date_utc=g["date"], home=nm(g["h"]), away=nm(g["a"]), neutral=g["neutral"], conference_game=g["conf"] and S.cof.get(g["h"]) == S.cof.get(g["a"]),
                          model_home_win_prob=round(float(R["p"][i]), 3), model_spread_home=spread, model_spread_raw=round(float(-k * d), 3), label="model"))   # raw = the same line before the 0.5 rounding: the page computes the gap to a market line from it
    json.dump(dict(label="MODEL spread = KickTip model-implied, not a market line. Negative = home favored.", model=S.model, margin_per_strength_point=round(k, 3), games=games), open(f"{outdir}/sim_games.json", "w"), indent=1)
    return teams, games

def fit_spread_scale(S):
    """OLS slope (through origin) of actual final margin (home minus away) on model diff, all rated games with an FBS team on both sides or FCS pooled."""
    xs = []; ys = []
    for g in S.m["games"]:
        h = S.tid(g["home"]); a = S.tid(g["away"])
        xs.append(S.s_g[h] - S.s_g[a] + (0 if g["neutral"] else S.hfa_g)); ys.append(g["hs"] - g["as_"])
    xs = np.array(xs); ys = np.array(ys)
    return float((xs * ys).sum() / (xs * xs).sum())

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    R = run(N); print("runtime %.1fs" % R["runtime"])
