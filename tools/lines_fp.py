#!/usr/bin/env python3
"""lines_fp.py <pipeline_tree> : fingerprint of the ESPN pre-game spreads snapshot (tree/data/store/espn_lines.json) + its pull epoch.
fp covers game id + spread only (numbers); a re-read with identical numbers keeps the fp. Prints: '<fp16> <pulled_epoch>'."""
import json,hashlib,sys,os
p=sys.argv[1]+'/data/store/espn_lines.json'
if not os.path.exists(p): print('none 0'); sys.exit(0)
d=json.load(open(p)); rows=sorted((str(r['id']),r['s']) for r in d.get('lines',[]))
print(hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16], int(d.get('pulled_epoch') or 0))
