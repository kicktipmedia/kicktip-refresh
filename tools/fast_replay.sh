#!/bin/bash
# Replay the fast scores path on a frozen ESPN artifact and a base zip. No network and no deploy.
# The artifact is the "Keep fetched ESPN inputs" tarball: data/store, data/cache, data/out/refresh_log.json.
# usage: tools/fast_replay.sh <inputs.tgz> <base.zip>
set -euo pipefail
[ $# -eq 2 ] || { echo "usage: tools/fast_replay.sh <inputs.tgz> <base.zip>" >&2; exit 2; }
IN=$1; ZIP=$2
ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/tree" "$WORK/site"
tar xzf "$IN" -C "$WORK/tree"
unzip -q "$ZIP" -d "$WORK/site"
if [ ! -f "$WORK/tree/data/ref/conf_2026.json" ]; then
  mkdir -p "$WORK/tree/data/ref"
  cp "$ROOT/tree/data/ref/conf_2026.json" "$WORK/tree/data/ref/conf_2026.json"
fi
STAMP=""
if [ -f "$WORK/tree/data/out/refresh_log.json" ]; then
  STAMP=$(python3 -c "import json;print(json.load(open('$WORK/tree/data/out/refresh_log.json')).get('refreshed_mt',''))")
fi
echo "fast replay $(basename "$IN") onto $(basename "$ZIP")"
python3 "$ROOT/tools/fast_patch.py" --site "$WORK/site" --tree "$WORK/tree" ${STAMP:+--stamp "$STAMP"} --check
