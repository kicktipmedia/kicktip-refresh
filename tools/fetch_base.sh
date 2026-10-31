#!/bin/bash
# download release 'base' into base/ and check the zip sha against state.json
set -euo pipefail; cd "$(dirname "$0")/.."; rm -rf base; mkdir -p base/s0/site
# S0 asset name comes from state.json s0_asset (templates and S0 must match; see RUNBOOK "Feature ships and the S0 merge base")
A=$(python3 -c "import json;print(json.load(open('state.json')).get('s0_asset','s0-site.tar.gz'))")
gh release download base -D base -p kicktip-site.zip -p "$A"
tar xzf "base/$A" -C base/s0/site
W=$(python3 -c "import json;print(json.load(open('state.json'))['live_sha'])"); H=$(sha256sum base/kicktip-site.zip | cut -d' ' -f1)
[ "$W" = "$H" ] || { echo "base zip sha $H != state.live_sha $W"; exit 12; }
echo "base ok ${H:0:12} s0=$A"
