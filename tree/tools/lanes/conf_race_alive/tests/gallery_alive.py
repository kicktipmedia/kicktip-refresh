#!/usr/bin/env python3
"""gallery_alive.py: real conf_race_alive cards (not the gal_* samples) in Chromium and WebKit at 320/390/430/1280 px.
Renders 10 real cards from the built tree's real data, writes screenshots to <out>/../out-gallery/conf_race_alive-<engine>-<width>.png, and checks: no JS errors, no render errors,
10 cards, no horizontal overflow, no card wider than its box, text identical in both engines, and the "Understood as" line height (reported, and capped at 3 lines at 320 px).
usage: python3 gallery_alive.py <built tree> [--browser chromium,webkit]"""
import sys, os, re, json, http.server, threading, functools
HERE = os.path.dirname(os.path.abspath(__file__)); TREE = os.path.abspath(sys.argv[1]); engines = (sys.argv[sys.argv.index('--browser') + 1] if '--browser' in sys.argv else 'chromium,webkit').split(',')
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Q, directory=TREE)); threading.Thread(target=srv.serve_forever, daemon=True).start(); base = 'http://127.0.0.1:%d' % srv.server_address[1]
shots = os.path.join(os.path.dirname(TREE), 'out-gallery'); os.makedirs(shots, exist_ok=True)
def route(rt):
    u = rt.request.url.replace(base, '')
    if u.startswith('/__alive/gallery.html'): return rt.fulfill(status=200, content_type='text/html', body=open(os.path.join(HERE, 'gallery_alive.html'), encoding='utf8').read())
    rt.continue_()
fails, texts, n = [], {}, 0
with sync_playwright() as pw:
    for eng in engines:
        br = getattr(pw, eng).launch()
        for w in (320, 390, 430, 1280):
            ctx = br.new_context(viewport={'width': w, 'height': 900}); pg = ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append('pageerror ' + str(e))); pg.on('console', lambda m: errs.append('console ' + m.text) if m.type == 'error' else None)
            pg.route(re.compile(r'.*127\.0\.0\.1.*/__alive/.*'), route)
            pg.goto(base + '/__alive/gallery.html'); pg.wait_for_selector('html[data-done="1"]', timeout=20000)
            d = pg.evaluate("""() => { const r = window.__TB, cards = [...document.querySelectorAll('.ac')], bad = cards.filter(c => c.scrollWidth > c.clientWidth + 1).map(c => c.getAttribute('data-tool'));
              const yq = cards.map(c => { const p = c.querySelector('p.yq'), tops = new Set(); [...p.childNodes].filter(n => n.nodeType === 3).forEach(n => { const r = document.createRange(); r.selectNodeContents(n); [...r.getClientRects()].forEach(x => tops.add(Math.round(x.top / 8))); }); return tops.size; });
              return { r, n: cards.length, page: document.scrollingElement.scrollWidth, vw: window.innerWidth, bad, yq, miss: cards.filter(c => c.classList.contains('tbox-miss')).length } }""")
            pg.screenshot(path=os.path.join(shots, 'conf_race_alive-%s-%d.png' % (eng, w)), full_page=True)
            probs = errs + d['r']['errors']
            if d['n'] != 10: probs.append('expected 10 cards, got %d' % d['n'])
            if d['miss']: probs.append('%d miss cards' % d['miss'])
            if d['page'] > d['vw'] + 1: probs.append('page overflows: %d > %d' % (d['page'], d['vw']))
            if d['bad']: probs.append('card wider than its box: %s' % d['bad'])
            if w == 320 and max(d['yq']) > 3:  probs.append('Understood-as line takes %d lines at 320 px (limit 3)' % max(d['yq']))
            texts.setdefault(w, {})[eng] = d['r']['texts']
            print('  %s %4dpx: %d cards, Understood-as lines per card %s' % (eng, w, d['n'], d['yq'])); n += 1
            if probs: fails.append('%s %dpx: %s' % (eng, w, '; '.join(probs)[:400]))
            ctx.close()
        br.close()
for w, m in texts.items():
    if len(m) == 2:
        a, b = list(m.values())
        if a != b: fails.append('%dpx: card text differs between engines' % w)
print(('FAILED' if fails else 'PASSED') + ': conf_race_alive gallery, %d page loads, shots in %s' % (n, shots)); [print('  FAIL', f) for f in fails]; sys.exit(1 if fails else 0)
