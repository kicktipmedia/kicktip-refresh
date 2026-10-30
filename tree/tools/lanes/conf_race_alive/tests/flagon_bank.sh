#!/usr/bin/env bash
# flagon_bank.sh: the QA bank with the CEO flag ON. Scratch copy of the built tree + a flag file with the real rules hashes (written only in /tmp), then the harness emits answers
# (its neutral fixtures are expected to fail in a flag-on tree and are ignored) and QA's run_bank.py is run with --verified for the Analyst-verified conferences. Must be run from the work folder.
set -e
OUT=${1:-out-tb}; LANE=lanes/conf_race_alive; T=$(mktemp -d)/outflag
cp -a $OUT $T
node - "$T" <<'JS'
const fs = require('fs'), T = process.argv[2], b = JSON.parse(fs.readFileSync(T + '/data/tb/ccg-alive.json')), f = {};
Object.keys(b.confs).forEach(c => f[c] = { verified: true, rules_hash: b.confs[c].rules.hash, by: 'flagon_bank', date: '2026-10-26' });
fs.writeFileSync(T + '/data/ccg-rules-verified.json', JSON.stringify(f));
JS
node $LANE/tools/build_alive.js --root $T --quiet
node -e "const b=require('$T/data/tb/ccg-alive.json');console.log('flag-on verified:',Object.keys(b.confs).filter(c=>b.confs[c].verified).join(','))"
python3 core/tests/tb/run_tb_tests.py --base base --out $T --no-build --lane lanes/ref --lane $LANE --qbank "$PWD/qbank_t05" --skip-mutation > /dev/null 2>&1 || true
ANS=$PWD/out-qbank-answers.json; ids=$(python3 -c "import json;print(','.join(json.load(open('$ANS')).keys()))")
( cd qbank_t05; python3 run_bank.py --answers $ANS --ids $ids --verified American,big12,midam,pac12,sec -q | grep "FAIL\|TOTAL\|RESULT\|x \[" )
( cd qbank_t05; python3 run_bank.py --answers $ANS --ids $ids --verified American,big12,midam,pac12,sec -q | grep -q "RESULT: PASS" ) && echo "FLAGON_BANK PASS" || { echo "FLAGON_BANK FAIL"; exit 1; }
