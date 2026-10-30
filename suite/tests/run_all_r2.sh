#!/bin/bash
# router2: every suite, one log per suite in logs/. usage: bash tests/run_all_r2.sh   (run from the bundle root after build-router2.py)
cd "$(dirname "$0")/.."; T=work/outrouter2; B=/workspace/kicktip-router2/work/base; Z=dist/kicktip-site-router2b-on-router1b.zip; Z0=/workspace/kicktip-router1/dist/kicktip-site-router1b-on-10d.zip; BANK=/workspace/hub/kicktip-toolbox-1026/qbank/questions.json
run() { n=$1; shift; "$@" > logs/$n.log 2>&1; rc=$?; echo "$n rc=$rc :: $(grep -E '[0-9]+ checks, [0-9]+ failed|identical|ALL DIFFS|drift|PASS$' logs/$n.log | tail -2 | tr '\n' ' ')"; }
run set2b_matcher node tests/set2b_matcher.js $T
run set2b_data node tests/set2b_data.js $T
run set2c node tests/set2c.js $T
run set9_polish node tests/set9_polish.js $T $B
run worker_dark10 node tests/worker_dark10.mjs $T
run worker_flagoff1 node tests/worker_flagoff1.mjs $B $T
run worker_router1 node tests/worker_router1.mjs $B $T
run set_router1 node tests/set_router1.js $T
run set_router2 node tests/set_router2.js $T
run worker_router2 node tests/worker_router2.mjs $B $T
run static_r1 python3 tests/static_checks_r2.py $Z $Z0
run equiv_bank node tests/equiv_bank9.js $B $T $BANK logs/equiv-vs10d.json
run equiv_dispatch node tests/equiv_dispatch_r1.js $B $T $BANK logs/equiv-dispatch.json
run equiv_parse node tests/equiv_parse_r2.js $B $T $BANK
run drift python3 tools/check_explain_drift.py $T
run drift_negative bash tests/drift_negative.sh $T
run browser_smoke python3 tests/browser/smoke_chooser.py $T logs/shots
run browser_smoke_r2 python3 tests/browser/smoke_router2.py $T logs/shots
