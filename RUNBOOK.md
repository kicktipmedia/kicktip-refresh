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

Steps and exit codes:
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
