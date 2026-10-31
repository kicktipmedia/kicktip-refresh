#!/usr/bin/env python3
"""Batch B ship fix (QA, Oct 31): state.json s0_asset pointed at s0-site-v2.tar.gz (old S0 e18db99f, pre-fix TBA).
Batch A's S0 is s0-site.tar.gz (5b375ecf). Sets s0_asset to s0-site.tar.gz and rewrites the RUNBOOK S0-asset paragraph. Idempotent.
usage: s0_asset_fix.py <repo>  (prints 'changed' or 'unchanged')"""
import json, re, sys, os
R = sys.argv[1]; ch = False
p = os.path.join(R, 'state.json'); t = open(p).read(); d = json.loads(t)
if d.get('s0_asset') != 's0-site.tar.gz':
    n = re.sub(r'("s0_asset"\s*:\s*)"[^"]*"', r'\1"s0-site.tar.gz"', t, count=1)
    if n == t: n = json.dumps(dict(d, s0_asset='s0-site.tar.gz'), indent=1) + '\n'
    assert json.loads(n)['s0_asset'] == 's0-site.tar.gz'; open(p, 'w').write(n); ch = True
p = os.path.join(R, 'RUNBOOK.md'); t = open(p).read()
NEW = ("**S0 asset name:** `state.json` key `s0_asset` = `s0-site.tar.gz` (absent = the same default). `fetch_base.sh`, `publish_base.sh`,\n"
       "`rebuild_s0.sh`, Batch B `ship_b.sh` and `final_rebase_b.sh` all resolve it from state.json. Since Batch A (live 561c9524) the S0 is\n"
       "`s0-site.tar.gz` sha 5b375ecf… (Batch A templates). `s0-site-v2.tar.gz` (e18db99f…, pre-fix TBA) is OLD: never point s0_asset at it.\n")
m = re.search(r'\*\*S0 asset name:\*\*.*?(?=^Old S0 )', t, re.S | re.M)
if not m: sys.exit('RUNBOOK: S0 asset paragraph not found')
if m.group(0) != NEW: t = t[:m.start()] + NEW + t[m.end():]; open(p, 'w').write(t); ch = True
print('changed' if ch else 'unchanged')
