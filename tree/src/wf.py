"""Walk-forward (expanding window) calibration, ridge selection and stacking on top of kt_models rows; plus metrics and paired bootstrap.
Every prediction for the games of cutoff c uses only rows of strictly earlier cutoffs (earlier blocks of the season and all earlier seasons)."""
import math, numpy as np, collections
from kt_models import LAMBDAS, sig

CL = (0.02, 0.98); MIN_TRAIN = 300
STACK_NAMES = ["msm", "eff", "elo", "prior", "msm_f", "eff_f", "prior_f"]

def fit_logit(X, y, pen, iters=60):
    """Newton-Raphson logistic regression, no intercept column added; pen = per-column L2 penalty (0 = unpenalized)."""
    d = X.shape[1]; w = np.zeros(d); pen = np.asarray(pen, float)
    for _ in range(iters):
        p = sig(X @ w); g = X.T @ (p - y) + pen * w; H = (X.T * (p * (1 - p))) @ X + np.diag(pen) + 1e-9 * np.eye(d)
        step = np.linalg.solve(H, g); w -= step
        if np.abs(step).max() < 1e-8: break
    return w

def nll(p, y, clip=CL):
    p = np.clip(p, *clip); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

def _col(rows, name): return np.array([r[name] for r in rows], float)

class WF:
    def __init__(self, rows, elo_hfa, alpha):
        self.rows = rows; self.elo_hfa = elo_hfa; self.alpha = alpha
        self.cuts = sorted({(r["season"], r["k"]) for r in rows})
        self.by = collections.defaultdict(list)
        for r in rows: self.by[(r["season"], r["k"])].append(r)
        self.fits = {}

    # ---- one fit on training rows (strictly earlier cutoffs); used for scoring AND for the current-state team vectors
    def fit(self, tr):
        ytr = _col(tr, "y"); htr = _col(tr, "home"); fit = {"n_train": len(tr)}
        fit["home_rate"] = float(ytr[htr == 1].mean())
        for comp in ("msm", "eff"):
            best = None
            for l in LAMBDAS:
                X = np.c_[_col(tr, f"{comp}{l}"), htr]; w = fit_logit(X, ytr, [1e-3, 0]); L = nll(sig(X @ w), ytr, (1e-6, 1 - 1e-6))
                if best is None or L < best[0] - 1e-12: best = (L, l, w)
            fit[f"{comp}_lambda"] = best[1]; fit[f"{comp}_cal_w"] = best[2].tolist()
        X = np.c_[_col(tr, "msm0.3"), htr]; fit["b3_w"] = fit_logit(X, ytr, [1e-3, 0]).tolist()   # B3: shipped lambda 0.3, only temperature/home recalibrated
        X = np.c_[_col(tr, "elo"), htr]; fit["elo_cal_w"] = fit_logit(X, ytr, [1e-3, 0]).tolist()
        Ftr = self._feats(tr, fit); sd = Ftr.std(axis=0); sd[sd < 1e-9] = 1.0
        fit["stack_w_std"] = fit_logit(np.c_[Ftr / sd, htr], ytr, [self.alpha] * Ftr.shape[1] + [0]).tolist(); fit["stack_sd"] = sd.tolist(); fit["stack_alpha"] = self.alpha
        return fit

    @staticmethod
    def _feats(rs, fit):
        lm, le = fit["msm_lambda"], fit["eff_lambda"]
        return np.c_[_col(rs, f"msm{lm}"), _col(rs, f"eff{le}"), _col(rs, "elo"), _col(rs, "prior"), _col(rs, f"msm_f{lm}"), _col(rs, f"eff_f{le}"), _col(rs, "prior_f")]

    def predict(self, fit, te, tr_home_rate=None):
        hte = _col(te, "home"); out = {}
        out["b1_home"] = np.where(hte == 1, fit["home_rate"], 0.5)
        out["b2_msm_raw"] = np.array([r["pmsm_raw0.3"] for r in te]); out["b4_elo_untuned"] = np.array([r["p_b4"] for r in te])
        out["msm_cal"] = sig(np.c_[_col(te, f"msm{fit['msm_lambda']}"), hte] @ np.array(fit["msm_cal_w"]))
        out["eff_cal"] = sig(np.c_[_col(te, f"eff{fit['eff_lambda']}"), hte] @ np.array(fit["eff_cal_w"]))
        out["b3_msm_wf_temp"] = sig(np.c_[_col(te, "msm0.3"), hte] @ np.array(fit["b3_w"]))
        out["elo_cal"] = sig(np.c_[_col(te, "elo"), hte] @ np.array(fit["elo_cal_w"])); out["elo_raw"] = sig(_col(te, "elo") + self.elo_hfa * hte)
        out["blend"] = sig(np.c_[self._feats(te, fit) / np.array(fit["stack_sd"]), hte] @ np.array(fit["stack_w_std"]))
        return out

    def vectors(self, fit, st):
        """Team strength vectors at cutoff state st for each model, in the form p(home wins) = sigmoid(s[h] - s[a] + hb*home). Index = kt_models.TEAMS."""
        v = {}; lm, le = fit["msm_lambda"], fit["eff_lambda"]
        v["b2_msm_raw"] = (st["msm"][0.3] / st["sigma"][0.3], st["hfa"][0.3] / st["sigma"][0.3])
        a, b = fit["b3_w"]; v["b3_msm_wf_temp"] = (a * st["msm"][0.3], b)
        a, b = fit["msm_cal_w"]; v["msm_cal"] = (a * st["msm"][lm], b)
        a, b = fit["eff_cal_w"]; v["eff_cal"] = (a * st["eff"][le], b)
        a, b = fit["elo_cal_w"]; v["elo_cal"] = (a * st["elo"], b); v["elo_raw"] = (st["elo"].copy(), self.elo_hfa)
        f = st["f"]; phi = np.c_[st["msm"][lm], st["eff"][le], st["elo"], st["prior"], st["msm"][lm] * f, st["eff"][le] * f, st["prior"] * f]
        w = np.array(fit["stack_w_std"]); sd = np.array(fit["stack_sd"]); v["blend"] = ((phi / sd) @ w[:-1], float(w[-1]))
        return v

    def run(self, only_seasons=None, quiet=True):
        out = collections.defaultdict(list); meta = []
        for ci, c in enumerate(self.cuts):
            if only_seasons and c[0] not in only_seasons: continue
            tr = [r for cc in self.cuts[:ci] for r in self.by[cc]]
            if len(tr) < MIN_TRAIN: continue
            te = self.by[c]; fit = self.fit(tr)
            for m, p in self.predict(fit, te).items(): out[m] += list(p)
            meta += [(r["id"], r["season"], r["k"], r["date"], r["y"], r["home"], r["fcs"], r["margin"]) for r in te]
            self.fits[c] = fit
        out = {k: np.array(v) for k, v in out.items()}
        m = dict(zip(["id", "season", "k", "date", "y", "home", "fcs", "margin"], zip(*meta))) if meta else {}
        return out, {k: np.array(v) for k, v in m.items()}

# ---------------------------------------------------------------- metrics
def logloss(p, y, clip=CL): p = np.clip(p, *clip); return -(y * np.log(p) + (1 - y) * np.log(1 - p))

def calib_slope(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6); L = np.log(p / (1 - p)); w = fit_logit(np.c_[L, np.ones(len(L))], y, [0, 0]); return float(w[0]), float(w[1])

def summarize(p, y):
    s, i = calib_slope(p, y)
    return dict(n=int(len(y)), logloss_clip=float(logloss(p, y).mean()), logloss_unclip=float(logloss(p, y, (1e-6, 1 - 1e-6)).mean()), brier=float(np.mean((p - y) ** 2)),
                pick_rate=float(np.mean((p > .5) == (y == 1))), slope=s, intercept=i)

def quantile_bins(p, y, nb=8):
    o = np.argsort(p); out = []
    for ch in np.array_split(o, nb):
        out.append(dict(n=int(len(ch)), pred=float(p[ch].mean()), obs=float(y[ch].mean()), lo=float(p[ch].min()), hi=float(p[ch].max())))
    return out

def conf_picks(p, y, thr=0.90):
    c = np.maximum(p, 1 - p) >= thr; win = ((p > .5) == (y == 1))
    return dict(n=int(c.sum()), win_rate=float(win[c].mean()) if c.sum() else None, mean_conf=float(np.maximum(p, 1 - p)[c].mean()) if c.sum() else None)

def paired_boot(la, lb, B=5000, seed=20261024, groups=None):
    """mean(la - lb) with 95% CI; la, lb per-game losses. groups: optional cluster labels (resample clusters)."""
    rng = np.random.default_rng(seed); d = la - lb; n = len(d)
    if groups is None:
        idx = rng.integers(0, n, size=(B, n)); bs = d[idx].mean(axis=1)
    else:
        u, inv = np.unique(groups, return_inverse=True); sums = np.bincount(inv, d); cnt = np.bincount(inv)
        ci = rng.integers(0, len(u), size=(B, len(u))); bs = sums[ci].sum(axis=1) / cnt[ci].sum(axis=1)
    return dict(mean=float(d.mean()), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)))
