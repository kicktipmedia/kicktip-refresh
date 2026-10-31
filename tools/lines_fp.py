#!/usr/bin/env python3
"""lines_fp.py <pipeline_tree> : fingerprint of the ESPN pre-game spreads snapshot (tree/data/store/espn_lines.json) + its pull epoch.
fp covers game id + spread only (numbers); a re-read with identical numbers keeps the fp. Prints: '<fp16> <pulled_epoch>'."""
import json,hashlib,sys,os
p=sys.argv[1]+'/data/store/espn_lines.json'
if not os.path.exists(p): print('none 0'); sys.exit(0)
try:
    d=json.load(open(p)); rows=sorted((str(r['id']),r['s']) for r in d['lines']); ep=int(d.get('pulled_epoch') or 0); assert rows and ep>0
except Exception: print('none 0'); sys.exit(0)   # corrupt/empty snapshot: no change signal (merge keeps the last good lines)
print(hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16], ep)
