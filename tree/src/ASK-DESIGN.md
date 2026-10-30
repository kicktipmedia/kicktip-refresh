# KickTip scenario chat: engine batch and what remains

Status as of this batch (engine and tests only, nothing visible on the site, nothing deployed, b1 zip untouched):
Jared approved natural-language scenarios, multi-game combos at launch, client-side simulation, free tools only. Nothing ships until QA PASS and his go-live OK.

## What exists now

| Piece | File | Notes |
|---|---|---|
| Single-game what-ifs | `src/whatif.py` -> `data/out/whatif/index.json` + `w<week>.json` | 368 games x 2 outcomes, 6,000 seasons each, same seed as the baseline (common random numbers). ~125 KB total. Optional step: `python3 src/run_all.py --whatif` (or `--whatif-only` for a daily rebuild after a refresh, about 4 min on 8 cores). |
| Browser bundle | `src/export_web.py` -> `data/out/web/bundle.json` (~70 KB) | Model constants, season-to-date counts, remaining games, per-conference tiebreak state and rule lists, alias dictionary. Written by every normal `run_all.py`. Public data only. |
| Browser engine | `src/web/sim.js` (`KTSim.simulate`) | Port of sim.py + tiebreak.py + cfp.py. Seeded, forced outcomes, "wins N of M" constraints (exact conditional sampling). Classic script, no inline code, no network. 2,000 seasons about 0.2 s in Node. |
| Parser | `src/web/parse.js` (`KTParse.parse`) | Rule-based. Strict JSON out, refusal flag for betting phrasings, clarify flag + candidates. No numbers or prose in the output. |
| Resolver | `src/web/scenario.js` (`KTScenario.resolve`) | Parser items -> engine inputs (forced game ids, constraints) or a clarify reason code. |
| Answer templates | `src/web/answer.js` (`KTAnswer`) | Label line, before/after table data, need table (uses the what-if shards), clarify and refusal texts. |
| Aliases | `src/aliases.py` | 138 teams: full name, school, mascot, nicknames, abbreviations. Collisions are ambiguous automatically; `ASK` forces a question for Utah, Miami, Louisiana, Carolina, OSU, Mississippi. Utah Tech and Southern Utah are recognised as "not modeled". |
| Tests | `tests/web/parity_test.js`, `tests/web/parse_test.js`, `tests/web_test.py` (runs both) | Parity vs Python, forced vs what-ifs, constraints, timing, parser cases, resolver, templates, no eval/network in the web modules. |

Data flow in the browser (when the UI exists): load bundle.json once (cache it), parse the question locally, resolve it, then run `KTSim.simulate` twice with the same seed (baseline and scenario) inside a Web Worker, then call `KTAnswer.scenarioAnswer`. Single-game questions can be answered instantly from the what-if shard instead of simulating.

## Not built yet (needs Jared's go-live path and QA)

1. **Pages Function `/api/ask`** (only needed for the fallback path and the gate token).
   - Free-plan limits to design around (docs read 2026-10-23): Functions share the Workers Free quota of 100,000 requests/day, 10 ms CPU per invocation, 50 subrequests. The regex parser is cheap, but keep the Function thin: validate the token, rate limit, call Workers AI only when the rule-based parser returns `unparsed` or `no_team`.
   - The Function must return the same strict JSON schema as `parse.js` and nothing else. The browser re-validates it: every team index must exist, every kind must be one of beats / wins_out / loses_out / wins_n_of_m, otherwise ignore it. The model never writes the answer text and never sees or produces numbers; the answer always comes from `answer.js` + the simulator.
2. **Workers AI fallback (binding limits to verify before relying on it).**
   - Docs say 10,000 Neurons/day free, shared across all models, resets 00:00 UTC; past that, calls fail (no spend unless the account is on Workers Paid; confirm the account is Workers Free so $0 is guaranteed). Text generation rate limit 300 requests/minute for models that do not need Paid. Check the exact per-request Neuron cost of the chosen small instruction model, the Pages `[ai]` binding name in the Pages project settings (Preview and Production separately), and that local `wrangler pages dev` calls also count.
   - Fail closed: on any error or quota exhaustion return `clarify: unparsed`, never an invented scenario.
   - System prompt must forbid betting advice; the refusal regex in `parse.js` runs first on both the raw question and the model output.
3. **Signed gate token.** The disclaimer gate (six elements in order) is accepted in the browser; the Function must not run any prediction tool without proof. Plan: on acceptance the browser calls `/api/gate` (or the Function on first ask) which returns an HMAC-signed token `{v: DISC_VERSION, sid: random, iat}`; keep the HMAC secret as a Pages encrypted environment variable (never in the repo or zip); token lives in sessionStorage so a new browser session means a new visit; `/api/ask` rejects missing, stale or wrong-version tokens. The client-side simulator is not gated by the token (it is static code), so the gate stays a UI gate there; the token protects only the Function and Workers AI quota.
4. **Rate limits.** Per-token and per-IP (use the Cloudflare-provided connecting-IP header, hash before storing) with KV or Durable Object counters, or a stateless fallback: 20 asks/hour/session via signed counters. Daily global cap so Workers AI cannot exhaust the free quota (for example stop at 80% of the 10,000 Neuron day). Free-plan KV limits (1,000 writes/day) must be checked before choosing KV.
5. **UI** from Creative's v4 chat mockups in `/workspace/hub/creative-v4-chat/` (not reviewed in this engine batch). Needs: entry pill, drawer / bottom sheet, gate-first state, empty state with example chips, scenario chips for combos, before/after table (`answer.js` row data), clarify chips (use `clarifyAnswer(...).options` and re-parse with `{choices: {alias: teamIndex}}`), error and limit states, accessibility, no school logos, no sportsbook names, tap targets 44 px, no inline scripts (load `/js/sim.js`, `/js/parse.js`, `/js/scenario.js`, `/js/answer.js` as classic scripts, run the engine in a Worker script file served from the same origin).
6. **Build wiring.** `src/build.py` does not copy bundle.json, the what-if shards or the web scripts yet; add them to the site build and to the service worker / sources and last-updated notes once the UI exists. The CSP must allow worker-src 'self'. Not done here on purpose (b1 zip and build/site untouched).
7. **Open model gaps** (affect answers, not structure):
   - Scenario "X wins the conference" or "X reaches the title game" as an input (rather than a question) is not supported yet; the engine would need to force title-game participants.
   - Questions about the national title, margins ("by 10"), and "what does X need" with exact record thresholds are out of scope; `need` answers are the swing table plus wins-out / loses-out runs.
   - Rematches and conference title games are not in the remaining-game list; a scenario that names a future title game gets `no_remaining_game`.
   - Utah Tech and other FCS opponents are only addressable through "wins out / loses out / wins N of M" (the five remaining FCS games are inside those teams' schedules; the bundle carries the FCS opponent name in `games[].fcs` for a future alias).
   - The rating step stands in for the proprietary tiebreakers exactly as in the Python engine (see data/rules_sources.json flags); the browser engine inherits every flag.
8. **Operational.** Rebuild after each data refresh: `python3 src/run_all.py --whatif` (bundle + what-ifs together so `as_of` and ratings match). Add parity_test to the daily check.

## CFP field rule (corrected 2026-27 rule, ported)
`src/web/sim.js` mirrors `cfp.field()` in its `SWAPPABLE SECTION` (`P4`, `G6`, `finish`, `field(rank, champs, order, nd, g6)`; g6 is built from `bundle.teams[].c`). The old "official-rule" metric is gone (`cfp12_official` removed from the JS output, the tests and py_ref). After any further change to src/cfp.py, sim.py or tiebreak.py, run `python3 tests/web_test.py --rebuild` (bundle + what-ifs + both Node suites, about 6 minutes). Rule-dependent tests: parity_test checks 1 and 2, parse_test's end-to-end answer checks. Tiebreak changes ported: `rr_equal` mode and the Pac-12 two-team step order (the step list comes from the bundle).
