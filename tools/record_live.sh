#!/bin/bash
# Write state.json and $RD/result.json after a verified production deploy.
# Same fields a successful auto_refresh records (clean compare and edge-lag both come here).
# Caller exports KT_ROOT, RD, NEW_ID, NEW_SHA, ASOF, FP1, DONE, LFP1, LEP1, SNAP, LIVE_ID, RUN.
# KT_RELATIVE=1 stores repo-relative paths in state.json (the GitHub workflow sets it).
set -uo pipefail
R=${KT_ROOT:?}
: "${RD:?}" "${NEW_ID:?}" "${NEW_SHA:?}" "${ASOF:?}" "${FP1:?}" "${DONE:?}" "${LFP1:?}" "${LEP1:?}" "${SNAP:?}" "${LIVE_ID:?}" "${RUN:?}"
python3 - <<P || exit 22
import json,os
s=json.load(open('$R/state.json')); json.dump(s,open('$R/state.prev.json','w'),indent=1)
rel=lambda x: os.path.relpath(x,'$R') if os.environ.get('KT_RELATIVE') else x
s.update(live_id='$NEW_ID',live_sha='$NEW_SHA',zip_path=rel('$RD/kicktip-site.zip'),site_dir=rel('$RD/deploy'),as_of='$ASOF',s0_pipeline_site=rel('$SNAP/site'),
         results_fp='$FP1',lines_fp='$LFP1',lines_epoch=int('$LEP1'),completed=int('$DONE'),rollback_id='$LIVE_ID',deployed_at=__import__('datetime').datetime.now().astimezone().isoformat(timespec='seconds'),run='$RUN')
json.dump(s,open('$R/state.json.tmp','w'),indent=1); os.replace('$R/state.json.tmp','$R/state.json')
P
echo "{\"run\":\"$RUN\",\"exit\":0,\"live_id\":\"$NEW_ID\",\"sha\":\"$NEW_SHA\",\"as_of\":\"$ASOF\",\"fp\":\"$FP1\",\"lines_fp\":\"$LFP1\",\"lines_epoch\":$LEP1,\"completed\":$DONE,\"zip\":\"$RD/kicktip-site.zip\",\"s0\":\"$SNAP/site\"}" > $RD/result.json
