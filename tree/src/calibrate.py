#!/usr/bin/env python3
"""KickTip v6a model fit. Fits the walk-forward models on every final game to date and writes the model files that sim.Season() uses for GAME win probabilities
(games, title-game/CFP/playoff odds, what-if shards, browser bundle). One file per model in src/models_registry.py:
  data/out/models/blend.json  DEFAULT = Phase 0 'blend': log-odds stack of the ridge MSM, ridge efficiency, Elo-style and last-season prior strengths (ridge-regularised, weights fitted only on earlier out-of-sample rows)
  data/out/models/elo.json    Elo-style (frozen parameters in data/ref/calibration_tuning.json) with the same recalibration ('elo_cal')
  data/out/models/eff.json    Efficiency (ridge chosen out of sample) with the same recalibration ('eff_cal')
Each file: p(home wins) = sigmoid(s[h] - s[a] + hfa*home), sigma = 1 (strengths already in logit units), stamped with n_games and the games_rated.json sha12.
sim.Season refuses a file whose stamp does not match the data (fail closed), so run this after EVERY refresh and before sim/whatif/export/build (run_all.py does).
Needs data/store/prior + data/cache/prior (2021-2025 seasons, public ESPN scores/status stored in the tree) and data/ref/calibration_tuning.json (frozen Elo parameters + stack alpha).
FINAL assert: kt_models.load_all hard-asserts STATUS_FINAL for all 2021-2025 games; a 2026 row in games_rated.json whose schedule row is not final is dropped and counted (printed as 'dropped').
About 15 seconds. No network, no private/ files.
Usage: python3 src/calibrate.py"""
import sys, os, json, hashlib, time, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.dont_write_bytecode = True
import kt_models as M, wf, ratings
ROOT = M.ROOT; MOD = f"{ROOT}/data/out/models"
import models_registry as MR
MAP = {m["id"]: m["component"] for m in MR.MODELS}   # blend (default), elo, eff (no MSM-rating model: not selectable)

def main():
    t0 = time.time(); tuning = json.load(open(f"{ROOT}/data/ref/calibration_tuning.json"))
    games, dropped = M.load_all(strict_live=False); rows, states = M.build(games, tuning["elo"])
    W = wf.WF(rows, tuning["elo"]["hfa"], tuning["alpha"]); now = max(states); st = states[now]
    assert now[0] == 2026 and not W.by.get(now), "virtual current block expected"
    fit = W.fit(rows); vec = W.vectors(fit, st); os.makedirs(MOD, exist_ok=True)
    m = ratings.fit(); assert m["teams"] == M.TEAMS, "team index mismatch"
    sha = hashlib.sha256(open(f"{ROOT}/data/store/games_rated.json", "rb").read()).hexdigest()[:12]
    keep = {k: (fit[k] if not hasattr(fit[k], "tolist") else fit[k].tolist()) for k in ("n_train", "home_rate", "msm_lambda", "eff_lambda", "msm_cal_w", "b3_w", "eff_cal_w", "elo_cal_w", "stack_w_std") if k in fit}
    for mid, comp in MAP.items():
        s, hb = vec[comp]
        d = dict(id=mid, component=comp, teams=m["teams"], s=[round(float(x), 6) for x in s], hfa=round(float(hb), 6), sigma=1.0, n_games=m["n_games"], games_sha12=sha,
                 state=list(now), cutoff=st["cut"], fit=keep, fitted_mt=dt.datetime.now(__import__("zoneinfo").ZoneInfo("America/Denver")).strftime("%Y-%m-%d %H:%M MT"))
        json.dump(d, open(f"{MOD}/{mid}.json", "w"), separators=(",", ":"))
        print(mid, comp, "hfa %.3f" % hb, "sd(s FBS) %.3f" % np.std(np.array(s)[M.FIDX]), "FCS slot %.3f" % float(np.array(s)[M.IX["FCS"]]))
    print("calibrate: dropped", dropped, "n_games", m["n_games"], "games_sha12", sha, "train rows", fit["n_train"], "%.0fs" % (time.time() - t0))

if __name__ == "__main__": main()
