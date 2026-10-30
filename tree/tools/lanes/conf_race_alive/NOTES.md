# conf_race_alive notes
Method, size, run time, search proofs and per-conference rules uncertainty: see `/workspace/kicktip-tb-alive/legacy_task1/NOTES_task1.md` (sections 2 to 9; the data shape there is v1, the shipped card is v2: row `best` is `{w,l}`, no `asof_text`, plus `analyst` per conference). Sensitivity to the Analyst's encoding mismatches: `SENSITIVITY.md`. Wiring and tests: `README.md`.
Key points for reviewers:
- The search judges every leaf with the live engine; ranking, rating and draw steps branch over every tied team. Out = no completion and no branch puts the team in. Unknown statuses are refused (gate exit 5).
- Three teams are out today and all three are proved twice: by the search and by a counting argument on total wins that uses no tiebreaker (tests/alive_test.js section E, tests/tb generator `pigeon()`, tools/sensitivity.js `pigeonK`).
- Wording: neutral by default; stronger wording needs the CEO-approved flag with a matching rules hash AND an Analyst VERIFIED MATCH for the same ccg-rules.json bytes.
