"""Method-page copy for the model section (v6a). Plain data in, HTML out; every number comes from data/ref/accuracy_claims.json (src/accuracy_claims.py) or the model registry.
No third-party rating names. Wording follows BUILD-SPEC 907ff03f7de6 ("KickTip's own version, inspired by ... rating systems") and QA's disclosure list."""
import html
E = html.escape
f3 = lambda x: f"{x:.3f}"; pc1 = lambda x: f"{100 * x:.1f}%"; f2 = lambda x: f"{x:.2f}"

def models_html(MR, games_rated):
    li = "".join(f'<li><b>{E(m["name"])}{" (default)" if m.get("default") else ""}.</b> {E(m["blurb"])}</li>' for m in MR.MODELS)
    return (f'<h2 id="models">The models</h2><p>KickTip can show its numbers from one of three models. The default is the <b>{E(MR.MODELS[0]["name"])}</b>. The model control at the top of each chances page lets you switch to another. '
            f'Your choice is remembered on this device until you change it or choose the default again. Every model is KickTip\'s own version, inspired by widely used rating systems, and every number on a page is an estimate.</p><ul>{li}</ul>'
            f'<p>Whichever model is selected drives the win probability of every game, the simulated seasons, and so the conference championship game, conference, playoff, first-round-bye and path numbers on that page. Two things do not change with the model: '
            f'the KickTip team rating below, which stands in for the selection committee (so the order of the "if the season ended today" bracket is the same under every model), and the market column. The MSM rating is one ingredient of the blend and drives that committee stand-in, but it is not offered as a model of its own.</p>'
            f'<h3>The KickTip team rating</h3><p>Team strength in the simulation\'s playoff steps comes from the KickTip team rating. It mostly measures what a team has earned: how hard its record would be to match against the same opponents in the same stadiums (Resume), '
            f'how firmly it controlled games, and efficiency on offense and defense, with recent games counting a little more. It is built only from completed FBS game results this season ({games_rated} games so far), with no preseason starting point, no polls and no betting lines. '
            f'The blend and the Elo-style model also carry results from earlier seasons (2021 onward) into this one, and every model turns a strength gap into a win probability with a conversion fitted only on earlier games.</p>')

def accuracy_html(A):
    ll, pk, f, m12, y26 = A["ll"], A["pick"], A["fcs"], A["make12"], A["y26"]; sl = A["slope_by_season"]
    outside = " and ".join(A["slope_outside"])
    return (f'<h2 id="accuracy">How accurate are these numbers?</h2>'
        f'<p>They are estimates, and they can be wrong. We tested the models by replaying {A["seasons"]}: for each game, a model could only use games played before it. Games from the first three weeks of each season were not scored. In all, {A["n"]:,} games were scored, {A["n_2026"]} of them from 2026 (games from late September through October 23). '
        f'The test was set up and scored before the blend was chosen as the default. It is a look back, not a promise about the games ahead.</p><ul>'
        f'<li><b>Average miss</b> (log loss, lower is better): KickTip blend {f3(ll["blend"])}, Elo-style {f3(ll["elo"])}, Efficiency {f3(ll["eff"])}, a rescaled MSM rating (an ingredient of the blend, not offered on its own) {f3(ll["msm"])}, and the original unscaled MSM percentages {f3(ll["raw"])}. Probabilities were limited to 2% to 98% before scoring; that matters only for the original MSM percentages, which score {f3(A["ll_raw_unclipped"])} without the limit. '
        f'The blend\'s lead over the best single model (the Elo-style one) is small: {abs(A["ci_blend_vs_best"][0]):.3f} lower, with a 95% range of {abs(A["ci_blend_vs_best"][2]):.3f} to {abs(A["ci_blend_vs_best"][1]):.3f} lower (resampling the test games). That comparison model was itself picked because it did best on these same test games.</li>'
        f'<li><b>Picks:</b> the blend picked the winner in {pc1(pk["blend"])} of games and the original MSM percentages in {pc1(pk["raw"])}. One pre-set pass mark (pick rate against the original MSM) was reworded after scoring to read "not lower by more than 1 point"; '
        f'the blend is {A["pick_item6_diff_pts"]:.1f} points higher, which meets the new wording but not the original "within 1 point" reading.</li>'
        f'<li><b>Confidence:</b> when the blend gave a team 90% or better, that team won {pc1(A["picks90"]["win"])} of the time ({A["picks90"]["n"]} games; {pc1(A["picks90"]["win_fbs"])} in the {A["picks90"]["n_fbs"]} games between two FBS teams). '
        f'The original MSM percentages averaged about {100 * A["raw_picks90"]["conf"]:.0f}% on {A["raw_picks90"]["n"]:,} such games, and those teams won {pc1(A["raw_picks90"]["win"])}. That overconfidence is why they were replaced as the default.</li>'
        f'<li><b>Calibration:</b> a slope of 1.00 means stated chances match results. The blend\'s overall slope is {f2(A["slope"])}; by season it is {sl["2023"]:.2f} (2023), {sl["2024"]:.2f} (2024), {sl["2025"]:.2f} (2025) and {sl["2026"]:.2f} (2026), so two of the four seasons ({outside}) fall outside the 0.85 to 1.15 range we aimed for. '
        f'In 2026 games from week 6 on ({y26["n"]} games) the blend\'s slope is {f2(y26["blend_slope"])} and the rescaled MSM rating\'s is {f2(y26["msm_slope"])}: both were more confident than results justified, so treat the early-season numbers with caution.</li>'
        f'<li><b>Games against FCS teams:</b> in {f["n"]} such games the blend\'s average miss ({f3(f["blend"])}) was worse than the Elo-style model\'s ({f3(f["elo"])}). FCS games are shown without a win probability, but an FCS result still counts in the simulation.</li>'
        f'<li><b>Season outcomes:</b> whether a team really made the 12 can only be checked for {m12["seasons"]}, about {m12["events"]} events (12 teams a season). On that small check, simpler models scored slightly better than the blend (Brier score, lower is better): Elo-style {f3(m12["brier"]["elo_cal"])} and Efficiency {f3(m12["brier"]["eff_cal"])}, against {f3(m12["brier"]["blend"])} for the blend. Two variants that are not offered did a little better still: the Elo-style rating before its last calibration step {f3(m12["brier"]["elo_raw"])}, and a re-fitted variant of the MSM rating (an ingredient of the blend, not offered as a choice) {f3(m12["brier"]["msm_cal"])}. The original MSM percentages scored {f3(m12["brier"]["b2_msm_raw"])}. '
        f'We cannot claim the blend\'s playoff chances are better than the simpler models\'.</li></ul>'
        f'<h3>Limits of the test</h3><ul>'
        f'<li>The 2026 list of FBS teams was applied to every season, so a team that joined FBS later is treated as an FCS opponent in earlier seasons.</li>'
        f'<li>Past seasons cannot be run through the live tiebreaker and playoff engine (it uses 2026 rules and members), so the season-level check uses a simpler stand-in: {A["harness"]["nsim"]:,} simulated seasons at three checkpoints per season (weeks {", ".join(str(x) for x in A["harness"]["cuts"][:-1])} and {A["harness"]["cuts"][-1]}) and a crude {A["harness"]["proxy"].replace(" committee stand-in", "")} stand-in for the selection committee.</li>'
        f'<li>Every gap between models is an estimate from {A["n"]:,} test games (the ranges above resample those games and treat them as independent), so small gaps between models mean little.</li></ul>')

def changed_html(asof_date, mv=None):
    """mv = data/ref/movers.json (internal raw-MSM vs default make-12 chances on the same data); the two named teams are written from it, nothing is typed by hand."""
    t = (mv or {}).get("teams", {}); ut, by = t.get("Utah Utes"), t.get("BYU Cougars")
    mover = (f' On the same data, Utah\'s chance to make the 12 is {ut[1]*100:.1f}% now against {ut[0]*100:.1f}% under the earlier percentages, and BYU\'s is {by[1]*100:.1f}% against {by[0]*100:.1f}%.' if ut and by else "")
    return (f'<h2 id="changed">What changed in this version</h2><p>Earlier versions of KickTip showed the MSM rating\'s own percentages. In the replay above those ran too confident, so the default is now the KickTip blend, and the chances on every page moved. '
            f'Heavy favorites drop and underdogs rise, so some teams move a lot.{mover} '
            f'The MSM rating is still part of the blend and still sets the committee stand-in, but its own percentages are no longer shown. Model numbers recalculated {E(asof_date)}.</p>')
