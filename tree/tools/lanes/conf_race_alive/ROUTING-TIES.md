# conf_race_alive routing decisions (CONTRACT 4.3)

| rule id | confidence | phrase it wins | lane / rule it meets |
|---|---|---|---|
| alive-conf | 0.92 | status word (alive, in the mix, eliminated, ...) + a conference (or the conference page) + a "championship game" word | none: more specific than lane C `cs-race` (0.90) |
| alive-team | 0.92 | one team + status word + "championship game" or "race" | lane C `cs-race` is silent on one-team status wording |
| alive-conf-race | **0.90** (kept; QA/parent: tell KT Builder this exact value) | status word + one conference + "race"/"hunt", or the conference page; no "championship" word | lane C `cs-race` (0.90). They tie at 0.90, so lane C excludes "(in|out) of the race" and alive / clinch / eliminated wording from `cs-race`; this rule is then the only match. A plain "how is the Big 12 race looking" has no status word, so it stays with `cs-race` |
| out-conf-bare | 0.88 | "who's eliminated / ruled out / knocked out in the SEC" (one conference, no team) | no other lane rule |

Same-tool rules may share a number. Not matched on purpose: national, playoff, bye, seeds, chance/odds/percent, need/must, scenarios, tiebreaker, rank, compare, versus.
Conference names: the longer name wins (CONTRACT 4.2.1), so "Mid-American" is the MAC and never American (`confsIn` in the rule drops a name that sits inside a longer one). "Utah" and "the U" go straight to Utah; "Bears" is a core chooser (Baylor, Missouri State).
