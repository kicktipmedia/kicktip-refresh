#!/usr/bin/env python3
"""router2 static checks. usage: static_checks_r2.py ZIP_ROUTER2 ZIP_ROUTER1B"""
import sys, zipfile, hashlib, re, json
z1, z0 = zipfile.ZipFile(sys.argv[1]), zipfile.ZipFile(sys.argv[2]); n = 0; bad = []
def chk(k, ok, info=''):
    global n; n += 1; print(('PASS ' if ok else 'FAIL ') + k, '' if ok else str(info)[:300]); (not ok) and bad.append(k)
a, b = set(z0.namelist()), set(z1.namelist())
chk('base is router1b: 934 entries, sha a75e1edb...', len(a) == 934 and hashlib.sha256(open(sys.argv[2], 'rb').read()).hexdigest().startswith('a75e1edb40cd4e96397a'))
chk('output 934 entries, no duplicates, no .zip entries, same file set', len(b) == 934 == len(z1.namelist()) and not [x for x in b if x.endswith('.zip')] and a == b)
EDIT = ['_worker.js', 'assets/ccgsim-ui.js', 'assets/tb/matcher.js', 'assets/tb/plan.js', 'assets/tb/conf_race_alive.js', 'assets/tb/rules/conf_race_alive.js', 'assets/tb/rules/team_schedule.js', 'assets/tb/manifest.js', 'assets/chat.js', 'assets/ks/parse.js', 'assets/ks/scenario.js', 'assets/ks/answer.js']
mod = sorted(x for x in a & b if z0.read(x) != z1.read(x)); tok = re.compile(r'\?v=[0-9a-z]+')
chk('hand-edited + manifest = 12 files differ in content', sorted(set(mod) & set(EDIT)) == sorted(EDIT), set(EDIT) - set(mod))
other = [x for x in mod if x not in EDIT]
chk('every other changed file differs only in ?v= tokens (%d files)' % len(other), all(tok.sub('?v=T', z0.read(x).decode()) == tok.sub('?v=T', z1.read(x).decode()) for x in other), [x for x in other if tok.sub('?v=T', z0.read(x).decode()) != tok.sub('?v=T', z1.read(x).decode())][:5])
w = z1.read('_worker.js').decode(); ids = lambda nm: re.search(r'const %s = \[([^\]]*)\]' % nm, w).group(1).count("'") // 2
chk('19 ids in TB_LIVE_TOOLS and TB_TOOL_IDS; dark tools absent from the Worker', ids('TB_LIVE_TOOLS') == 19 and ids('TB_TOOL_IDS') == 19 and 'ccg_matchup' not in w and 'team_trend' not in w)
rt = json.loads(re.search(r'^const ROUTER_TOOLS = (\{.*\});$', w, re.M).group(1)); old = z0.read('_worker.js').decode()
chk('ROUTER_TOOLS = the 19 live ids, all ASCII', len(rt) == 19 and 'ccg_matchup' not in rt and 'team_trend' not in rt and all(ord(c) < 128 for c in json.dumps(rt)))
chk('ROUTER_TOOLS modes subset of home/conference/team and params typed', all(set(v['m']) <= {'home', 'conference', 'team'} and all(p['t'] in ('team', 'teams', 'conf', 'enum', 'int') for p in v['p'].values()) for v in rt.values()))
chk('AI_ROUTER only ever compared to the literal on; default off', len(re.findall(r"AI_ROUTER", w)) >= 1 and re.findall(r"env\.AI_ROUTER", w) == ["env.AI_ROUTER"] and "env.AI_ROUTER === 'on'" in w)
chk('flag-off paths: ask-config router field is guarded by routerOn(env)', "if (ready && TB_ON.length && routerOn(env)) cfg.router = true;" in w)
man = z1.read('assets/tb/manifest.js').decode()
chk('manifest: ccg_matchup and team_trend still live:false; only data/rules tokens differ', all(re.search(r'"%s":\{"url"[^{}]*?"live":false' % t, man) for t in ('ccg_matchup', 'team_trend')))
hk = z1.read('assets/tb/hook.js').decode(); ac = z1.read('assets/ai-client.js').decode()
chk('ai-client sends the router flag only when cfg.router is true (home mode)', 'opts.router === true && cfg.router === true && mode === "home"' in ac)
for f in EDIT:
    old_l = set(z0.read(f).decode().splitlines()); new_l = [l for l in z1.read(f).decode().splitlines() if l not in old_l]
    chk(f + ': added lines ASCII only', all(ord(c) < 128 for l in new_l for c in l), [l[:60] for l in new_l if any(ord(c) > 127 for c in l)][:2])
print('%d checks, %d failed' % (n, len(bad))); sys.exit(1 if bad else 0)
