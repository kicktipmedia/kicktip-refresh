#!/bin/bash
# Offline test for tools/wait_canonical.sh (no network, no Cloudflare). Uses the real prod.log of run 45099256261.
set -u
cd "$(dirname "$0")/../.."; W=tools/wait_canonical.sh; LOG=tools/tests/fixtures/prod-45099256261.log
T=$(mktemp -d); NEW=0e5c2b13-ed0d-491a-aba0-0c342ac20562; OLD=3e57e577-091d-417d-ae22-ad007204cb7d; F=0
# fake canonical reader: prints line N of $T/seq on call N (last line repeats)
mk() { printf '%s\n' "$@" > $T/seq; echo 0 > $T/n; }
CMD="n=\$((\$(cat $T/n)+1)); echo \$n > $T/n; sed -n \"\${n}p\" $T/seq | grep . || tail -n 1 $T/seq"
run() { KT_CANON_SLEEP=0 KT_CANON_TRIES=${TR:-5} KT_CANON_CMD="$CMD" bash $W "$1" $OLD 2>$T/err; }
chk() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got '$2' want '$3' ($(cat $T/err))"; F=$((F+1)); fi; }
mk $NEW;                 o=$(run $LOG); chk "immediate" "$?:$o" "0:$NEW"
mk $OLD $OLD $NEW;       o=$(run $LOG); chk "Nov 22 lag: old twice, then new" "$?:$o" "0:$NEW"; chk "reads used" "$(cat $T/n)" 3
mk "" "" $NEW;           o=$(run $LOG); chk "API unreadable twice, then new" "$?:$o" "0:$NEW"
mk $OLD;                 o=$(run $LOG); chk "still old after all tries" "$?" 2; chk "tries" "$(cat $T/n)" 5
mk 11111111-aaaa-bbbb-cccc-000000000000; o=$(run $LOG); chk "someone else deployed" "$?" 3
echo "no url here" > $T/empty.log; mk $NEW; o=$(run $T/empty.log); chk "no deploy URL" "$?" 1
rm -rf $T; echo "wait_canonical_test: $F failed"; exit $F
