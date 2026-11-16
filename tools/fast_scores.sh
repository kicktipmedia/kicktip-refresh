#!/bin/bash
# Scores-only publish. One ESPN pull, a merge-safe HTML card, then Preview, one Production
# attempt, and live_verify. Never writes FREEZE and never takes the full-refresh lock.
# usage:
#   tools/fast_scores.sh --gate
#   tools/fast_scores.sh --no-deploy [--skip-fetch]
#   tools/fast_scores.sh --deploy production|preview|none [--skip-fetch]
# exit: 0 skip, ship, or yield; 10 lock; 11 FREEZE; 12 bad base sha; 13 fetch;
#       18 preview; 21 prod; 22 pages.dev mismatch after rollback, or state write;
#       31 allowlist; 32 records or a byte outside the scores card.
set -euo pipefail
R=${KT_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
TOOLS=$R/tools
TREE=$R/tree
MODE=deploy
TARGET=production
SKIP_FETCH=0
while [ $# -gt 0 ]; do case $1 in
  --gate) MODE=gate; shift;;
  --no-deploy) MODE=dry; shift;;
  --skip-fetch) SKIP_FETCH=1; shift;;
  --deploy) TARGET=$2; shift 2;;
  *) echo "unknown arg $1"; exit 2;; esac; done
case $TARGET in production|preview|none) ;; *) echo "bad deploy target $TARGET"; exit 2;; esac
ACCT=${CLOUDFLARE_ACCOUNT_ID:-2b5bfb9838968d7cde32f13967e882e0}
PROJ=kicktip
WR=${KT_WRANGLER:-$R/wr/node_modules/.bin/wrangler}
PBRANCH=${KT_FAST_PREVIEW_BRANCH:-refresh-fast}
RUN=$(date +%Y%m%d-%H%M%S)
RD=$R/runs/fast-$RUN
mkdir -p "$RD"
LOG=$RD/run.log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(date '+%F %T %Z')] $*"; }
fail() { say "FAIL($1): $2"; python3 -c 'import json,sys;json.dump({"run":sys.argv[1],"exit":int(sys.argv[2]),"reason":sys.argv[3]},open(sys.argv[4],"w"))' "$RUN" "$1" "$2" "$RD/result.json"; exit "$1"; }
exec 9>"$R/.fast_scores.lock"
flock -n 9 || { say "another fast run holds the lock; exiting"; exit 10; }
[ -e "$R/FREEZE" ] && fail 11 "FREEZE file present: $(cat "$R/FREEZE")"
LIVE_ID=$(python3 -c "import json;print(json.load(open('$R/state.json'))['live_id'])") || fail 12 "state.json unreadable"
LIVE_SHA=$(python3 -c "import json;print(json.load(open('$R/state.json'))['live_sha'])") || fail 12 "state.json unreadable"
OLD_FP=$(python3 -c "import json;print(json.load(open('$R/state.json')).get('scores_fp') or '')") || true
say "fast scores live $LIVE_ID sha ${LIVE_SHA:0:12} scores_fp ${OLD_FP:-none}"

if [ -n "${KT_BASE_ZIP:-}" ]; then
  mkdir -p "$RD/zip" 
  cp "$KT_BASE_ZIP" "$RD/zip/kicktip-site.zip"
else
  mkdir -p "$RD/zip"
  gh release download base -D "$RD/zip" -p kicktip-site.zip || fail 13 "could not download the live zip"
fi
HAVE=$(sha256sum "$RD/zip/kicktip-site.zip" | cut -d' ' -f1)
[ "$HAVE" = "$LIVE_SHA" ] || fail 12 "base zip sha $HAVE != state.live_sha $LIVE_SHA"
rm -rf "$RD/base" "$RD/deploy"
mkdir -p "$RD/base"
unzip -q "$RD/zip/kicktip-site.zip" -d "$RD/base" || fail 12 "could not unzip the live zip"
cp -a "$RD/base" "$RD/deploy"

if [ "$SKIP_FETCH" != 1 ] && [ "${KT_SKIP_FETCH:-0}" != 1 ]; then
  (cd "$TREE" && python3 src/refresh.py > "$RD/refresh.json") || fail 13 "refresh.py failed: $(tail -n 3 "$RD/refresh.json" 2>/dev/null)"
  python3 -c "import json,sys;l=json.load(open('$TREE/data/out/refresh_log.json'));sys.exit(1 if l.get('errors') else 0)" || fail 13 "ESPN errors: $(python3 -c "import json;print(json.load(open('$TREE/data/out/refresh_log.json')).get('errors'))")"
else
  say "KT_SKIP_FETCH: using the schedule already in the tree"
fi
STAMP=$(python3 -c "import json;print(json.load(open('$TREE/data/out/refresh_log.json')).get('refreshed_mt',''))" 2>/dev/null || true)
FP=$(python3 "$TOOLS/fast_patch.py" --fp "$TREE") || fail 13 "could not fingerprint scores"
say "scores fp ${OLD_FP:-none} -> $FP"

set +e
python3 "$TOOLS/fast_patch.py" --site "$RD/deploy" --tree "$TREE" ${STAMP:+--stamp "$STAMP"} --check > "$RD/patch-check.txt"
prc=$?
set -e
cat "$RD/patch-check.txt"
[ "$prc" -eq 0 ] || fail "$prc" "score patch check failed"
CH=0
grep -q '^changed=0$' "$RD/patch-check.txt" || CH=1
if [ -n "${GITHUB_OUTPUT:-}" ]; then echo "changed=$CH" >> "$GITHUB_OUTPUT"; fi
if [ "$CH" = 0 ]; then
  say "no score change: skip, nothing deployed"
  echo "{\"run\":\"$RUN\",\"exit\":0,\"skipped\":true,\"fp\":\"$FP\"}" > "$RD/result.json"
  exit 0
fi
if [ "$MODE" = gate ]; then
  say "gate: scores changed; deploy step will patch"
  exit 0
fi

# Rebuild the deploy dir (the check did not write) and write the zip.
rm -rf "$RD/deploy"
cp -a "$RD/base" "$RD/deploy"
set +e
python3 "$TOOLS/fast_patch.py" --site "$RD/deploy" --tree "$TREE" ${STAMP:+--stamp "$STAMP"} --out-zip "$RD/kicktip-site.zip" > "$RD/patch.txt"
prc=$?
set -e
cat "$RD/patch.txt"
[ "$prc" -eq 0 ] || fail "$prc" "score patch failed"
cat "$RD/patch.txt"
NEW_SHA=$(sha256sum "$RD/kicktip-site.zip" | cut -d' ' -f1)
say "patched sha ${NEW_SHA:0:12}"
if [ "$MODE" = dry ] || [ "$TARGET" = none ]; then
  say "dry run: not deploying"
  echo "{\"run\":\"$RUN\",\"exit\":0,\"dry\":true,\"sha\":\"$NEW_SHA\",\"fp\":\"$FP\"}" > "$RD/result.json"
  exit 0
fi
[ -n "${CLOUDFLARE_API_TOKEN:-}" ] || fail 18 "CLOUDFLARE_API_TOKEN not set"
export CLOUDFLARE_ACCOUNT_ID=$ACCT
cd "${KT_WRANGLER_DIR:-$R/wr}" || fail 18 "wrangler directory missing"
timeout 900 "$WR" pages deploy "$RD/deploy" --project-name "$PROJ" --branch "$PBRANCH" --commit-dirty=true > "$RD/preview.log" 2>&1 || fail 18 "preview deploy: $(tail -n 3 "$RD/preview.log")"
PURL=$(grep -o 'https://[0-9a-f]\{8\}\.kicktip\.pages\.dev' "$RD/preview.log" | head -n 1 || true)
[ -n "$PURL" ] || fail 18 "no preview URL"
if [ -n "${KT_BYTECMP:-}" ]; then "$KT_BYTECMP" "$RD/deploy" "$PURL" > "$RD/bytecmp-preview.txt" || fail 18 "preview byte-compare"
else python3 "$TOOLS/bytecmp.py" "$RD/deploy" "$PURL" > "$RD/bytecmp-preview.txt" || fail 18 "preview byte-compare: $(head -n 3 "$RD/bytecmp-preview.txt")"; fi
if [ "$TARGET" = preview ]; then
  say "preview only: $PURL"
  echo "{\"run\":\"$RUN\",\"exit\":0,\"preview\":\"$PURL\",\"sha\":\"$NEW_SHA\",\"fp\":\"$FP\"}" > "$RD/result.json"
  exit 0
fi

cd "$R"
GUARD=$(bash "$TOOLS/fast_guard.sh" --base-sha "$LIVE_SHA") || fail 13 "guard read failed: $GUARD"
say "guard: $GUARD"
if [ "$GUARD" != ok ]; then
  say "$GUARD"
  echo "{\"run\":\"$RUN\",\"exit\":0,\"yield\":true,\"fp\":\"$FP\"}" > "$RD/result.json"
  exit 0
fi
[ "$(sha256sum "$RD/kicktip-site.zip" | cut -d' ' -f1)" = "$NEW_SHA" ] || fail 32 "zip changed after the patch"
timeout 900 "$WR" pages deploy "$RD/deploy" --project-name "$PROJ" --branch main --commit-dirty=true > "$RD/prod.log" 2>&1 || fail 21 "prod deploy (no retry): $(tail -n 3 "$RD/prod.log")"
set +e
NEW_ID=$(curl -s -m 30 -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/$ACCT/pages/projects/$PROJ" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['canonical_deployment']['id'])")
set -e
[ -n "$NEW_ID" ] || fail 21 "could not read the canonical deployment"
grep -q "${NEW_ID:0:8}" "$RD/prod.log" || fail 21 "canonical $NEW_ID is not this deploy"
PAGES=$(grep -o 'https://[0-9a-f]\{8\}\.kicktip\.pages\.dev' "$RD/prod.log" | grep -F "${NEW_ID:0:8}" | head -n 1 || true)
[ -n "$PAGES" ] || PAGES="https://${NEW_ID:0:8}.kicktip.pages.dev"
set +e
TAG=$(KT_NO_FREEZE=1 bash "$TOOLS/live_verify.sh" "$RD/deploy" "$RD/bytecmp-live.txt" "$PAGES" "$R/FREEZE" "$NEW_ID" "$RUN" "$LIVE_ID")
vrc=$?
set -e
rm -f "$R/FREEZE"
if [ "$vrc" -ne 0 ] || { [ "$TAG" != ok ] && [ "$TAG" != edge-lag ]; }; then
  say "pages.dev mismatch; rolling back to $LIVE_ID (no FREEZE)"
  curl -s -m 60 -X POST -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H "Content-Type: application/json" \
    "https://api.cloudflare.com/client/v4/accounts/$ACCT/pages/projects/$PROJ/deployments/$LIVE_ID/rollback" > "$RD/rollback.json" || true
  RB=$(python3 -c "import json;d=json.load(open('$RD/rollback.json'));print((d.get('result') or {}).get('id') or '')" 2>/dev/null || true)
  RBPAGES="https://${RB:0:8}.kicktip.pages.dev"
  if [ -n "$RB" ]; then
    if [ -n "${KT_BYTECMP:-}" ]; then "$KT_BYTECMP" "$RD/base" "$RBPAGES" > "$RD/bytecmp-rollback.txt" || true
    else python3 "$TOOLS/bytecmp.py" "$RD/base" "$RBPAGES" > "$RD/bytecmp-rollback.txt" || true; fi
  fi
  fail 22 "pages.dev mismatch after rollback to $LIVE_ID (rollback id ${RB:-none})"
fi
if [ "$TAG" = edge-lag ]; then say "WARNING: apex/www still mismatched after retries; $PAGES matches the build; recording the live base, no FREEZE"; fi
"$TOOLS/publish_base.sh" "$RD/kicktip-site.zip" "$NEW_ID" --fast --scores-fp "$FP" ${STAMP:+--scores-as-of "$STAMP"} || fail 22 "state.json write failed"
if [ -n "${GITHUB_OUTPUT:-}" ]; then echo "shipped=1" >> "$GITHUB_OUTPUT"; fi
say "LIVE $NEW_ID sha $NEW_SHA scores_fp $FP (fast base $LIVE_ID)"
echo "{\"run\":\"$RUN\",\"exit\":0,\"live_id\":\"$NEW_ID\",\"sha\":\"$NEW_SHA\",\"fp\":\"$FP\",\"scores_as_of\":\"$STAMP\",\"zip\":\"$RD/kicktip-site.zip\"}" > "$RD/result.json"
