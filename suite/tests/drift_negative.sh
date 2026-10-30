#!/bin/bash
# negative test for the explain_site drift check: a one-word change to the Method page text must make it fail (exit 1)
set -e; cd "$(dirname "$0")/.."; T=${1:-work/out7}; D=$(mktemp -d); cp -r $T/assets $T/method $T/index.html $D/
python3 - "$D" <<'P'
import sys; p=sys.argv[1]+'/method/index.html'; s=open(p,encoding='utf-8').read(); t=s.replace('We tested the models by replaying','We tested the models by re-playing',1); assert s!=t; open(p,'w',encoding='utf-8').write(t)
P
python3 tools/check_explain_drift.py $T >/dev/null && echo "clean tree: exit 0 (expected)"
if python3 tools/check_explain_drift.py $D >/dev/null; then echo "FAIL: drift not caught"; exit 1; else echo "drifted tree: exit 1 (expected) PASS"; fi
