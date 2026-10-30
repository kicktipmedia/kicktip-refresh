"""Writes BEFORE-AFTER.md: v6a default (KickTip blend) vs the MSM raw numbers live on b9d (before/), plus the two alternates (Elo-style, Efficiency). Same data snapshot. The raw MSM numbers are the INTERNAL before-comparison only; no MSM model is offered."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda p: json.load(open(p))
B = J(f"{ROOT}/before/sim_teams.json"); A = J(f"{ROOT}/data/out/sim_teams.json"); M = J(f"{ROOT}/data/out/m/elo/sim_teams.json"); N = J(f"{ROOT}/data/out/m/eff/sim_teams.json")
BG = J(f"{ROOT}/before/sim_games.json"); AG = J(f"{ROOT}/data/out/sim_games.json"); MG = J(f"{ROOT}/data/out/m/elo/sim_games.json"); NG = J(f"{ROOT}/data/out/m/eff/sim_games.json")
idx = lambda d: {t["team"]: t for t in d["teams"]}
b, a, m, e = idx(B), idx(A), idx(M), idx(N)
pc = lambda x: "-" if x is None else f"{x*100:.1f}%"
o = []
o.append(f"# BEFORE / AFTER, KickTip v6a (default = KickTip blend)\n\nSame data snapshot for every column: {A.get('as_of','')} (sim stamp; games_rated 534 final games), 10,000 seasons, seed {A['seed']}. BEFORE = what the deployed dom1 site shows, recomputed with the live code on the same newer data (the b9e/b9f refresh, ESPN 3:18 PM MT, 534 games), so only the model differs: raw MSM win probabilities. AFTER = v6a default (blend). Elo and Eff = the two alternates under 'More models'. There is no MSM model any more: the MSM rating lives inside the blend and drives the committee proxy. The page now deployed (dom1) carries the older 1:53 PM MT data, so its numbers differ slightly from the BEFORE column; the earlier cal1 fallback column was dropped because it was run on that older data.\n")
o.append("## Utah-area teams (FBS teams only; Weber State, Southern Utah and Utah Tech are FCS, so they are not site teams and have no page or simulated numbers)\n")
o.append("| Team | Make 12: before (raw) | v6a blend | Elo-style | Efficiency | Win conf: before | v6a blend | Bye: before | v6a blend | Exp wins: before | v6a blend |\n|---|---|---|---|---|---|---|---|---|---|---|")
for n in ("BYU Cougars", "Utah Utes", "Utah State Aggies"):
    o.append(f"| {n} | {pc(b[n]['p_cfp_12'])} | **{pc(a[n]['p_cfp_12'])}** | {pc(m[n]['p_cfp_12'])} | {pc(e[n]['p_cfp_12'])} | {pc(b[n]['p_conf_title'])} | **{pc(a[n]['p_conf_title'])}** | {pc(b[n]['p_cfp_bye'])} | **{pc(a[n]['p_cfp_bye'])}** | {b[n]['exp_wins']} | **{a[n]['exp_wins']}** |")
o.append("| Weber State, Southern Utah, Utah Tech | FCS: not simulated, no page. Their games vs FBS teams show only inside the FBS side's schedule as 'FCS opponent' with the model win chance for the FBS team (see sample games). | | | | | | | | | |")
o.append("\n## Top 10 nationally by chance to make the 12 (v6a blend order; before = raw MSM)\n")
o.append("| # | Team | v6a blend make-12 | v6a bye | Elo-style | Efficiency | Before (raw) | Before rank |\n|---|---|---|---|---|---|---|---|")
bo = sorted(b, key=lambda n: -b[n]['p_cfp_12']); brk = {n: i + 1 for i, n in enumerate(bo)}
for i, n in enumerate(sorted(a, key=lambda n: -a[n]['p_cfp_12'])[:10], 1):
    o.append(f"| {i} | {n} | **{pc(a[n]['p_cfp_12'])}** | {pc(a[n]['p_cfp_bye'])} | {pc(m[n]['p_cfp_12'])} | {pc(e[n]['p_cfp_12'])} | {pc(b[n]['p_cfp_12'])} | {brk[n]} |")
o.append("\nFor reference, the before top 10 (raw MSM): " + "; ".join(f"{n} {pc(b[n]['p_cfp_12'])}" for n in bo[:10]) + ".\n")
gb = {g['id']: g for g in BG['games']}; ga = {g['id']: g for g in AG['games']}; gm = {g['id']: g for g in MG['games']}; gn = {g['id']: g for g in NG['games']}
rows = [i for i in ga if ga[i].get('model_home_win_prob') is not None and i in gb and gb[i].get('model_home_win_prob') is not None]
def utah(i): return any(k in ga[i]['home'] + ga[i]['away'] for k in ("BYU", "Utah"))
pick = [i for i in rows if utah(i) and ga[i]['status'] == 'STATUS_SCHEDULED'][:4]
rest = [i for i in rows if i not in pick and ga[i]['status'] != 'STATUS_IN_PROGRESS']
rest.sort(key=lambda i: gb[i]['model_home_win_prob'] - ga[i]['model_home_win_prob'])
pick += rest[:3] + rest[-3:]
o.append("## 10 sample games (home win chance; model line = home spread, negative = home favored)\n")
o.append("| Game | Date | Before (raw MSM) | v6a blend | Elo-style | Efficiency | Before line | v6a line |\n|---|---|---|---|---|---|---|---|")
for i in pick:
    g = ga[i]; ln = lambda x: "-" if x is None else f"{x:+.1f}"
    o.append(f"| {g['away']} at {g['home']} | {g['date_utc'][:10]} | {pc(gb[i]['model_home_win_prob'])} | **{pc(g['model_home_win_prob'])}** | {pc(gm[i]['model_home_win_prob']) if i in gm else '-'} | {pc(gn[i]['model_home_win_prob']) if i in gn else '-'} | {ln(gb[i].get('model_spread_home'))} | {ln(g.get('model_spread_home'))} |")
sd = [(n, a[n]['p_cfp_12'] - b[n]['p_cfp_12']) for n in a]; sd.sort(key=lambda x: x[1])
o.append("\n## Biggest movers in make-12 chance (v6a blend minus before)\nDown: " + "; ".join(f"{n} {d*100:+.1f}" for n, d in sd[:8]) + "\n\nUp: " + "; ".join(f"{n} {d*100:+.1f}" for n, d in sd[-8:][::-1]) + "\n")
o.append("## Why numbers moved\n- Game win percentages: raw MSM was overconfident (calls of 90%+ won 83.2% of the time); the blend is walk-forward calibrated (90%+ calls won 95.5%, n=331), so heavy favorites drop and underdogs rise. Both effects flatten the simulated seasons, so near-certain outcomes (e.g. a 99% make-12) lose a few points and long shots gain.\n- The blend also uses last season's final strength as a prior; this is a likely reason a team that was strong last year (e.g. Georgia) reads higher than raw MSM, and a team with a thin 2026 record reads lower or higher accordingly.\n- Heavy favorites drop and underdogs rise, so some teams move a lot (see the mover lists above; data/ref/movers.json holds the numbers quoted on the method page: Utah 15.8% to 40.1%, BYU 95.2% to 88.8% on this data).\n- The committee proxy, the standings and the bracket field still come from the unchanged MSM composite rank (rank_now), for every model.\n")
open(f"{ROOT}/BEFORE-AFTER.md", "w").write("\n".join(o)); print("BEFORE-AFTER.md written", len(o))
