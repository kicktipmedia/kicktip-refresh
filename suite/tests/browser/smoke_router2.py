#!/usr/bin/env python3
"""router2 browser smoke (headless chromium, offline: /api/* and Turnstile are stubbed). usage: smoke_router2.py TREE [outdir]"""
import sys, os, json, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
TREE = os.path.abspath(sys.argv[1]); OUT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else 'logs/shots'); os.makedirs(OUT, exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=TREE)); PORT = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()
IDS = ["conf_race_alive", "conf_standings", "explain_site", "games_that_matter", "head_to_head", "path_compare", "playoff_field", "quality_wins", "rankings_list", "schedule_strength", "slate_this_week", "status_check", "team_compare", "team_needs", "team_path", "team_projection", "team_schedule", "team_snapshot", "tiebreak_explain"]
AIREPLY = {'enabled': True, 'ok': False, 'fallback': True, 'reason': 'daily_cap'}
n = 0; bad = 0
def ck(ok, what, x=''):
    global n, bad; n += 1
    if not ok: bad += 1
    print(('PASS ' if ok else 'FAIL ') + what + ('' if ok else ' :: ' + str(x)[:300]))
TS = "window.turnstile={render:function(el,o){setTimeout(function(){o.callback&&o.callback('good')},10);return 'w1'},reset:function(){},remove:function(){},getResponse:function(){return 'good'}};"
def run(pw, w, h, router, scenario):
    b = pw.chromium.launch(); ctx = b.new_context(viewport={'width': w, 'height': h}); pg = ctx.new_page(); calls = []; errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    def api(route):
        u = route.request.url; calls.append((route.request.method, u.split(str(PORT))[1], route.request.post_data or ''))
        if u.endswith('/api/ask-config'):
            cfg = {'enabled': True, 'sitekey': 'x', 'maxChars': 300, 'tokenField': 'cf_turnstile', 'tb': IDS}
            if router: cfg['router'] = True
            route.fulfill(status=200, content_type='application/json', body=json.dumps(cfg))
        elif u.endswith('/api/tb-count'): route.fulfill(status=200, content_type='application/json', body='{"ok":true,"n":1}')
        elif u.endswith('/api/ask'): route.fulfill(status=200, content_type='application/json', body=json.dumps(AIREPLY))
        else: route.fulfill(status=404, body='{}')
    pg.route('**/api/**', api); pg.route('**/challenges.cloudflare.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=TS))
    return b, pg, calls, errs
with sync_playwright() as pw:
    for (w, h) in ((320, 640), (390, 800)):
        for q, must, local in (("Will byu make it to the big12 championship?", "BYU has a 47.2% chance of reaching the conference championship game.", True),
                               ("who is still in the Big 12 race", "Big 12", True), ("who is still alive in the SEC", "SEC", True),
                               ("how tough is Arizona State schedule compared to Iowa State", None, False)):
            tag = '%dpx %s' % (w, q[:40])
            b, pg, calls, errs = run(pw, w, h, True, 'home'); pg.goto('http://127.0.0.1:%d/' % PORT); pg.wait_for_timeout(600)
            pg.click('#kpill'); pg.wait_for_selector('#kask', state='visible'); pg.fill('#kask', q); pg.press('#kask', 'Enter'); pg.wait_for_timeout(2500)
            asks = [c for c in calls if c[1] == '/api/ask']
            if local:
                ans = pg.query_selector_all('.tbox:not([data-miss])'); t = ans[-1].inner_text() if ans else ''
                ck(bool(ans) and must in t, 'home %s: local card shows %r' % (tag, must), t[:200]); ck(not asks, 'home %s: no /api/ask (no AI)' % tag, asks)
                if ans:
                    bb = ans[-1].bounding_box(); ck(bb['x'] >= -1 and bb['x'] + bb['width'] <= w + 1, 'home %s: card inside viewport' % tag, bb)
                    if 'BYU' in q.upper(): ck(t.index(must) < t.index('BYU is in the race for the conference'), 'home %s: chance line leads the race status' % tag)
                    pg.screenshot(path=os.path.join(OUT, 'r2-home-%d-%s.png' % (w, q[:12].replace(' ', '_').replace('?', ''))))
            else:
                bd = json.loads(asks[-1][2]) if asks else {}; ck(len(asks) == 1 and bd.get('router') is True, 'home %s: goes to the router (ONE /api/ask, router:true)' % tag, [len(asks), bd.get('router')])
            ck(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'home %s: no horizontal overflow' % tag); ck(not errs, 'home %s: no page errors' % tag, errs); b.close()
        # steering 2: loss-count questions (home chat, AI toggle on)
        for q, reply, kind, must in (("What if Arizona, TCU and Utah all lose 1 of the remaining games", None, 'shared', "Those teams play each other"),
                                     ("What if BYU ends with just one loss?", None, 'std', "BYU wins out"),
                                     ("What if BYU and Texas Tech both end with just one loss?", None, 'std', "Texas Tech wins out"),
                                     ("What if BYU ends with 3 losses?", None, 'std', "BYU loses 2 of the remaining games"),
                                     ("What if Utah finishes with no losses?", None, 'std', "Utah wins out"),
                                     ("What if BYU finishes with no losses?", None, 'shared', "BYU already has 1 loss, so it cannot end with none."),
                                     ("what if byu somehow manages to have one loss", {'enabled': True, 'ok': True, 'source': 'model', 'interpretation': {'v': 1, 'status': 'ok', 'scenarios': [{'label': 'A', 'record_targets': [{'team': 'BYU', 'wins': 0, 'window': 'remaining', 'games': 1}]}]}}, 'bad', "I DIDN'T CATCH THAT"),
                                     ("what if byu somehow takes three of its last five", {'enabled': True, 'ok': True, 'source': 'model', 'interpretation': {'v': 1, 'status': 'ok', 'scenarios': [{'label': 'A', 'record_targets': [{'team': 'BYU', 'wins': 3, 'window': 'remaining', 'games': 5}]}]}}, 'ai', "BYU wins 3 of the remaining games")):
            tag = '%dpx %s' % (w, q[:44]); AIREPLY.clear(); AIREPLY.update(reply or {'enabled': True, 'ok': False, 'fallback': True, 'reason': 'daily_cap'})
            b, pg, calls, errs = run(pw, w, h, False, 'home'); pg.goto('http://127.0.0.1:%d/' % PORT); pg.wait_for_timeout(600)
            pg.click('#kpill'); pg.wait_for_selector('#kask', state='visible'); pg.fill('#kask', q); pg.press('#kask', 'Enter'); pg.wait_for_timeout(3500)
            t = pg.evaluate("(document.getElementById('kask').closest('[role=dialog]')||document.body).innerText"); asks = [c for c in calls if c[1] == '/api/ask']
            ck(must.upper() in t.upper(), 'loss %s: shows %r' % (tag, must), t[:400])
            if kind in ('shared', 'std'): ck(not asks, 'loss %s: no /api/ask (no AI call)' % tag, asks)
            if kind == 'std': ck('READ BY THE STANDARD PARSER' in t and 'wins 0 of' not in t, 'loss %s: understood card, nothing inverted' % tag, t[:300])
            if kind == 'bad': ck('wins 0 of' not in t and 'HERE IS WHAT I UNDERSTOOD' not in t, 'loss %s: the inverted AI read is never shown' % tag, t[:300])
            ck(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'loss %s: no horizontal overflow' % tag); ck(not errs, 'loss %s: no page errors' % tag, errs); b.close()
        AIREPLY.clear(); AIREPLY.update({'enabled': True, 'ok': False, 'fallback': True, 'reason': 'daily_cap'})
        b, pg, calls, errs = run(pw, w, h, False, 'lab'); pg.goto('http://127.0.0.1:%d/conference/big-12/simulator/' % PORT); pg.wait_for_timeout(800)
        try:
            pg.wait_for_selector('#aib', state='attached', timeout=5000); pg.evaluate("document.getElementById('aib')&&document.getElementById('aib').scrollIntoView()"); pg.click('#aibopen'); pg.wait_for_timeout(600)
            inp = pg.query_selector('#aib input[type=text], #aib textarea, #aib input:not([type])')
            for q in ('what if the sun explodes',):
                inp = pg.query_selector('#aib input[type=text], #aib textarea, #aib input:not([type])'); inp.fill(q); inp.press('Enter'); pg.wait_for_timeout(2000); t = pg.inner_text('#aib')
                ck("I couldn't match that one. Name a team or a conference, like: What if BYU beats Utah?" in t, 'lab %dpx: %r shows the approved no-match line' % (w, q), t[-300:])
            ck(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'lab %dpx: no horizontal overflow' % w)
        except Exception as e: ck(False, 'lab %dpx flow' % w, e)
        ck(not errs, 'lab %dpx: no page errors' % w, errs); b.close()
print('%d checks, %d failed' % (n, bad)); srv.shutdown(); sys.exit(1 if bad else 0)
