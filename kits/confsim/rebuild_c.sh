#!/bin/bash
# Rebuild the confsim (cc5) zip on top of ANY live base zip (release 'base' kicktip-site.zip whose sha = main state.json live_sha). Does NOT deploy.
# usage: rebuild_c.sh <live_base_zip> <out_zip> <work_dir(new)>
# Recipe: unzip live -> kit/feat_c.py (anchored, asserting patch of assets/ccgsim-ui.js + append to assets/ccgsim.css) -> bump_all (?v= tokens) -> mkzip
# Assets only: no HTML template, data or build.py change, so S0 and the refresh pipeline are unaffected (apply_data carries live assets forward; the ?v= tokens are token-only changes).
set -euo pipefail
BASE=$(realpath "$1"); OUTZ=$(realpath -m "$2"); W=$(realpath -m "$3"); K=$(cd "$(dirname "$0")" && pwd)
REPO=${KT_REPO:-/workspace/hub/kicktip-confsim/repo}
[ ! -e "$W" ] || { echo "work dir $W exists (no rm -rf)"; exit 2; }
[ "$(git -C $REPO rev-parse --abbrev-ref HEAD)" = confsim ] || { echo "repo not on confsim"; exit 3; }
[ -z "$(git -C $REPO status --porcelain)" ] || { echo "repo tree not clean: commit first"; exit 3; }
HEAD=$(git -C $REPO rev-parse HEAD)
for f in feat_c.py cc5.js cc5.css rebuild_c.sh; do cmp -s "$K/$f" <(git -C $REPO show HEAD:kits/confsim/$f) || { echo "kit $f ($K) differs from kits/confsim/$f committed at HEAD"; exit 3; }; done   # vs the committed blob, not the working copy
mkdir -p "$W/m" && (cd "$W/m" && unzip -q "$BASE")
python3 "$REPO/kits/confsim/feat_c.py" "$W/m"
python3 $REPO/tree/tools/feature/bump_all.py "$W/m"
python3 /workspace/hub/kicktip-trim/mkzip.py "$W/m" "$OUTZ"; echo "$HEAD" > "$OUTZ.head"; sha256sum "$OUTZ" | tee "$OUTZ.sha256"
echo "built from confsim $HEAD on base $(sha256sum "$BASE" | cut -c1-12)"
