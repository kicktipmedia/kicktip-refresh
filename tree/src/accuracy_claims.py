#!/usr/bin/env python3
"""Every accuracy number on the method page, read from the frozen Phase 0 results (data/ref/phase0/metrics.json, season_metrics.json copied from /workspace/kicktip-v6/data/out/backtest,
FREEZE.json v2 alongside). Writes data/ref/accuracy_claims.json; build.py reads ONLY that file for accuracy text, so no number on the page is typed by hand.
Usage: python3 src/accuracy_claims.py"""
import json, hashlib, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = f"{ROOT}/data/ref/phase0"
m = json.load(open(f"{P}/metrics.json")); s = json.load(open(f"{P}/season_metrics.json"))
sha = lambda f: hashlib.sha256(open(f"{P}/{f}", "rb").read()).hexdigest()[:12]
A = m["sets"]["primary_all"]; F = m["sets"]["primary_fbs_fcs"]; ps = m["per_season"]; st = s["summary"]["static"]
bar = m["bar"]["blend"]; sl = [round(ps[y]["blend"]["slope"], 2) for y in ("2023", "2024", "2025", "2026")]
c = dict(
    source=dict(metrics_sha12=sha("metrics.json"), season_metrics_sha12=sha("season_metrics.json"), freeze_sha12=sha("FREEZE.json"), protocol_sha12=m["protocol_sha12"]),
    n=A["blend"]["n"], n_2026=ps["2026"]["blend"]["n"], seasons="2023, 2024 and 2025, plus part of 2026",
    ll_raw_unclipped=A["b2_msm_raw"]["logloss_unclip"], ci_blend_vs_best=[m["boot"]["blend minus elo_cal"]["iid"]["mean"], m["boot"]["blend minus elo_cal"]["iid"]["lo"], m["boot"]["blend minus elo_cal"]["iid"]["hi"]],
    ll=dict(raw=A["b2_msm_raw"]["logloss_clip"], blend=A["blend"]["logloss_clip"], msm=A["b3_msm_wf_temp"]["logloss_clip"], elo=A["elo_cal"]["logloss_clip"], eff=A["eff_cal"]["logloss_clip"], elo_untuned=A["b4_elo_untuned"]["logloss_clip"]),
    pick=dict(raw=A["b2_msm_raw"]["pick_rate"], blend=A["blend"]["pick_rate"], msm=A["b3_msm_wf_temp"]["pick_rate"], elo=A["elo_cal"]["pick_rate"], eff=A["eff_cal"]["pick_rate"]),
    slope=A["blend"]["slope"], slope_by_season=dict(zip(("2023", "2024", "2025", "2026"), sl)), slope_outside=[y for y, v in zip(("2023", "2024", "2025", "2026"), sl) if not .85 <= v <= 1.15],
    picks90=dict(n=bar["5_90pct_picks_win>=85%"]["all"]["n"], win=bar["5_90pct_picks_win>=85%"]["all"]["win"], n_fbs=bar["5_90pct_picks_win>=85%"]["fbs_fbs"]["n"], win_fbs=bar["5_90pct_picks_win>=85%"]["fbs_fbs"]["win"]),
    raw_picks90=dict(n=m["picks"]["b2_msm_raw"]["all"]["n"], win=m["picks"]["b2_msm_raw"]["all"]["win_rate"], conf=m["picks"]["b2_msm_raw"]["all"]["mean_conf"]),
    fcs=dict(n=F["blend"]["n"], blend=F["blend"]["logloss_clip"], elo=F["elo_cal"]["logloss_clip"], raw=F["b2_msm_raw"]["logloss_clip"]),
    make12=dict(brier={k: st[k]["cfp"]["brier"] for k in ("b2_msm_raw", "msm_cal", "elo_raw", "elo_cal", "eff_cal", "blend")}, rows=st["blend"]["cfp"]["n"], seasons="2024 and 2025", events=24),
    y26=dict(n=m["sets"]["current_2026_k6plus"]["blend"]["n"], blend_slope=m["sets"]["current_2026_k6plus"]["blend"]["slope"], msm_slope=m["sets"]["current_2026_k6plus"]["b3_msm_wf_temp"]["slope"],
             n4=m["sets"]["current_2026_k4plus"]["blend"]["n"], blend_slope4=m["sets"]["current_2026_k4plus"]["blend"]["slope"], msm_slope4=m["sets"]["current_2026_k4plus"]["b3_msm_wf_temp"]["slope"]),
    harness=dict(nsim=s["nsim"], cuts=s["cuts"], proxy="5 + 7 committee stand-in", seed=s["seed"]),
    pick_item6_diff_pts=bar["6_pick_rate_within_1pt_of_MSMv3"]["diff_pts"],
    ci_vs_raw=[bar["2_upper_CI(vs MSM v3 raw)<0"]["lo"], bar["2_upper_CI(vs MSM v3 raw)<0"]["hi"]],
)
json.dump(c, open(f"{ROOT}/data/ref/accuracy_claims.json", "w"), indent=1); print(json.dumps(c, indent=1)[:2500])
