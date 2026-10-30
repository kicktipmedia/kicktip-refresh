"""Check the simulator's linearised rating update: fit MSM on games up to a cutoff, apply the update with the ACTUAL later results,
compare with the real full refit. Reports rank-order agreement and error in rating points."""
import sys, os, copy, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import ratings
sig = lambda x: 1 / (1 + np.exp(-x))
G = ratings.load_games(); dates = sorted(set(g["date"] for g in G))
for back in (7, 14):
    cut = dates[-1]; import datetime as dt
    cut = (dt.date.fromisoformat(dates[-1]) - dt.timedelta(days=back)).isoformat()
    base = [copy.deepcopy(g) for g in G if g["date"] <= cut]; later = [g for g in G if g["date"] > cut]
    a = ratings.fit(base); full = ratings.fit(copy.deepcopy(G)); ix = a["ix"]; fbs = a["fbs"]
    s = np.array(a["strength"]); n = a["n"]; col = np.array(a["colley"]); cg = np.zeros(n)
    for g in base:
        for t in (g["home"], g["away"]): cg[ix[t if t in fbs else "FCS"]] += 1
    dsor = np.zeros(n); dcol = np.zeros(n)
    for g in later:
        h = ix[g["home"] if g["home"] in fbs else "FCS"]; aw = ix[g["away"] if g["away"] in fbs else "FCS"]
        hw = g["hs"] > g["as_"]
        for t, o, win, side in ((h, aw, hw, 1), (aw, h, not hw, -1)):
            dsor[t] += win - sig((a["bench"] - s[o] + (0 if g["neutral"] else side * a["hfa"])) / a["sigma"])
            dcol[t] += ((float(win) - 0.5) + col[o] - col[t]) / (3 + cg[t])
    r0 = np.array(a["rating"]); r1 = r0 + 10 * 0.6 / a["resume_sd"] * (0.7 * dsor / a["sor_sd"] + 0.3 * dcol / a["colley_sd"])
    rf = np.array(full["rating"]); F = a["F"]
    played = np.array([dsor[t] != 0 or dcol[t] != 0 for t in F])
    err = (r1[F] - rf[F]); err0 = (r0[F] - rf[F])
    rank = lambda v: np.argsort(np.argsort(-v[F]))
    top25 = set(np.argsort(-rf[F])[:25]); top25a = set(np.argsort(-r1[F])[:25]); top25b = set(np.argsort(-r0[F])[:25])
    print(f"hold-out last {back} days: {len(later)} games; RMSE no-update {np.sqrt((err0**2).mean()):.2f}, with update {np.sqrt((err**2).mean()):.2f} rating pts; "
          f"teams with games: {np.sqrt((err[played]**2).mean()):.2f} vs {np.sqrt((err0[played]**2).mean()):.2f}; top-25 overlap update {len(top25 & top25a)}/25 vs no-update {len(top25 & top25b)}/25; spearman-ish rank corr "
          f"{np.corrcoef(rank(r1), rank(rf))[0,1]:.3f}")
