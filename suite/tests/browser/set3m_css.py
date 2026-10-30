#!/usr/bin/env python3
"""set3m core CSS fix check: `.pnl .ac .yq a[data-tb-change]{display:inline;min-height:0;padding:12px 0}`.
 usage: set3m_css.py TREE ENGINE [outdir] [BASE_TREE]. For existing cards (schedule_strength, rankings_list, team_needs) and every new Set 3 card, at 320/390/768:
 the 'Understood as ... Change' paragraph (p.yq) is about 40px tall (<= 48; was ~64 with the inline-flex 44px link), the Change link box is >= 44px tall and
 elementFromPoint 2px inside its top and bottom edges hits the link (44px tap area kept). Crops: <outdir>/set3m-change-<engine>-<w>-<case>.png (the p.yq line)."""
import sys, os, json, re, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
TREE = os.path.abspath(sys.argv[1]); ENG = sys.argv[2]; OUT = os.path.abspath(sys.argv[3] if len(sys.argv) > 3 else 'crops'); os.makedirs(OUT, exist_ok=True)
BASE = os.path.abspath(sys.argv[4]) if len(sys.argv) > 4 else None
def serve(d):
    csp = re.search(r'Content-Security-Policy: (.*)', open(os.path.join(d, '_headers')).read()).group(1).strip()
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
        def end_headers(self): self.send_header('Content-Security-Policy', csp); super().end_headers()
    s = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=d)); threading.Thread(target=s.serve_forever, daemon=True).start(); return s.server_address[1]
W = open(os.path.join(TREE, '_worker.js')).read()
L = json.loads(re.search(r"const TB_LIVE_TOOLS = (\[[^\]]*\]);", W).group(1).replace("'", '"')) + json.loads(re.search(r"const TB_SET3_IDS = (\[[^\]]*\]);", W).group(1).replace("'", '"'))
CASES = [('schedule_strength', "How hard is Utah's schedule?", 'schedule_strength', 1), ('rankings_list', 'Top 25', 'rankings_list', 1), ('team_needs', 'What does Utah need to make the playoff?', 'team_needs', 1),
         ('team_history', 'When did Utah last make the playoff?', 'team_history', 0), ('game_win_chance', 'Will Utah beat BYU?', 'game_win_chance', 0), ('team_stats', 'How many points per game does BYU score?', 'team_stats', 0),
         ('whatif_conference_outcome', 'if Utah wins the Big 12', 'whatif_conference_outcome', 0), ('my_teams_digest', 'How are my teams doing?', 'my_teams_digest', 0), ('cfp_committee_rankings', 'Committee top 12', 'cfp_committee_rankings', 0)]
TS = "window.turnstile={render:function(el,o){setTimeout(function(){o.callback&&o.callback('good')},10);return 'w1'},reset:function(){},remove:function(){},getResponse:function(){return 'good'}};"
n = 0; bad = 0
def ck(ok, what, x=''):
    global n, bad; n += 1
    if not ok: bad += 1
    print(('PASS ' if ok else 'FAIL ') + what + ('' if ok else ' :: ' + str(x)[:300])); sys.stdout.flush()
MEAS = """(el) => { var p = el.querySelector('p.yq'); if (!p) return null; var a = p.querySelector('a[data-tb-change]'); var pr = p.getBoundingClientRect(), r = a.getBoundingClientRect(), rs = a.getClientRects(), cs = getComputedStyle(a);
  var x = r.left + r.width / 2, hit = 0, over = {}; for (var y = r.top + 0.5; y < r.bottom; y++) { var e = document.elementFromPoint(x, y); if (e && (e === a || a.contains(e))) hit++; else if (e) { var k = e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).split(' ')[0] : ''); over[k] = (over[k] || 0) + 1; } }
  var lh = parseFloat(getComputedStyle(p).lineHeight); a.classList.add('x-nopad'); var st = document.createElement('style'); st.textContent = '.x-nopad{padding:0!important}'; document.head.appendChild(st); var h0 = p.getBoundingClientRect().height; st.remove(); a.classList.remove('x-nopad');
  return { yq: pr.height, yqNoPad: h0, lh: lh, textLines: Math.round(h0 / lh), ah: r.height, lines: rs.length, hit: hit, over: over, disp: cs.display, pos: cs.position, mh: cs.minHeight, pad: cs.paddingTop + ' ' + cs.paddingBottom }; }"""
def run(pw, port, w, case, q, tool, crop):
    b = getattr(pw, ENG).launch(headless=True); pg = b.new_context(viewport={'width': w, 'height': 900}).new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    def api(route):
        u = route.request.url
        if u.endswith('/api/ask-config'): route.fulfill(status=200, content_type='application/json', body=json.dumps({'enabled': True, 'sitekey': 'x', 'maxChars': 300, 'tokenField': 'cf_turnstile', 'tb': L, 'router': True}))
        elif u.endswith('/api/tb-count'): route.fulfill(status=200, content_type='application/json', body='{"ok":true,"n":1}')
        else: route.fulfill(status=200, content_type='application/json', body=json.dumps({'enabled': True, 'ok': False, 'fallback': True, 'reason': 'daily_cap'}))
    pg.route('**/api/**', api); pg.route('**/challenges.cloudflare.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=TS))
    if tool == 'my_teams_digest': pg.goto('http://127.0.0.1:%d/' % port); pg.wait_for_timeout(400); pg.evaluate("() => ['utah','byu','indiana','notre-dame'].forEach(s => window.KTMyTeams.toggle(s))")
    pg.goto('http://127.0.0.1:%d/' % port); pg.wait_for_timeout(500); pg.click('#kpill'); pg.wait_for_selector('#kask', state='visible'); pg.fill('#kask', q); pg.press('#kask', 'Enter')
    pg.wait_for_selector('.tbox[data-tool="%s"]' % tool, timeout=8000); pg.wait_for_timeout(250); el = pg.query_selector('.tbox[data-tool="%s"]' % tool); m = el.evaluate(MEAS)
    if crop and m: y = el.query_selector('p.yq'); y.scroll_into_view_if_needed(); y.screenshot(path=crop)
    b.close(); return m, errs
with sync_playwright() as pw:
    P = serve(TREE); BP = serve(BASE) if BASE else None
    for w in (320, 390, 768):
        for case, q, tool, old in CASES:
            tag = '%s %dpx %s' % (ENG, w, case)
            try: m, errs = run(pw, P, w, case, q, tool, os.path.join(OUT, 'set3m-change-%s-%d-%s.png' % (ENG, w, case)))
            except Exception as e: ck(False, tag + ': card renders', e); continue
            ck(m is not None, tag + ': card has the Understood as / Change line', m)
            if not m: continue
            print('info %s: %s' % (tag, json.dumps(m)))
            ck(not errs, tag + ': no page errors', errs)
            ck(m['disp'] == 'inline' and m['pos'] == 'relative' and m['mh'] in ('0px', 'auto') and m['pad'] == '12px 12px', tag + ': fix applied (inline, min-height 0, padding 12px 0, position relative)', m)
            ck(abs(m['yq'] - m['yqNoPad']) < 0.5, tag + ': the Change link adds no height to p.yq (%.1f = text only %.1f, %d line(s); 2 lines ~40px)' % (m['yq'], m['yqNoPad'], m['textLines']), m)
            ck(m['textLines'] > 2 or m['yq'] <= 48, tag + ': p.yq about 40px or less at <= 2 text lines (%.1f)' % m['yq'], m)
            ck(m['ah'] >= 44, tag + ': Change link box >= 44px tall (%.1f)' % m['ah'], m)
            ck(m['hit'] >= 44, tag + ': taps hit the link over >= 44px of its height (%d px; covered by %s)' % (m['hit'], m['over']), m)
            if old and BP:
                try: bm, _ = run(pw, BP, w, case, q, tool, None); print('info base vis1c %s: %s' % (tag, json.dumps(bm))); ck(bm and bm['yq'] >= m['yq'] + 20, tag + ': base vis1c p.yq taller (%.1f) than set3m (%.1f)' % (bm['yq'], m['yq']), bm)
                except Exception as e: ck(False, tag + ': base card', e)
print('\n%d checks, %d failed' % (n, bad)); sys.exit(1 if bad else 0)
