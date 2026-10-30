#!/usr/bin/env python3
"""scn_b browser smoke (headless chromium, offline: /api/* and Turnstile stubbed) at 320 and 390 px: shared-game branches on the facts card (exact BYU/Utah/Texas Tech one-loss question, both-live, 4-branch, impossible branch line), the old clarify for 3 shared games, SCNB off = old clarify, a write-up on a branched card, no overflow; A2b 390px top alignment of the Yes cell.   usage: smoke_scn_b.py TREE_B TREE_A2B [outdir]"""
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
with sync_playwright() as pw:
    for (w, h) in ((320, 640), (390, 800)):
        P = '%dpx' % w
        # 1. the exact question: two labelled branches, one live, one not possible
        b, pg, calls, errs = run(pw, w, h, scn_cfg=False, enabled=False); ask(pg, Q1, 2500); t = panel(pg)
        ck(len(pg.query_selector_all('.pnl .sx')) == 1, '%s Q1: one facts card' % P)
        for m in ["What this means for BYU, Utah and Texas Tech", "If BYU beats Utah", "If Utah beats BYU", "Not possible:", "BYU would end with more losses than your scenario allows.", "reach the Big 12 conference championship game", "Tiebreaker steps"]: ck(m in t or m.upper() in t, '%s Q1: shows %r' % (P, m), t[:300])
        ck('Those teams play each other' not in t, '%s Q1: the old clarify is gone' % P)
        ck(len(pg.query_selector_all('.pnl .sx .sxb')) == 2 and len(pg.query_selector_all('.pnl .sx .sxb > h4.sxh')) == 2 and len(pg.query_selector_all('.pnl .sx p.sxx')) == 1, '%s Q1: 2 branch sections, 2 labels, 1 impossible line' % P, [len(pg.query_selector_all('.pnl .sx .sxb')), len(pg.query_selector_all('.pnl .sx p.sxx'))])
        ck(len([c for c in calls if c[1] == '/api/ask']) == 0, '%s Q1: no AI call (A1 card needs none)' % P)
        fits(pg, w, P + ' Q1'); ck(not errs, '%s Q1: no page errors' % P, errs); pg.screenshot(path=os.path.join(OUT, 'b-%d-q1.png' % w)); b.close()
        # 2. both directions live, with chances per branch
        b, pg, calls, errs = run(pw, w, h, scn_cfg=False, enabled=False); ask(pg, QLIVE, 2500); t = panel(pg)
        ck(len(pg.query_selector_all('.pnl .sx .sxb')) == 2 and len(pg.query_selector_all('.pnl .sx p.sxx')) == 0, '%s both live: 2 branch sections, no impossible line' % P)
        ck('If BYU beats Utah' in t and 'If Utah beats BYU' in t and "Not possible" not in t, '%s both live: both labels, nothing impossible' % P, t[:300])
        fits(pg, w, P + ' both live'); ck(not errs, '%s both live: no page errors' % P, errs); pg.screenshot(path=os.path.join(OUT, 'b-%d-live.png' % w)); b.close()
        # 3. four branches (the cap)
        b, pg, calls, errs = run(pw, w, h, scn_cfg=False, enabled=False); ask(pg, Q4, 3500); t = panel(pg)
        ck(len(pg.query_selector_all('.pnl .sx .sxb')) == 4, '%s four branches: 4 labelled sections' % P, len(pg.query_selector_all('.pnl .sx .sxb')))
        ck('If BYU beats Utah and Utah beats Arizona' in t, '%s four branches: combined label' % P, t[:300]); fits(pg, w, P + ' four branches'); ck(not errs, '%s four branches: no page errors' % P, errs); pg.screenshot(path=os.path.join(OUT, 'b-%d-four.png' % w)); b.close()
        # 4. three shared games: the existing clarify, no card
        b, pg, calls, errs = run(pw, w, h, scn_cfg=False, enabled=False); ask(pg, Q3, 1500); t = panel(pg)
        ck('Those teams play each other' in t and len(pg.query_selector_all('.pnl .sx')) == 0, '%s three shared games: old clarify, no card' % P, t[:200]); fits(pg, w, P + ' clarify'); b.close()
        # 5. switch off: Q1 gives the old clarify
        b = pw.chromium.launch(); ctx = b.new_context(viewport={'width': w, 'height': h}); pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.route('**/api/**', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps({'enabled': False}) if r.request.url.endswith('ask-config') else '{"ok":true}')); pg.route('**/challenges.cloudflare.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=TS))
        pg.goto('http://127.0.0.1:%d/' % PORT_OFF); pg.wait_for_timeout(600); ask(pg, Q1, 1500); t = panel(pg)
        ck('Those teams play each other' in t and len(pg.query_selector_all('.pnl .sx')) == 0, '%s SCNB off: old clarify, no card' % P, t[:200]); ck(not errs, '%s SCNB off: no page errors' % P, errs); b.close()
        # 6. write-up on the branched card: only the card's facts go out, prose shows when valid
        PR = "If BYU beats Utah, BYU and Utah both finish 8-1 in Big 12 play and reach the Big 12 conference championship game, on our reading of the rules. If Utah beats BYU, that branch is not possible. The result depends on games the scenario does not set."
        b, pg, calls, errs = run(pw, w, h, handler=lambda body: ok_scn(PR)); ask(pg, Q1, 3000); S = scns(calls)
        ck(len(S) == 1, '%s write-up: one scn request' % P, len(S))
        if S:
            f = S[0]['facts']; ck(set(S[0].keys()) <= {'mode', 'facts', 'cf_turnstile', 'tok_reason'} and any(x.get('label') == 'If BYU beats Utah' for x in f['branches']) and f.get('impossible'), '%s write-up: request carries the labelled branch and the impossible list, no typed text' % P, json.dumps(f)[:300])
        tt = pg.evaluate("(document.querySelector('.pnl .sxai')||{innerText:''}).innerText"); ck(PR in tt.replace('\n', ' ') and TAG in tt, '%s write-up: shown with the AI tag' % P, tt[:200]); fits(pg, w, P + ' write-up'); ck(not errs, '%s write-up: no page errors' % P, errs); b.close()
    # 7. A2b at 390px: the "In the game" cell and the team-name cell share a top alignment
    for (w, h) in ((390, 800),):
        b = pw.chromium.launch(); ctx = b.new_context(viewport={'width': w, 'height': h}); pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.route('**/api/**', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps({'enabled': False}) if r.request.url.endswith('ask-config') else '{"ok":true}')); pg.route('**/challenges.cloudflare.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=TS))
        pg.goto('http://127.0.0.1:%d/' % PORT_A); pg.wait_for_timeout(600); ask(pg, "what if Utah and Texas Tech win out", 2000)
        va = pg.evaluate("(function(){var c=document.querySelectorAll('.pnl .sx .sxt td');var out=[];for(var i=0;i<c.length;i++)out.push(getComputedStyle(c[i]).verticalAlign);return out})()")
        ck(len(va) > 0 and all(v == 'top' for v in va), 'A2b 390px: every scenario-card figures-table cell (team name and In the game) is vertical-align top', va[:12]); ck(not errs, 'A2b: no page errors', errs); b.close()
print('%d checks, %d failed' % (n, bad)); srv.shutdown(); sys.exit(1 if bad else 0)
