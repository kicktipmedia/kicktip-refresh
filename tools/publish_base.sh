#!/bin/bash
# Record a new live deploy in the repo: upload its zip (and optionally a new S0 pipeline site) to release 'base', update state.json, commit, push.
# Used by the GitHub workflow after a refresh deploy AND by any box/feature deploy (home7x, brag, ...). Without it the next refresh stops at the guard.
# usage: tools/publish_base.sh <zip> <deploy_id> [--s0 <pipeline_site_dir> --s0-inputs <pipeline_tree> --as-of "YYYY-MM-DD HH:MM MT" --fp <results_fp> --completed N --lines-fp F --lines-epoch E] [--no-verify]
# Feature ship that changes pipeline-generated HTML: port the change to tree/src/build.py, run tools/rebuild_s0.sh <dir> --check <feature zip> --upload, then this (no --s0).
# Box: export GH_CONFIG_DIR=/workspace/kicktip-refresh/.gh; run from a clone of kicktipmedia/kicktip-refresh.
set -euo pipefail
cd "$(dirname "$0")/.."; ZIP=$1; ID=$2; shift 2; S0=""; ASOF=""; FP=""; DONE=""; LFP=""; LEP=""; S0IN=""; VERIFY=1
while [ $# -gt 0 ]; do case $1 in --s0) S0=$2; shift 2;; --as-of) ASOF=$2; shift 2;; --fp) FP=$2; shift 2;; --completed) DONE=$2; shift 2;; --lines-fp) LFP=$2; shift 2;; --lines-epoch) LEP=$2; shift 2;; --s0-inputs) S0IN=$2; shift 2;; --no-verify) VERIFY=0; shift;; *) echo "bad arg $1"; exit 2;; esac; done
SHA=$(sha256sum "$ZIP" | cut -d' ' -f1)
if [ $VERIFY = 1 ]; then
  C=$(curl -s -m 30 -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID:-2b5bfb9838968d7cde32f13967e882e0}/pages/projects/kicktip" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['canonical_deployment']['id'])")
  [ "$C" = "$ID" ] || { echo "canonical deployment is $C, not $ID: refusing to record"; exit 3; }
fi
TMP=$(mktemp -d); cp "$ZIP" $TMP/kicktip-site.zip
gh release view base >/dev/null 2>&1 || gh release create base --title "Live base (do not delete)" --notes "Current live zip and S0 pipeline site for the refresh workflow." >/dev/null
OLD=$(python3 -c "import json;print(json.load(open('state.json'))['live_id'])")
gh release upload base $TMP/kicktip-site.zip --clobber
if [ -n "$S0" ]; then A=$(python3 -c "import json;print(json.load(open('state.json')).get('s0_asset','s0-site.tar.gz'))"); tar czf "$TMP/$A" -C "$S0" .; gh release upload base "$TMP/$A" --clobber; fi
# pipeline inputs/outputs of this as-of, so tools/rebuild_s0.sh can re-render S0 with new templates (feature ships)
if [ -n "$S0IN" ]; then tar czf $TMP/s0-inputs.tar.gz -C "$S0IN" data/store data/out data/cache/scoreboard; gh release upload base $TMP/s0-inputs.tar.gz --clobber; fi
python3 - "$ID" "$SHA" "$OLD" "$ASOF" "$FP" "$DONE" "$LFP" "$LEP" <<'P'
import json,sys,datetime
i,sha,old,asof,fp,done,lfp,lep=sys.argv[1:9]; s=json.load(open('state.json'))
if old!=i: s['rollback_id']=old
s.update(live_id=i,live_sha=sha,zip_path='base/kicktip-site.zip',s0_pipeline_site='base/s0/site',recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'))
if asof: s['as_of']=asof
if fp: s['results_fp']=fp
if done: s['completed']=int(done)
if lfp: s['lines_fp']=lfp
if lep: s['lines_epoch']=int(lep)
json.dump(s,open('state.json','w'),indent=1); open('state.json','a').write('\n')
P
git add state.json; [ -n "$S0" ] && git add -A tree/data/store || true
git -c user.name="kicktipmedia" -c user.email="kicktipmedia@users.noreply.github.com" commit -q -m "live: $ID (${SHA:0:12})" || true
for i in 1 2 3; do git pull -q --rebase && git push -q && break; sleep 5; done
echo "recorded live $ID sha $SHA"
