"""MSM rating model v3, vendored from /workspace/msm-rankings/rank_v3.py (copied 2026-10-23) and refactored into a function.
Same formulas, same constants. Differences from the original script: no network calls (reads data/store/games_rated.json), no CSV/audit writing,
and it also returns the strength vector, home-field term and win-probability scale that the simulator needs.
Conference data is NOT used by the rating (conference-blind), exactly as in the original."""
import json, math, os, datetime as dt
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIDGE = 0.3; K = 28.0; S = 14.0; GARBAGE = 25; REC_MIN = 0.75; H2H_GAP = 1.0
W = {"resume": 0.60, "control": 0.25, "eff": 0.15}; W_SOR = 0.7; W_COLLEY = 0.3; BENCH_RANK = 25
FCS = "FCS"

def load_games():
    return sorted(json.load(open(f"{ROOT}/data/store/games_rated.json")), key=lambda g: g["date"])

def fit(G=None, conf=None):
    G = G or load_games()
    conf = conf or json.load(open(f"{ROOT}/data/ref/conf_2026.json"))
    fbs = {v["id"]: k for k, v in conf.items()}
    key = lambda i: i if i in fbs else FCS
    teams = sorted(fbs) + [FCS]; ix = {t: k for k, t in enumerate(teams)}; n = len(teams)
    D = lambda s: dt.date.fromisoformat(s)
    dates = sorted(set(g["date"] for g in G)); d0, d1 = dates[0], dates[-1]; span = max(1, (D(d1) - D(d0)).days)
    for g in G: g["w"] = REC_MIN + (1 - REC_MIN) * (D(g["date"]) - D(d0)).days / span
    f = lambda m: math.copysign(K * (1 - math.exp(-abs(m) / S)), m)
    def control(g):
        fin = g["hs"] - g["as_"]; q = g.get("q3")
        if q is None: return f(fin)
        q3m = q[0] - q[1]
        if abs(q3m) >= GARBAGE and (q3m > 0) == (fin > 0): fin = q3m
        return 0.5 * f(q3m) + 0.5 * f(fin)
    def wridge(rows, y, w, free=1):
        X = np.array(rows); y = np.array(y); Wt = np.array(w); P = np.eye(X.shape[1]) * RIDGE
        for k in range(free): P[-1 - k, -1 - k] = 0
        return np.linalg.solve(X.T @ (X * Wt[:, None]) + P, X.T @ (Wt * y))
    R = []; Y = []; Wg = []
    for g in G:
        r = np.zeros(n + 1); r[ix[key(g["home"])]] += 1; r[ix[key(g["away"])]] -= 1; r[n] = 0 if g["neutral"] else 1
        R.append(r); Y.append(control(g)); Wg.append(g["w"])
    bm = wridge(R, Y, Wg); strength = bm[:n]; hfa = bm[n]
    diff = np.array([strength[ix[key(g["home"])]] - strength[ix[key(g["away"])]] + (0 if g["neutral"] else hfa) for g in G]); win = np.array([g["hs"] > g["as_"] for g in G])
    def ll(s):
        p = 1 / (1 + np.exp(-diff / s)); p = np.clip(p, 1e-6, 1 - 1e-6); return np.sum(win * np.log(p) + (~win) * np.log(1 - p))
    SIG = float(max(np.arange(2, 30, 0.25), key=ll))
    F = [ix[t] for t in fbs]
    bench = sorted(strength[F], reverse=True)[BENCH_RANK - 1]
    sor = {t: 0.0 for t in fbs}; rec = {t: [0, 0] for t in fbs}; h2h = {}
    for g in G:
        for t, o, won, side in ((g["home"], g["away"], g["hs"] > g["as_"], 1), (g["away"], g["home"], g["as_"] > g["hs"], -1)):
            if t not in fbs: continue
            edge = 0 if g["neutral"] else side * hfa
            p = 1 / (1 + math.exp(-(bench - strength[ix[key(o)]] + edge) / SIG))
            sor[t] += (1 if won else 0) - p; rec[t][0 if won else 1] += 1
            if won: h2h[(t, o)] = h2h.get((t, o), 0) + 1
    C = 2 * np.eye(n); b = np.ones(n)
    for g in G:
        h, a = ix[key(g["home"])], ix[key(g["away"])]
        if h == a: continue
        C[h, h] += 1; C[a, a] += 1; C[h, a] -= 1; C[a, h] -= 1
        w_, l_ = (h, a) if g["hs"] > g["as_"] else (a, h); b[w_] += .5; b[l_] -= .5
    colley = np.linalg.solve(C, b)
    def adj(statfn):
        R = []; Y = []; Wt = []
        for g in G:
            bx = g.get("box", {})
            for o, d, home in ((g["home"], g["away"], 1), (g["away"], g["home"], -1)):
                v = statfn(g, o, bx)
                if v is None: continue
                r = np.zeros(2 * n + 2); r[ix[key(o)]] = 1; r[n + ix[key(d)]] = -1; r[2 * n] = 0 if g["neutral"] else home; r[2 * n + 1] = 1
                R.append(r); Y.append(v); Wt.append(g["w"])
        bb = wridge(R, Y, Wt, 2); return bb[:n] + bb[n:2 * n]
    ypp = lambda g, o, bx: bx[o]["yds"] / bx[o]["plays"] if o in bx and bx[o]["plays"] > 20 else None
    ppd = lambda g, o, bx: (g["hs"] if o == g["home"] else g["as_"]) / bx[o]["drives"] if o in bx and bx[o].get("drives", 0) >= 5 else None
    zf = lambda v: (v - v[F].mean()) / v[F].std()
    eff = (zf(adj(ypp)) + zf(adj(ppd))) / 2
    sor_v = np.zeros(n)
    for t in fbs: sor_v[ix[t]] = sor[t]
    resume = W_SOR * zf(sor_v) + W_COLLEY * zf(colley)
    resume_sd = float(((resume - resume[F].mean()) ).std()) if False else float(resume[F].std())
    comp = W["resume"] * zf(resume) + W["control"] * zf(strength) + W["eff"] * zf(eff)
    rating = comp * 10 + 50
    order = sorted(fbs, key=lambda t: -rating[ix[t]])
    for _ in range(3):   # head-to-head swap of near-tied neighbours (rank only; ratings unchanged)
        for k in range(len(order) - 1):
            a, b_ = order[k], order[k + 1]
            if rating[ix[a]] - rating[ix[b_]] <= H2H_GAP and h2h.get((b_, a), 0) > h2h.get((a, b_), 0): order[k], order[k + 1] = b_, a
    return dict(fbs=fbs, teams=teams, ix=ix, n=n, strength=strength, hfa=float(hfa), sigma=SIG, bench=float(bench), rating=rating, order=order,
                sor=sor_v, colley=colley, resume_sd=resume_sd, sor_sd=float(sor_v[F].std()), colley_sd=float(colley[F].std()), rec=rec, games=G, n_games=len(G), F=F)

if __name__ == "__main__":
    m = fit()
    print("games", m["n_games"], "hfa %.2f sigma %.2f bench %.2f" % (m["hfa"], m["sigma"], m["bench"]))
    for i, t in enumerate(m["order"][:10], 1): print(i, m["fbs"][t], round(m["rating"][m["ix"][t]], 1))
