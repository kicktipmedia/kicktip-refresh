#!/bin/bash
# National ranks step (refresh.yml). Never fails the run: always exits 0. Writes $GITHUB_OUTPUT:
#   ranks_changed=0|1 (cache differs from live and is not older), ranks_force=0|1 (may trigger ONE ranks-only forced run),
#   ranks_save=0|1 (cache state changed: save it), ranks_fresh=0|1, ranks_out=<file for apply_data --ranks> (only if not older than live).
# Cache dir $KT_RANKS_LAST (actions/cache): ranks.json last good; fetched_at = epoch of last good fetch; tried_at = epoch of last
#   fetch attempt; forced = "<sha256> <epoch>" of the last ranks-only force.
# Rules: fetch when last good is >= 20 h old (KT_RANKS_CAP_H) and no attempt in the last 6 h (KT_RANKS_RETRY_H).
#   Any failure (fetch, parse, mapping gate, schema) keeps last good. Never older than live: a cache with thru < live thru is
#   reseeded from live, and a fetch with thru < cache thru is discarded. One forced ranks-only run per ranks sha per 20 h,
#   never on Saturday (America/Denver). Step summary every run; ::warning when thru is > 7 days old.
# Test knobs (never set by refresh.yml): KT_RANKS_TEAMS, KT_RANKS_FAIL=fetch, KT_RANKS_DOW (1..7), KT_RANKS_BASE_ZIP.
set -u
R=${KT_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}; L=${KT_RANKS_LAST:-$R/natranks/last}; OUT=${KT_RANKS_OUT:-$R/natranks/cur/ranks.json}
CAP=${KT_RANKS_CAP_H:-20}; RETRY=${KT_RANKS_RETRY_H:-6}; TEAMS=${KT_RANKS_TEAMS:-$R/base/s0/site/data/pred-teams.json}
ZIP=${KT_RANKS_BASE_ZIP:-$R/base/kicktip-site.zip}; GO=${GITHUB_OUTPUT:-/dev/null}; SUM=${GITHUB_STEP_SUMMARY:-/dev/null}
NOW=$(date +%s); DOW=${KT_RANKS_DOW:-$(TZ=America/Denver date +%u)}; T=$(mktemp -d)
mkdir -p "$L" "$(dirname "$OUT")"; FRESH=0; SAVE=0; MODE=cached; NOTE=""
put() { cp "$1" "$2.tmp.$$" && mv -f "$2.tmp.$$" "$2"; }                    # atomic
wr() { printf '%s\n' "$2" > "$T/w" && put "$T/w" "$L/$1"; }
num() { cat "$L/$1" 2>/dev/null | head -n1 | cut -d' ' -f"${2:-1}" | grep -E '^[0-9]+$' || echo 0; }
ok() { python3 - "$1" <<'P' 2>/dev/null
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))
assert d.get('v')==1 and len(d['t'])>=130 and len(d['cats'])==9 and all(c['n']>=130 for c in d['cats']) and d['thru']
P
}
thru() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['thru'])" "$1" 2>/dev/null || echo 0000-00-00; }
hsh() { sha256sum "$1" | cut -c1-64; }
LIVE=$T/live.json; unzip -p "$ZIP" data/ranks.json > $LIVE 2>/dev/null && ok $LIVE || rm -f $LIVE
LT=0000-00-00; [ -s $LIVE ] && LT=$(thru $LIVE)
# seed / N1 reseed
if [ -s $LIVE ]; then
  if ! { [ -s "$L/ranks.json" ] && ok "$L/ranks.json"; }; then put $LIVE "$L/ranks.json"; SAVE=1; NOTE="seeded from live"; echo "ranks: seeded last good from live"
  elif [[ "$(thru "$L/ranks.json")" < "$LT" ]]; then echo "ranks: cache thru $(thru "$L/ranks.json") older than live $LT: reseeded from live"; put $LIVE "$L/ranks.json"; SAVE=1; NOTE="reseeded from newer live"; fi
fi
FA=$(num fetched_at); TA=$(num tried_at); AGE=$(( (NOW-FA)/3600 )); TAGE=$(( (NOW-TA)/3600 ))
if [ $AGE -ge $CAP ] && [ $TAGE -ge $RETRY ]; then
  wr tried_at $NOW; SAVE=1
  P=(); [ "${KT_RANKS_FAIL:-}" = fetch ] && P=(env https_proxy=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9)   # test: unreachable network
  if timeout 300 "${P[@]}" python3 $R/natranks/build_ranks.py --teams "$TEAMS" --out $T/new.json && ok $T/new.json; then
    if [ -s "$L/ranks.json" ] && [[ "$(thru $T/new.json)" < "$(thru "$L/ranks.json")" ]]; then
      MODE=fallback; echo "::warning::NCAA ranks thru $(thru $T/new.json) older than last good; kept last good"
    else put $T/new.json "$L/ranks.json"; wr fetched_at $NOW; FRESH=1; MODE=fresh; echo "ranks: fresh fetch OK"; fi
  else MODE=fallback; echo "::warning::national ranks fetch/parse/gate failed; keeping last good ranks.json (next try in ${RETRY}h)"; echo "ranks: FALLBACK to last good"; fi
elif [ $AGE -lt $CAP ]; then echo "ranks: cached (${AGE}h old < ${CAP}h cap): fetch skipped"
else MODE=backoff; echo "ranks: last attempt ${TAGE}h ago < ${RETRY}h retry backoff: fetch skipped"; fi
CH=0; FORCE=0; CT=none
if [ -s "$L/ranks.json" ] && ok "$L/ranks.json"; then
  CT=$(thru "$L/ranks.json")
  if [ ! -s $LIVE ]; then rm -f "$OUT"; echo "ranks: live base has no data/ranks.json (pre-ranks site): not applied"
  elif [[ "$CT" < "$LT" ]]; then rm -f "$OUT"; echo "ranks: cache older than live: not applied"
  else
    put "$L/ranks.json" "$OUT"
    if cmp -s "$OUT" $LIVE; then echo "ranks: same as live"; else CH=1; echo "ranks: differs from live (thru $LT -> $CT)"; fi
  fi
else rm -f "$OUT"; echo "ranks: no good file; live copy kept"; fi
if [ $CH = 1 ]; then
  H=$(hsh "$OUT"); FH=$(cut -d' ' -f1 "$L/forced" 2>/dev/null); FT=$(num forced 2)
  if [ "$DOW" = 6 ]; then echo "ranks: Saturday (America/Denver): no ranks-only forced run"
  elif [ "$FH" = "$H" ] && [ $(( (NOW-FT)/3600 )) -lt 20 ]; then echo "ranks: ranks-only run for ${H:0:12} already tried $(( (NOW-FT)/3600 ))h ago: not forcing again"
  else FORCE=1; wr forced "$H $NOW"; SAVE=1; echo "ranks: ranks-only forced run allowed for ${H:0:12}"; fi
fi
{ echo "ranks_changed=$CH"; echo "ranks_force=$FORCE"; echo "ranks_save=$SAVE"; echo "ranks_fresh=$FRESH"; [ -s "$OUT" ] && echo "ranks_out=$OUT"; } >> "$GO"
TD=$(python3 -c "import datetime as d,sys
try: print((d.date.today()-d.date.fromisoformat(sys.argv[1])).days)
except Exception: print(-1)" "$CT")
{ echo "### National ranks"; echo "- thru: $CT (live $LT), ${TD} days old"; echo "- last good fetch: $([ $FA = 0 ] && echo never || echo "${AGE}h ago"); mode: $MODE${NOTE:+; $NOTE}"
  echo "- changed vs live: $CH; ranks-only force: $FORCE"; } >> "$SUM"
[ "$TD" -gt 7 ] 2>/dev/null && echo "::warning::national ranks thru $CT is $TD days old (row hides after 10)"
echo "ranks: thru $CT, $TD days old, mode $MODE"
rm -rf "$T"; exit 0
