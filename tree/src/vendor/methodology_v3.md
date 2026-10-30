# The MSM Rankings (MSM Top 25) — Methodology v3

## Plain English
The MSM Top 25 ranks teams mostly on what they've *earned*.
- **60% résumé:** how hard your record would be for a typical top-25 team to match against the same opponents in the same stadiums. Quality wins count a lot. Losses to weak teams cost a lot.
- **25% game control:** how firmly you controlled games. Each point of lead is worth less as the lead grows. Fourth-quarter scoring in games already decided by 25+ points after three quarters is ignored, so running up the score doesn't pay.
- **15% efficiency:** yards per play and points per drive, on offense and defense, adjusted for opponent.

In the strength and efficiency parts, recent games count a little more (the oldest game weighs 75% as much as the newest). There is no preseason starting point, and nothing carries over from last season. Every team starts at zero.

When two teams end up nearly tied (within 1 rating point) and one beat the other, the winner goes ahead.

We're conference-blind: no conference data goes in. Schedule strength comes only from game results. Leftover gaps between conferences are measured every week and reported, not corrected.

We use no polls, no outside rankings and no betting lines. We never predict scores or spreads.

## Technical
- **Data:** ESPN public JSON only.
  - Scoreboard (`groups=80`, completed games).
  - FBS standings for the team list (138 teams in 2026).
  - Game summaries for box scores (total yards; plays = rush attempts + pass attempts), drive counts and scoring plays (score at end of Q3).
  - Team schedules for completed-game checks and remaining opponents.
  - All FCS opponents are pooled as one rated team.
- **Game control value** per game, for the home team:
  - f(m) = sign(m)·28·(1−e^(−|m|/14)).
  - GC = ½·f(Q3 margin) + ½·f(final margin).
  - If |Q3 margin| ≥ 25 and the final has the same sign, the final margin is replaced with the Q3 margin (garbage-time filter).
- **Strength:**
  - Weighted ridge least squares: GC = s_home − s_away + h·(not neutral). λ = 0.3, home-field term unpenalized.
  - Recency weight w = 0.75 + 0.25·(days since opener / season span).
- **Win-probability scale σ:** fitted by maximum likelihood of game winners on strength differences, logistic P = 1/(1+e^(−d/σ)). σ = 4.5 GC points this run.
- **Strength of Record:**
  - Benchmark = the 25th-best FBS strength.
  - SOR = Σ_games [win − P(benchmark beats opponent at that venue)], in wins above the top-25 benchmark.
- **Resume** = 0.7·z(SOR) + 0.3·z(Colley W/L matrix).
- **Efficiency:**
  - Weighted ridge with separate offense and defense terms for yards per play (games with >20 plays) and points per drive (≥5 drives).
  - Net = offense + defense. eff = mean of the two z-scores.
- **Composite** = 0.60·z(Resume) + 0.25·z(Strength) + 0.15·z(eff). Displayed as 50 + 10·z.
- **Head-to-head:**
  - Up to 3 passes over adjacent pairs.
  - Swap when the gap is ≤ 1.0 rating point and the lower team has more H2H wins over the higher one. Swaps are logged in the audit.
  - A swapped team can show a slightly lower rating than the team below it.
- **Display only:** SOS played (mean opponent rating) and remaining SOS (mean current rating of unplayed scheduled opponents). Neither affects rank.
- **Audits** (`audit_v3_2026.txt`):
  - Completeness for every team vs its ESPN schedule, plus 10 random spot checks.
  - Garbage-filter count and H2H swaps.
  - Conference residuals in non-conference FBS games (game-control units; reported, not corrected).
- **Outputs:** `msm_top25_v3_2026_published.csv` (ranks 1–25 only), `msm_all_v3_2026.csv` (internal, all 138 teams), `games_v3_2026.json`.
- **Run:** `python3 rank_v3.py 2026`. v2 (`rank_v2.py`) is left untouched.
- **Known limits:**
  - No common-opponent criterion yet.
  - Quarter-level garbage filter only.
  - Yards per play are not garbage-filtered.
  - The benchmark and σ come from our own strength model, so résumé values move when strength moves.
