#!/bin/bash
# final3: same suites as final2 on the final3 tree; final2_unit kept as a regression on the final2 trees (its exact-diff checks are vs final1); plus final3_unit.
# final2: same suites as final1 on the final2 tree (T=work/out), plus phase4_bank without the base arg (QA method) and final2_unit.
# scn_b4: B3 suites on the B4 tree (expectations updated for 70b/8000 ms in worker_scn_a2/_b/_b2); the B3-vs-B2 delta suites run on the B3 tree (base_b3); plus the B4 suites.
# scn_b3: every earlier suite re-run on the B3 tree (T = B3, B = A2b as before, BB = B, BB2 = B2), plus the B2 suites (updated where the all-impossible lead changed) and the B3 suites. usage: bash tests/run_all_b3.sh (from the bundle root, after build-scn-b3.py --stage b3)
cd "$(dirname "$0")/.."; S4=/workspace/kicktip-scn-b4; T=work/out; B=/workspace/kicktip-scn-b/work/outa2b; BB=$S4/work/base_b; BB2=$S4/work/base_b2; ZB2=/workspace/kicktip-scn-b2/dist/kicktip-site-scn-b2-on-b.zip; Z=$S4/dist/kicktip-site-scn-b4-on-b3.zip; ZB=/workspace/kicktip-scn-b/dist/kicktip-site-scn-b-on-a2b.zip; Z0=/workspace/kicktip-router2/dist/kicktip-site-router2c-on-router1b.zip; A1B=/workspace/kicktip-scn-a2/work/base; BANK=/workspace/hub/kicktip-toolbox-1026/qbank/questions.json
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
run qbank_scn_a1 node tests/qbank_scn_a1_check.js $T
run equiv_card_a1 node tests/equiv_card_a1.js $B $T $BANK logs/cards-in-bank.json
run equiv_bank node tests/equiv_bank9.js $B $T $BANK logs/equiv-vs10d.json
run equiv_dispatch node tests/equiv_dispatch_r1_6c.js $B $T $BANK logs/equiv-dispatch.json
run equiv_parse node tests/equiv_parse_r2.js $B $T $BANK
run drift python3 tools/check_explain_drift.py $T
run drift_negative bash tests/drift_negative.sh $T
run browser_smoke python3 tests/browser/smoke_chooser.py $T logs/shots
run browser_smoke_r2 python3 tests/browser/smoke_router2.py $T logs/shots
run browser_smoke_scn_a1 python3 tests/browser/smoke_scn_a1.py $T logs/shots
run scnai_unit node tests/scnai_unit.js $T
run set_copy_a2 node tests/set_copy_a2.js $T $A1B
run worker_scn_a2 node tests/worker_scn_a2.mjs $A1B $T
run cost_scn node tests/cost_scn.js $T
run qbank_scn_a2 node tests/qbank_scn_a2.mjs $T
run eval_models_dry node tests/eval_models.js --dry --tree $T
run static_b3 python3 tests/static_checks_b3.py $ZB2 /workspace/kicktip-scn-b3/dist/kicktip-site-scn-b3-on-b2.zip
run set_scn_b node tests/set_scn_b.js $T $B
run equiv_b_bank node tests/equiv_b_bank.js $B $T $BANK logs/equiv-b-shared.json
run qbank_scn_b node tests/qbank_scn_b_check.js $T
run worker_scn_b node tests/worker_scn_b.mjs $B $T
run browser_smoke_scn_b python3 -u tests/browser/smoke_scn_b.py $T $B logs/shots
run browser_smoke_scn_a2 python3 tests/browser/smoke_scn_a2.py $T logs/shots

run browser_smoke_scn_b2 python3 -u tests/browser/smoke_scn_b2.py $T $BB logs/shots
run set_scn_b2 node tests/set_scn_b2.js $T $BB
run worker_scn_b2 node tests/worker_scn_b2.mjs $BB $T
run sweep_fold_b3 node tests/sweep_fold_b3.mjs $T
run set_scn_b3_vs_b2 node tests/set_scn_b3.js $S4/work/base_b3 $BB2
run worker_scn_b3_vs_b2 node tests/worker_scn_b3.mjs $BB2 $S4/work/base_b3
run browser_smoke_scn_b3_375 python3 -u tests/browser/smoke_scn_b3.py $T $BB logs/shots
run static_b4 python3 tests/static_checks_b4.py /workspace/kicktip-scn-b3/dist/kicktip-site-scn-b3-on-b2.zip $Z
run worker_scn_b4 node tests/worker_scn_b4.mjs $S4/work/base_b3 $T
run set2b_sor_cvc node tests/set2b_sor_cvc.js $T
run phase4_bank node /workspace/kicktip-phase4-build/tests/run_bank_p4_6c.js $T /workspace/kicktip-final1/work/base_b4
run toolbox3_routing_dark node tests/tb3/routing_check_final1.js /workspace/kicktip-scn-b4/work/base_b3 $T /workspace/hub/kicktip-toolbox-1026/qbank --out logs/routing_check_dark.json
run toolbox3_routing_vs_set2b node tests/tb3/routing_check.js /workspace/kicktip-set2b/work/outset2b $T /workspace/hub/kicktip-toolbox-1026/qbank --out logs/routing_check_vs_set2b.json
run phase4_bank_nobase node /workspace/kicktip-phase4-build/tests/run_bank_p4_6c.js $T
run final2_unit_on_final2 node tests/final2_unit.mjs /workspace/kicktip-final2/work/base_final1 /workspace/kicktip-final2/work/out
run final3_unit node tests/final3_unit.mjs /workspace/kicktip-final3/work/base_final2 $T
run final3_evalkey node tests/final3_evalkey.mjs $T
# set3m: the three Set 3 lanes on the merged tree (base = vis1c), expectations updated for #28 live and #23-#27 behind TB_SET3_IDS
BANK=/workspace/hub/kicktip-toolbox-1026/qbank/questions.json; SIM=$T/assets/ks/sim.js
node tools/gen_conf_outcome.js --sim $SIM --bundle $T/data/sim-bundle.json --out work/recount-same.json >/dev/null && node tools/gen_conf_outcome.js --sim $SIM --bundle $T/data/sim-bundle.json --out work/recount-seed777.json --seed 777 >/dev/null
run set3a_unit node tests/set3a/set3a_unit.js $T
run worker_set3a node tests/set3a/worker_set3a.mjs work/base_vis1c $T
run set3b node tests/set3b.js $T work/base_vis1c $BANK
run set3c node tests/set3c.js $T work/base_vis1c $BANK
run set3m_charter node tests/set3m_charter.js $T work/base_vis1c
for e in chromium webkit; do [ $e = webkit ] && export PLAYWRIGHT_BROWSERS_PATH=/workspace/kicktip-set3c/work/pwb; for l in a b c; do run browser_set3${l}_$e python3 -u tests/browser/smoke_set3$l.py $T $e crops/smoke work/base_vis1c; done; run browser_set3m_css_$e python3 -u tests/browser/set3m_css.py $T $e crops work/base_vis1c; done; unset PLAYWRIGHT_BROWSERS_PATH
run set3m3_routing node tests/set3m3_routing.js $T work/base_vis1c $BANK
run set3m3_cfpno node tests/set3m3_cfpno.js $T
run why2 node tests/why2.js $T
