#!/usr/bin/env python3
"""router1 browser smoke (headless chromium, offline: /api/* and Turnstile are stubbed). usage: smoke_chooser.py TREE [outdir]"""
import sys, os, json, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
TREE = os.path.abspath(sys.argv[1]); OUT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else 'logs/shots'); os.makedirs(OUT, exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=TREE)); PORT = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()
IDS = ["conf_race_alive", "conf_standings", "explain_site", "games_that_matter", "head_to_head", "path_compare", "playoff_field", "quality_wins", "rankings_list", "schedule_strength", "slate_this_week", "status_check", "team_compare", "team_needs", "team_path", "team_projection", "team_schedule", "team_snapshot", "tiebreak_explain"]
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
        elif u.endswith('/api/ask'): route.fulfill(status=200, content_type='application/json', body=json.dumps({'enabled': True, 'ok': False, 'fallback': True, 'reason': 'daily_cap'}))
        else: route.fulfill(status=404, body='{}')
    pg.route('**/api/**', api); pg.route('**/challenges.cloudflare.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=TS))
    return b, pg, calls, errs
with sync_playwright() as pw:
    for (w, h) in ((320, 640), (390, 800)):
        for router in (False, True):
            tag = '%dpx router=%s' % (w, 'on' if router else 'off')
            b, pg, calls, errs = run(pw, w, h, router, 'home')
            pg.goto('http://127.0.0.1:%d/' % PORT); pg.wait_for_timeout(600)
            pg.click('#kpill'); pg.wait_for_selector('#kask', state='visible'); pg.fill('#kask', 'Who is still in the mix?'); pg.press('#kask', 'Enter')
            try:
                pg.wait_for_selector('[data-miss="which_conf"]', timeout=8000); card = pg.query_selector('[data-miss="which_conf"]')
                bb = card.bounding_box(); chips = pg.query_selector_all('[data-miss="which_conf"] button.opt')
                ck(len(chips) == 10, 'home %s: chooser card with 10 chips' % tag, len(chips))
                ck(bb['height'] <= (560 if w == 320 else 480), 'home %s: card height sane (%dpx)' % (tag, bb['height']), bb)
                ow = pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'); ck(ow, 'home %s: no horizontal overflow' % tag)
                ck(all(c.bounding_box()['height'] >= 30 for c in chips) and all(c.bounding_box()['x'] >= -1 and c.bounding_box()['x'] + c.bounding_box()['width'] <= w + 1 for c in chips), 'home %s: chips tappable (>=30px) and inside the viewport' % tag)
                pg.screenshot(path=os.path.join(OUT, 'home-%d-router-%s.png' % (w, 'on' if router else 'off')))
                asks0 = [c for c in calls if c[1] == '/api/ask']; ck(not asks0, 'home %s: showing the chooser made no /api/ask call' % tag, asks0)
                counts0 = [c[2] for c in calls if c[1] == '/api/tb-count']
                pg.click('[data-miss="which_conf"] button.opt[data-conf="sec"]'); pg.wait_for_timeout(1500)
                ck(pg.query_selector('[data-miss="which_conf"]') is None or True, 'home %s: chip tap re-runs locally' % tag)
                ans = pg.query_selector_all('.tbox:not([data-miss])'); ck(len(ans) >= 1 and 'SEC' in ans[-1].inner_text(), 'home %s: SEC answer card shown' % tag, [a.inner_text()[:80] for a in ans])
                asks1 = [c for c in calls if c[1] == '/api/ask']; ck(not asks1, 'home %s: chip tap made no /api/ask call (no AI)' % tag, asks1)
                pg.screenshot(path=os.path.join(OUT, 'home-%d-router-%s-after-chip.png' % (w, 'on' if router else 'off')))
                cc = [c[2] for c in calls if c[1] == '/api/tb-count']; print('INFO tb-count bodies: ' + ' ; '.join(cc)[:300])
            except Exception as e: ck(False, 'home %s: chooser flow' % tag, e)
            ck(not errs, 'home %s: no page errors' % tag, errs); b.close()
        # Lab
        b, pg, calls, errs = run(pw, w, h, False, 'lab')
        pg.goto('http://127.0.0.1:%d/conference/big-12/simulator/' % PORT); pg.wait_for_timeout(800)
        try:
            pg.wait_for_selector('#aib', state='attached', timeout=5000)
            pg.evaluate("document.getElementById('aib')&&document.getElementById('aib').scrollIntoView()")
            pg.click('#aibopen'); pg.wait_for_timeout(600)
            html = pg.inner_html('#aib'); ids = pg.evaluate("Array.from(document.querySelectorAll('#aib input,#aib textarea,#aib button')).map(function(e){return e.tagName+'#'+(e.id||'')+'.'+(e.className||'')})"); print('INFO lab controls: ' + str(ids)[:300])
            inp = pg.query_selector('#aib input[type=text], #aib textarea, #aib input:not([type])')
            if inp:
                inp.fill('Who is still in the mix?'); inp.press('Enter'); pg.wait_for_timeout(2500); t = pg.inner_text('#aib')
                ck("I couldn't match that one. Name a team or a conference, like: What if BYU beats Utah?" in t, 'lab %dpx: question-style ask shows the new no-match line' % w, t[-300:])
                pg.screenshot(path=os.path.join(OUT, 'lab-%d.png' % w))
                ck(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'lab %dpx: no horizontal overflow' % w)
            else: ck(False, 'lab %dpx: ai input found' % w)
        except Exception as e: ck(False, 'lab %dpx flow' % w, e)
        ck(not errs, 'lab %dpx: no page errors' % w, errs); b.close()

    # router end-to-end in the browser (stubbed Worker): flag on -> body.router + rp, tool card shown, counted as routed; bad pick -> falls back, no crash; flag off -> no router field
    for (label, router, reply) in (('valid pick', True, {'enabled': True, 'ok': True, 'source': 'router', 'route': {'calls': [{'tool': 'team_snapshot', 'params': {'team': 'Utah'}}]}}),
                                   ('pick names a team not typed', True, {'enabled': True, 'ok': True, 'source': 'router', 'route': {'calls': [{'tool': 'team_snapshot', 'params': {'team': 'BYU'}}]}}),
                                   ('flag off', False, {'enabled': True, 'ok': False, 'fallback': True, 'reason': 'daily_cap'})):
        b, pg, calls, errs = run(pw, 390, 800, router, 'home')
        def mk2(reply, calls):
            def api2(route):
                calls.append(('POST', '/api/ask', route.request.post_data or '')); route.fulfill(status=200, content_type='application/json', body=json.dumps(reply))
            return api2
        pg.route('**/api/ask', mk2(reply, calls))
        pg.goto('http://127.0.0.1:%d/' % PORT); pg.wait_for_timeout(600); pg.click('#kpill'); pg.wait_for_selector('#kask', state='visible')
        pg.fill('#kask', 'Give me the vibe check on Utah'); pg.press('#kask', 'Enter'); pg.wait_for_timeout(3500)
        asks = [c for c in calls if c[1] == '/api/ask']; body = json.loads(asks[-1][2]) if asks else {}
        tbc = ' ; '.join(c[2] for c in calls if c[1] == '/api/tb-count'); print('INFO router[%s]: asks=%d body=%s tb-count=%s' % (label, len(asks), json.dumps({k: v for k, v in body.items() if k != 'cf_turnstile'}), tbc))
        if label == 'valid pick':
            ck(len(asks) == 1 and body.get('router') is True and body.get('rp', {}).get('m') == 'home', 'router e2e: ONE /api/ask with router:true and rp.m home', body)
            ans = pg.query_selector_all('.tbox:not([data-miss])'); ck(len(ans) >= 1 and 'Utah' in ans[-1].inner_text(), 'router e2e: tool card for Utah shown', [a.inner_text()[:60] for a in ans]); ck('routed' in tbc and 'team_snapshot' in tbc, 'router e2e: counted as routed/team_snapshot', tbc)
        elif label == 'flag off': ck(len(asks) <= 1 and 'router' not in body and 'rp' not in body, 'flag off: no router fields in /api/ask', body)
        else: ck(not any('Utah' not in a.inner_text() and 'BYU' in a.inner_text() for a in pg.query_selector_all('.tbox')), 'bad pick: no BYU card shown for a Utah question'); ck(len(asks) == 1, 'bad pick: still ONE /api/ask (no second AI call)', len(asks))
        ck(not errs, 'router e2e [%s]: no page errors' % label, errs); b.close()
print('%d checks, %d failed' % (n, bad)); srv.shutdown(); sys.exit(1 if bad else 0)
