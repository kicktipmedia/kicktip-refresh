#!/bin/bash
# KickTip unattended data refresh. Reads $KT_ROOT/state.json (default: repo root) (the live deploy), refreshes ESPN results,
# and only if a final/score/kickoff changed: models -> apply_data onto the CURRENT live zip -> checks -> Preview -> guard -> Production
# -> byte-compare -> state.json. Any failure: nonzero exit, clear reason, nothing deployed after the failing step.
# usage: auto_refresh.sh [--no-deploy] [--force] [--preview-only]
#   --no-deploy    build + all checks, no Cloudflare calls except the read-only guard GET (dry run)
#   --force        run even if results did not change
# exit: 0 ok/skip, 10 locked, 11 FREEZE, 12 state/base bad, 13 ESPN pull, 14 models, 15 build, 16 apply_data, 17 checks,
#       18 preview, 20 guard, 21 prod deploy, 22 pages.dev byte-compare mismatch (FREEZE; edge lag records the base, rollback = state.rollback_id)
set -uo pipefail
R=${KT_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}; TOOLS=$R/tools; NODEPLOY=0; FORCE=0; PREVONLY=0
for a in "$@"; do case $a in --no-deploy) NODEPLOY=1;; --force) FORCE=1;; --preview-only) PREVONLY=1;; *) echo "unknown arg $a"; exit 2;; esac; done
ACCT=${CLOUDFLARE_ACCOUNT_ID:-2b5bfb9838968d7cde32f13967e882e0}; PROJ=kicktip; WR=${KT_WRANGLER:-$R/wr/node_modules/.bin/wrangler}; PBRANCH=${KT_PREVIEW_BRANCH:-refresh-auto}
RUN=$(date +%Y%m%d-%H%M%S); RD=$R/runs/$RUN; mkdir -p $RD; LOG=$RD/run.log
exec > >(tee -a $LOG) 2>&1
say() { echo "[$(date '+%F %T %Z')] $*"; }
fail() { say "FAIL($1): $2"; echo "{\"run\":\"$RUN\",\"exit\":$1,\"reason\":$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$2")}" > $RD/result.json; exit $1; }
exec 9>$R/.auto_refresh.lock; flock -n 9 || { say "another run holds the lock; exiting"; exit 10; }
[ -e $R/FREEZE ] && fail 11 "FREEZE file present: $(cat $R/FREEZE)"
js() { python3 -c "import json,os;v=json.load(open('$R/state.json'))['$1'];print(os.path.join('$R',v) if '$1' in ('zip_path','s0_pipeline_site','pipeline_tree','site_dir') and not v.startswith('/') else v)"; }
LIVE_ID=$(js live_id) && LIVE_SHA=$(js live_sha) && ZIP=$(js zip_path) && S0=$(js s0_pipeline_site) && TREE=$(js pipeline_tree) && FP0=$(js results_fp) && OLD_ASOF=$(js as_of) || fail 12 "state.json unreadable"
LFP0=$(python3 -c "import json;print(json.load(open('$R/state.json')).get('lines_fp',''))"); LEP0=$(python3 -c "import json;print(json.load(open('$R/state.json')).get('lines_epoch',0))") || fail 12 "state.json unreadable"
[ "$(sha256sum "$ZIP" | cut -d' ' -f1)" = "$LIVE_SHA" ] || fail 12 "base zip sha != state.live_sha"
[ -n "${KT_S0_OVERRIDE:-}" ] && [ $NODEPLOY = 1 ] && S0=$KT_S0_OVERRIDE   # rebuild_s0 check 2: dry run only
[ -d "$S0" ] || fail 12 "S0 pipeline site missing: $S0"
say "live $LIVE_ID sha ${LIVE_SHA:0:12} as_of $OLD_ASOF"
# 1. pull
cd $TREE || fail 12 "no pipeline tree"
if [ "${KT_SKIP_FETCH:-0}" = 1 ]; then echo "KT_SKIP_FETCH: using frozen inputs already in tree/data" > $RD/refresh.json; else timeout 300 python3 src/refresh.py > $RD/refresh.json 2>&1; fi || fail 13 "refresh.py failed: $(tail -n 3 $RD/refresh.json)"
python3 -c "import json,sys;l=json.load(open('data/out/refresh_log.json'));sys.exit(1 if l['errors'] else 0)" || fail 13 "ESPN errors: $(python3 -c "import json;print(json.load(open('data/out/refresh_log.json'))['errors'])")"
# 1b. ESPN pre-game spreads (fail soft, at most every 2 h on Thu-Sat, 12 h otherwise); skipped on replays (snapshot comes from the frozen inputs)
if [ "${KT_SKIP_FETCH:-0}" != 1 ] && [ "${KT_LINES_PULLED:-0}" != 1 ]; then timeout 180 python3 src/lines.py --pull --no-merge > $RD/lines_pull.log 2>&1 || say "lines pull failed (kept last snapshot): $(tail -n 1 $RD/lines_pull.log)"; fi
read LFP1 LEP1 <<< "$(python3 $TOOLS/lines_fp.py $TREE)"; LFP1=${LFP1:-none}; [[ "$LEP1" =~ ^[0-9]+$ ]] || LEP1=0; [[ "${LEP0:-0}" =~ ^[0-9]+$ ]] || LEP0=0   # one pull per run (KT_LINES_PULLED: the gate already pulled); empty/corrupt -> none 0
say "lines fp ${LFP0:-none} -> $LFP1 (pulled $(date -d @$LEP1 '+%F %T %Z' 2>/dev/null))"
LCHG=0; { [ "$LFP1" != "none" ] && [ "$LFP1" != "$LFP0" ]; } && LCHG=1; [ "$LEP1" -gt $(( ${LEP0:-0} + 72000 )) ] && LCHG=1   # new numbers, or the live read is 20 h+ older than this pull
tar czf $RD/inputs.tgz --exclude=data/cache/val --exclude=data/store/forecast_log.jsonl --exclude=data/store/snapshots-archive data/store data/cache data/out/refresh_log.json 2>/dev/null || true
read FP1 DONE <<< "$(python3 $TOOLS/results_fp.py $TREE)"
say "results fp $FP0 -> $FP1 (completed $DONE)"
if [ "$FP1" = "$FP0" ] && [ $LCHG = 0 ] && [ $FORCE = 0 ]; then say "no new final, score, kickoff or spread change: skip, nothing deployed"; echo "{\"run\":\"$RUN\",\"exit\":0,\"skipped\":true}" > $RD/result.json; exit 0; fi
# 2. models (whole box when idle, else 1 thread niced)
L1=$(cut -d' ' -f1 /proc/loadavg); NP=$(nproc); TH=$(python3 -c "print($NP if $L1<2 else 1)")
say "models: OMP_NUM_THREADS=$TH"
export KT_ASOF=$(python3 -c "import json;print(json.load(open('data/out/refresh_log.json'))['refreshed_mt'])")   # model stamp = results-pulled minute (one as-of per run; makes replays reproducible)
OMP_NUM_THREADS=$TH timeout 5400 nice python3 src/run_all.py --no-refresh --whatif --whatif-all > $RD/run_all.log 2>&1 || fail 14 "run_all failed: $(tail -n 3 $RD/run_all.log)"
timeout 120 python3 src/forecast_log.py > $RD/forecast_log.log 2>&1 || say "WARNING forecast log failed (refresh continues): $(tail -n 1 $RD/forecast_log.log)"   # accuracy logger: data/store/forecast_log.jsonl only, committed by publish_base (git add -A tree/data/store); never blocks
timeout 120 python3 src/lines.py > $RD/lines_merge.log 2>&1 || say "lines merge failed, the previous market_lines.json is kept: $(tail -n 1 $RD/lines_merge.log)"   # never blocks a results deploy
timeout 600 python3 src/build.py > $RD/build.log 2>&1 || fail 15 "build.py failed: $(tail -n 3 $RD/build.log)"
ASOF=$(python3 -c "import json;print(json.load(open('build/site/data/sim-bundle.json'))['as_of'])")
[ "$ASOF" != "$OLD_ASOF" ] || fail 15 "new build as_of equals live as_of ($ASOF)"
SNAP=$R/pipeline/$(echo "$ASOF" | sed 's/ MT//;s/ /_/;s/://'); rm -rf $SNAP; mkdir -p $SNAP; cp -r build/site $SNAP/site
# 2c. AP / Coaches polls and the CFP committee rankings. Never blocks: a timeout, bad feed, or unmapped team keeps the last good file and the scores still publish.
# CFP is inside the same command. Its own reads are short, and a failure here is a warning (exit stays 0). It is not part of the failed-input hold.
POLL_CAND=""; POLL_BASE=""; PA=""
timeout 80 python3 src/poll_refresh.py --zip "$ZIP" --out $RD/polls.json --baseline-out $RD/polls-baseline.json --cfp > $RD/polls.log 2>&1 || say "WARNING polls: step crashed; keeping the last good polls file"
cat $RD/polls.log
if grep -q '^POLLS_CHANGED=1$' $RD/polls.log && [ -f $RD/polls.json ]; then POLL_CAND=$RD/polls.json; fi
if grep -q '^POLLS_BASELINE=' $RD/polls.log && [ -f $RD/polls-baseline.json ]; then POLL_BASE=$RD/polls-baseline.json; fi
[ -n "$POLL_CAND" ] && PA="$PA --polls $POLL_CAND"
if [ -n "$POLL_BASE" ]; then
  if [ $NODEPLOY = 1 ] || [ $PREVONLY = 1 ]; then PA="$PA --polls-baseline $POLL_BASE"; export KT_ALLOW_POLLS_BASELINE=1
  else say "WARNING polls: baseline override ignored on a production deploy"; fi
fi
# 3. apply onto live
python3 $TREE/tools/apply_data.py --base-zip "$ZIP" --base-sha "$LIVE_SHA" --s0 "$S0" --s1 $SNAP/site --pipeline $TREE \
  --out $RD/kicktip-site.zip --report $RD/report.json --site-out $RD/site ${KT_RANKS:+--ranks "$KT_RANKS"} $PA > $RD/apply.log 2>&1 || fail 16 "apply_data: $(grep -h 'APPLY_DATA FAIL' $RD/apply.log | tail -n 1)"
grep -E '^(polls:|WARNING polls:)' $RD/apply.log || true
python3 src/poll_refresh.py --check-site "$RD/site" || say "WARNING polls: baked-HTML check could not run"
NEW_SHA=$(sha256sum $RD/kicktip-site.zip | cut -d' ' -f1)
rm -rf $RD/deploy; mkdir $RD/deploy; (cd $RD/deploy && unzip -q ../kicktip-site.zip) || fail 16 "unzip"
diff -rq $RD/deploy $RD/site >/dev/null || fail 16 "deploy dir != zip"
# 4. checks
python3 - $RD/deploy <<'P' || fail 17 "sum/sanity check failed"
import json,sys
S=sys.argv[1]; T=json.load(open(S+'/data/pred-teams.json'))['teams']
s={k:round(sum(v.get(k) or 0 for v in T.values()),2) for k in 'pbwc'}
ok=s=={'p':12.0,'b':4.0,'w':10.0,'c':20.0} and len(T)>=130
print('sums',s,'teams',len(T)); sys.exit(0 if ok else 1)
P
$TOOLS/suite_subset.sh $RD/deploy $RD/suite > $RD/suite.txt 2>&1; cat $RD/suite.txt
grep -q "SUITE_DONE fail=0" $RD/suite.txt || fail 17 "suite subset failed: $(grep -v 'rc=0' $RD/suite.txt | head -n 3 | tr '\n' ' ')"
say "build OK sha $NEW_SHA as_of $ASOF ($(python3 -c "import json;print(len(json.load(open('$RD/report.json')).get('changed',{})))") files changed)"
if [ $NODEPLOY = 1 ]; then
  C=$(curl -s -m 30 -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN:-}" https://api.cloudflare.com/client/v4/accounts/$ACCT/pages/projects/$PROJ | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['canonical_deployment']['id'])" 2>/dev/null)
  say "DRY RUN (--no-deploy): would deploy $NEW_SHA; guard canonical=$C vs state.live_id=$LIVE_ID -> $([ "$C" = "$LIVE_ID" ] && echo PASS || echo WOULD-ABORT)"
  echo "{\"run\":\"$RUN\",\"exit\":0,\"dry\":true,\"sha\":\"$NEW_SHA\",\"as_of\":\"$ASOF\",\"guard\":\"$C\"}" > $RD/result.json; exit 0
fi
[ -n "${CLOUDFLARE_API_TOKEN:-}" ] || fail 18 "CLOUDFLARE_API_TOKEN not set"
export CLOUDFLARE_ACCOUNT_ID=$ACCT
# 5. preview
cd ${KT_WRANGLER_DIR:-$R/wr} && timeout 900 $WR pages deploy $RD/deploy --project-name $PROJ --branch $PBRANCH --commit-dirty=true > $RD/preview.log 2>&1 || fail 18 "preview deploy: $(tail -n 3 $RD/preview.log)"
PURL=$(grep -o 'https://[0-9a-f]\{8\}\.kicktip\.pages\.dev' $RD/preview.log | head -n 1); [ -n "$PURL" ] || fail 18 "no preview URL"
python3 $TOOLS/bytecmp.py $RD/deploy $PURL > $RD/bytecmp-preview.txt || fail 18 "preview byte-compare: $(head -n 3 $RD/bytecmp-preview.txt)"
python3 $TOOLS/crops.py $PURL $RD/crops-preview > $RD/crops-preview.txt 2>&1 || fail 18 "preview crops"
grep -q "errs \[\]" $RD/crops-preview.txt || fail 18 "preview page errors: $(head -n 2 $RD/crops-preview.txt)"
[ $PREVONLY = 1 ] && { say "preview only: $PURL"; echo "{\"run\":\"$RUN\",\"exit\":0,\"preview\":\"$PURL\",\"sha\":\"$NEW_SHA\",\"as_of\":\"$ASOF\"}" > $RD/result.json; exit 0; }
# 6. guard (one read, then exactly one deploy attempt)
C=$(curl -s -m 30 -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" https://api.cloudflare.com/client/v4/accounts/$ACCT/pages/projects/$PROJ | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['canonical_deployment']['id'])")
[ "$C" = "$LIVE_ID" ] || fail 20 "GUARD: canonical $C != state.live_id $LIVE_ID (someone else deployed; rebase needed)"
[ "$(sha256sum $RD/kicktip-site.zip | cut -d' ' -f1)" = "$NEW_SHA" ] || fail 20 "GUARD: zip changed since preview"
timeout 900 $WR pages deploy $RD/deploy --project-name $PROJ --branch main --commit-dirty=true > $RD/prod.log 2>&1 || fail 21 "prod deploy (no retry): $(tail -n 3 $RD/prod.log)"
NEW_ID=$(curl -s -m 30 -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" https://api.cloudflare.com/client/v4/accounts/$ACCT/pages/projects/$PROJ | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['canonical_deployment']['id'])")
grep -q "${NEW_ID:0:8}" $RD/prod.log || fail 21 "canonical $NEW_ID is not this deploy"
# 7. verify. A custom-domain edge can serve the previous deploy for a couple of minutes.
# Retry cache-busted compares over that window. Only a pages.dev mismatch writes FREEZE;
# when pages.dev matches, the deploy is good and step 8 records the live base (the next guard needs it).
PAGES=$(grep -o 'https://[0-9a-f]\{8\}\.kicktip\.pages\.dev' $RD/prod.log | grep -F "${NEW_ID:0:8}" | head -n 1 || true)
[ -n "$PAGES" ] || PAGES="https://${NEW_ID:0:8}.kicktip.pages.dev"
TAG=$(bash $TOOLS/live_verify.sh $RD/deploy $RD/bytecmp-live.txt "$PAGES" $R/FREEZE "$NEW_ID" "$RUN" "$LIVE_ID") || fail 22 "live byte-compare failed; FREEZE written; rollback id $LIVE_ID"
if [ "$TAG" != ok ] && [ "$TAG" != edge-lag ]; then fail 22 "live byte-compare failed; FREEZE written; rollback id $LIVE_ID"; fi
if [ "$TAG" = edge-lag ]; then say "WARNING: apex/www still mismatched after retries; $PAGES matches the build; recording the live base, no FREEZE"; fi
python3 $TOOLS/crops.py https://kicktipmedia.com $RD/crops-live > $RD/crops-live.txt 2>&1
# 8. state (same write on a clean compare and on edge-lag)
export KT_ROOT=$R RD NEW_ID NEW_SHA ASOF FP1 DONE LFP1 LEP1 SNAP LIVE_ID RUN
bash $TOOLS/record_live.sh || fail 22 "state.json write failed"
say "LIVE $NEW_ID sha $NEW_SHA as_of $ASOF (rollback $LIVE_ID)"
