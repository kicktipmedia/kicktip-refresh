#!/bin/bash
# After a Production deploy, wait until Cloudflare's canonical deployment is that deploy, then print its full id.
# Cloudflare's project API can keep returning the previous canonical for a few seconds after wrangler reports
# "Deployment complete" (run 45099256261, Nov 22: deploy finished 02:27:06Z, read at 02:27:09Z still showed the old id).
# A single read then failed the run (21) after the site had changed, state.json was never recorded,
# and every later run stopped at the guard (20).
# usage: wait_canonical.sh <prod.log> <previous live id>
# exit 0: prints the new canonical id (its 8-char prefix is the one wrangler printed in prod.log)
# exit 1: no deploy URL in prod.log; 2: canonical is still the previous id after the wait; 3: canonical is some other deploy
# env: KT_CANON_TRIES (default 18), KT_CANON_SLEEP (seconds, default 10), KT_CANON_CMD (test hook: command that prints the canonical id)
set -uo pipefail
LOG=$1; OLD=$2; TRIES=${KT_CANON_TRIES:-18}; SLP=${KT_CANON_SLEEP:-10}
P=$(grep -o 'https://[0-9a-f]\{8\}\.kicktip\.pages\.dev' "$LOG" | tail -n 1 | sed 's#https://##;s#\..*##')
[ -n "$P" ] || { echo "no deploy URL in $LOG" >&2; exit 1; }
canon() {
  if [ -n "${KT_CANON_CMD:-}" ]; then bash -c "$KT_CANON_CMD"; return; fi
  curl -s -m 30 -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/pages/projects/${KT_PROJ:-kicktip}" \
    | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['canonical_deployment']['id'])" 2>/dev/null
}
C=""
for i in $(seq 1 "$TRIES"); do
  C=$(canon || true)
  case "$C" in "$P"-*) echo "$C"; [ "$i" -gt 1 ] && echo "canonical became $C after $i reads" >&2; exit 0;; esac
  [ "$i" -lt "$TRIES" ] && sleep "$SLP"
done
if [ "$C" = "$OLD" ] || [ -z "$C" ]; then echo "canonical is still ${C:-unreadable} (not $P) after $TRIES reads" >&2; exit 2; fi
echo "canonical is $C, neither this deploy ($P) nor the previous live $OLD" >&2; exit 3
