#!/bin/bash
# final3: same suites as final2 on the final3 tree; final2_unit kept as a regression on the final2 trees (its exact-diff checks are vs final1); plus final3_unit.
# final2: same suites as final1 on the final2 tree (T=work/out), plus phase4_bank without the base arg (QA method) and final2_unit.
# scn_b4: B3 suites on the B4 tree (expectations updated for 70b/8000 ms in worker_scn_a2/_b/_b2); the B3-vs-B2 delta suites run on the B3 tree (base_b3); plus the B4 suites.
# scn_b3: every earlier suite re-run on the B3 tree (T = B3, B = A2b as before, BB = B, BB2 = B2), plus the B2 suites (updated where the all-impossible lead changed) and the B3 suites. usage: bash tests/run_all_b3.sh (from the bundle root, after build-scn-b3.py --stage b3)
cd "$(dirname "$0")/.."; S4=/workspace/kicktip-scn-b4; T=work/outb; B=/workspace/kicktip-scn-b/work/outa2b; BB=$S4/work/base_b; BB2=$S4/work/base_b2; ZB2=/workspace/kicktip-scn-b2/dist/kicktip-site-scn-b2-on-b.zip; Z=$S4/dist/kicktip-site-scn-b4-on-b3.zip; ZB=/workspace/kicktip-scn-b/dist/kicktip-site-scn-b-on-a2b.zip; Z0=/workspace/kicktip-router2/dist/kicktip-site-router2c-on-router1b.zip; A1B=/workspace/kicktip-scn-a2/work/base; BANK=/workspace/hub/kicktip-toolbox-1026/qbank/questions.json
run() { n=$1; shift; "$@" > logs/$n.log 2>&1; rc=$?; echo "$n rc=$rc :: $(grep -E '[0-9]+ checks, [0-9]+ failed|identical|ALL DIFFS|drift|PASS$' logs/$n.log | tail -2 | tr '\n' ' ')"; }
# final3: same suites as final2 on the final3 tree; final2_unit kept as a regression on the final2 trees (its exact-diff checks are vs final1); plus final3_unit.
# scn_b4: B3 suites on the B4 tree (expectations updated for 70b/8000 ms in worker_scn_a2/_b/_b2); the B3-vs-B2 delta suites run on the B3 tree (base_b3); plus the B4 suites.
run worker_dark10 node tests/worker_dark10.mjs $T
run worker_flagoff1 node tests/worker_flagoff1.mjs /workspace/kicktip-deploy-ee333cae/site $T
run worker_router1 node tests/worker_router1.mjs $B $T
run worker_scn_a2 node tests/worker_scn_a2.mjs $A1B $T
run worker_scn_b2 node tests/worker_scn_b2.mjs $BB $T
run worker_scn_b4 node tests/worker_scn_b4.mjs $S4/work/base_b3 $T
run set2b_sor_cvc node tests/set2b_sor_cvc.js $T
run final3_unit node tests/final3_unit.mjs /workspace/kicktip-final3/work/base_final2 $T
