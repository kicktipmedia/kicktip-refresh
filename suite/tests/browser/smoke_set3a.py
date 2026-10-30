#!/usr/bin/env python3
"""Set 3a browser smoke (set3m) + crops (headless, offline: /api/* and Turnstile stubbed; the shipped CSP from _headers is served on every response).
 usage: smoke_set3c.py TREE ENGINE(chromium|webkit) [outdir] [BASE_TREE]. CSP: the card run's CSP console messages must equal the base tree's for the same home page + ask flow (WebKit reports one pre-existing home-page style refusal on the base too). ask-config 'tb' = the 19 shipped ids + team_stats + whatif_conference_outcome (the page switch, test only).
 Checks per card and width (320/390/768): card renders for the right tool, no page errors, no CSP violations, no /api/ask POST, no inline style attr in the card, no horizontal overflow,
 every link/button in the card >= 44px tall, text contrast >= 4.5:1. Also: flag off (19 ids) -> no new-tool card. Crops: <outdir>/set3c-<engine>-<w>-<case>.png"""
import sys, os, json, re, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
TREE = os.path.abspath(sys.argv[1]); ENG = sys.argv[2]; OUT = os.path.abspath(sys.argv[3] if len(sys.argv) > 3 else 'crops'); os.makedirs(OUT, exist_ok=True)
CSP = re.search(r'Content-Security-Policy: (.*)', open(os.path.join(TREE, '_headers')).read()).group(1).strip()
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def end_headers(self): self.send_header('Content-Security-Policy', CSP); super().end_headers()
BASE = os.path.abspath(sys.argv[4]) if len(sys.argv) > 4 else None
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=TREE)); PORT = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()
W = open(os.path.join(TREE, '_worker.js')).read(); L19 = json.loads(re.search(r"const TB_LIVE_TOOLS = (\[[^\]]*\]);", W).group(1).replace("'", '"'))
NEW = ['my_teams_digest', 'cfp_committee_rankings']
CASES = [('mt-digest', 'How are my teams doing?', 'my_teams_digest'), ('mt-empty', 'My teams', 'my_teams_digest'), ('cr-top', 'Committee top 12', 'cfp_committee_rankings'), ('cr-team', 'Where is Indiana in the committee rankings?', 'cfp_committee_rankings')]
TS = "window.turnstile={render:function(el,o){setTimeout(function(){o.callback&&o.callback('good')},10);return 'w1'},reset:function(){},remove:function(){},getResponse:function(){return 'good'}};"
n = 0; bad = 0
def ck(ok, what, x=''):
    global n, bad; n += 1
    if not ok: bad += 1
    print(('PASS ' if ok else 'FAIL ') + what + ('' if ok else ' :: ' + str(x)[:300])); sys.stdout.flush()
JS_TS = """(el) => {
  var out={align:[],split:[],clip:[],hdr:[]}; var t=el.querySelector('table.ba'); if(!t) return {none:1};
  t.querySelectorAll('tr').forEach(function(tr){ [].forEach.call(tr.children,function(c,j){ out.align.push(j+':'+getComputedStyle(c).textAlign); if(c.scrollWidth>c.clientWidth+1) out.clip.push(c.textContent.trim());
    var tn=document.createTreeWalker(c,NodeFilter.SHOW_TEXT),x; while((x=tn.nextNode())){ var re=/\\S+/g,m; while((m=re.exec(x.textContent))){ var rg=document.createRange(); rg.setStart(x,m.index); rg.setEnd(x,m.index+m[0].length); var ys={}; [].forEach.call(rg.getClientRects(),function(q){ if(q.width>0) ys[Math.round(q.top)]=1}); if(Object.keys(ys).length>1) out.split.push(m[0]); } } }); });
  t.querySelectorAll('th').forEach(function(h){out.hdr.push(h.textContent.trim())}); return out; }"""
JS_CHECK = """(el) => {
  function lum(c){var m=c.match(/[\\d.]+/g).map(Number);var a=m.length>3?m[3]:1;var f=m.slice(0,3).map(function(v){v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)});return [0.2126*f[0]+0.7152*f[1]+0.0722*f[2],a]}
  function bg(e){while(e){var c=getComputedStyle(e).backgroundColor;var l=lum(c);if(l[1]>0.5)return l[0];e=e.parentElement}return 1}
  var worst=99, wtxt='', small=[];
  el.querySelectorAll('*').forEach(function(e){ if(!e.childNodes.length) return; var own=[].some.call(e.childNodes,function(c){return c.nodeType===3&&c.textContent.trim()}); if(!own) return;
    var r=e.getBoundingClientRect(); if(!r.width) return; var fg=lum(getComputedStyle(e).color)[0], b=bg(e); var cr=(Math.max(fg,b)+0.05)/(Math.min(fg,b)+0.05); if(cr<worst){worst=cr;wtxt=e.textContent.trim().slice(0,40)} });
  el.querySelectorAll('a,button').forEach(function(e){var r=e.getBoundingClientRect(); if(r.width&&r.height<44) small.push(e.textContent.trim().slice(0,30)+':'+Math.round(r.height))});
  return {worst:worst, wtxt:wtxt, small:small, styled: el.querySelectorAll('[style]').length + (el.hasAttribute('style')?1:0), over: document.documentElement.scrollWidth - document.documentElement.clientWidth};
}"""
def page(pw, w, live):
    b = getattr(pw, ENG).launch(headless=True); ctx = b.new_context(viewport={'width': w, 'height': 900}); pg = ctx.new_page(); st = {'calls': [], 'errs': [], 'csp': []}
    pg.on('pageerror', lambda e: st['errs'].append(str(e)))
    pg.on('console', lambda m: st['csp'].append(m.text) if ('Content Security Policy' in m.text or 'Refused to' in m.text) else None)
    def api(route):
        u = route.request.url; st['calls'].append((route.request.method, '/' + u.split('/', 3)[3]))
        if u.endswith('/api/ask-config'): route.fulfill(status=200, content_type='application/json', body=json.dumps({'enabled': True, 'sitekey': 'x', 'maxChars': 300, 'tokenField': 'cf_turnstile', 'tb': live, 'router': True}))
        elif u.endswith('/api/tb-count'): route.fulfill(status=200, content_type='application/json', body='{"ok":true,"n":1}')
        elif '/api/ask' in u: route.fulfill(status=200, content_type='application/json', body=json.dumps({'enabled': True, 'ok': False, 'fallback': True, 'reason': 'daily_cap'}))
        else: route.fulfill(status=404, body='{}')
    pg.route('**/api/**', api); pg.route('**/challenges.cloudflare.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=TS))
    return b, pg, st
def ask(pg, q, port=None):
    pg.goto('http://127.0.0.1:%d/' % (port or PORT)); pg.wait_for_timeout(500)
    pg.click('#kpill'); pg.wait_for_selector('#kask', state='visible'); pg.fill('#kask', q); pg.press('#kask', 'Enter')
shots = 0
BASEMSG = {}
if BASE:
    bsrv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=BASE)); BPORT = bsrv.server_address[1]; threading.Thread(target=bsrv.serve_forever, daemon=True).start()
with sync_playwright() as pw:
    if BASE:
        for w in (320, 390, 768):
            b, pg, st = page(pw, w, L19); ask(pg, 'When did Utah last make the playoff?', BPORT); pg.wait_for_timeout(2500); BASEMSG[w] = sorted(st['csp']); b.close()
            print('info: base tree CSP console messages at %dpx (pre-existing): %d %s' % (w, len(BASEMSG[w]), sorted(set(x[:80] for x in BASEMSG[w]))))
    for w in (320, 390, 768):
        for case, q, tool in CASES:
            b, pg, st = page(pw, w, L19 + NEW); tag = '%s %dpx %s' % (ENG, w, case)
            try:
                if case == 'mt-digest': pg.goto('http://127.0.0.1:%d/' % PORT); pg.wait_for_timeout(400); pg.evaluate("() => ['utah','byu','indiana','notre-dame'].forEach(s => window.KTMyTeams.toggle(s))")
                ask(pg, q); pg.wait_for_selector('.tbox[data-tool="%s"]' % tool, timeout=8000); el = pg.query_selector('.tbox[data-tool="%s"]' % tool); pg.wait_for_timeout(200)
                r = el.evaluate(JS_CHECK)
                ck(True, tag + ': card for ' + tool)
                ck(r['over'] <= 0, tag + ': no horizontal overflow', r['over'])
                ck(not r['small'], tag + ': taps >= 44px', r['small'])
                ck(r['worst'] >= 4.5, tag + ': contrast >= 4.5 (worst %.2f)' % r['worst'], r['wtxt'])
                ck(r['styled'] == 0, tag + ': no inline style attributes in the card', r['styled'])
                cspN = list(st['csp']); el.scroll_into_view_if_needed(); el.screenshot(caret='initial', animations='allow', path=os.path.join(OUT, 'set3a-%s-%d-%s.png' % (ENG, w, case))); shots += 1
            except Exception as e: cspN = list(st['csp']); ck(False, tag + ': card for ' + tool, e)
            ck(not st['errs'], tag + ': no page errors', st['errs']); ck(sorted(cspN) == BASEMSG.get(w, []), tag + ': no CSP violations beyond the base tree (%d vs base %d; counted before the crop, Playwright screenshots inject their own style)' % (len(cspN), len(BASEMSG.get(w, []))), cspN)
            ck(not [c for c in st['calls'] if c[0] == 'POST' and c[1].startswith('/api/ask') and 'config' not in c[1]], tag + ': no /api/ask POST (matcher answer, zero model calls)', st['calls'])
            b.close()
    for case, q, tool in CASES[::2]:
        b, pg, st = page(pw, 390, L19); ask(pg, q); pg.wait_for_timeout(2500)
        ck(not pg.query_selector('.tbox[data-tool="%s"]' % tool), '%s flag off (19 ids) "%s": no %s card' % (ENG, q, tool)); b.close()
print('crops %d in %s' % (shots, OUT)); print('\n%d checks, %d failed' % (n, bad)); sys.exit(1 if bad else 0)
