#!/usr/bin/env python3
"""scn_b3 browser smoke (the all-impossible card has NO shared-game lead: the approved line is the first paragraph after the title) (headless chromium, offline) at 320 and 390 px: the all-impossible card (flag on: one line, no branch sections, no AI call), the old conflict clarify (flag off, and SCNIMPALL=false), usage: smoke_scn_b3.py TREE_B3 TREE_B [OUT]"""
import sys, os, json, re, time, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
TREE = os.path.abspath(sys.argv[1]); TREE2 = os.path.abspath(sys.argv[2]); OUT = os.path.abspath(sys.argv[3] if len(sys.argv) > 3 else 'logs/shots'); os.makedirs(OUT, exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=TREE)); PORT = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()
IDS = ["conf_race_alive", "conf_standings", "games_that_matter", "path_compare", "playoff_field", "rankings_list", "team_needs", "team_path", "team_schedule", "team_snapshot", "tiebreak_explain"]
n = 0; bad = 0
def ck(ok, what, x=''):
    global n, bad; n += 1
    if not ok: bad += 1
    print(('PASS ' if ok else 'FAIL ') + what + ('' if ok else ' :: ' + str(x)[:300]))
TS = "var __o=null;window.turnstile={render:function(el,o){__o=o;setTimeout(function(){o.callback&&o.callback('good')},10);return 'w1'},reset:function(){setTimeout(function(){__o&&__o.callback&&__o.callback('good')},10)},remove:function(){},getResponse:function(){return 'good'}};"
TAG = "Written by AI from KickTip's numbers"
QLOSS = "what if BYU and Texas Tech end with just one loss"          # read by the standard parser in the browser (no AI call): the 'local trigger'
QS = [QLOSS, "what if Utah and Texas Tech win out", "what if New Mexico State and Western Kentucky win out", "what if Arizona State and Houston win out"]
HOME = {"what if Utah and Texas Tech win out": {'label': 'A', 'wins_out': ['Utah', 'Texas Tech']}, "what if New Mexico State and Western Kentucky win out": {'label': 'A', 'wins_out': ['New Mexico State', 'Western Kentucky']}, "what if Arizona State and Houston win out": {'label': 'A', 'wins_out': ['Arizona State', 'Houston']}}
def prose_for(facts):   # a valid write-up built only from the facts the page sent
    t = facts['branches'][0]['teams'][0]; names = facts['scenario']
    return "In this scenario, %s finishes %s in %s play, and KickTip's numbers show the records on this card. The result depends on games the scenario does not set." % (t['team'], t['conference_record'], facts['conference'])
GOOD_FIXED = "In this scenario, BYU and Texas Tech both finish 8-1 in Big 12 play, and KickTip's numbers show Utah can still reach 8-1 too. If BYU and Texas Tech are tied at 8-1, step 1 is head-to-head. The result depends on games the scenario does not set."
def resp(status, body, ctype='application/json', delay=0): return {'status': status, 'body': body if isinstance(body, str) else json.dumps(body), 'ctype': ctype, 'delay': delay}
def ok_scn(prose): return resp(200, {'enabled': True, 'ok': True, 'source': 'scn', 'v': 1, 'prose': prose})
def fb(reason): return resp(200, {'enabled': True, 'ok': False, 'fallback': True, 'reason': reason})
def run(pw, w, h, scn_cfg=True, enabled=True, handler=None, use_ai_off=False, tk=None):
    b = pw.chromium.launch(); ctx = b.new_context(viewport={'width': w, 'height': h}); pg = ctx.new_page(); calls = []; errs = []
    if use_ai_off: ctx.add_init_script("try{localStorage.setItem('kicktip_ai','off')}catch(e){}")
    pg.on('pageerror', lambda e: errs.append(str(e)))
    def api(route):
        rq = route.request; u = rq.url; path = u.split(str(PORT))[1]; raw = rq.post_data or ''; calls.append((rq.method, path, raw))
        if path == '/api/ask-config':
            c = {'enabled': enabled, 'sitekey': 'x', 'maxChars': 300, 'tokenField': 'cf_turnstile', 'tb': IDS}
            if scn_cfg: c['scn'] = True
            route.fulfill(status=200, content_type='application/json', body=json.dumps(c))
        elif path == '/api/tb-count': route.fulfill(status=200, content_type='application/json', body='{"ok":true,"n":1}')
        elif path == '/api/ask':
            try: body = json.loads(raw)
            except Exception: body = {}
            if body.get('mode') == 'scn':
                r = handler(body) if handler else ok_scn(prose_for(body['facts']))
                if r['delay']: time.sleep(r['delay'])
                try: route.fulfill(status=r['status'], content_type=r['ctype'], body=r['body'])
                except Exception: pass
            else:
                q = (body.get('text') or ''); sc = {k.lower(): v for k, v in HOME.items()}.get(q.lower().strip('?'), {'label': 'A', 'wins_out': ['Utah']})
                out = {'enabled': True, 'ok': True, 'source': 'model', 'interpretation': {'v': 1, 'mode': 'home', 'status': 'ok', 'scenarios': [sc]}}
                if tk: out['scn_tk'] = tk
                route.fulfill(status=200, content_type='application/json', body=json.dumps(out))
        else: route.fulfill(status=404, body='{}')
    pg.route('**/api/**', api); pg.route('**/challenges.cloudflare.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=TS))
    pg.goto('http://127.0.0.1:%d/' % PORT); pg.wait_for_timeout(600)
    return b, pg, calls, errs
def ask(pg, q, wait_ms=1500):
    if not pg.is_visible('#kask'): pg.click('#kpill'); pg.wait_for_selector('#kask', state='visible')
    pg.fill('#kask', q); pg.press('#kask', 'Enter')
    try: pg.wait_for_selector('[data-airun]', timeout=2500); pg.click('[data-airun]')
    except Exception: pass
    try: pg.wait_for_selector('.pnl .sx', timeout=20000)
    except Exception: pass
    pg.wait_for_timeout(wait_ms)
def scns(calls): return [json.loads(c[2]) for c in calls if c[1] == '/api/ask' and '"mode": "scn"' in c[2].replace('":"', '": "').replace('","', '", "') or (c[1] == '/api/ask' and '"mode":"scn"' in c[2])]
def panel(pg): return pg.evaluate("(document.getElementById('kask').closest('[role=dialog]')||document.body).innerText")
ERRWORDS = re.compile(r"error|went wrong|failed|try again later|could not|couldn.t write|unavailable|AI is off", re.I)
def plain_card(tag, pg, errs, w):
    ck(len(pg.query_selector_all('.pnl .sx')) == 1, '%s: the facts card is shown' % tag, len(pg.query_selector_all('.pnl .sx')))

import shutil, tempfile
OFF = os.path.join(tempfile.mkdtemp(), 'off'); shutil.copytree(TREE, OFF); cj = os.path.join(OFF, 'assets/chat.js'); t0 = open(cj).read(); assert t0.count('var SCNB = true;') == 1; open(cj, 'w').write(t0.replace('var SCNB = true;', 'var SCNB = false;'))
def serve(tree):
    s2 = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=tree)); threading.Thread(target=s2.serve_forever, daemon=True).start(); return s2
srvOff = serve(OFF); PORT_OFF = srvOff.server_address[1]; srvA = serve(TREE2); PORT_A = srvA.server_address[1]
Q1 = "What if BYU, Utah and Texas Tech all end with just one loss?"; QLIVE = "What if BYU and Utah each end with 3 losses"; Q4 = "What if BYU, Utah and Arizona all end with 3 losses"; Q3 = "What if Arizona, TCU and Utah all lose 1 of the remaining games"
def fits(pg, w, tag):
    ck(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), '%s: no horizontal overflow' % tag)
    ck(pg.evaluate("(function(){var s=document.querySelector('.pnl .sx');if(!s)return true;var r=s.getBoundingClientRect();var ok=r.left>=-1&&r.right<=window.innerWidth+1&&s.scrollWidth<=s.clientWidth+1;s.querySelectorAll('.sxb,table,h4,p').forEach(function(e){var b=e.getBoundingClientRect();if(b.right>r.right+1)ok=false});return ok})()"), '%s: card and every branch section fit inside the card/viewport' % tag)
QI = "What if Kansas and TCU each end with 4 losses"; QI2 = "What if Delaware and Western Kentucky each end with 4 losses"; OLD = "Those results contradict each other. Remove one."; LINE = "No result of those games fits your scenario."
import shutil, tempfile
OFF = os.path.join(tempfile.mkdtemp(), 'off'); shutil.copytree(TREE, OFF); cj = os.path.join(OFF, 'assets/chat.js'); t0 = open(cj).read(); assert t0.count('var SCNIMPALL = true;') == 1; open(cj, 'w').write(t0.replace('var SCNIMPALL = true;', 'var SCNIMPALL = false;'))
def serve(tree):
    s2 = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=tree)); threading.Thread(target=s2.serve_forever, daemon=True).start(); return s2
srvOff = serve(OFF); PORT_OFF = srvOff.server_address[1]; srvB = serve(TREE2); PORT_B = srvB.server_address[1]
def fits(pg, tag):
    ck(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), '%s: no horizontal overflow' % tag)
    ck(pg.evaluate("(function(){var s=document.querySelector('.pnl .sx');if(!s)return true;var r=s.getBoundingClientRect();var ok=r.left>=-1&&r.right<=window.innerWidth+1&&s.scrollWidth<=s.clientWidth+1;s.querySelectorAll('table,h3,h4,p,a').forEach(function(e){var b=e.getBoundingClientRect();if(b.right>r.right+1)ok=false});return ok})()"), '%s: the card fits inside the viewport' % tag)
def goto_port(pw, w, h, port, cfg):
    b = pw.chromium.launch(); ctx = b.new_context(viewport={'width': w, 'height': h}); pg = ctx.new_page(); errs = []; calls = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    def api(route):
        rq = route.request; path = rq.url.split(str(port))[1]; calls.append((rq.method, path, rq.post_data or ''))
        if path == '/api/ask-config': route.fulfill(status=200, content_type='application/json', body=json.dumps(cfg))
        elif path == '/api/tb-count': route.fulfill(status=200, content_type='application/json', body='{"ok":true,"n":1}')
        else: route.fulfill(status=404, body='{}')
    pg.route('**/api/**', api); pg.route('**/challenges.cloudflare.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=TS))
    pg.goto('http://127.0.0.1:%d/' % port); pg.wait_for_timeout(600); return b, pg, calls, errs
ON = {'enabled': True, 'sitekey': 'x', 'maxChars': 300, 'tokenField': 'cf_turnstile', 'tb': IDS, 'scn': True}; NOSCN = dict(ON); NOSCN.pop('scn'); OFFCFG = {'enabled': False}
# flag-on cases run on the B2 tree (the first server); PORT_B serves the base B tree
with sync_playwright() as pw:
    for (w, h) in ((320, 640), (375, 812)):
        P = '%dpx' % w
        for q in (QI, QI2):
            b, pg, calls, errs = run(pw, w, h); ask(pg, q, 3000); t = panel(pg); tag = '%s %s' % (P, q[8:40])
            ck(len(pg.query_selector_all('.pnl .sx')) == 1, '%s flag on: one facts card' % tag, t[:200])
            ck(LINE in t and t.count(LINE) == 1, '%s flag on: the approved line, once' % tag, t[:300])
            ck(len(pg.query_selector_all('.pnl .sx .sxb')) == 0 and 'If ' + q.split()[2] + ' beats' not in t and 'Not possible' not in t, '%s flag on: no branch sections or labels' % tag)
            ck('what this means for' in t.lower() and 'rules source' in t.lower() and 'as of' in t.lower() and 'play each other in a game' not in t and 'here is each result' not in t.lower(), '%s flag on (scn_b3): title, the approved line, rules source, as-of, NO shared-game lead' % tag, t[:300])
            ck(OLD not in t, '%s flag on: the old conflict question is gone' % tag)
            fp = pg.evaluate("(function(){var s=document.querySelector('.pnl .sx');if(!s)return null;var h=s.querySelector('h3');var e=h&&h.nextElementSibling;return e?[e.tagName,e.className,e.innerText]:null})()")
            ck(fp is not None and fp[2] == LINE and 'sxl' not in fp[1], '%s flag on (scn_b3): the first element after the title is the approved line, no lead paragraph' % tag, fp)
            ck(len(pg.query_selector_all('.pnl .sx .sxl')) == 0, '%s flag on (scn_b3): no shared-game lead element' % tag)
            ck(len([c for c in calls if c[1] == '/api/ask']) == 0, '%s flag on: no AI call and no write-up offered' % tag, [c[1] for c in calls])
            ck(not pg.query_selector('[data-airun]') and 'Written by AI' not in t, '%s flag on: no write-up control' % tag)
            fits(pg, tag); ck(not errs, '%s flag on: no page errors' % tag, errs); pg.screenshot(path=os.path.join(OUT, 'b3-%d-%s.png' % (w, 'k' if q == QI else 'd'))); b.close()
        b, pg, calls, errs = goto_port(pw, w, h, PORT_B, NOSCN); ask(pg, QI, 1500); t = panel(pg)
        ck(OLD in t and LINE not in t and len(pg.query_selector_all('.pnl .sx')) == 0, '%s ask-config without scn: the old conflict question, no card (same as B)' % P, t[:200]); ck(not errs, '%s no scn: no page errors' % P, errs); b.close()
        b, pg, calls, errs = goto_port(pw, w, h, PORT_B, OFFCFG); ask(pg, QI, 1500); t = panel(pg)
        ck(OLD in t and LINE not in t and len(pg.query_selector_all('.pnl .sx')) == 0, '%s AI off (enabled:false): the old conflict question, no card (same as B)' % P, t[:200]); b.close()
        PORT_SAVE = PORT; PORT = PORT_OFF; b, pg, calls, errs = run(pw, w, h); ask(pg, QI, 1500); t = panel(pg); PORT = PORT_SAVE
        ck(OLD in t and LINE not in t and len(pg.query_selector_all('.pnl .sx')) == 0, '%s SCNIMPALL=false with the flag on: the old conflict question' % P, t[:200]); b.close()
srv.shutdown()
print('%d checks, %d failed' % (n, bad)); sys.exit(1 if bad else 0)
