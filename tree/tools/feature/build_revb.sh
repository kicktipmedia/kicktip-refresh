#!/bin/bash
# merged rev b = siteMerged (fd1b7739) + revb_fix.py + token bump + bake verify. usage: build_revb.sh <outdir> <zip>
set -euo pipefail; H=/workspace/hub/kicktip-merge; O=$1
rm -rf $O; mkdir -p $O; (cd $O && unzip -q $H/siteMerged.zip)
python3 $H/revb/revb_fix.py $O >/dev/null
python3 $H/revb/revb2_fix.py $O >/dev/null
python3 $H/repo/tree/tools/feature/bump_all.py $O
node $H/repo/tree/tools/bake_static.js $O --verify >/dev/null
python3 /workspace/hub/kicktip-trim/mkzip.py $O $2
sha256sum $2
