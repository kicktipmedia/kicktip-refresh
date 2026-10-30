#!/usr/bin/env python3
"""v6a engine checks (adapted from cal1's cal_test): per-model stamps for the three offered models (blend default, Elo-style, Efficiency), a FINAL-assert test for kt_models.load_all; monotone/sanity of the game probabilities (blend), regression of the 'raw' path against the live b9d outputs, favourite/spread agreement. Original docstring: calibrated-MSM stamp, monotone/sanity of the game probabilities, regression of the 'raw' path against the live b9d outputs, favourite/spread agreement.
Usage: python3 tests/cal_test.py [--regress]   (--regress re-simulates the raw model, ~1 min, and compares it with before/sim_teams.json)"""
import sys, os, json, hashlib
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src"); sys.dont_write_bytecode = True
import sim
fails = []
def ok(name, c):
    print(("PASS " if c else "FAIL ") + name)
    if not c: fails.append(name)
sig = lambda x: 1 / (1 + np.exp(-x))
S = sim.Season("default"); R = sim.Season("raw")
mm = json.load(open(f"{ROOT}/data/out/models/blend.json"))
for _m in ("blend", "elo", "eff"):
    _j = json.load(open(f"{ROOT}/data/out/models/{_m}.json")); ok(f"model file {_m}: stamps match games_rated.json", _j["games_sha12"] == sim.games_sha12() and _j["n_games"] == S.m["n_games"])
ok("no msm model file exists (MSM rating is not offered as a model)", not os.path.exists(f"{ROOT}/data/out/models/msm.json") and not os.path.exists(f"{ROOT}/data/out/m/msm"))
ok("default model is the blend and its stamp matches games_rated.json", S.model == "blend" and mm["games_sha12"] == sim.games_sha12() and mm["n_games"] == S.m["n_games"])
ok("model file: sigma 1, finite strengths, home term in (0, 1.5) logit", mm["sigma"] == 1.0 and np.isfinite(mm["s"]).all() and 0 < mm["hfa"] < 1.5)
ok("raw path is MSM v3 unchanged (s, hfa, sigma are the fitted values)", R.model is None and R.s_g is R.s and R.hfa_g == R.hfa and R.SIG_g == R.SIG)
# FINAL assert (QA non-blocking item): kt_models.load_all must hard-fail on a game that is not STATUS_FINAL/completed or is missing from the cached scoreboards
import kt_models as KM
_orig = KM._prior_status
try:
    ok("load_all passes on the real cached scoreboards (positive control)", len(KM.load_all(strict_live=False)[0]) > 1000 if isinstance(KM.load_all(strict_live=False), tuple) else True)
    def _notfinal(y, root):
        st = _orig(y, root); k = next(iter(st)); st[k] = ("STATUS_POSTPONED", False); return st
    KM._prior_status = _notfinal
    try: KM.load_all(strict_live=False); _r = False
    except AssertionError as e: _r = "not STATUS_FINAL" in str(e)
    ok("load_all raises AssertionError when a prior-season game is not STATUS_FINAL", _r)
    def _missing(y, root):
        st = _orig(y, root); st.pop(next(iter(st))); return st
    KM._prior_status = _missing
    try: KM.load_all(strict_live=False); _r = False
    except AssertionError as e: _r = "not STATUS_FINAL" in str(e)
    ok("load_all raises AssertionError when a prior-season game is missing from the cached scoreboards", _r)
finally:
    KM._prior_status = _orig
# stale file must be refused
import copy, tempfile
bad = dict(mm); bad["n_games"] = mm["n_games"] + 1
p = f"{ROOT}/data/out/models/_stale_test.json"; json.dump(bad, open(p, "w"))
try: sim.Season("_stale_test"); stale_refused = False
except AssertionError: stale_refused = True
os.remove(p); ok("stale calibration file is refused (fail closed)", stale_refused)
# monotone + symmetry on the calibrated basis
F = [t for t in range(S.n) if t != S.FCS]; rng = np.random.default_rng(1)
pairs = [(int(rng.choice(F)), int(rng.choice(F))) for _ in range(2000)]; pairs = [(h, a) for h, a in pairs if h != a]
pn = lambda h, a, neu: sig((S.s_g[h] - S.s_g[a] + (0 if neu else S.hfa_g)) / S.SIG_g)
ok("neutral-site symmetry p(h,a)+p(a,h)=1", all(abs(pn(h, a, True) + pn(a, h, True) - 1) < 1e-12 for h, a in pairs))
ok("home field helps: p(home) > p(neutral) for every pair", all(pn(h, a, False) > pn(h, a, True) for h, a in pairs))
d = np.array([S.s_g[h] - S.s_g[a] for h, a in pairs]); pp = np.array([pn(h, a, False) for h, a in pairs]); o = np.argsort(d)
ok("probability is monotone increasing in the strength difference", (np.diff(pp[o]) >= -1e-12).all())
order_s = np.argsort(-S.s_g[F]); ok("better strength => higher win prob vs a fixed opponent", all(pn(F[order_s[i]], F[order_s[-1]], True) >= pn(F[order_s[i + 1]], F[order_s[-1]], True) for i in range(len(F) - 2)))
# published game file
G = json.load(open(f"{ROOT}/data/out/sim_games.json"))["games"]
pr = np.array([g["model_home_win_prob"] for g in G]); sp = np.array([g["model_spread_home"] for g in G])
ok("all published win probabilities are in [0.001, 0.999]", ((pr >= 0.001) & (pr <= 0.999)).all())
ok("favourite agrees with the model line (spread<0 <=> p>0.5) in every game with a nonzero line", all((s_ < 0) == (p_ > 0.5) for p_, s_ in zip(pr, sp) if s_ != 0 and p_ != 0.5))
NIX = {v: k for k, v in S.name.items()}
Gr = [g for g in G if g["home"] != "FCS opponent" and g["away"] != "FCS opponent"]
ok("published probabilities match the engine (sim_games vs Season)", all(abs(g["model_home_win_prob"] - round(float(pn(NIX[g["home"]], NIX[g["away"]], g["neutral"])), 3)) < 1e-9 for g in Gr))
rawp = np.array([sig((R.s[g["h"]] - R.s[g["a"]] + (0 if g["neutral"] else R.hfa)) / R.SIG) for g in S.rem]); calp = np.array([pn(g["h"], g["a"], g["neutral"]) for g in S.rem])
ok("blend is less extreme than raw MSM on average", np.maximum(calp, 1 - calp).mean() < np.maximum(rawp, 1 - rawp).mean() - 0.05)
ok("ranking of games broadly preserved (Spearman raw vs blend > 0.8; the blend adds last season's strength and efficiency, so not 0.97 as for cal1)", np.corrcoef(np.argsort(np.argsort(rawp)), np.argsort(np.argsort(calp)))[0, 1] > 0.8)
_fl = [(r, c) for r, c in zip(rawp, calp) if max(r, 1 - r) >= 0.70 and (c > 0.5) != (r > 0.5)]; print("   (info: %d of %d games flip the favourite vs raw MSM at raw >= 70%%: the blend lands within 35-65%% in all of them)" % (len(_fl), len(rawp)))
ok("blend flips a raw >= 70% favourite only to a near toss-up (35-65%), and in under 3% of games", all(0.35 <= c <= 0.65 for r, c in _fl) and len(_fl) < 0.03 * len(rawp))
T = json.load(open(f"{ROOT}/data/out/sim_teams.json"))["teams"]
ok("sim_teams: every chance in [0,1]; make-12 chances sum to about 12", all(0 <= t["p_cfp_12"] <= 1 and 0 <= t["p_cfp_bye"] <= t["p_cfp_12"] + 1e-9 for t in T) and 11.5 < sum(t["p_cfp_12"] for t in T) <= 12.01)
if "--regress" in sys.argv:
    bt = {t["team"]: t for t in json.load(open(f"{ROOT}/before/sim_teams.json"))["teams"]}
    Rr = sim.run(10000, 2026, S=R); S0 = Rr["S"]
    mism = [S0.name[t] for t in range(S0.n) if t != S0.FCS and abs(float(Rr["cfp_site"][:, t].mean()) - bt[S0.name[t]]["p_cfp_12"]) > 5e-5]
    ok("RAW path reproduces the b9d live make-12 numbers exactly (10,000 seasons, seed 2026)", not mism and len(bt) > 100)
    if mism: print("   mismatch:", mism[:5])
print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
