#!/bin/bash
# fast suite subset against a refreshed site tree. usage: suite_subset.sh <site> <logdir>
T=$(realpath "$1"); L=$(realpath -m "$2"); B=$(realpath "${3:-$1}"); mkdir -p $L; cd "$(dirname "$0")/../suite"; fail=0
run() { n=$1; shift; "$@" > $L/$n.log 2>&1; rc=$?; [ $rc = 0 ] || fail=1; echo "$n rc=$rc :: $(grep -E '[0-9]+ checks, [0-9]+ failed' $L/$n.log | tail -1)"; }
run set2b_matcher node tests/set2b_matcher.js $T
run set2b_data node tests/set2b_data.js $T
run set2c node tests/set2c.js $T
run set9_polish node tests/set9_polish.js $T
run worker_dark10 node tests/worker_dark10.mjs $T
run set_router1 node tests/set_router1.js $T
run set_router2 node tests/set_router2.js $T
run qbank_scn_a1 node tests/qbank_scn_a1_check.js $T
run drift python3 tools/check_explain_drift.py $T
run scnai_unit node tests/scnai_unit.js $T
run cost_scn node tests/cost_scn.js $T
run qbank_scn_a2 node tests/qbank_scn_a2.mjs $T
run set_scn_b node tests/set_scn_b.js $T $B
run qbank_scn_b node tests/qbank_scn_b_check.js $T
run set3m3_cfpno node tests/set3m3_cfpno.js $T
run why2 node tests/why2.js $T
echo SUITE_DONE fail=$fail; exit $fail
