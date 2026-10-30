# Lane B: conf_race_alive (ships dark)

Tool `conf_race_alive`: which teams are in the race for a conference's championship game and which are out, on our reading of the rules. Precomputed data `data/tb/ccg-alive.json` (about 23 KB). Folder: `/workspace/kicktip-tb-alive/` (lane at `lanes/conf_race_alive`, base copy in `base/`, core copy in `core/` re-synced from tb-core, never edited).

## Requests for core
NEEDS-CORE: none.

## Layout
- `assets/tb/conf_race_alive.js` tool (live:false), `assets/tb/rules/conf_race_alive.js` matcher rules.
- `tools/` `alive_core.js` (search over the unchanged engine `assets/ccgsim.js`), `build_alive.js` (writes the card), `alive_gate.js` (publish gates), `refresh_hook.sh`, `sensitivity.js`, `analyst_verdicts.json` (Analyst verdicts, bound to the exact ccg-rules.json bytes).
- `build_lane.py` (run by build_tb after the overlay): refuses if `<tree>/../FREEZE` exists (exit 3), dry-runs the build.py patch, regenerates or `--check`s the card (stale = refuse), runs the gate. The lane ships no `data/tb/ccg-alive.json` of its own: it is generated in the tree, so it can never collide with a file the refresh hook wrote.
- `patch_sim_build.py` the one build.py line (see below). `tests/` see "Tests".

## Refresh hook wiring (exact)
1. The patch is ONE line inserted right after the line that writes `data/ccg-rules.json` in `kicktip-sim6/src/build.py` (anchor: `    w("data/ccg-rules.json", json.dumps(dict(codes=sorted(_cr), rules=_cr), separators=(",", ":"), ensure_ascii=False))`, must occur exactly once):
   `    if os.environ.get("KT_ALIVE_HOOK"): __import__("subprocess").run(["bash", os.environ["KT_ALIVE_HOOK"], SITE], check=True)   # tb-lane:conf_race_alive`
   It is applied by `python3 lanes/conf_race_alive/patch_sim_build.py --file /workspace/kicktip-sim6/src/build.py --apply` (uses core `patchlib.replace_exact`, count=1; fails loudly on 0 or 2+ matches; idempotent through the marker). Check first with `--dry-run`. Do NOT apply until the CEO gives the go (build folders are read only for now). `build_lane.py` only dry-runs it, and applies only if `KT_SIM_BUILD_PY=<path>` is set.
2. The line is opt-in: nothing happens unless the refresh routine sets `KT_ALIVE_HOOK=/workspace/kicktip-tb-alive/lanes/conf_race_alive/tools/refresh_hook.sh` (use the final lane path after merge). An unpatched or unset run is byte-identical to today.
3. The hook gets `SITE` (the folder holding `assets/` and `data/`; assets/ccgsim.js and data/ccg-sim.json, ccg-rules.json are already written there). It writes `data/tb/ccg-alive.json` (about 4 s), rebuilds in memory and requires byte equality, requires `asof` equal to ccg-sim (exit 4), refuses any unknown status (exit 5), and a banned word (7). Any non-zero exit fails the build step (`check=True`): do not deploy. The proof file is written NEXT TO the tree (`<SITE>/../<site name>.ccg-alive-proof.json`), not shipped.
4. FREEZE: if `<SITE>/../FREEZE` exists the hook and build_lane exit 3 and write nothing.
5. Cadence: every time ccg-sim.json changes (the same refresh that rewrites it).

## Wording gate (stronger words)
Default and only wording today: "in the race / out of the race on our reading of the rules". "Clinched" and "eliminated" exist only as gated copy and appear only for a conference when BOTH hold: (a) `data/ccg-rules-verified.json` has `{conf:{verified:true, rules_hash, by, date}}` with the sha16 of that conference's rules (the card shows it as `rules.hash`), and (b) `tools/analyst_verdicts.json` says VERIFIED MATCH for the exact ccg-rules.json bytes the Analyst checked (sha256 9af75431...6ff4); if those bytes change, every conference falls back to neutral and a new Analyst check is needed. The CEO decides flips; this lane never writes `ccg-rules-verified.json`. To enable: add that file (add-only overlay, e.g. `lanes/conf_race_alive/data/ccg-rules-verified.json`, or the refresh routine's own copy) and rebuild. Verdicts today: verified: Pac-12, MAC, American, Big 12, SEC; partial: Mountain West, Sun Belt, Conference USA, Big Ten; not verified: ACC. Partial and not-verified conferences can never use the stronger wording and show a note that some calls could change.
Card never equates a model number with the race status (no percentages anywhere; a fixed note says in the race is not a model chance) and never says every team is alive.

## Tests (run against a built tree; `OUT=/workspace/kicktip-tb-alive/out-tb`)
- Harness: `python3 core/tests/tb/run_tb_tests.py --base base --out $OUT --lane lanes/ref --lane lanes/conf_race_alive --browser chromium,webkit`
- Fixtures regenerate: `python3 lanes/conf_race_alive/tests/tb/gen_conf_race_alive_fixtures.py $OUT` (independent Python: records, games left, best finish, two certificates that use no tiebreaker).
- `node tests/alive_test.js [--quick] --root $OUT --proof $OUT.ccg-alive-proof.json` (search soundness, 4,499 checks full, about 3.5 min).
- `node tests/verified_out_test.js --root $OUT` (verified conferences: every out call holds under all ranking/draw outcomes and both readings).
- `node tests/lane_extra_test.js --root $OUT` (gated wording, analyst guard, singular forms, fail closed). `python3 tests/wiring_test.py $OUT` (patch, FREEZE, refusals).
- `node tools/sensitivity.js --root $OUT` (which calls depend on an encoding mismatch; output also in `SENSITIVITY.json`).

## QA 2 round (Oct 26, 2026): what changed
- Wording: every "out" phrase is the full "out of the race on our reading of the rules" (Understood-as lines, out-list items, out-team sentence); the neutral note no longer says "out of the race" (it reads "Race status is our reading ..., not a model chance."); the stale-rules note no longer says "is out of date". Out-team title + Understood-as line read as one statement ending in the full phrase. Empty out-state (both modes): "None yet." under "Out of the race (0)".
- `TB.render` with the verified flag on works (gated copy entries `{t, gate}` are passed to the shared card builder as `.t`). Tests: `tests/flagon_test.js` (scratch tree + real flag file + real hashes, through TB.render) and every `lane_extra_test.js` scenario now also goes through TB.render.
- Independents (Notre Dame, UConn, or `conference: "ind"`): a normal list card ("X plays as an independent, so it is not in a conference race.") with as-of and estimate footer; `not_applicable` is only for a slug the site does not cover.
- Matcher: "Who's eliminated in the SEC?" (a plain out word + one conference or the conference page) -> `{conference, status: "out"}` at 0.88.
- Data: `rules.url` (10 outside https:// links) is no longer written to `data/tb/ccg-alive.json`; the tool never rendered it. A test asserts no URL of any kind is in the data file.
- Gallery: `tests/gallery_alive.py` renders 10 real conf_race_alive cards (conference lists, out lists, out/tie/in/independent teams) in Chromium and WebKit at 320/390/430/1280 px (screens in `out-gallery/conf_race_alive-*.png`).
- QA bank: `tests/run_all.sh` makes a COPY of the official bank with the 13 T05 rows set `active:true` and runs the harness with `--strict-qbank`.
- Debug helper: `node tools/show.js --root out-tb '{"conference":"big10","team":"michigan-state"}'` prints the card text through TB.render.

## Creative-approved changes (Oct 26, 5 PM round)
- Out heading is "Out of the race (n)" in BOTH modes; no "Eliminated (n)" heading. The empty line is "None yet." (see caveat below). The full phrase "on our reading of the rules" stays on out-team sentences and the Understood-as lines; the heading needs no extra line.
- Neutral note (exact): "Race status is our reading of the conference's published tiebreaker rules, not a chance estimate." "model" no longer appears in any copy string (nBasis now ends "...and it is not a chance estimate.").
- Independents: one team keeps "X plays as an independent, so it is not in a conference race."; the group (conference "ind") reads "Notre Dame and UConn play as independents, so they are not in a conference race." (names from pred-teams, sorted; any other count falls back to one single-team line per team).
- QA bank pair b71bc3d3/58c1f9f4, then 8a8a56b1/7aedcced: T05-01..13 pass 13/13 on a COPY of the bank (run_all.sh).
- Matcher: the longer conference name wins ("Mid-American" is the MAC); fixtures RACE-M-09 (Utah resolves to Utah), -17 (Bears chooser), -18, -19, -20 added. See ROUTING-TIES.md.
