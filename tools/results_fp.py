#!/usr/bin/env python3
"""results_fp.py <pipeline_tree> : fingerprint of everything a refresh can change: finals + scores, kickoffs, postponements.
In-progress scores are ignored (the model treats live games as unplayed)."""
import json,hashlib,sys
T=sys.argv[1]
g=json.load(open(T+'/data/store/games_rated.json')); s=json.load(open(T+'/data/store/schedule.json'))
rows=sorted([('R',x['id'],x['hs'],x['as_']) for x in g]+
            [('S',x['id'],x['date'],x['home'],x['away'],bool(x['done']),x['hs'] if x['done'] else None,x['as_'] if x['done'] else None,
              x['status'] if any(k in str(x.get('status','')).upper() for k in ('POSTPON','CANCEL','DELAY')) else '') for x in s],key=str)
print(hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16], sum(1 for x in s if x['done']))
