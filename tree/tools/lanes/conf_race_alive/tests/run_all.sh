#!/usr/bin/env bash
# run_all.sh: build + every lane suite. usage (from the lane's work folder, e.g. /workspace/kicktip-tb-alive): bash lanes/conf_race_alive/tests/run_all.sh [--full]
# The QA bank copy "qbank_t05" is the official bank with the 13 T05 (conf_race_alive) rows set active:true (the official file ships them active:false while the tool is dark); the official bank is never written.
set -e
LANE=lanes/conf_race_alive; OUT=out-tb; QSRC=/workspace/hub/kicktip-toolbox-1026/qbank
rm -rf qbank_t05; cp -a $QSRC qbank_t05; rm -rf qbank_t05/__pycache__
python3 - <<'PY'
import json
p='qbank_t05/questions.json'; q=json.load(open(p)); rows=q['rows'] if isinstance(q,dict) else q
n=0
for r in rows:
    if r['id'].startswith('T05-'): r['active']=True; n+=1
json.dump(q,open(p,'w')); print('T05 rows activated in the COPY:', n)
PY
python3 core/tools/build_tb.py --base base --out $OUT --lane lanes/ref --lane $LANE | tail -2
python3 $LANE/tests/tb/gen_conf_race_alive_fixtures.py $OUT | cut -c1-160
bash $LANE/tests/flagon_bank.sh $OUT
python3 core/tests/tb/run_tb_tests.py --base base --out $OUT --lane lanes/ref --lane $LANE --qbank "$PWD/qbank_t05" --strict-qbank --browser chromium,webkit
node $LANE/tests/lane_extra_test.js --root $OUT
node $LANE/tests/flagon_test.js --root $OUT
node $LANE/tests/verified_out_test.js --root $OUT
python3 $LANE/tests/wiring_test.py $OUT
node $LANE/tools/sensitivity.js --root $OUT --json $LANE/SENSITIVITY.json | tail -3
python3 $LANE/tests/gallery_alive.py $OUT
if [ "$1" = "--full" ]; then node $LANE/tests/alive_test.js --root $OUT --proof $OUT.ccg-alive-proof.json | tail -2; else node $LANE/tests/alive_test.js --quick --root $OUT --proof $OUT.ccg-alive-proof.json | tail -2; fi
echo RUN_ALL_DONE
