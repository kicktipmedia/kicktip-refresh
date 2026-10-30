#!/bin/bash
# National ranks step (refresh.yml). Never fails the run: always exits 0 and writes $GITHUB_OUTPUT ranks_changed=0|1.
# Cache dir $KT_RANKS_LAST (restored by actions/cache): ranks.json = last good file, fetched_at = epoch of its fetch.
# Fetch NCAA.com at most once per 20 h (KT_RANKS_CAP_H). On any failure (fetch, parse, mapping gate, schema) keep the last good file.
# If there is no last good file, seed it from the live base zip's data/ranks.json (no change). Output: $KT_RANKS_OUT (for apply_data --ranks).
# Test knobs (dry-run branch only, never set by refresh.yml): KT_RANKS_TEAMS (teams file), KT_RANKS_FAIL=fetch.
set -u
R=${KT_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}; L=${KT_RANKS_LAST:-$R/natranks/last}; OUT=${KT_RANKS_OUT:-$R/natranks/cur/ranks.json}
CAP=${KT_RANKS_CAP_H:-20}; TEAMS=${KT_RANKS_TEAMS:-$R/base/s0/site/data/pred-teams.json}; ZIP=${KT_RANKS_BASE_ZIP:-$R/base/kicktip-site.zip}
GO=${GITHUB_OUTPUT:-/dev/null}; mkdir -p "$L" "$(dirname "$OUT")"; FRESH=0
ok() { python3 - "$1" <<'P'
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))
assert d.get('v')==1 and len(d['t'])>=130 and len(d['cats'])==9 and all(c['n']>=130 for c in d['cats']) and d['thru']
P
}
LIVE=/tmp/ranks-live.json; rm -f $LIVE
unzip -p "$ZIP" data/ranks.json > $LIVE 2>/dev/null || rm -f $LIVE
if [ ! -s "$L/ranks.json" ] && [ -s $LIVE ] && ok $LIVE 2>/dev/null; then cp $LIVE "$L/ranks.json"; echo 0 > "$L/fetched_at"; echo "ranks: seeded last good from live base"; fi
AGE=$(python3 -c "import time,sys
try: print(int((time.time()-int(open('$L/fetched_at').read().strip()))/3600))
except Exception: print(9999)")
if [ "$AGE" -ge "$CAP" ]; then
  P=(); [ "${KT_RANKS_FAIL:-}" = fetch ] && P=(env https_proxy=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9)   # test: unreachable network
  rm -f /tmp/ranks-new.json
  if timeout 300 "${P[@]}" python3 $R/natranks/build_ranks.py --teams "$TEAMS" --out /tmp/ranks-new.json && ok /tmp/ranks-new.json; then
    cp /tmp/ranks-new.json "$L/ranks.json"; date +%s > "$L/fetched_at"; FRESH=1; echo "ranks: fresh fetch OK"
  else echo "::warning::national ranks fetch/parse/gate failed; keeping last good ranks.json"; echo "ranks: FALLBACK to last good"; fi
else echo "ranks: cached (${AGE}h old < ${CAP}h cap): fetch skipped"; fi
CH=0
if [ -s "$L/ranks.json" ] && ok "$L/ranks.json" 2>/dev/null; then
  cp "$L/ranks.json" "$OUT"
  if [ ! -s $LIVE ]; then echo "ranks: live base has no data/ranks.json (pre-ranks site): no ranks-only run"
  elif cmp -s "$OUT" $LIVE; then echo "ranks: same as live"; else CH=1; echo "ranks: differs from live"; fi
else rm -f "$OUT"; echo "ranks: no good file; live copy kept"; fi
echo "ranks_changed=$CH" >> "$GO"; echo "ranks_fresh=$FRESH" >> "$GO"
[ -s "$OUT" ] && echo "ranks_out=$OUT" >> "$GO"
python3 -c "import json;d=json.load(open('$L/ranks.json'));print('ranks: thru',d['thru'],'teams',len(d['t']))" 2>/dev/null || true
exit 0
