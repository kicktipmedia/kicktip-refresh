#!/bin/bash
# scn_a2: every A1 suite re-run on the A2 tree (base = A1b), plus the new scenario-facts suite. usage: bash tests/run_all_a2.sh  (from the bundle root, after build-scn-a1.py)
cd "$(dirname "$0")/.."; T=work/outscna2; B=work/base; Z=dist/kicktip-site-scn-a2-on-a1b.zip; Z0=/workspace/kicktip-router2/dist/kicktip-site-router2c-on-router1b.zip; BANK=/workspace/hub/kicktip-toolbox-1026/qbank/questions.json
run() { n=$1; shift; "$@" > logs/$n.log 2>&1; rc=$?; echo "$n rc=$rc :: $(grep -E '[0-9]+ checks, [0-9]+ failed|identical|ALL DIFFS|drift|PASS$' logs/$n.log | tail -2 | tr '\n' ' ')"; }
run set2b_matcher node tests/set2b_matcher.js $T
run set2b_data node tests/set2b_data.js $T
run set2c node tests/set2c.js $T
run set9_polish node tests/set9_polish.js $T $B
run worker_dark10 node tests/worker_dark10.mjs $T
run worker_flagoff1 node tests/worker_flagoff1.mjs /workspace/kicktip-deploy-ee333cae/site $T
run worker_router1 node tests/worker_router1.mjs $B $T
run set_router1 node tests/set_router1.js $T
run set_router2 node tests/set_router2.js $T
run worker_router2 node tests/worker_router2.mjs $B $T
run static_a2 python3 tests/static_checks_a2.py $Z /workspace/kicktip-scn-a1/dist/kicktip-site-scn-a1b-on-router2c.zip
run set_scn_a1_on_a2 node tests/set_scn_a1_on_a2.js $T $B
run qbank_scn_a1 node tests/qbank_scn_a1_check.js $T
run equiv_card_a1 node tests/equiv_card_a1.js $B $T $BANK logs/cards-in-bank.json
run equiv_bank node tests/equiv_bank9.js $B $T $BANK logs/equiv-vs10d.json
run equiv_dispatch node tests/equiv_dispatch_r1.js $B $T $BANK logs/equiv-dispatch.json
run equiv_parse node tests/equiv_parse_r2.js $B $T $BANK
run drift python3 tools/check_explain_drift.py $T
run drift_negative bash tests/drift_negative.sh $T
run browser_smoke python3 tests/browser/smoke_chooser.py $T logs/shots
run browser_smoke_r2 python3 tests/browser/smoke_router2.py $T logs/shots
run browser_smoke_scn_a1 python3 tests/browser/smoke_scn_a1.py $T logs/shots
run scnai_unit node tests/scnai_unit.js
run set_copy_a2 node tests/set_copy_a2.js $T $B
run worker_scn_a2 node tests/worker_scn_a2.mjs $B $T
run cost_scn node tests/cost_scn.js
run qbank_scn_a2 node tests/qbank_scn_a2.mjs $T
run eval_models_dry node tests/eval_models.js --dry
run browser_smoke_scn_a2 python3 tests/browser/smoke_scn_a2.py $T logs/shots
