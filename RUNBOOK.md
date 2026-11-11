# KickTip data refresh: RUNBOOK (rewritten Oct 30, 2026)

New numbers only, no design changes. Every refresh is the **current live zip** + the data delta. It is never a rebuild from the pipeline.

## Where things are
| What | Path |
|---|---|
| Live state (source of truth) | `/workspace/kicktip-refresh/state.json`: `live_id`, `live_sha`, `zip_path`, `site_dir`, `as_of`, `s0_pipeline_site`, `pipeline_tree`, `results_fp`, `rollback_id` |
| Pipeline tree (ESPN pull + models + pipeline site) | `/workspace/kicktip-refresh-1030/tree` (`src/refresh.py`, `src/run_all.py`, `src/build.py`) |
| Data layer onto a live zip | `tree/tools/apply_data.py` (+ `tree/tools/merge3.py` and generators in `tree/tools/`) |
| Unattended wrapper | `/workspace/kicktip-refresh/tools/auto_refresh.sh` |
| Checks | `tools/suite_subset.sh` (suite copy in `/workspace/kicktip-refresh/suite`, number-pinned fixtures made data-consistent), `tools/bytecmp.py`, `tools/crops.py`, `tools/results_fp.py` |
| Pipeline-site snapshots (S0 for the next run) | `/workspace/kicktip-refresh/pipeline/<YYYY-MM-DD_HHMM>/site` |
| Per-run output | `/workspace/kicktip-refresh/runs/<run>/` (run.log, result.json, zip, deploy/, report.json, suite/, crops) |
| Wrangler (local install) | `/workspace/kicktip-refresh/wr/node_modules/.bin/wrangler` (`npx wrangler` fails here: EACCES /node_modules) |
| Kill switch | `/workspace/kicktip-refresh/FREEZE` (exists = no run deploys; delete only on Jared/CEO say-so) |

## Normal run
```
cd /workspace/kicktip-refresh && setsid nohup tools/auto_refresh.sh > /dev/null 2>&1 < /dev/null &
```
- Agent shells kill background children, so always `setsid nohup`. Watch `runs/<latest>/run.log`. The result is in `runs/<latest>/result.json`.
- `--no-deploy` is a dry run: everything up to the checks, plus a read-only guard GET. `--force` runs even with no data change. `--preview-only` stops after Preview.

Steps and exit codes (the script exit; the GitHub job is green or red from the table under **Job result and email**, and `auto_refresh.sh` itself is unchanged):
0. A lock (`.auto_refresh.lock`, flock) means only one run at a time; a second run exits **10**. FREEZE gives **11**. Bad state, base zip sha ≠ `live_sha`, or a missing S0 gives **12**.
1. `refresh.py` (ESPN, about 3 s). Any ESPN error gives **13**. Then `results_fp.py` compares finals, scores, kickoffs and postponements with `state.results_fp`. **If they are unchanged: exit 0, skipped, nothing deployed.**
2. `run_all.py --no-refresh --whatif --whatif-all`. It uses 8 threads when load < 2, otherwise 1 thread under nice. About 6 min idle and 15 min contended. Then `build.py`. Failure gives **14** or **15**. The new pipeline site is snapshotted to `pipeline/<as_of>/site`.
3. `apply_data.py` onto the live zip gives **16** on any problem:
   - 3-way merge of live + (S0→S1). Any conflict is a hard stop.
   - Regenerates every data-derived file: tile-data, conf-bids, conf-outcome, team-stats, history, resume, ccg-games, needs-by-record, path-by-stage, trend, ccg-alive, ccg-paths and the per-conference split, and cfp-rankings.
   - Replaces every stamp form. Both the dated sentence and `kt-asof data-asof="YYYY-MM-DD HH:MM"` are handled.
   - Allow-list: only HTML, `data/`, or `?v=`-token-only files may change. `_worker.js` must be identical, and no files are added.
   - Four-way as-of check and an old-stamp-left check.
   - Builds twice and the shas must match.
4. Checks give **17**: sums 12/4/10/20, at least 130 teams, and the suite subset is green.
5. Preview to branch `refresh-auto`. Every file is byte-compared and the 390 crops must have no page errors. Failure gives **18**.
6. **Guard:** the canonical deployment must equal `state.live_id`, and the zip sha must be unchanged since Preview. Otherwise **20**: someone else deployed, so rebase; never force it. Then exactly one Production deploy attempt, with no retry. Failure gives **21**.
7. Apex and www byte-compare (Accept `*/*`, cache-bust, redirects followed, GET only). Cloudflare's zone email obfuscation strips `<!--email_off-->` on the custom domains, and the compare allows for that. A mismatch gives **22**: FREEZE is written and you roll back to `rollback_id`.
8. `state.json` is updated atomically (the previous copy goes to `state.prev.json`).

The pre-deploy gate (`tools/suite_subset.sh`) must not include a frozen record fixture. A hardcoded loss count, an "unbeaten" flag, or a leftover matchup (BYU still to play Utah, last week's loss totals) goes stale the moment a game goes final and then blocks kicktipmedia.com. A blocking check has to derive those numbers from the tree's played and remaining games. `set2c` and `set_router2` stay out of this gate until they do that. Replaying a named question against the frozen `suite/tests/fixtures/scn_575` bundle is fine, because that snapshot does not move when this week's games finish. Point those banks at that snapshot only. A weekly handwritten record snapshot is not a deploy blocker.

## Rollback
Dashboard → Pages → kicktip → Deployments → `state.rollback_id` → Rollback. You can also use the Pages API rollback endpoint. After a rollback, restore `state.prev.json` to `state.json`.

## Other deploys (feature builds: home7x, brag, ...)
Any non-refresh Production deploy MUST then write `state.json`. Set `live_id` and `live_sha`, set `zip_path` to its zip, and keep `s0_pipeline_site` and `as_of` if it did not change data. Otherwise the next refresh stops at the guard (exit 20). That is safe but stale. Feature builds should take their BASE from `state.json` `zip_path` so they carry the latest numbers. A feature deploy can pause refreshes by creating `FREEZE` and removing it afterwards.

## Proof that apply_data is pure data
`apply_data` with S0 = S1 = the Oct 27 5:58 PM MT pipeline site onto ship6c reproduces ship6c byte for byte (sha `327705459a93…1314`). Re-run it after any change to apply_data or merge3:
```
cd /workspace/kicktip-refresh-1030 && S0=/workspace/kicktip-refresh/pipeline/2026-10-27_1758/site && python3 tree/tools/apply_data.py --base-zip ../kicktip-home6/ship6c/kicktip-site-home6c.zip --base-sha 327705459a9394144e0a27bdee94c756ede628b0e8b221ae5a87078e2e101314 --s0 $S0 --s1 $S0 --pipeline ../kicktip-toolbox9c/work/ref1 --no-network --out proof/proof.zip
```

## Known limits
- `refresh.py` never re-reads a game that is already rated, so an ESPN score correction after a final is not picked up.
- The `/method/` spread count ("57 of the N games") comes from the lines feed, which this refresh does not touch.
- Some suite tests fail on the old base too (`set3m3_routing`). They are excluded from the gate.
- ESPN endpoints are unofficial: no licence, no published rate limit.

## Scheduling
No cron is installed. See the recommendation in the latest report. When the go comes, the job line is
`*/15 * * * * cd /workspace/kicktip-refresh && tools/auto_refresh.sh >/dev/null 2>&1`
(the lock makes overlaps harmless, and runs without a change cost about 3 s).

## GitHub Actions (kicktipmedia/kicktip-refresh, private)
- Workflow `.github/workflows/refresh.yml`. Scheduled runs only fire when repo variable `KT_SCHEDULE=on`
  (`gh variable set KT_SCHEDULE --body off` pauses them; manual runs always work: `gh workflow run refresh.yml -f deploy_target=preview|production|none [-f force=true]`).
- Base lives in release `base` (kicktip-site.zip = current live zip, s0-site.tar.gz = pipeline site it was built from). `tools/fetch_base.sh` checks the zip sha against `state.json`.
- Guard unchanged: Production only if Cloudflare canonical deployment == `state.json` live_id. FREEZE file in the repo root stops every run.
- Secrets: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID (set with `gh secret set`, never echoed).
- Each changed run uploads `inputs-<run>` (fetched ESPN store/cache). Box replay on the same data: extract into tree/ and run `KT_SKIP_FETCH=1 tools/auto_refresh.sh --no-deploy --force`.

### After ANY deploy from the box (feature builds, hotfixes) — required, or the next refresh stops at the guard
    export GH_CONFIG_DIR=/workspace/kicktip-refresh/.gh   # plus CLOUDFLARE_API_TOKEN in env
    cd /workspace/kicktip-gh/repo && tools/publish_base.sh <deployed zip> <deployment id>
  It refuses unless the canonical deployment is that id, then uploads the zip to release `base`, updates state.json, commits, pushes.
  (Add `--s0 <pipeline site> --as-of "..." --fp <fp> --completed N` only if the build also changed the pipeline data.)

### Measured (repo is public: standard 4-core runners, no minute cap)
- Run 41027620992 (full, preview, replayed inputs): setup+base+installs ~1.5 min; run_all 29 min (moves 248 s, what-if blend 494 s, all models 1472 s); build+apply_data+suite+preview ~4 min; Refresh step 33.6 min, job ~35 min. First public run 41019832179: run_all 55 min (runner speed varies).
- Box replay on the same inputs (KT_SKIP_FETCH=1): 1011 of 1014 files identical; the 3 sim-bundle.json files differ only in last-digit float noise in 4 model-metadata fields (resume_sd, bench, sor_sd, hfa; CPU/BLAS rounding). No displayed number differs.
- Every refresh is a full run (what-ifs on the same as-of as scores). One as-of per run: model stamp = results-pulled minute (KT_ASOF in run_all.py).
- Cadence: off-days hourly check (skip ~20 s when nothing changed). Saturday ticks every 30 min; concurrency group 'refresh' runs one at a time and keeps at most ONE pending run (GitHub replaces an older pending run with the newer one), so busy Saturdays run back-to-back: a fresh update roughly every 35-60 min.

## Feature ships and the S0 merge base (added Oct 30, 2026, refreshfix)
Why: every refresh 3-way-merges live + (S0 -> S1). S0/S1 are rendered by `tree/src/build.py`; feature ships edit the live HTML directly.
If a feature changes HTML that the pipeline also regenerates (games table/rows/cards, Sources strip, method page, stamps), the data merge
conflicts (Oct 30, 9:39 PM MT run 41165311294: live B5 games table had renamed headers + no Gap column; S1 added/removed rows next to them -> `games/index.html rc=3`).
**S0 asset name:** `state.json` key `s0_asset` = `s0-site.tar.gz` (absent = the same default). `fetch_base.sh`, `publish_base.sh`,
`rebuild_s0.sh`, Batch B `ship_b.sh` and `final_rebase_b.sh` all resolve it from state.json. Since Batch A (live 561c9524) the S0 is
`s0-site.tar.gz` sha 5b375ecf… (Batch A templates). `s0-site-v2.tar.gz` (e18db99f…, pre-fix TBA) is OLD: never point s0_asset at it.
Old S0 (e78fc637…, before Oct 30) is kept as `s0-site-backup-oct29.tar.gz` on release `base` and in `/workspace/hub/backups/`.

**Rule for every feature ship that touches pipeline-generated HTML:**
1. Port the same change into `tree/src/build.py` (same branch/PR as the ship). Visible copy must match the live wording; do not use "market".
2. `tools/rebuild_s0.sh <new empty dir outside the repo> --check <feature zip>` re-renders S0 at the live as-of from `s0-inputs.tar.gz`.
   The out dir is never deleted (the script refuses the repo, /, $HOME, /workspace, /tmp, and non-empty dirs).
   - Check 1 (report only): merge of the feature zip + (old S0 -> new S0). Lists pages where the zip carries the change in other markup.
   - Check 2 (required, gate): `KT_S0_OVERRIDE=<out>/new tools/auto_refresh.sh --no-deploy --force` in a clone whose `base/kicktip-site.zip`
     is the feature zip and `state.json live_sha` its sha. Must exit 0 (apply_data with no conflict + full suite).
3. Ship as usual (guard, sha, deploy, bytecmp), then `tools/publish_base.sh <zip> <id>` and `tools/rebuild_s0.sh <dir> --upload`.
   `--upload` first saves the current asset once as `s0-site-backup-<sha12>.tar.gz` (never overwritten by a second run), then replaces it.
   Rollback: `gh release download base -p s0-site-backup-<sha12>.tar.gz -D /tmp/rb && mv /tmp/rb/s0-site-backup-<sha12>.tar.gz /tmp/rb/<s0_asset> && gh release upload base /tmp/rb/<s0_asset> --clobber`.
   Ships that only change JS/CSS/assets need neither step.
4. Refresh runs keep `s0-inputs.tar.gz` current (`publish_base --s0-inputs tree`).

**Spreads (ESPN):** `src/lines.py --pull` runs ONCE per run before the gate fingerprint (50 min minimum interval, so every hourly run pulls;
the interval counts failed/empty attempts too, via `espn_lines.json.attempt`). The workflow sets `KT_LINES_PULLED=1` so `auto_refresh.sh`
does not pull again: the gate fp equals the build fp. A new snapshot (`lines_fp`) triggers a full run. Safety:
- Empty pull (no usable spreads) or network error: `espn_lines.json` is not touched (last good lines stay, `pulled_epoch` never 0).
- Corrupt `espn_lines.json`: `lines_fp.py` prints `none 0`; the merge keeps the previous `market_lines.json` and logs it; never a hard failure.
- The `lines.py` merge failing is a warning, not a failed run.

**Failed-input hold (no loop on a red suite):** when a main Production run is classified **red** and the gate recorded an input
hash `<results_fp>-<lines_fp>`, the workflow stores that hash in the Actions cache `refresh-hold-*`. The next scheduled run with the SAME inputs stops at the gate
("Held: …" in the summary) instead of rerunning the 15-min models. New results or new spreads give a new hash: one retry. `force=true` overrides.
A green classification does not write the hold, so the next run retries the same inputs. `tools/report_outcome.py` never writes `hold/failed` itself. The hold steps run only when the reporter set `KT_HOLD=1` (a red class) and the step actually failed.

### Job result and email

GitHub emails the account owner when the **job** fails. `tools/auto_refresh.sh` still exits with the same codes, and guard, FREEZE, and byte-compare behavior on a real failure is unchanged. `tools/report_outcome.py` (using `tools/classify_outcome.py`) writes the job step summary plus `runs/0-report/result.json` and `runs/0-report/outcome.log`. Those files show `FAIL(code)` and the log tail, and the run-log artifact uploads them. `runs/0-report` sorts before a timestamped run directory, so the record step's `ls -d runs/* | tail` still picks the real run.

**Test run** (green, no hold, for every exit including 12 from a stale branch `state.json` / base zip sha): any ref other than `main`, or `workflow_dispatch` with `deploy_target=none` or `preview`. A scheduled run is on `main`. An empty dispatch target is production.

**Main Production** is `main` and not a none/preview dispatch (the schedule, or `workflow_dispatch` with `production`).

| Exit | What it means | Main Production job | Hold on main Production | Test run |
|---|---|---|---|---|
| 0 | clean ship or skip | green | no | green, no hold |
| 10 | lock held by another run | green | no | green, no hold |
| 11 | FREEZE present | red | yes, if the gate has an input hash | green, no hold |
| 12 | broken state, or base zip sha ≠ `live_sha` (includes a stale branch) | red | yes, if the gate has an input hash | green, no hold |
| 13 | ESPN or other fetch error (`refresh.py`, replay, or ESPN errors in the log) | green | no | green, no hold |
| 14 | `run_all` failed | red | yes | green, no hold |
| 15 | `build.py` failed, or `as_of` equals live | red | yes | green, no hold |
| 16 | `apply_data`, unzip, or zip-vs-site mismatch | red | yes | green, no hold |
| 17 | sanity or suite failed | red | yes | green, no hold |
| 18 | preview deploy flake, and Production was not attempted | green | no | green, no hold |
| 18 | preview code but a Production deploy log was written | red | yes | green, no hold |
| 20 | guard: someone else deployed, or the zip changed after preview | red | yes | green, no hold |
| 21 | Production deploy failed | red | yes | green, no hold |
| 22 | live byte-compare failed (FREEZE written) or `state.json` write failed | red | yes | green, no hold |
| any other code | unexpected or unknown | red | yes | green, no hold |
| install | `Install tools (pinned)` still failing after 3 tries (apt, DNS, network) | green | no | green, no hold |

Exit 22 sets `KT_COMMIT_FREEZE=1` on every run type. The existing FREEZE commit step still runs and pushes `FREEZE` when that file is present, including when a test run stays green. Other green outcomes do not run that step.

The install step runs `tools/retry_cmd.sh --tries 3 --backoff 20`. After the first failure it waits 20s, after the second 40s. If the third try still fails, the reporter writes `FAIL(install)` and the log tail, the job stays green, and the hold is not written. The next run retries normally.

A green non-zero outcome sets `KT_HALT=1` so later build, deploy, and publish steps are skipped. Exit 0 does not halt. The record step runs only when `auto_refresh.sh` itself exited 0 (`steps.refresh.outputs.shipped == '1'`).
