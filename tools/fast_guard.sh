#!/bin/bash
# Read Cloudflare's canonical deployment and origin/main state.json.
# Print "ok" when both still name the zip this fast run patched.
# Print "yield: another deploy landed; next tick retries" and exit 0 otherwise.
# usage: tools/fast_guard.sh --base-sha SHA
# curl and git are the real commands unless KT_CURL / KT_GIT point at a stand-in.
set -euo pipefail
BASE=""
while [ $# -gt 0 ]; do case $1 in --base-sha) BASE=$2; shift 2;; *) echo "bad arg $1" >&2; exit 2;; esac; done
[ -n "$BASE" ] || { echo "need --base-sha" >&2; exit 2; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
CURL=${KT_CURL:-curl}
GIT=${KT_GIT:-git}
ACCT=${CLOUDFLARE_ACCOUNT_ID:-2b5bfb9838968d7cde32f13967e882e0}
TMP=$(mktemp -d)
"$CURL" -s -m 30 -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN:-}" \
  "https://api.cloudflare.com/client/v4/accounts/$ACCT/pages/projects/kicktip" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['canonical_deployment']['id'])" > "$TMP/can"
"$GIT" fetch origin main >/dev/null
"$GIT" show origin/main:state.json > "$TMP/state.json"
python3 "$ROOT/tools/fast_patch.py" --yield-check --state "$TMP/state.json" --canonical "$(cat "$TMP/can")" --base-sha "$BASE"
rm -rf "$TMP"
