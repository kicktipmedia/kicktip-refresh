#!/bin/bash
# A full refresh reached its guard and Cloudflare's canonical deploy is not the one it started from.
# If every deploy since that id is a fast-scores deploy, rebuild onto the new zip, re-check, preview,
# and overlay a fresh scoreboard so a final that landed during the sim is not rolled back.
# Anything else exits 20 (today's guard).
# usage: tools/fast_rebase.sh --canonical ID --live-id ID --run-dir DIR --tree DIR --s0 DIR --s1 DIR
# Writes <run-dir>/rebase.json {sha, canonical} on success.
# KT_CURL KT_GIT KT_APPLY KT_SUITE KT_REFRESH KT_WRANGLER KT_BYTECMP KT_REBASE_ZIP override the real tools.
set -euo pipefail
CAN=""; LIVE=""; RD=""; TREE=""; S0=""; S1=""
while [ $# -gt 0 ]; do case $1 in
  --canonical) CAN=$2; shift 2;; --live-id) LIVE=$2; shift 2;; --run-dir) RD=$2; shift 2;;
  --tree) TREE=$2; shift 2;; --s0) S0=$2; shift 2;; --s1) S1=$2; shift 2;;
  *) echo "bad arg $1" >&2; exit 2;; esac; done
[ -n "$CAN" ] && [ -n "$LIVE" ] && [ -n "$RD" ] && [ -n "$TREE" ] && [ -n "$S0" ] && [ -n "$S1" ] || { echo "missing args" >&2; exit 2; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
TOOLS=$ROOT/tools
CURL=${KT_CURL:-curl}
GIT=${KT_GIT:-git}
ACCT=${CLOUDFLARE_ACCOUNT_ID:-2b5bfb9838968d7cde32f13967e882e0}
PROJ=kicktip
say() { echo "[fast-rebase] $*"; }
"$GIT" fetch origin main >/dev/null
"$GIT" show origin/main:state.json > "$RD/state-remote.json"
python3 "$TOOLS/fast_patch.py" --chain --state "$RD/state-remote.json" --live-id "$LIVE" --canonical "$CAN" || {
  say "not a fast-scores chain from $LIVE (canonical $CAN)"
  exit 20
}
BASE_SHA=$(python3 -c "import json;print(json.load(open('$RD/state-remote.json'))['live_sha'])")
if [ -n "${KT_REBASE_ZIP:-}" ]; then
  ZIP=$KT_REBASE_ZIP
else
  mkdir -p "$RD/rebase-base"
  gh release download base -D "$RD/rebase-base" -p kicktip-site.zip
  ZIP=$RD/rebase-base/kicktip-site.zip
fi
HAVE=$(sha256sum "$ZIP" | cut -d' ' -f1)
[ "$HAVE" = "$BASE_SHA" ] || { echo "rebase zip sha $HAVE != state.live_sha $BASE_SHA" >&2; exit 12; }
say "rebasing onto $CAN sha ${BASE_SHA:0:12}"
if [ -n "${KT_APPLY:-}" ]; then
  "$KT_APPLY" --base-zip "$ZIP" --base-sha "$BASE_SHA" --s0 "$S0" --s1 "$S1" --pipeline "$TREE" --out "$RD/kicktip-site.zip" --site-out "$RD/site"
else
  python3 "$TREE/tools/apply_data.py" --base-zip "$ZIP" --base-sha "$BASE_SHA" --s0 "$S0" --s1 "$S1" --pipeline "$TREE" --out "$RD/kicktip-site.zip" --report "$RD/report.json" --site-out "$RD/site"
fi
rm -rf "$RD/deploy"; mkdir -p "$RD/deploy"
(cd "$RD/deploy" && unzip -q "$RD/kicktip-site.zip")
diff -rq "$RD/deploy" "$RD/site" >/dev/null || { echo "rebase deploy dir != zip" >&2; exit 16; }
python3 - "$RD/deploy" "${KT_SUMS_MIN:-130}" <<'P' || { echo "rebase sum check failed" >&2; exit 17; }
import json,sys
S=sys.argv[1]; T=json.load(open(S+'/data/pred-teams.json'))['teams']
s={k:round(sum(v.get(k) or 0 for v in T.values()),2) for k in 'pbwc'}
ok=s=={'p':12.0,'b':4.0,'w':10.0,'c':20.0} and len(T)>=int(sys.argv[2])
print('sums',s,'teams',len(T)); sys.exit(0 if ok else 1)
P
SUITE=${KT_SUITE:-$TOOLS/suite_subset.sh}
set +e
"$SUITE" "$RD/deploy" "$RD/suite" > "$RD/suite.txt" 2>&1
set -e
cat "$RD/suite.txt"
grep -q "SUITE_DONE fail=0" "$RD/suite.txt" || { echo "rebase suite failed" >&2; exit 17; }
if [ -n "${KT_REFRESH:-}" ]; then
  bash "$KT_REFRESH" > "$RD/refresh-rebase.json" 2>&1 || { echo "rebase scoreboard pull failed" >&2; exit 13; }
else
  (cd "$TREE" && python3 src/refresh.py > "$RD/refresh-rebase.json") || { echo "rebase scoreboard pull failed" >&2; exit 13; }
fi
python3 "$TOOLS/fast_patch.py" --site "$RD/deploy" --tree "$TREE" --out-zip "$RD/kicktip-site.zip" > "$RD/fast-overlay.txt"
cat "$RD/fast-overlay.txt"
# Preview the bytes that will ship, overlay included, so the compare matches production.
WR=${KT_WRANGLER:-$ROOT/wr/node_modules/.bin/wrangler}
PBRANCH=${KT_FAST_PREVIEW_BRANCH:-refresh-fast}
timeout 900 "$WR" pages deploy "$RD/deploy" --project-name "$PROJ" --branch "$PBRANCH" --commit-dirty=true > "$RD/preview-rebase.log" 2>&1 || { echo "rebase preview failed" >&2; exit 18; }
PURL=$(grep -o 'https://[0-9a-f]\{8\}\.kicktip\.pages\.dev' "$RD/preview-rebase.log" | head -n 1 || true)
[ -n "$PURL" ] || { echo "rebase preview has no URL" >&2; exit 18; }
if [ -n "${KT_BYTECMP:-}" ]; then "$KT_BYTECMP" "$RD/deploy" "$PURL" > "$RD/bytecmp-rebase.txt" || { echo "rebase bytecmp failed" >&2; exit 18; }
else python3 "$TOOLS/bytecmp.py" "$RD/deploy" "$PURL" > "$RD/bytecmp-rebase.txt" || { echo "rebase bytecmp failed" >&2; exit 18; }
fi
# Guard once more. A deploy that landed while we rebuilt is exit 20; the next full run tries again.
C2=$("$CURL" -s -m 30 -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN:-}" "https://api.cloudflare.com/client/v4/accounts/$ACCT/pages/projects/$PROJ" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['canonical_deployment']['id'])")
"$GIT" fetch origin main >/dev/null
"$GIT" show origin/main:state.json > "$RD/state-remote-2.json"
python3 "$TOOLS/fast_patch.py" --chain --state "$RD/state-remote-2.json" --live-id "$LIVE" --canonical "$C2" || { say "guard: canonical moved during rebase"; exit 20; }
NOW=$(python3 -c "import json;print(json.load(open('$RD/state-remote-2.json'))['live_sha'])")
[ "$NOW" = "$BASE_SHA" ] || { say "guard: live zip changed during rebase"; exit 20; }
NEW=$(sha256sum "$RD/kicktip-site.zip" | cut -d' ' -f1)
python3 -c "import json;json.dump({'sha':'$NEW','canonical':'$C2','base_sha':'$BASE_SHA'},open('$RD/rebase.json','w'))"
say "rebase ready sha ${NEW:0:12} canonical $C2"
