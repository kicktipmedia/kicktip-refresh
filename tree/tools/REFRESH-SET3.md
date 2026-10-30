# Set 3 refresh step (set3m)

Run these in the refresh, **after `data/sim-bundle.json` is written** and before `tools/restamp.py` and the manifest/zip step. They run in the same place as `gen_conf_bids.js`. None of them need a network call except `export_cfp_rankings.py`, which reads ESPN. Each file carries the sim-bundle `as_of`. A file left over from an older bundle makes its tool answer `no_data`. It never shows stale numbers.

| order | command | writes | tool |
|---|---|---|---|
| 1 | `node tools/gen_conf_outcome.js --sim <tree>/assets/ks/sim.js --bundle <tree>/data/sim-bundle.json --out <tree>/data/tb/conf-outcome.json` (same seed and season count as gen_conf_bids.js: defaults 20261 / 10000) | data/tb/conf-outcome.json | #24 whatif_conference_outcome |
| 2 | `python3 tools/gen_team_stats.py --pipeline <pipeline root> --bundle <tree>/data/sim-bundle.json --out <tree>/data/tb/team-stats.json` | data/tb/team-stats.json | #26 team_stats |
| 3 | `python3 tools/gen_history.py --pipeline <pipeline root> --bundle <tree>/data/sim-bundle.json --out <tree>/data/tb/history.json` (prior seasons 2021-2025; only the as-of changes week to week) | data/tb/history.json | #25 team_history |
| 4 | `python3 tools/export_cfp_rankings.py <tree>` (ESPN; "not released" gives `{"released": false, "teams": []}`) | data/tb/cfp-rankings.json | #23 cfp_committee_rankings |

The other two tools need no export of their own:

- #27 my_teams_digest reads the sim-bundle and `tb/ccg-alive`, which `gen_conf_bids.js` already writes.
- #28 game_win_chance reads only the sim-bundle.

After the four commands, run `tools/gen_manifest.js` (only if a tool file changed), then `tools/restamp.py`, then the build and zip.
