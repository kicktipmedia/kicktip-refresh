#!/usr/bin/env python3
"""scn_a1 static checks. usage: static_checks_a1.py ZIP_A1 ZIP_ROUTER2C"""
import sys, zipfile, hashlib, re, json
z1, z0 = zipfile.ZipFile(sys.argv[1]), zipfile.ZipFile(sys.argv[2]); n = 0; bad = []
def chk(k, ok, info=''):
    global n; n += 1; print(('PASS ' if ok else 'FAIL ') + k, '' if ok else str(info)[:300]); (not ok) and bad.append(k)
a, b = set(z0.namelist()), set(z1.namelist()); TOK = re.compile(r'\?v=[0-9a-f]{10}')
chk('base is router2c: 934 entries, sha 2cb9f66d...', len(a) == 934 and hashlib.sha256(open(sys.argv[2], 'rb').read()).hexdigest().startswith('2cb9f66df392778fea72'))
chk('output 935 entries, no duplicates, no .zip entries, file set = base + assets/ks/explain.js only', len(b) == 935 == len(z1.namelist()) and not [x for x in b if x.endswith('.zip')] and b - a == {'assets/ks/explain.js'} and not (a - b))
EDIT = ['assets/chat.js', 'assets/chat.css']
mod = sorted(x for x in a & b if z0.read(x) != z1.read(x))
chk('hand-edited files that differ in content: exactly chat.js and chat.css', sorted(x for x in mod if TOK.sub('?v=T', z0.read(x).decode('utf-8', 'ignore')) != TOK.sub('?v=T', z1.read(x).decode('utf-8', 'ignore'))) == sorted(EDIT))
other = [x for x in mod if x not in EDIT]
chk('every other changed file differs only in ?v= tokens (%d files)' % len(other), all(TOK.sub('?v=T', z0.read(x).decode()) == TOK.sub('?v=T', z1.read(x).decode()) for x in other))
chk('_worker.js, ks/parse.js, ks/scenario.js, ks/answer.js, ccgsim.js, data/*.json byte-identical to router2c', all(z0.read(f) == z1.read(f) for f in ['_worker.js', 'assets/ks/parse.js', 'assets/ks/scenario.js', 'assets/ks/answer.js', 'assets/ccgsim.js', 'data/ccg-sim.json', 'data/ccg-rules.json', 'data/sim-bundle.json']), [f for f in ['_worker.js', 'assets/ks/parse.js', 'assets/ks/scenario.js', 'assets/ks/answer.js', 'assets/ccgsim.js'] if z0.read(f) != z1.read(f)])
w = z1.read('_worker.js').decode(); ids = lambda nm: re.search(r'const %s = \[([^\]]*)\]' % nm, w).group(1).count("'") // 2
chk('19 ids in TB_LIVE_TOOLS and TB_TOOL_IDS; dark tools absent from the Worker; ROUTER_TOOLS line same', ids('TB_LIVE_TOOLS') == 19 and ids('TB_TOOL_IDS') == 19 and 'ccg_matchup' not in w and re.findall(r'^const ROUTER_TOOLS = .*$', w, re.M) == re.findall(r'^const ROUTER_TOOLS = .*$', z0.read('_worker.js').decode(), re.M))
chk("ask-config: router field still guarded by routerOn(env); AI_ROUTER only compared to 'on'", "if (ready && TB_ON.length && routerOn(env)) cfg.router = true;" in w and "env.AI_ROUTER === 'on'" in w)
man = z1.read('assets/tb/manifest.js').decode()
chk('manifest: ccg_matchup and team_trend still live:false; same tool ids', all(re.search(r'"%s":\{"url"[^{}]*?"live":false' % t, man) for t in ('ccg_matchup', 'team_trend')) and TOK.sub('', man) == TOK.sub('', z0.read('assets/tb/manifest.js').decode()))
ex = z1.read('assets/ks/explain.js').decode(); c = z1.read('assets/chat.js').decode()
chk('chat.js loads explain.js with the real ?v= token (sha256[:10] of the file)', ('/assets/ks/explain.js?v=' + hashlib.sha256(ex.encode()).hexdigest()[:10]) in c)
chk('explain.js: ASCII only; no network, storage or cookie calls', all(ord(ch) < 128 for ch in ex) and not re.search(r'fetch\(|XMLHttpRequest|sendBeacon|localStorage|sessionStorage|document\.cookie|eval\(|new Function', ex))
chk('chat.js: SCNCARD switch defaults to true; only two new data fetches (ccg-sim.json, ccg-rules.json)', 'var SCNCARD = true;' in c and c.count("fetchJson('/data/ccg-") == 2)
for f in EDIT:
    old = set(z0.read(f).decode().splitlines()); new = [l for l in z1.read(f).decode().splitlines() if l not in old]
    chk(f + ': added lines ASCII only', all(ord(ch) < 128 for l in new for ch in l))
chk('chat.css: card rules are scoped to .pnl .sx (no global selector added)', all(l.startswith(('.pnl .sx', '/*', '@media(max-width:420px){.pnl .sx')) or not l.strip() for l in z1.read('assets/chat.css').decode().split('/* scenario facts card (scn_a1)')[1].splitlines()[1:]))
print('%d checks, %d failed' % (n, len(bad))); sys.exit(1 if bad else 0)
