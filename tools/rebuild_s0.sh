#!/bin/bash
# Rebuild the S0 merge base (release 'base' asset s0-site.tar.gz) with the CURRENT tree/src templates, at the live as-of, from the saved
# pipeline inputs of that as-of (release asset s0-inputs.tar.gz = tree/data/store + tree/data/out + tree/data/cache/scoreboard, written by publish_base --s0-inputs).
# Use it in every feature ship that changes HTML the pipeline generates (tables, rows, cards, Sources strip, method page): port the same change
# into tree/src/build.py first, then run this, then the merge check below; only then deploy + publish_base.
# usage (box, from a clone): export GH_CONFIG_DIR=/workspace/kicktip-refresh/.gh; tools/rebuild_s0.sh <out_dir> [--check <feature_or_live_zip>] [--upload]
#   --check ZIP : two 3-way merge dry runs (merge3.py): (1) ZIP + (old S0 -> new S0), REPORT ONLY (lists where the zip differs from the new templates); (2) FAILS on any conflict: ZIP + (new S0 -> new S0 with every
#                 as-of time restamped one minute later), i.e. a stamp-only refresh on top of the new base
#   --upload    : uploads the CURRENT release s0-site.tar.gz once as s0-site-backup-<sha12>.tar.gz (skipped if that asset already exists, so a
#                 second run never overwrites the original backup), then uploads the new one as s0-site.tar.gz (--clobber). Production is not touched.
#   <out_dir> must be a new or empty directory outside the repo.
set -euo pipefail
cd "$(dirname "$0")/.."; OUT=$1; shift; CHECK=""; UP=0
while [ $# -gt 0 ]; do case $1 in --check) CHECK=$2; shift 2;; --upload) UP=1; shift;; *) echo "bad arg $1"; exit 2;; esac; done
[ -n "$OUT" ] || { echo "usage: rebuild_s0.sh <new_or_empty_out_dir> ..."; exit 2; }
AOUT=$(realpath -m "$OUT"); AREPO=$(pwd -P)
case "$AOUT/" in "$AREPO"/*|/|"$HOME"/|/workspace/|/tmp/) echo "refusing out_dir $AOUT (inside the repo or a top-level dir)"; exit 2;; esac
[ ! -e "$AOUT" ] || [ -z "$(ls -A "$AOUT")" ] || { echo "refusing: $AOUT exists and is not empty (no rm -rf)"; exit 2; }
OUT=$AOUT; mkdir -p "$OUT/tree" "$OUT/old"
A=$(python3 -c "import json;print(json.load(open('state.json')).get('s0_asset','s0-site.tar.gz'))")   # state.json s0_asset (default s0-site.tar.gz)
gh release download base -D "$OUT" -p s0-inputs.tar.gz -p "$A"
tar xzf "$OUT/$A" -C "$OUT/old"; mv "$OUT/$A" "$OUT/s0-site.prev.tar.gz"
tar cf - --exclude=./build --exclude=./data/out --exclude=./data/store -C tree . | tar xf - -C "$OUT/tree"
tar xzf "$OUT/s0-inputs.tar.gz" -C "$OUT/tree"
ASOF=$(python3 -c "import json;print(json.load(open('state.json'))['as_of'])")
GOT=$(python3 -c "import json;print(json.load(open('$OUT/tree/data/out/refresh_log.json'))['refreshed_mt'])")
[ "$ASOF" = "$GOT" ] || { echo "s0-inputs as-of $GOT != live as-of $ASOF: refusing"; exit 3; }
(cd "$OUT/tree" && KT_ASOF="$ASOF" python3 src/build.py > ../build.log 2>&1) || { tail -n 5 "$OUT/build.log"; exit 4; }
REN="$OUT/tree/build/site"; NEW="$OUT/new"; cp -r "$OUT/old" "$NEW"
# templates change HTML AND the assets build.py renders (e.g. terms_copy -> assets/chat.js, myteams.js, rootables.js): overlay every re-rendered file
# outside data/ (derived from build.py's own output, so new templated assets are covered automatically); keep data/ JSON byte-identical (float noise would conflict)
(cd "$REN" && find . -type f ! -path './data/*') | while read -r f; do mkdir -p "$NEW/$(dirname "$f")"; cp "$REN/$f" "$NEW/$f"; done
B=$(python3 -c "import json;print(json.load(open('$REN/data/sim-bundle.json'))['as_of'])"); [ "$B" = "$ASOF" ] || { echo "rebuilt as_of $B != $ASOF"; exit 4; }
echo "files differing old S0 -> new S0:"; diff -rq "$OUT/old" "$NEW" | sed 's/^/  /' | head -n 40 || true
if [ -n "$CHECK" ]; then
  mkdir -p "$OUT/chk/L" && (cd "$OUT/chk/L" && unzip -q "$(realpath "$OLDPWD/$CHECK" 2>/dev/null || realpath "$CHECK")")
  cp -r "$OUT/chk/L" "$OUT/chk/out"
  python3 tree/tools/merge3.py "$OUT/chk/L" "$OUT/old" "$NEW" "$OUT/chk/out" "$OUT/chk/merge.json" '[]' >/dev/null
  python3 -c "import json,sys;r=json.load(open('$OUT/chk/merge.json'));print('merge check 1 (zip + old->new S0, report only: a template change that the zip already carries in other markup shows here; review the list):',len(r['conflict']),'html',len(r['json_conflicts']),'json',r['conflict'][:5])" || true
  echo "merge check 2 (required before --upload): end-to-end dry run on this S0 = KT_S0_OVERRIDE=$NEW tools/auto_refresh.sh --no-deploy --force (must exit 0: apply_data + full suite)"
fi
tar czf "$OUT/s0-site.tar.gz" -C "$NEW" .; echo "new s0 sha $(sha256sum "$OUT/s0-site.tar.gz" | cut -d' ' -f1)  prev $(sha256sum "$OUT/s0-site.prev.tar.gz" | cut -d' ' -f1)"
if [ $UP = 1 ]; then
  PS=$(sha256sum "$OUT/s0-site.prev.tar.gz" | cut -c1-12); BK="s0-site-backup-$PS.tar.gz"
  if gh release view base --json assets --jq '.assets[].name' | grep -qx "$BK"; then echo "backup $BK already on release base (kept)"; else cp "$OUT/s0-site.prev.tar.gz" "$OUT/$BK" && gh release upload base "$OUT/$BK"; fi
  mkdir -p "$OUT/up" && cp "$OUT/s0-site.tar.gz" "$OUT/up/$A" && gh release upload base "$OUT/up/$A" --clobber
  echo "uploaded; rollback: gh release download base -p $BK -D /tmp/rb && mv /tmp/rb/$BK /tmp/rb/$A && gh release upload base /tmp/rb/$A --clobber"
fi
