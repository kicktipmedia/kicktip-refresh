#!/bin/bash
# confsim pre-ship re-base (modeled on audit2 a2kit/final_rebase.sh). Run AFTER Batch A and Batch B are live. Does NOT deploy, does NOT push.
# usage: final_rebase_c.sh <tag> -> /workspace/hub/kicktip-confsim/siteC-<tag>.zip (+ .head, .sha256) and the ship_c.sh line
set -euo pipefail; export GH_CONFIG_DIR=/workspace/kicktip-refresh/.gh
TAG=$1; C=${KT_C:-/workspace/hub/kicktip-confsim}; REPO=${KT_REPO:-$C/repo}; export KT_REPO=$REPO   # KT_C/KT_REPO/KT_CANON_ID/KT_BASE_ZIP: scratch-test overrides only
cd $REPO; [ "$(git rev-parse --abbrev-ref HEAD)" = confsim ] || { echo "not on confsim"; exit 2; }
[ -z "$(git status --porcelain)" ] || { echo "repo tree not clean: commit first"; exit 2; }
git -c credential.helper='!gh auth git-credential' fetch -q origin main || { echo "ABORT 30: cannot fetch origin/main (origin unreachable or auth failed); nothing changed"; exit 30; }   # QA N3: named exit code, not git's 128
GI=(-c user.name="KickTip Build" -c user.email=build@kicktip.invalid)   # QA B2: the box has no git identity; rebase replays commits
set +e; RB=$(git "${GI[@]}" rebase origin/main 2>&1); rc=$?; set -e
if [ $rc -ne 0 ]; then echo "$RB" | tail -5
  if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then git rebase --abort || true; echo "rebase stopped (rc $rc, conflict or replay failure; see above). Aborted; resolve by hand"; exit 3
  else echo "rebase failed before starting (rc $rc; see above)"; exit 7; fi; fi
read SHA ID ASOF <<< "$(git show origin/main:state.json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['live_sha'],d['live_id'],d['as_of'])")"
echo "main $(git rev-parse --short origin/main) live $ID sha ${SHA:0:12} as_of $ASOF; confsim $(git rev-parse --short HEAD)"
if [ -n "${KT_CANON_ID:-}" ]; then CN=$KT_CANON_ID; else CN=$(curl -s -m 30 -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" https://api.cloudflare.com/client/v4/accounts/2b5bfb9838968d7cde32f13967e882e0/pages/projects/kicktip | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['canonical_deployment']['id'])"); fi
[ "$CN" = "$ID" ] || { echo "canonical $CN != state live_id $ID: refresh or ship mid-flight, wait"; exit 4; }
R=$C/rel-$TAG; mkdir -p $R; if [ -n "${KT_BASE_ZIP:-}" ]; then cp "$KT_BASE_ZIP" $R/kicktip-site.zip; else gh release download base -R kicktipmedia/kicktip-refresh -p kicktip-site.zip -D $R --clobber; fi
[ "$(sha256sum $R/kicktip-site.zip | cut -d' ' -f1)" = "$SHA" ] || { echo "release zip sha != live_sha"; exit 5; }
Z=$C/siteC-$TAG.zip; $REPO/kits/confsim/rebuild_c.sh $R/kicktip-site.zip $Z $C/w-$TAG
n=$(grep -rlP '\xA0' $C/w-$TAG/m/assets/ccgsim-ui.js $C/w-$TAG/m/assets/ccgsim.css $C/w-$TAG/m/assets/cc5home.js $C/w-$TAG/m/assets/cc5conf.js $C/w-$TAG/m/assets/cc5pages.css $C/w-$TAG/m/assets/cc5pre.js $C/w-$TAG/m/assets/ccgbar.js $C/w-$TAG/m/assets/chat.css || true)   # QA B1: grep exits 1 when clean; rev 5 adds the three new cc5 assets
[ -z "$n" ] || { echo "literal NBSP in $n"; exit 6; }; echo "literal NBSP: 0"

echo "GUARD=$ID"; echo "next (after Creative OK + QA PASS): QA/ship_c.sh $Z $(cut -d' ' -f1 $Z.sha256) $ID $(cat $Z.head)"
