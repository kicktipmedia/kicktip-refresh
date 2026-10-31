#!/bin/bash
# KickTip confsim (cc5 scenario result view) Production ship, modeled on kicktip-audit2/QA/ship_a2.sh. DO NOT RUN without Creative OK + QA PASS + the go.
# usage: ship_c.sh <zip> <approved_sha256> <guard_canonical_id> <approved_confsim_head>
# Order: KT_SCHEDULE off -> guards (FREEZE, no in_progress/queued/waiting/requested/pending refresh runs, clean head, canonical == guard, zip sha, main state.json live_id == guard, confsim on origin/main)
#   -> deploy once (flock, no retry) -> bytecmp apex+www -> push confsim to main (fast-forward) -> publish_base (state.json) -> KT_SCHEDULE back to its prior value.
# No S0 step: the change is a live-asset layer (assets/ccgsim-ui.js, assets/ccgsim.css + ?v= tokens); no template, data or build.py change, so the S0 merge base is unchanged.
# Exit codes: 2-20 = nothing deployed (KT_SCHEDULE restored). >=21 = KT_SCHEDULE kept OFF + exact recovery steps in ship.out.
#   21 deploy failed / canonical unknown   22 bytecmp failed (NEW live)   23 main push failed   24 publish_base / state check failed
# Test mode (no network, no deploy, mocks only): KT_SHIP_TEST=1 KT_MOCK=<ok|pubfail|bytecmp|deployfail> ship_c.sh x x x x  (log: QA/ship.test.out)
set -euo pipefail
[ $# -eq 4 ] || { echo "usage: ship_c.sh <zip> <approved_sha256> <guard_canonical_id> <approved_confsim_head>"; exit 2; }
C=/workspace/hub/kicktip-confsim; TEST=${KT_SHIP_TEST:-0}; MOCK=${KT_MOCK:-ok}
ZIP=$(realpath -m "$1"); OK_SHA=$2; GUARD=$3; OK_HEAD=$4
REPO=$C/repo; REL=kicktipmedia/kicktip-refresh; ACCT=2b5bfb9838968d7cde32f13967e882e0
export GH_CONFIG_DIR=/workspace/kicktip-refresh/.gh CLOUDFLARE_ACCOUNT_ID=$ACCT
SO=$C/ship.out; [ "$TEST" = 1 ] && SO=$C/QA/ship.test.out
say(){ echo "[$(date '+%F %T %Z')] $*" | tee -a "$SO"; [ "$TEST" = 1 ] || echo "[$(date '+%F %T %Z')] $*" >> $C/PROGRESS.md; }
canon(){ curl -s -m 30 -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" https://api.cloudflare.com/client/v4/accounts/$ACCT/pages/projects/kicktip | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['canonical_deployment']['id'])"; }
GH(){ gh "$@"; }
deploy(){ (cd /workspace/kicktip-tok1/wr && flock /workspace/hub/.deploy.lock env CLOUDFLARE_ACCOUNT_ID=$ACCT ./node_modules/.bin/wrangler pages deploy "$1" --project-name kicktip --branch main --commit-dirty=true 2>&1); }
bytecmp(){ python3 $REPO/tools/bytecmp.py "$1" https://kicktipmedia.com && python3 $REPO/tools/bytecmp.py "$1" https://www.kicktipmedia.com; }
push_main(){ git -C $REPO checkout -q confsim && git -C $REPO -c credential.helper='!gh auth git-credential' push origin confsim:main; }   # fast-forward only (no force)
publish(){ (cd $REPO && git fetch -q origin main && git checkout -q -B main origin/main && git branch -q --set-upstream-to=origin/main main && bash tools/publish_base.sh "$ZIP" "$NEW"); }
state_id(){ git -C $REPO fetch -q origin main; git -C $REPO show origin/main:state.json | python3 -c "import json,sys;print(json.load(sys.stdin)['live_id'])"; }
if [ "$TEST" = 1 ]; then   # mocks: every external effect is replaced; KT_SCHEDULE lives in a file
  KTS=$C/QA/.kt_schedule.test; [ -f $KTS ] || echo on > $KTS; : > "$SO"
  GH(){ case "$1 $2" in "variable get") cat $KTS;; "variable set") echo "$5" > $KTS; echo "  mock gh variable set KT_SCHEDULE=$5" >> "$SO";; "run list") echo 0;; *) echo "  mock gh $*" >> "$SO";; esac; }
  canon(){ if [ -f $C/QA/.deployed.test ]; then echo NEWID-test; else echo "$GUARD"; fi; }
  deploy(){ [ "$MOCK" != deployfail ] || return 1; touch $C/QA/.deployed.test; echo "mock deployed https://abc123.kicktip.pages.dev"; }
  bytecmp(){ [ "$MOCK" != bytecmp ]; }
  push_main(){ echo "  mock push confsim:main" >> "$SO"; }
  publish(){ echo "  mock publish_base (state.json)" >> "$SO"; [ "$MOCK" != pubfail ]; }
  state_id(){ echo NEWID-test; }
  rm -f $C/QA/.deployed.test
fi
STEP=none; NEW=""
recovery(){
  local rc=$1
  say "RECOVERY (exit $rc, last step: $STEP). KT_SCHEDULE is OFF and stays OFF until these are done (check: gh variable get KT_SCHEDULE -R $REL)."
  local RB="curl -s -X POST -H \"Authorization: Bearer \$CLOUDFLARE_API_TOKEN\" https://api.cloudflare.com/client/v4/accounts/$ACCT/pages/projects/kicktip/deployments/$GUARD/rollback   # rollback Production to $GUARD (or dashboard: Pages > kicktip > Deployments > $GUARD > Rollback)"
  local FIN_PUB="cd $REPO && git fetch -q origin main && git checkout -q -B main origin/main && git branch -q --set-upstream-to=origin/main main && bash tools/publish_base.sh $ZIP <NEW_ID> && git fetch -q origin main && git show origin/main:state.json | grep live_id   # must show <NEW_ID>"
  local ON="gh variable set KT_SCHEDULE --body $PREV -R $REL   # LAST, only after the steps above"
  case $rc in
    21) say "  Deploy failed or the canonical id is unknown. Check the dashboard: if canonical is still $GUARD, nothing went live: run: $ON"
        say "  If a new deployment IS canonical: either roll back: $RB ; then $ON — or finish: confirm bytecmp, push (cd $REPO && git push origin confsim:main), publish: $FIN_PUB , then $ON";;
    22) say "  LIVE IS $NEW (bytecmp failed), state.json still says $GUARD. Roll back now: $RB"
        say "  Then confirm canonical = $GUARD; then $ON";;
    23) say "  LIVE IS $NEW, main NOT pushed, state.json old ($GUARD). EITHER roll back: $RB ; then $ON"
        say "  OR finish: (cd $REPO && git -c credential.helper='!gh auth git-credential' push origin confsim:main) ; publish (NEW_ID=$NEW): $FIN_PUB ; then $ON";;
    24) say "  LIVE IS $NEW, main pushed, state.json NOT recorded. Finish: publish (NEW_ID=$NEW): $FIN_PUB ; then $ON"
        say "  Or roll back: $RB ; then $ON";;
    *)  say "  Unexpected exit $rc after the deploy step. Check canonical vs $GUARD and state.json; roll back if unsure: $RB ; then $ON";;
  esac
}
PREV=$(GH variable get KT_SCHEDULE -R $REL) || { echo "ABORT: cannot read KT_SCHEDULE (nothing changed)"; exit 10; }
restore(){ local rc=$?; trap - EXIT
  if [ $rc -ne 0 ] && [ $rc -lt 21 ] && [ "$STEP" != none ]; then say "ship_c: unexpected exit $rc at step $STEP (after the deploy started): treated as 27"; rc=27; fi
  if [ $rc -ge 21 ]; then GH variable set KT_SCHEDULE --body off -R $REL || true; say "ship_c: exit $rc: KT_SCHEDULE kept OFF (trap; prior value '$PREV')"; recovery $rc
  else GH variable set KT_SCHEDULE --body "$PREV" -R $REL && say "ship_c: exit $rc: KT_SCHEDULE restored to '$PREV' (trap)"; fi
  exit $rc; }
trap restore EXIT; trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# 1. schedule off
GH variable set KT_SCHEDULE --body off -R $REL; say "ship_c: KT_SCHEDULE off"
# 2. guards
if [ "$TEST" != 1 ]; then
[ ! -e /workspace/kicktip-refresh/FREEZE ] || { say "ABORT: FREEZE present"; exit 11; }
for st in in_progress queued waiting requested pending; do   # never over a running or queued refresh
  N=$(GH run list -R $REL -s $st --json databaseId -q length) || { say "ABORT: cannot list $st runs"; exit 12; }
  [ "$N" = 0 ] || { say "ABORT: $N refresh run(s) $st"; exit 12; }; done
[ -z "$(git -C $REPO status --porcelain)" ] || { say "ABORT: repo tree not clean"; exit 13; }
[ "$(git -C $REPO rev-parse confsim)" = "$OK_HEAD" ] || { say "ABORT: confsim head $(git -C $REPO rev-parse --short confsim) != approved $OK_HEAD"; exit 13; }
[ -f "$ZIP.head" ] && [ "$(cat "$ZIP.head")" = "$OK_HEAD" ] || { say "ABORT: $ZIP.head missing or != approved head"; exit 13; }
CN=$(canon); [ "$CN" = "$GUARD" ] || { say "ABORT: canonical $CN != guard $GUARD"; exit 20; }
SHA=$(sha256sum "$ZIP" | cut -d' ' -f1); [ "$SHA" = "$OK_SHA" ] || { say "ABORT: zip sha $SHA != approved $OK_SHA"; exit 20; }
git -C $REPO -c credential.helper='!gh auth git-credential' fetch -q origin main
LIVE=$(git -C $REPO show origin/main:state.json | python3 -c "import json,sys;print(json.load(sys.stdin)['live_id'])")
[ "$LIVE" = "$GUARD" ] || { say "ABORT: main state.json live_id $LIVE != guard (a refresh or ship deployed since the guard)"; exit 20; }
git -C $REPO merge-base --is-ancestor origin/main confsim || { say "ABORT: confsim not on current origin/main: run QA/final_rebase_c.sh first"; exit 20; }
else SHA=test; fi
say "ship_c: guards OK canonical $GUARD sha ${SHA:0:12}; rollback = $GUARD"
# 3. deploy once
STEP=deploy; D=$(mktemp -d $C/shipdir.XXXX); [ "$TEST" = 1 ] || (cd $D && unzip -q "$ZIP")
OUT=$(deploy $D) || { echo "$OUT" | tail -5; say "DEPLOY FAILED (no retry)"; exit 21; }
NEW=$(canon) || NEW=""
[ -n "$NEW" ] || { say "DEPLOYED (wrangler OK) but reading the canonical id FAILED; deployment URL: $(echo "$OUT" | grep -o 'https://[a-z0-9]*\.kicktip\.pages\.dev' | head -1)"; exit 21; }
say "ship_c: deployed, canonical now $NEW (rollback $GUARD)"
[ "$NEW" != "$GUARD" ] || { say "ABORT: canonical unchanged after deploy"; exit 21; }
# 4. bytecmp apex + www
STEP=bytecmp; [ "$TEST" = 1 ] || sleep 15
bytecmp $D || { say "BYTECMP FAILED"; exit 22; }
# 5. kit to main, then state.json
STEP=push; push_main || { say "MAIN PUSH FAILED"; exit 23; }
STEP=publish; publish || { say "PUBLISH_BASE FAILED"; exit 24; }
REC=$(state_id); [ "$REC" = "$NEW" ] || { say "STATE CHECK FAILED: origin/main state.json live_id=$REC != $NEW"; exit 24; }
STEP=done; say "ship_c: DONE Production $NEW sha $SHA rollback $GUARD; state.json live $NEW. Next: smoke /conference/big-12/simulator/ + /conference/sun-belt/simulator/ (390 crop)"
