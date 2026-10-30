#!/usr/bin/env python3
"""scn_a1 browser smoke (headless chromium, offline: /api/* and Turnstile stubbed). Home What-If panel at 320 and 390 px: the facts card, the clarify (no card), no AI call, no overflow. usage: smoke_scn_a1.py TREE [outdir]"""
import sys, os, json, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
TREE = os.path.abspath(sys.argv[1]); OUT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else 'logs/shots'); os.makedirs(OUT, exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=TREE)); PORT = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()
IDS = ["conf_race_alive", "conf_standings", "games_that_matter", "path_compare", "playoff_field", "rankings_list", "team_needs", "team_path", "team_schedule", "team_snapshot", "tiebreak_explain"]
n = 0; bad = 0
def ck(ok, what, x=''):
    global n, bad; n += 1
    if not ok: bad += 1
    print(('PASS ' if ok else 'FAIL ') + what + ('' if ok else ' :: ' + str(x)[:300]))
TS = "window.turnstile={render:function(el,o){setTimeout(function(){o.callback&&o.callback('good')},10);return 'w1'},reset:function(){},remove:function(){},getResponse:function(){return 'good'}};"
def run(pw, w, h, ai=False):
    b = pw.chromium.launch(); ctx = b.new_context(viewport={'width': w, 'height': h}); pg = ctx.new_page(); calls = []; errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    def api(route):
        u = route.request.url; calls.append((route.request.method, u.split(str(PORT))[1], route.request.post_data or ''))
        if u.endswith('/api/ask-config'): route.fulfill(status=200, content_type='application/json', body=json.dumps({'enabled': ai, 'sitekey': 'x', 'maxChars': 300, 'tokenField': 'cf_turnstile', 'tb': IDS}))
        elif u.endswith('/api/tb-count'): route.fulfill(status=200, content_type='application/json', body='{"ok":true,"n":1}')
        else: route.fulfill(status=404, body='{}')
    pg.route('**/api/**', api); pg.route('**/challenges.cloudflare.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=TS))
    return b, pg, calls, errs
CASES = [  # question, kind, must-contain, must-not
    ("what if BYU and Texas Tech end with just one loss", 'card', ["What this means for BYU and Texas Tech", "8-1 conference", "Tiebreaker steps", "Rules source", "Head-to-head"], []),
    ("What if Arizona, TCU and Utah all lose 1 of the remaining games", 'clarify', ["Those teams play each other"], ["What this means for"]),
    ("what if Utah and Texas Tech win out", 'card', ["reach the Big 12 conference championship game", "Utah: ", "Figures"], []),
    ("what if New Mexico State and Western Kentucky win out", 'card', ["broken by head-to-head (Step 1)", "Conference USA"], []),
    ("what if BYU and Texas Tech end with just one loss", 'card-ai', ["What this means for BYU and Texas Tech", "8-1 conference"], []),
    ("what if BYU beats Utah", 'nocard', ["BYU"], ["What this means for"]),
]
with sync_playwright() as pw:
    for (w, h) in ((320, 640), (390, 800)):
        for q, kind, must, mustnot in CASES:
            tag = '%dpx %s' % (w, q[:40]); b, pg, calls, errs = run(pw, w, h, kind == 'card-ai'); pg.goto('http://127.0.0.1:%d/' % PORT); pg.wait_for_timeout(600)
            pg.click('#kpill'); pg.wait_for_selector('#kask', state='visible'); pg.fill('#kask', q); pg.press('#kask', 'Enter')
            if kind == 'card-ai':
                pg.wait_for_selector('[data-airun]', timeout=15000); pg.click('[data-airun]')
            try: pg.wait_for_function("() => { const d = document.getElementById('kask').closest('[role=dialog]') || document.body; return !/Running your scenario/.test(d.innerText) && !!d.querySelector('.pnl .ac, .pnl .sx'); }", timeout=60000)
            except Exception: pass
            pg.wait_for_timeout(1500)
            t = pg.evaluate("(document.getElementById('kask').closest('[role=dialog]')||document.body).innerText"); asks = [c for c in calls if c[1] == '/api/ask']
            for m in must: ck((m in t) or (m.startswith('What this means') and m.upper() in t), 'scn %s: shows %r' % (tag, m), t[:500])
            for m in mustnot: ck(m not in t, 'scn %s: does not show %r' % (tag, m), t[:300])
            sx = pg.query_selector_all('.pnl .sx'); ck((len(sx) == 1) == (kind in ('card', 'card-ai')), 'scn %s: card present = %s' % (tag, kind in ('card', 'card-ai')), len(sx))
            ck(not asks, 'scn %s: no /api/ask (no AI call)' % tag, asks)
            if sx:
                bb = sx[0].bounding_box(); ck(bb['x'] >= -1 and bb['x'] + bb['width'] <= w + 1, 'scn %s: card inside viewport' % tag, bb)
                ck(pg.evaluate("(function(){var s=document.querySelector('.pnl .sx');return s.scrollWidth<=s.clientWidth+1})()"), 'scn %s: card content does not overflow its box' % tag)
                ck(pg.evaluate("(function(){var s=document.querySelector('.pnl .sx');var t=s.querySelector('table');return !t||t.getBoundingClientRect().right<=s.getBoundingClientRect().right+1})()"), 'scn %s: figures table fits inside the card' % tag)
                ck(pg.evaluate("(function(){var a=document.querySelector('.pnl .ac');var c=a.children;var i=-1,j=-1;for(var k=0;k<c.length;k++){if(c[k].classList.contains('sx'))i=k;if(c[k].tagName=='TABLE'&&j<0)j=k}return i>=0&&(j<0||i<j)})()"), 'scn %s: card sits above the before/after tables' % tag)
                pg.screenshot(path=os.path.join(OUT, 'a1-%d-%s.png' % (w, q[8:24].replace(' ', '_'))))
            ck(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'scn %s: no horizontal overflow' % tag); ck(not errs, 'scn %s: no page errors' % tag, errs); b.close()
        # card survives "Run again", loads its two data files once
        b, pg, calls, errs = run(pw, w, h, False); reqs = []; pg.on('request', lambda r: reqs.append(r.url)); pg.goto('http://127.0.0.1:%d/' % PORT); pg.wait_for_timeout(600)
        pg.click('#kpill'); pg.wait_for_selector('#kask', state='visible')
        ck(not [u for u in reqs if 'explain.js' in u or 'ccg-sim.json' in u or 'ccgsim.js' in u], 'scn %dpx: opening the panel loads none of the card files' % w, [u for u in reqs if 'ccg' in u])
        pg.fill('#kask', 'what if Utah and Texas Tech win out'); pg.press('#kask', 'Enter'); pg.wait_for_selector('.pnl .sx', timeout=60000)
        pg.click('[data-regen]'); pg.wait_for_timeout(500)
        try: pg.wait_for_selector('.pnl .sx', timeout=60000)
        except Exception: pass
        ck(len(pg.query_selector_all('.pnl .sx')) == 1, 'scn %dpx: card is back after Run again' % w); ck(len([u for u in reqs if 'ccg-sim.json' in u]) <= 2, 'scn %dpx: ccg-sim.json fetched at most twice (cache lets a repeat reuse it)' % w, [u for u in reqs if 'ccg-sim.json' in u])
        ck(not errs, 'scn %dpx: no page errors after Run again' % w, errs); b.close()
print('%d checks, %d failed' % (n, bad)); srv.shutdown(); sys.exit(1 if bad else 0)
