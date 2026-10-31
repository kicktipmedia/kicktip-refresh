#!/bin/bash
# Rebuild the S0 merge base (release 'base' asset s0-site.tar.gz) with the CURRENT tree/src templates, at the live as-of, from the saved
# pipeline inputs of that as-of (release asset s0-inputs.tar.gz = tree/data/store + tree/data/out + tree/data/cache/scoreboard, written by publish_base --s0-inputs).
# Use it in every feature ship that changes HTML the pipeline generates (tables, rows, cards, Sources strip, method page): port the same change
# into tree/src/build.py first, then run this, then the merge check below; only then deploy + publish_base.
# usage (box, from a clone): export GH_CONFIG_DIR=/workspace/kicktip-refresh/.gh; tools/rebuild_s0.sh <out_dir> [--check <feature_or_live_zip>] [--upload]
#   --check ZIP : 3-way merge dry run (merge3.py) of ZIP + (new S0 -> new S0 restamped) and of ZIP + (old S0 -> new S0); fails on any conflict
#   --upload    : backs up the current s0-site.tar.gz to <out_dir>/s0-site.prev.tar.gz, then uploads the new one (--clobber). Production is not touched.
set -euo pipefail
cd "$(dirname "$0")/.."; OUT=$1; shift; CHECK=""; UP=0
while [ $# -gt 0 ]; do case $1 in --check) CHECK=$2; shift 2;; --upload) UP=1; shift;; *) echo "bad arg $1"; exit 2;; esac; done
rm -rf "$OUT"; mkdir -p "$OUT/tree" "$OUT/old"
gh release download base -D "$OUT" -p s0-inputs.tar.gz -p s0-site.tar.gz
tar xzf "$OUT/s0-site.tar.gz" -C "$OUT/old"; mv "$OUT/s0-site.tar.gz" "$OUT/s0-site.prev.tar.gz"
tar cf - --exclude=./build --exclude=./data/out --exclude=./data/store -C tree . | tar xf - -C "$OUT/tree"
tar xzf "$OUT/s0-inputs.tar.gz" -C "$OUT/tree"
ASOF=$(python3 -c "import json;print(json.load(open('state.json'))['as_of'])")
GOT=$(python3 -c "import json;print(json.load(open('$OUT/tree/data/out/refresh_log.json'))['refreshed_mt'])")
[ "$ASOF" = "$GOT" ] || { echo "s0-inputs as-of $GOT != live as-of $ASOF: refusing"; exit 3; }
(cd "$OUT/tree" && KT_ASOF="$ASOF" python3 src/build.py > ../build.log 2>&1) || { tail -n 5 "$OUT/build.log"; exit 4; }
REN="$OUT/tree/build/site"; NEW="$OUT/new"; cp -r "$OUT/old" "$NEW"
# templates only change HTML: overlay the re-rendered .html onto the old S0 and keep its JSON byte-identical (float noise in a re-run would make JSON leaves conflict)
(cd "$REN" && find . -name '*.html') | while read -r f; do mkdir -p "$NEW/$(dirname "$f")"; cp "$REN/$f" "$NEW/$f"; done
B=$(python3 -c "import json;print(json.load(open('$REN/data/sim-bundle.json'))['as_of'])"); [ "$B" = "$ASOF" ] || { echo "rebuilt as_of $B != $ASOF"; exit 4; }
echo "files differing old S0 -> new S0:"; diff -rq "$OUT/old" "$NEW" | sed 's/^/  /' | head -n 40 || true
if [ -n "$CHECK" ]; then
  mkdir -p "$OUT/chk/L" && (cd "$OUT/chk/L" && unzip -q "$(realpath "$OLDPWD/$CHECK" 2>/dev/null || realpath "$CHECK")")
  cp -r "$OUT/chk/L" "$OUT/chk/out"
  python3 tree/tools/merge3.py "$OUT/chk/L" "$OUT/old" "$NEW" "$OUT/chk/out" "$OUT/chk/merge.json" '[]' >/dev/null
  python3 -c "import json,sys;r=json.load(open('$OUT/chk/merge.json'));print('merge check (live + old->new S0): conflicts',r['conflict'],list(r['json_conflicts']));sys.exit(1 if r['conflict'] or r['json_conflicts'] else 0)"
fi
tar czf "$OUT/s0-site.tar.gz" -C "$NEW" .; echo "new s0 sha $(sha256sum "$OUT/s0-site.tar.gz" | cut -d' ' -f1)  prev $(sha256sum "$OUT/s0-site.prev.tar.gz" | cut -d' ' -f1)"
if [ $UP = 1 ]; then gh release upload base "$OUT/s0-site.tar.gz" --clobber; echo "uploaded; rollback: gh release upload base $OUT/s0-site.prev.tar.gz (renamed to s0-site.tar.gz) --clobber"; fi
