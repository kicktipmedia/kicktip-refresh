"""Single-game what-ifs: for every remaining game and each outcome (home wins / away wins) rerun the SAME simulator (src/sim.py) with that game forced,
and write compact static JSON under data/out/whatif/.
  index.json       teams (index = simulator team index; 138 = FCS), metrics, baseline per team, game list (id, week, h, a, ...), shard map
  w<week>.json     {game_id: {"h": [[team, ccg, title, cfp12, bye], ...], "a": [...]}}   "h" = home team wins, "a" = away team wins
Values are integer per-mille (0..1000). Only teams whose chance moves by >= MIN_MOVE per-mille on any metric (plus both teams in the game) are listed;
an unlisted team is unchanged within MIN_MOVE of its baseline.
Forced runs use the SAME seed as the baseline run (common random numbers), so differences are far less noisy than the levels themselves.
Optional step in run_all.py:  python3 src/run_all.py --whatif   (or run this file directly).  ~8 CPU cores: about 3 minutes at 6000 seasons."""
import json, os, sys, time, multiprocessing as mp, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim

ROOT = sim.ROOT; OUTDIR = f"{ROOT}/data/out/whatif"
METRICS = ["ccg", "title", "cfp12", "bye"]
MIN_MOVE = 3        # per-mille (0.3 percentage points)

def metrics(R, permille=True):
    S = R["S"]; N = R["N"]; n = S.n
    ccg = np.zeros(n); title = np.zeros(n)
    for c in sim.CONFS:
        ccg += R["ccg_in"][c].mean(axis=0)
        ch = R["champ"][c]; ch = ch[ch >= 0]
        title += np.bincount(ch, minlength=n) / N
    out = np.stack([ccg, title, R["cfp_site"].mean(axis=0), R["bye"].mean(axis=0)], axis=1)
    out = out[: n - 1]                                          # drop the FCS pseudo-team (last index)
    return np.rint(out * 1000).astype(int) if permille else out

_S = {}
def _work(args):
    N, seed, gid, outcome = args[:4]; model = args[4] if len(args) > 4 else "default"
    if model not in _S: _S[model] = sim.Season(model)
    R = sim.run(N, seed, forced={gid: outcome}, S=_S[model])
    return gid, outcome, metrics(R)

def rows(base, m, g):
    d = np.abs(m - base).max(axis=1); keep = set(np.nonzero(d >= MIN_MOVE)[0].tolist()) | {t for t in (g["h"], g["a"]) if t < len(base)}
    return [[int(t)] + [int(v) for v in m[t]] for t in sorted(keep)]

def build(N=6000, seed=2026, procs=None, outdir=None, only=None, model="default"):
    """model="default": the shipped calibrated-MSM shards (sim.DEFAULT_MODEL), same format and location as before (data/out/whatif). model="raw": MSM v3 as before the
    calibration build, written to data/out/whatif-models/raw (comparison only). Any other id: that model file, with extra keys model, model_label in index.json."""
    model = "default" if model is None else model
    outdir = outdir or (OUTDIR if model in ("default", None) else f"{ROOT}/data/out/whatif-models/{model}")
    t0 = time.time(); S = sim.Season(model); os.makedirs(outdir, exist_ok=True)
    base = metrics(sim.run(N, seed, S=S))
    games = S.rem if only is None else [g for g in S.rem if g["id"] in only]
    jobs = [(N, seed, g["id"], o, model) for g in games for o in (1, 0)]
    with mp.Pool(procs or min(8, os.cpu_count() or 1)) as pool: res = pool.map(_work, jobs, chunksize=4)
    got = {(gid, o): m for gid, o, m in res}
    shards = {}; gl = []
    for g in games:
        e = {"h": rows(base, got[(g["id"], 1)], g), "a": rows(base, got[(g["id"], 0)], g)}
        shards.setdefault(g["week"], {})[g["id"]] = e
        gl.append(dict(id=g["id"], week=g["week"], h=int(g["h"]), a=int(g["a"]), neutral=bool(g["neutral"]),
                       p_home=int(round(1000 / (1 + np.exp(-(S.s_g[g["h"]] - S.s_g[g["a"]] + (0 if g["neutral"] else S.hfa_g)) / S.SIG_g))))))
    for wk, d in shards.items(): json.dump(d, open(f"{outdir}/w{wk}.json", "w"), separators=(",", ":"))
    names = [S.name.get(t, "FCS opponent") for t in range(S.n)]
    idx = dict(label="Single-game what-ifs from the KickTip model (simulation analysis, not betting advice). Values are per-mille.",
               as_of=__import__("export_web").sim_as_of(), seasons=N, seed=seed, min_move_permille=MIN_MOVE, metrics=METRICS,
               team_names=names, baseline=base.tolist(), games=gl, shards={str(w): f"w{w}.json" for w in sorted(shards)})
    import models_registry as MR
    mid = S.model; idx["model"] = mid; idx["model_label"] = MR.BY_ID[mid]["name"] if mid in MR.BY_ID else mid      # as_of above is already the shared sim_as_of() stamp
    json.dump(idx, open(f"{outdir}/index.json", "w"), separators=(",", ":"))
    size = sum(os.path.getsize(f"{outdir}/{f}") for f in os.listdir(outdir))
    print(f"whatif: {len(games)} games x 2 outcomes, {N} seasons each, {size/1024:.0f} KB total, {time.time()-t0:.0f}s")
    return idx

if __name__ == "__main__":
    import argparse; ap = argparse.ArgumentParser(); ap.add_argument("--seasons", type=int, default=6000); ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--procs", type=int, default=None); ap.add_argument("--model", default="default"); a = ap.parse_args(); build(a.seasons, a.seed, a.procs, model=a.model)
