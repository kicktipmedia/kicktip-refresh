"""'Why it moved' chip engine (SPEC-4-upgrades-v2.md section 2a, sha12 fa5ead38bf0c). Public model data only; no network, no private/, no odds.
What it does
  snapshot_all()  (run_all.py, after the simulations): records today's make-the-12 chance per team for EACH model in data/store/snapshots/<model>/<YYYY-MM-DD_HHMM>.json
                  (as_of in MT, the model version, seasons, seed, remaining games, and the per-game driver table below). Idempotent: the same as_of overwrites itself. Old files (> KEEP_DAYS) are pruned.
  chips(model, sim_teams, short)  (build.py, read-only): for one model returns {team full name: [delta_points_rounded (signed int), popover text]} for the teams that get a chip, and a status dict.
Rules (all decided here, in Python; assets/kt.js only draws what pred-teams.json carries, key 'm' per team)
  * Reference snapshot = the LAST snapshot of the most recent EARLIER Mountain Time calendar day that has one ('the previous daily update'). None -> no chip for that model.
  * Threshold: |cur - ref| >= 5.0 percentage points on the UNROUNDED stored values (4-decimal probabilities, lossless at 10,000 seasons). Computed in integer micro-probability units
    (5.0 points = 50,000), so 4.99 never shows and 5.00 always does. The chip number is the same difference rounded half up to a whole point.
  * Model-change suppression: if the model version differs between the reference and now, or between any snapshot recorded in between and now, NO chip for that model (the first run after the
    blend launch included). The version (model_version) = sha12 of the model-defining code (sim, tiebreak, cfp, rules, ratings, kt_models, wf, calibrate), the frozen tuning file,
    the registry component, seasons and seed. Daily REFIT weights are deliberately NOT part of it (they are the normal daily update, like ratings); see REFRESH-PIPELINE.md and
    FIT_IN_VERSION below.
  * Driver: games that finished since the reference (remaining at the reference, done now) are checked against the reference's driver table (the single-game what-if rerun of the SAME
    simulator with that game forced to each outcome, same seed, so the difference is the change in the team's make-the-12 chance if that game goes the way it went). The driver is the finished game
    whose actual-result effect has the SAME sign as the move and is at least half of it (largest wins); otherwise the fixed fallback sentence. No other causal wording.
  * Popover text is a template filled from this output; the stamp is the reference's as_of in MT."""
import os, sys, re, json, glob, hashlib, datetime as dt, time
from zoneinfo import ZoneInfo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src")
MT = ZoneInfo("America/Denver")
SNAPDIR = os.environ.get("KT_SNAP_DIR") or f"{ROOT}/data/store/snapshots"   # tests and the demo fixture point this elsewhere
THRESH_MICRO = 50000        # 5.0 percentage points, in millionths of a probability
KEEP_DAYS = 30
HORIZON_H = 48              # driver tables cover games kicking off within this many hours of the snapshot (the next daily update comes before most of them finish)
DRIVER_MIN_PM = 5           # a team's driver delta is stored only when it is at least this many per-mille (0.5 points); smaller can never be half of a 5-point move
DRIVER_SEASONS = 6000       # same figure as the what-if shards
FIT_IN_VERSION = False      # True: also put the refit weights into the model version (chips would then be suppressed after almost every refresh, because every refresh refits the weights)
ENGINE_FILES = ["sim.py", "tiebreak.py", "cfp.py", "rules.py", "ratings.py", "kt_models.py", "wf.py", "calibrate.py"]
TEXT_UP = "{name}'s make-the-12 chance is up {n} points since the last daily update ({stamp}). {why}"
TEXT_DN = "{name}'s make-the-12 chance is down {n} points since the last daily update ({stamp}). {why}"
WHY_GAME = "The biggest change came from {winner}'s win over {loser}."
WHY_FALLBACK = "The change came from rating and schedule updates."

def _j(p): return json.load(open(p))
def parse_mt(s): return dt.datetime.strptime(s.replace(" MT", ""), "%Y-%m-%d %H:%M").replace(tzinfo=MT)
def stamp_label(as_of):
    d = parse_mt(as_of); return f"{d.strftime('%b')} {d.day}, {d.strftime('%-I:%M %p')} MT"
def micro(p): return int(round(float(p) * 1_000_000))

def model_version(model_id, seasons, seed):
    h = hashlib.sha256()
    for f in ENGINE_FILES: h.update(open(f"{ROOT}/src/{f}", "rb").read())
    h.update(open(f"{ROOT}/data/ref/calibration_tuning.json", "rb").read())
    import models_registry as MR
    h.update(json.dumps([MR.BY_ID[model_id]["component"], int(seasons), int(seed)]).encode())
    if FIT_IN_VERSION: h.update(json.dumps(_j(f"{ROOT}/data/out/models/{model_id}.json")["fit"], sort_keys=True).encode())
    return "mv1-" + h.hexdigest()[:12]

# ---------------------------------------------------------------- the decision (pure functions, unit-tested)
def move(prev_p, cur_p):
    """-> (delta_micro, shows_chip, rounded_points). delta in millionths of a probability, signed. A chip needs |delta| >= 5.0 points exactly; the number is delta rounded half up in points."""
    d = micro(cur_p) - micro(prev_p); a = abs(d)
    pts = (a + 5000) // 10000
    return d, a >= THRESH_MICRO, (pts if d >= 0 else -pts)

def possessive(name): return f"{name}'s"
def popover(name, delta_pts, ref_as_of, driver=None):
    why = WHY_GAME.format(winner=driver[0], loser=driver[1]) if driver else WHY_FALLBACK
    t = TEXT_UP if delta_pts > 0 else TEXT_DN
    return t.format(name=name, n=abs(delta_pts), stamp=stamp_label(ref_as_of), why=why)

def pick_driver(team, move_micro, ref_dr, finished):
    """ref_dr: {game_id: {'h': {team: per-mille}, 'a': {...}}} (effect on the team if the home / away side wins, vs the reference baseline). finished: {game_id: ('h'|'a', winner_label, loser_label)}.
    -> (winner_label, loser_label) of the game whose actual-result effect has the same sign as the move and is >= half of it; the largest such game; else None."""
    best = None
    for gid, (side, w, l) in finished.items():
        e = (ref_dr.get(gid) or {}).get(side, {}).get(team, 0) * 1000        # per-mille -> micro
        if e == 0 or (e > 0) != (move_micro > 0): continue
        if 2 * abs(e) >= abs(move_micro) and (best is None or abs(e) > best[0]): best = (abs(e), w, l)
    return (best[1], best[2]) if best else None

# ---------------------------------------------------------------- store
def _files(model):
    out = []
    for f in glob.glob(f"{SNAPDIR}/{model}/*.json"):
        try: s = _j(f); out.append((parse_mt(s["as_of"]), f, s))
        except Exception: pass
    return sorted(out, key=lambda x: x[0])

def reference(model, cur_as_of, cur_version):
    """-> (ref_snapshot or None, status). Status 'ok' | 'no previous snapshot' | 'model changed since the previous update'."""
    cur = parse_mt(cur_as_of); snaps = _files(model)
    prev_days = [s for d, f, s in snaps if d.date() < cur.date()]
    if not prev_days: return None, "no previous snapshot"
    ref = prev_days[-1]; rdt = parse_mt(ref["as_of"])
    between = [s for d, f, s in snaps if rdt <= d <= cur]
    if any(s.get("model_version") != cur_version for s in between + [ref]): return None, "model changed since the previous update"
    return ref, "ok"

def chips(model, st, short):
    """st: that model's sim_teams.json dict. short: {full name: display name}. -> ({full: [pts, text]}, status dict). Read-only."""
    ver = model_version(model, st["seasons"], st["seed"]); ref, why = reference(model, st["as_of"], ver)
    info = dict(model=model, as_of=st["as_of"], model_version=ver, status=why, ref_as_of=ref["as_of"] if ref else None, chips=0)
    if not ref: return {}, info
    sched = {g["id"]: g for g in _j(f"{ROOT}/data/store/schedule.json")}
    def lab(n, full_ok=True): return "an FCS opponent" if n == "FCS opponent" else short.get(n, n)
    finished = {}
    for gid, (h, a) in ref.get("rem", {}).items():
        g = sched.get(gid)
        if g and g.get("done") and g.get("hs") is not None and g["hs"] != g["as_"]:
            hw = g["hs"] > g["as_"]; finished[gid] = ("h" if hw else "a", lab(h if hw else a), lab(a if hw else h))
    out = {}; n_driver = 0
    for t in st["teams"]:
        name = t["team"]; rp = ref["p"].get(name)
        if rp is None: continue
        d, show, pts = move(rp, t["p_cfp_12"])
        if not show: continue
        drv = pick_driver(name, d, ref.get("dr", {}), finished); n_driver += bool(drv)
        out[name] = [pts, popover(short.get(name, name), pts, ref["as_of"], drv)]
    info.update(chips=len(out), with_driver_game=n_driver, finished_since_ref=len(finished), driver_tables=len(ref.get("dr", {})))
    return out, info

# ---------------------------------------------------------------- recording (run_all.py)
def _drivers(model, base_of=None, now=None, procs=None):
    """Single-game what-ifs (whatif._work: the same simulator, same seed, one game forced) for games kicking off within HORIZON_H. -> {gid: {'h': {team name: per-mille delta}, 'a': {...}}}"""
    import numpy as np, multiprocessing as mp, whatif, sim
    S = sim.Season(model); now = now or dt.datetime.now(dt.timezone.utc)
    lim = now + dt.timedelta(hours=HORIZON_H)
    def ko(g): return dt.datetime.strptime(g["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
    games = [g for g in S.rem if ko(g) <= lim]
    if not games: return {}
    base = whatif.metrics(sim.run(DRIVER_SEASONS, 2026, verbose=False, S=S))[:, 2]
    jobs = [(DRIVER_SEASONS, 2026, g["id"], o, model) for g in games for o in (1, 0)]
    with mp.Pool(procs or min(4, os.cpu_count() or 1)) as pool: res = pool.map(whatif._work, jobs, chunksize=2)
    got = {(gid, o): m[:, 2] for gid, o, m in res}; names = [S.name.get(t) for t in range(S.n - 1)]
    out = {}
    for g in games:
        e = {}
        for side, o in (("h", 1), ("a", 0)):
            dlt = got[(g["id"], o)] - base
            e[side] = {names[t]: int(dlt[t]) for t in range(len(names)) if names[t] and abs(int(dlt[t])) >= DRIVER_MIN_PM}
        out[g["id"]] = e
    return out

def snapshot(model, outdir, with_drivers=True, procs=None):
    st = _j(f"{outdir}/sim_teams.json"); sg = _j(f"{outdir}/sim_games.json")
    assert st["model"] == model, (st["model"], model)
    n = st["seasons"]
    for t in st["teams"]:
        assert abs(t["p_cfp_12"] * n - round(t["p_cfp_12"] * n)) < 1e-6 * n or n != 10000, "make-12 value is not a whole number of seasons (rounding would no longer be lossless)"
    s = dict(model=model, as_of=st["as_of"], model_version=model_version(model, n, st["seed"]), seasons=n, seed=st["seed"],
             p={t["team"]: t["p_cfp_12"] for t in st["teams"]}, rem={g["id"]: [g["home"], g["away"]] for g in sg["games"]})
    if with_drivers:
        try: s["dr"] = _drivers(model, procs=procs)
        except Exception as e: print(f"WARNING moves: driver tables for {model} failed ({type(e).__name__}: {e}); chips will use the fallback sentence", file=sys.stderr)
    d = parse_mt(st["as_of"]); os.makedirs(f"{SNAPDIR}/{model}", exist_ok=True)
    p = f"{SNAPDIR}/{model}/{d.strftime('%Y-%m-%d_%H%M')}.json"; json.dump(s, open(p, "w"), separators=(",", ":"))
    cut = dt.datetime.now(MT) - dt.timedelta(days=KEEP_DAYS)
    for dd, f, _ in _files(model):
        if dd < cut: os.remove(f)
    return p

def snapshot_all(with_drivers=True, procs=None):
    import models_registry as MR
    t0 = time.time(); paths = []
    for m in MR.MODELS:
        out = f"{ROOT}/data/out" if m["default"] else f"{ROOT}/data/out/m/{m['id']}"
        paths.append(snapshot(m["id"], out, with_drivers, procs))
    print("moves: snapshots", [os.path.relpath(p, ROOT) for p in paths], f"{time.time()-t0:.0f}s"); return paths

if __name__ == "__main__":
    snapshot_all(with_drivers="--no-drivers" not in sys.argv)
