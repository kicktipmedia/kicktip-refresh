#!/bin/bash
# Rebuild the Batch B zip (Batch A head/footer layer + cap 8 + share cards) on top of ANY live base zip (the release kicktip-site.zip whose sha = main state.json live_sha).
# Only from a committed, clean batchB head. Does NOT deploy. usage: rebuild_b.sh <live_base_zip> <out_zip> <work_dir(new)>
# Recipe: unzip live -> unbake -> merge3(release S0 -> S0 rebuilt from batchB HEAD) -> live-only assets (kit/assets) -> feat.py -> feat_blend.py
#         -> bake --check, --verify -> bump_all -> mkzip. Writes <out_zip>.head (batchB commit) and <out_zip>.sha256.
set -euo pipefail
BASE=$(realpath "$1"); OUTZ=$(realpath -m "$2"); W=$(realpath -m "$3"); K=$(cd "$(dirname "$0")" && pwd)
REPO=${KT_B_REPO:-/workspace/hub/kicktip-batchB/repo}; T=$REPO/tree/tools; export GH_CONFIG_DIR=/workspace/kicktip-refresh/.gh
[ ! -e "$W" ] || { echo "work dir $W exists (no rm -rf)"; exit 2; }
case "$(git -C $REPO rev-parse --abbrev-ref HEAD)" in batchB|batchB-rehearse) ;; *) echo "repo not on batchB"; exit 3;; esac
[ -z "$(git -C $REPO status --porcelain)" ] || { echo "repo tree not clean: commit first"; git -C $REPO status --short | head; exit 3; }
HEAD=$(git -C $REPO rev-parse HEAD); mkdir -p "$W"
(cd $REPO && tools/rebuild_s0.sh "$W/s0" > "$W/s0.log" 2>&1) || { tail -5 "$W/s0.log"; echo "rebuild_s0 failed"; exit 4; }
# resolved s0 asset check (QA r3): state.json must name s0-site.tar.gz and the release copy merged against must be Batch A's s0 (5b375ecf...)
S0_EXPECT=${KT_B_S0_LIVE:-5b375ecf6afb2f9c6b61ee3fe9a5aa1823fa1ca49c0dc61ec9009a48bd05988b}
S0A=$(python3 -c "import json;print(json.load(open('$REPO/state.json')).get('s0_asset','s0-site.tar.gz'))"); [ "$S0A" = s0-site.tar.gz ] || { echo "state.json resolves s0 asset to $S0A, want s0-site.tar.gz"; exit 7; }
S0H=$(sha256sum "$W/s0/s0-site.prev.tar.gz" | cut -d' ' -f1); [ "$S0H" = "$S0_EXPECT" ] || { echo "resolved $S0A sha $S0H != expected $S0_EXPECT"; exit 7; }
mkdir "$W/L" && (cd "$W/L" && unzip -q "$BASE") && node $T/bake_static.js "$W/L" --unbake > /dev/null
cp -a "$W/L" "$W/F"; python3 $T/merge3.py "$W/L" "$W/s0/old" "$W/s0/new" "$W/F" "$W/merge.json" > "$W/merge.out"
python3 - "$W/merge.json" <<'P'
import json,sys; d=json.load(open(sys.argv[1])); known={'index.html','sitemap.xml','conference/american/simulator/index.html','assets/rootables.js'}   # rootables.js: overwritten by kit/assets right after (batchB: MAXROWS 8 on both sides)
bad=[c for c in d['conflict'] if c.split(' ')[0] not in known]; print('merge3 merged',len(d['merged']),'conflicts',d['conflict'])
ml=[m for m in d['missing_live'] if m not in ('playoff/index.html','top25/index.html')]   # S0-only pages live redirects away
sys.exit(5 if bad or ml or d['json_conflicts'] else 0)
P
cp "$K"/assets/* "$W/F/assets/"; python3 "$K/feat.py" "$W/F"; python3 "$K/feat_blend.py" "$W/F"
git -C $REPO diff --quiet "$HEAD" || { echo "repo changed during the build"; exit 6; }
cp -a "$W/F" "$W/m"; node $T/bake_static.js "$W/m" --check; node $T/bake_static.js "$W/m" --verify; KT_OG_CACHE="$W/ogcache" python3 $T/og/og_cards.py "$W/m" --report "$W/og_cards.json"; python3 $T/feature/bump_all.py "$W/m"
python3 /workspace/hub/kicktip-trim/mkzip.py "$W/m" "$OUTZ"; echo "$HEAD" > "$OUTZ.head"; sha256sum "$OUTZ" | tee "$OUTZ.sha256"
echo "built from batchB $HEAD on base $(sha256sum "$BASE" | cut -c1-12)"
