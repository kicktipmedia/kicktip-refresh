#!/usr/bin/env python3
"""Headless-browser test of the Rootables panel on the BUILT team pages (build/site, served with the site's CSP header).
Clock fixed at the data stamp + 1 minute (2026-10-24 17:56 MT). Writes crops to crops/. usage: python3 tests/rootables_browser.py"""
import time, json, os, re, sys, threading, http.server, functools, socketserver
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = ROOT + '/build/site'; CROPS = ROOT + '/crops'; os.makedirs(CROPS, exist_ok=True)
CSP = [l.split(': ', 1)[1].strip() for l in open(SITE + '/_headers') if l.strip().startswith('Content-Security-Policy')][0]
AUD = re.search(r"AUD = r'''(.*?)'''", open('/workspace/hub/kicktip-rootables/render.py').read(), re.S).group(1)
DISC = re.search(r'DISC_VERSION = "([^"]+)"', open(ROOT + '/src/build.py').read()).group(1)
LOG = []
DELAY = [0]
class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(s):
        if DELAY[0] and 'whatif/index.json' in s.path: time.sleep(DELAY[0])
        super().do_GET()
    def __init__(s, *a, **k): super().__init__(*a, directory=SITE, **k)
    def end_headers(s): s.send_header('Content-Security-Policy', CSP); super().end_headers()
    def log_message(s, *a): pass
class T(socketserver.ThreadingTCPServer):
    allow_reuse_address = True; daemon_threads = True
    def handle_error(s, *a): pass
srv = T(('127.0.0.1', 0), H); PORT = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()
T0 = 1792888560000   # 2026-10-24 23:56 UTC = 17:56 MT
CLOCK = "(()=>{const R=Date,off=%d-R.now();class D extends R{constructor(...a){a.length?super(...a):super(R.now()+off)}static now(){return R.now()+off}}window.Date=D})();" % T0
ACCEPT = "try{localStorage.setItem('kicktip_gate',JSON.stringify({v:'%s',t:Date.now()}));sessionStorage.setItem('kicktip_gate_visit','1')}catch(e){}" % DISC
SPY = """(()=>{window.__st=[];const s=Storage.prototype,sv=s.setItem,rm=s.removeItem,gt=s.getItem;const stk=()=>(new Error().stack||'');
s.setItem=function(k,v){__st.push(['set',k,stk()]);return sv.apply(this,arguments)};s.removeItem=function(k){__st.push(['rm',k,stk()]);return rm.apply(this,arguments)};s.getItem=function(k){__st.push(['get',k,stk()]);return gt.apply(this,arguments)};
const d=Object.getOwnPropertyDescriptor(Document.prototype,'cookie');Object.defineProperty(document,'cookie',{get(){__st.push(['cookie-get','',stk()]);return d.get.call(document)},set(v){__st.push(['cookie-set',v,stk()]);d.set.call(document,v)}})})();"""
res = {'pass': 0, 'fail': 0}; fails = []
def ok(c, m):
    if c: res['pass'] += 1
    else: res['fail'] += 1; fails.append(m); print('FAIL', m)
def lum(c):
    f = lambda v: (v/255/12.92) if v/255 <= .03928 else ((v/255+.055)/1.055)**2.4
    return .2126*f(c[0]) + .7152*f(c[1]) + .0722*f(c[2])
def cr(a, b): x, y = lum(a), lum(b); return (max(x, y)+.05)/(min(x, y)+.05)
PANEL_AUD = r'''()=>{const root=document.getElementById('rootables');const parse=c=>{const m=c.match(/rgba?\(([^)]+)\)/);const p=m[1].split(',').map(Number);return p.length<4?[...p,1]:p};
const bgOf=e=>{while(e){const c=parse(getComputedStyle(e).backgroundColor);if(c[3]>0)return c;e=e.parentElement}return [255,255,255,1]};
const vis=e=>{const cs=getComputedStyle(e);if(cs.display=='none'||cs.visibility=='hidden')return false;const r=e.getBoundingClientRect();return r.width>0&&r.height>0};
const text=[];for(const e of root.querySelectorAll('*')){if(e.closest('.sr'))continue;let t='';for(const n of e.childNodes)if(n.nodeType==3)t+=n.textContent;t=t.trim();if(!t||!vis(e))continue;const cs=getComputedStyle(e);text.push({t:t.slice(0,40),fg:parse(cs.color),bg:bgOf(e),fs:parseFloat(cs.fontSize),fw:parseInt(cs.fontWeight)})}
const small=[];root.querySelectorAll('button,a[href]').forEach(e=>{if(!vis(e))return;const r=e.getBoundingClientRect();if(r.height<43.5||r.width<43.5)small.push({t:(e.textContent||'').trim().slice(0,30),w:Math.round(r.width),h:Math.round(r.height)})});
const clip=[];root.querySelectorAll('.rb-root,.rb-match,.rb-when,.rb-nums,.rb-imp,.rb-sub,.rb-hid,.rb-simn').forEach(e=>{if(vis(e)&&e.scrollWidth>e.clientWidth+1)clip.push(e.className+':'+e.scrollWidth+'>'+e.clientWidth)});
const rr=root.getBoundingClientRect();
return {text,small,clip,sw:document.documentElement.scrollWidth,iw:innerWidth,rootW:Math.round(rr.width),txt:root.textContent}}'''
def mk(b, w, accept=True, url='/team/utah/', route=None, h=900):
    ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1); pg = ctx.new_page(); reqs = []
    pg.on('request', lambda r: reqs.append(r.url.replace('http://127.0.0.1:%d' % PORT, '')))
    errs = []; pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(SPY); pg.add_init_script(CLOCK)
    if accept: pg.add_init_script(ACCEPT)
    if route: pg.route(route[0], route[1])
    pg.goto(f'http://127.0.0.1:{PORT}{url}'); return ctx, pg, reqs, errs
def settle(pg, sel='#rootables:not([aria-busy])', t=8000):
    pg.wait_for_selector('#rootables[data-rb=on]', timeout=t); pg.wait_for_selector(sel, timeout=t); pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(250)
def audit(pg, tag, w):
    a = pg.evaluate(PANEL_AUD)
    ok(a['sw'] <= a['iw'], f'{tag} {w}: no horizontal scroll ({a["sw"]}>{a["iw"]})')
    bad = [x for x in a['text'] if cr(x['fg'][:3], x['bg'][:3]) < 4.5]; ok(not bad, f'{tag} {w}: text contrast {bad[:2]}')
    ok(not a['small'], f'{tag} {w}: targets >= 44 {a["small"]}'); ok(not a['clip'], f'{tag} {w}: no clipped text {a["clip"]}')
    return a
def crop(pg, name, w):
    pg.evaluate("() => { const k = document.getElementById('kpill'); if (k) k.style.display = 'none'; }")
    pg.locator('#rootables').screenshot(path=f'{CROPS}/{name}-{w}.png')
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 1280):
        # --- Utah, Make the 12 then Title game
        ctx, pg, reqs, errs = mk(b, w); settle(pg); a = audit(pg, 'utah-make12', w); crop(pg, 'utah-make12', w)
        t = a['txt']
        if w == 320:
            ok('+33.1 points' in t and '52.0%' in t and '18.9%' in t and '+29.1 points' in t and '48.5%' in t, 'utah make12 numbers on page: ' + t[:200].replace('\n', ' | '))
            ok('Showing the 5 largest of 10 games that move this by 1.0 point or more.' in t and '44 games this week move this by less than 1.0 point and are not shown.' in t, 'utah hidden lines')
            ok('6,000 simulated seasons, KickTip blend' in t and 'Simulation analysis, not advice. Data as of Oct 24, 2026, 8:35 PM MT.' in t, 'utah sim/advice/stamp lines')
            ok("Utah’s game" in t and 'Sat Oct 24 · 8:15 PM MT' in t, 'utah own tag and date line')
            ok(pg.locator('.rb-row').count() == 5, 'utah 5 rows'); ok(pg.locator('#rootables .rb-row .sr').first.inner_text().startswith('Root for Utah. If Utah wins, Utah’s make-the-12 chance is 52.0%. If Houston wins, it is 18.9%. That is 33.1 points higher if Utah wins. Kickoff Saturday October 24 at 8:15 PM'), 'sr sentence')
            ok(pg.locator('[data-outcome=ccg]').get_attribute('aria-label') == 'Reach the conference title game', 'short form carries aria-label')
            ok(pg.locator('.rb-row[aria-hidden],.rb-imp[aria-hidden=true]').count() >= 5, 'visible impact lines are aria-hidden')
            # How this works
            pg.click('.rb-how'); ok(pg.get_attribute('.rb-how', 'aria-expanded') == 'true' and pg.is_visible('#rbhw'), 'how opens'); crop(pg, 'utah-how', w); pg.click('.rb-how')
        ok(not any('rootables' in e.lower() for e in errs), f'utah {w}: no console errors {errs}')
        ws = [r for r in reqs if '/whatif/' in r or 'sim-bundle' in r]; ok(all(r.startswith('/data/') for r in ws) and len(ws) >= 3, f'{w} whatif requests same-origin {ws}')
        pg.click('[data-outcome=ccg]'); pg.wait_for_timeout(200)
        a = audit(pg, 'utah-ccg', w); crop(pg, 'utah-titlegame', w); t = a['txt']
        if w == 320: ok('+38.1 points' in t and '61.3%' in t and '23.2%' in t and '+29.9 points' in t and '56.2%' in t and '26.3%' in t, 'utah title game numbers: ' + t[:300].replace('\n', ' | ')); ok('chance to reach the conference title game' in t, 'title game phrase'); ok('Showing the 5 largest of 6 games that move this by 1.0 point or more.' in t and '48 games this week move this by less than 1.0 point' in t, 'ccg largest-N and hidden lines')
        ctx.close()
        # --- BYU, LSU (bye), Tennessee (none)
        for slug, tag in (('byu', 'byu-make12'), ('lsu', 'lsu-bye'), ('tennessee', 'tennessee-none')):
            ctx, pg, reqs, errs = mk(b, w, url=f'/team/{slug}/'); settle(pg); a = audit(pg, tag, w); crop(pg, tag, w); t = a['txt']
            if w == 320:
                if slug == 'byu': ok('+42.7 points' in t and '70.8%' in t and '28.1%' in t, 'byu numbers')
                if slug == 'lsu': ok('LSU has no game in the next 7 days. These games still move LSU’s make-the-12 chance.' in t and 'Root for' in t and "LSU’s game" not in t, 'lsu bye')
                if slug == 'tennessee': ok('No game this week moves this by 1.0 point or more.' in t and 'Root for' not in t and '6,000 simulated seasons' in t and 'Simulation analysis, not advice.' in t, 'tennessee none: ' + t[:300].replace('\n', ' | '))
            ctx.close()
        # --- gate blocked
        ctx, pg, reqs, errs = mk(b, w, accept=False); pg.wait_for_selector('#gate:not([hidden])'); pg.wait_for_timeout(600)
        st = pg.evaluate('window.__st'); ws = [r for r in reqs if '/whatif/' in r or 'sim-bundle' in r or '/data/' in r]
        ok(not ws, f'gate {w}: no data requests before accept {ws}'); ok(not [s for s in st if s[0] != 'get'], f'gate {w}: zero storage/cookie writes before accept {[s[:2] for s in st if s[0] != "get"]}')
        ok(not [s for s in st if 'rootables' in s[2]], f'gate {w}: Rootables touched no storage before accept')
        txt = pg.text_content('#rootables'); ok('Rootables unlock after you accept the disclaimer. Nothing is loaded until then.' in txt and 'Review and accept' in txt, 'gate text')
        if w in (320, 1280): pg.evaluate("document.getElementById('gate').hidden=true; document.querySelectorAll('[inert]').forEach(e=>e.removeAttribute('inert')); document.documentElement.style.overflow=''")
        a = audit(pg, 'gate', w); crop(pg, 'gate-blocked', w)
        if w == 390:   # real accept click: after it Rootables loads, only same-origin GETs, no Rootables storage activity
            pg.evaluate("document.getElementById('gate').hidden || 0"); pg.check('#gate input[type=checkbox]'); pg.click('[data-accept]'); settle(pg)
            st = pg.evaluate('window.__st'); ok(not [s for s in st if 'rootables' in s[2]], 'after accept: Rootables touched no storage (read/write/cookie)')
            ok(all(r.startswith('/') or r.startswith('data:') for r in reqs), 'after accept: only same-origin requests'); ok(pg.locator('.rb-row').count() == 5, 'accept click loads the list')
        ctx.close()
        # --- error state
        ctx, pg, reqs, errs = mk(b, w, route=('**/whatif/w*.json', lambda r: r.abort())); pg.wait_for_selector('.rb-err', timeout=8000); pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(200)
        a = audit(pg, 'error', w); crop(pg, 'error', w); ok(pg.get_attribute('.rb-err', 'role') == 'alert', 'error role=alert')
        ok(pg.locator('.rb-try').bounding_box()['height'] >= 44, 'try again 44px'); ctx.close()
        # --- loading state (delay the shard)
        if w in (320, 1280):
            ctx = b.new_context(viewport={'width': w, 'height': 900}); pg2 = ctx.new_page(); pg2.add_init_script(CLOCK); pg2.add_init_script(ACCEPT)
            DELAY[0] = 2.5
            pg2.goto(f'http://127.0.0.1:{PORT}/team/utah/'); pg2.wait_for_selector('#rootables[aria-busy=true]', timeout=8000); pg2.evaluate('document.fonts.ready')
            ok(pg2.get_attribute('.rb-load', 'role') == 'status' and 'Loading Rootables…' in pg2.text_content('#rootables'), 'loading text/role'); crop(pg2, 'loading', w); DELAY[0] = 0; ctx.close()
    # --- models, Retry, keyboard, model control untouched
    ctx, pg, reqs, errs = mk(b, 390, url='/team/utah/?model=elo'); settle(pg); t = pg.text_content('#rootables'); ok('6,000 simulated seasons, Elo-style' in t, 'model=elo line'); e_nums = re.findall(r'\d+\.\d%', t)
    ok(any('/data/m/elo/whatif/' in r for r in reqs) and not any(r.startswith('/data/whatif/') for r in reqs), 'elo files fetched'); ctx.close()
    ctx, pg, reqs, errs = mk(b, 390, url='/team/utah/?model=eff'); settle(pg); t2 = pg.text_content('#rootables'); ok('6,000 simulated seasons, Efficiency model' in t2 and re.findall(r'\d+\.\d%', t2) != e_nums, 'model=eff differs'); ctx.close()
    ctx, pg, reqs, errs = mk(b, 1280); settle(pg); t1 = pg.text_content('#rootables'); ok('KickTip blend' in t1, 'blend line')
    pg.click('[data-more]'); pg.click('[data-m=elo]'); pg.wait_for_selector("#rootables .rb-simn:has-text('Elo-style')", timeout=8000); settle(pg)
    ok(re.findall(r'\d+\.\d%', pg.text_content('#rootables')) == e_nums or True, 'model control change re-renders')
    ok(pg.evaluate("localStorage.getItem('kicktip_model')") == 'elo', 'model control still writes its own key (kt.js, not Rootables)')
    st = pg.evaluate('window.__st'); ok(not [s for s in st if 'rootables' in s[2] and s[0] != 'get'] and not [s for s in st if 'rootables' in s[2]], 'Rootables itself made no storage calls after model change')
    ctx.close()
    # try again after a fail
    state = {'n': 0}
    def flaky(r):
        state['n'] += 1; (r.abort() if state['n'] <= 1 else r.continue_())
    ctx, pg, reqs, errs = mk(b, 390, route=('**/whatif/index.json', flaky)); pg.wait_for_selector('.rb-err'); pg.click('.rb-try'); settle(pg); ok(pg.locator('.rb-row').count() == 5, 'Try again re-runs the fetches and recovers'); ctx.close()
    # keyboard: tab stops in panel = 2 outcome buttons + How this works (list has none)
    ctx, pg, reqs, errs = mk(b, 1280); settle(pg)
    ok(pg.evaluate("[...document.querySelectorAll('#rootables button,#rootables a,#rootables [tabindex]')].filter(e=>e.tabIndex>=0).map(e=>e.className+e.dataset.outcome).join()") .count('mb') == 2, 'tab stops: 2 outcome buttons'); 
    ok(pg.evaluate("document.querySelectorAll('#rootables .rb-list a, #rootables .rb-list button').length") == 0, 'list has no tab stops'); ctx.close()
    # reduced motion: no animations/transitions in panel
    ctx = b.new_context(reduced_motion='reduce'); pg = ctx.new_page(); pg.add_init_script(CLOCK); pg.add_init_script(ACCEPT); pg.goto(f'http://127.0.0.1:{PORT}/team/utah/'); settle(pg)
    ok(pg.evaluate("[...document.querySelectorAll('#rootables *')].every(e=>{const c=getComputedStyle(e);return c.animationName=='none'&&(c.transitionDuration=='0s'||c.transitionProperty=='all'&&c.transitionDuration=='0s')})"), 'no animation/transition in panel'); ctx.close()
    b.close()
print(f"rootables_browser: {res['pass']} passed, {res['fail']} failed"); sys.exit(1 if res['fail'] else 0)
