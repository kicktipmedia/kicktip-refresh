#!/usr/bin/env python3
"""og_cards.py: KickTip Batch B per-team Rootables share cards (SHARE-SPEC rev 3, sha 1b18d56c) drawn into a site dir.
usage: og_cards.py <site> [--base <previous site>] [--all] [--report R.json]
 - data: og_rows.js (the site's own assets/rootables.js blended compute, the same rows as the page, cap 8)
 - layout: card3.py html() (Creative's renderer). Both sizes per team page: og/rootables/{slug}-1200x630.png (og:image) and -1080x1350.png (tall).
 - render-only-changed: key = sha256(card html without the Updated stamp + card3.py + font + this file). A card whose key equals the one in
   <base>/data/og-cards.json keeps the base PNG byte-for-byte (and its stamp); otherwise it is drawn with the stamp of this data.
   KT_OG_CACHE (dir): key -> PNG cache, so apply_data's second (determinism) build reuses the first build's renders.
 - Headless Chromium via Playwright (already installed by the refresh workflow for the browser suite). PNGs re-encoded with Pillow, palette-quantized (deterministic).
Exit 0 ok, 3 failure (caller fails the refresh)."""
import argparse, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import card3
SIZES = (('og', '1200x630'), ('portrait', '1080x1350'))
FONT = os.path.join(HERE, 'fonts', 'NotoSans-VF-latin.ttf')
def sha(b): return hashlib.sha256(b).hexdigest()
def die(m): print('OG_CARDS FAIL:', m, file=sys.stderr); sys.exit(3)
VER = sha(b''.join(open(p, 'rb').read() for p in (os.path.join(HERE, 'card3.py'), FONT, os.path.abspath(__file__), os.path.join(HERE, 'og_rows.js'))))[:16]
def card_data(t, stamp):
    gs = []
    for g in t['games']:
        a, h = dict(g['away']), dict(g['home'])
        gs.append(dict(ko=g['ko'], when=g['when'], day=g['day'], time=g['time'], away=a, home=h, root=g['root'], neutral=g['neutral'], race=g['race'], gain=g['gain'], color=g['color']))
    return dict(team=t['team'], asof=stamp, games=gs)
def page_html(d, sz, site):
    h, n, x = card3.html(d, sz)
    # assets: logos only from /assets/logos/108/{espn_id}.png (spec); missing logo -> slate text-initial disc
    def lg(m):
        i = m.group(1)
        if i != 'None' and os.path.exists(f'{site}/assets/logos/108/{i}.png'): return f'src="LOGO/{i}.png"'
        return 'src="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22%3E%3Ccircle cx=%2232%22 cy=%2232%22 r=%2232%22 fill=%22%234C5560%22/%3E%3C/svg%3E"'
    h = re.sub(r'src="\.\./logos/([^".]+)\.png"', lg, h).replace('src="../kt_header.png"', 'src="BRAND"')
    ff = '@font-face{font-family:"Noto Sans";src:url("FONT") format("truetype");font-weight:100 900;font-stretch:62.5% 100%}'
    return h.replace('<style>', '<style>' + ff, 1), n, x
# fit pass (Batch B, open for Creative): a long opponent name next to a long tag ('Mountain West championship') does not fit the wide row.
# Root-for panel (r3.1): the name must end >= 12px inside the panel. Font steps down 1px to 80% of its size; past that it wraps at a space (never mid-word); still bad -> .nmbad = overflow (keep previous card).
# Step 4 (r3 dates): if a row still overflows, every row's time drops ' MT' ('1:45 PM') and the card says 'Kickoff times MT' once. The date is never dropped.
# Step 5 (r3 dates): a row that still overflows wraps its kickoff line at the ' · ' only (every other space there is &nbsp;): 'Sat Oct 31 ·' / '1:30 PM'.
# Step 1: that tag drops to 18px. Step 2: the opponent name may wrap to 2 lines. Step 3: tag 16px, kickoff 18px. Anything still overflowing fails the run (no clipped text ships).
FIT = """()=>{const ov=e=>e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+1;
 const gap=pn=>{const nm=pn.querySelector('.nm'),r=document.createRange();r.selectNodeContents(nm);return pn.getBoundingClientRect().right-Math.max(...[...r.getClientRects()].map(x=>x.right))};
 for(const pn of document.querySelectorAll('.pn')){const nm=pn.querySelector('.nm'),f0=parseFloat(getComputedStyle(nm).fontSize),fl=Math.round(f0*0.8);let f=f0;const bad=()=>ov(pn)||gap(pn)<12;
  while(bad()&&f>fl){f-=1;nm.style.fontSize=f+'px';}
  if(bad()){nm.textContent=nm.textContent.replace(/\u00a0/g,' ');Object.assign(nm.style,{whiteSpace:'normal',wordBreak:'normal',overflowWrap:'normal',hyphens:'none',lineHeight:'1.05'});const w=nm.parentElement;Object.assign(w.style,{minWidth:'0',flex:'1 1 auto',maxWidth:(pn.getBoundingClientRect().right-w.getBoundingClientRect().left-12)+'px'});}
  if(bad())pn.classList.add('nmbad');}
 for(const r of document.querySelectorAll('.r')){const op=r.querySelector('.op'),on=r.querySelector('.on'),tg=r.querySelector('.tg');const md=r.querySelector('.mid'),bad=()=>ov(op)||ov(md);if(!op||!bad())continue;
  tg.style.fontSize='18px';tg.style.padding='6px 10px';if(!bad())continue;
  const b=on.querySelector('b');if(b)b.textContent=b.textContent.replace(/\u00a0/g,' ');on.style.whiteSpace='normal';on.style.lineHeight='1';if(!bad())continue;
  tg.style.fontSize='16px';tg.style.padding='5px 8px';const kt=r.querySelector('.kt');if(kt)kt.style.fontSize='18px';}
 if([...document.querySelectorAll('.r')].some(r=>ov(r.querySelector('.op'))||ov(r.querySelector('.mid'))))document.body.classList.add('nomt');
 for(const r of document.querySelectorAll('.r')){const op=r.querySelector('.op'),md=r.querySelector('.mid');if(!ov(op)&&!ov(md))continue;const kt=r.querySelector('.kt');kt.style.whiteSpace='normal';kt.style.lineHeight='1.1';kt.style.marginTop='2px';}}"""
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('site'); ap.add_argument('--base'); ap.add_argument('--all', action='store_true'); ap.add_argument('--report'); ap.add_argument('--only'); a = ap.parse_args()
    S = os.path.abspath(a.site); t0 = time.time()
    r = subprocess.run(['node', os.path.join(HERE, 'og_rows.js'), S], capture_output=True, text=True)
    if r.returncode: die('og_rows.js: ' + r.stderr[-800:])
    D = json.loads(r.stdout); stamp = card3.nb(D['stamp']) if D.get('stamp') else ''
    old = {}
    bm = os.path.join(a.base or S, 'data', 'og-cards.json')
    if os.path.exists(bm): old = json.load(open(bm)).get('cards', {})
    for c in old.values():
        for e in c.values(): e.pop('asof', None)   # pre-fix manifests carried the as-of text
    cache = os.environ.get('KT_OG_CACHE')
    if cache == 'off': cache = None   # KT_OG_CACHE=off: no cache (QA determinism check: every card drawn from scratch)
    if cache: os.makedirs(cache, exist_ok=True)
    od = os.path.join(S, 'og', 'rootables'); os.makedirs(od, exist_ok=True)
    man, todo, kept, stats = {}, [], 0, {'teams': 0, 'rows': {}}
    only = set(a.only.split(',')) if a.only else None
    for slug, t in sorted(D['teams'].items()):
        if only and slug not in only: continue
        stats['teams'] += 1; stats['rows'][slug] = len(t['games']); man[slug] = {}
        for sz, px in SIZES:
            key = sha((VER + page_html(card_data(t, ''), sz, S)[0]).encode())[:24]
            dst = os.path.join(od, f'{slug}-{px}.png'); prev = old.get(slug, {}).get(px, {})
            src_prev = os.path.join(a.base, 'og', 'rootables', f'{slug}-{px}.png') if a.base else dst
            if not a.all and prev.get('k') == key and os.path.exists(src_prev):
                if os.path.abspath(src_prev) != os.path.abspath(dst): shutil.copyfile(src_prev, dst)
                man[slug][px] = prev; kept += 1; continue
            man[slug][px] = {'k': key, 'sd': sha(stamp.encode())[:8], 'rows': min(len(t['games']), card3.S[sz]['CAP'])}   # sd = hash of the drawn Updated stamp: no as-of text in data/og-cards.json (apply_data's old-as-of check)
            ck = os.path.join(cache, f'{key}-{sha(stamp.encode())[:8]}.png') if cache else None
            if ck and os.path.exists(ck): shutil.copyfile(ck, dst); kept += 0; continue
            todo.append((slug, sz, px, dst, ck, page_html(card_data(t, stamp), sz, S)[0]))
    tr = time.time(); times = []; warns = []; kept_prev = 0
    if todo:
        from playwright.sync_api import sync_playwright
        from PIL import Image
        tmp = tempfile.mkdtemp(prefix='ogc_')
        try:
            logo = 'file://' + S + '/assets/logos/108/'; brand = 'file://' + S + '/assets/brand/logo/kicktip-header-nosub-transparent.png'; font = 'file://' + FONT
            with sync_playwright() as p:
                b = p.chromium.launch(args=['--font-render-hinting=none', '--disable-lcd-text', '--force-color-profile=srgb'])
                pages = {sz: b.new_page(viewport={'width': card3.S[sz]['W'], 'height': card3.S[sz]['H']}, device_scale_factor=1) for sz, _ in SIZES}
                for slug, sz, px, dst, ck, h in todo:
                    t1 = time.time(); f = os.path.join(tmp, f'{slug}-{px}.html')
                    open(f, 'w', encoding='utf-8').write(h.replace('src="LOGO/', 'src="' + logo).replace('src="BRAND"', 'src="' + brand + '"').replace('url("FONT")', 'url("' + font + '")'))
                    pg = pages[sz]; pg.goto('file://' + f, wait_until='load'); pg.evaluate('document.fonts.ready.then(()=>Promise.all([...document.images].map(i=>i.decode().catch(()=>0))))')
                    pg.evaluate(FIT)
                    over = pg.evaluate("()=>{const bd=document.querySelector('.bd');return [bd.scrollHeight-bd.clientHeight].concat([...document.querySelectorAll('.r,.pn,.op,.mid,.nmbad')].filter(e=>e.classList.contains('nmbad')||e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+2).map(e=>e.className+' '+e.scrollWidth+'x'+e.scrollHeight+'/'+e.clientWidth+'x'+e.clientHeight+' '+e.textContent.slice(0,40)))}")
                    if os.environ.get('KT_OG_FORCE_OVERFLOW') == slug: over = [1, 'forced (test)']   # test hook only
                    if over[0] > 0 or len(over) > 1:   # QA r3 item 4: one bad card never fails the refresh. Keep the previous card; with none, draw the safe no-rows card. No clipped text ships.
                        prevp = os.path.join(a.base, 'og', 'rootables', f'{slug}-{px}.png') if a.base else None
                        if prevp and os.path.exists(prevp) and old.get(slug, {}).get(px):
                            shutil.copyfile(prevp, dst); man[slug][px] = dict(old[slug][px], k='stale-' + old[slug][px]['k'][:18]); warns.append(f'{slug} {px}: overflow {over}; kept previous card'); kept_prev += 1; times.append(time.time() - t1); continue
                        else:
                            fb = dict(card_data(D['teams'][slug], stamp), fallback=True); open(f, 'w', encoding='utf-8').write(page_html(fb, sz, S)[0].replace('src="LOGO/', 'src="' + logo).replace('src="BRAND"', 'src="' + brand + '"').replace('url("FONT")', 'url("' + font + '")'))
                            pg.goto('file://' + f, wait_until='load'); pg.evaluate('document.fonts.ready'); man[slug][px] = dict(man[slug][px], k='fallback'); warns.append(f'{slug} {px}: overflow {over}; no previous card, drew the no-rows fallback card')
                        ck = None
                    png = pg.screenshot(type='png')
                    im = Image.open(io.BytesIO(png)).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
                    bio = io.BytesIO(); im.save(bio, 'PNG', optimize=True); open(dst, 'wb').write(bio.getvalue())
                    if ck: shutil.copyfile(dst, ck)
                    times.append(time.time() - t1)
                b.close()
        finally: shutil.rmtree(tmp, ignore_errors=True)
    # cards of team pages that no longer exist are not removed here (apply_data never removes files); every team page has both sizes
    for slug in man:
        for _, px in SIZES:
            if not os.path.exists(os.path.join(od, f'{slug}-{px}.png')): die(f'missing card {slug}-{px}')
    if not only:
        json.dump({'v': 1, 'spec': '1b18d56c', 'renderer': VER, 'cards': man}, open(os.path.join(S, 'data', 'og-cards.json'), 'w'), separators=(',', ':'), sort_keys=True)
    tot = sum(os.path.getsize(os.path.join(od, f)) for f in os.listdir(od))
    rep = {'teams': stats['teams'], 'rendered': len(todo) - kept_prev, 'kept': kept + kept_prev, 'render_s': round(time.time() - tr, 2), 'per_card_s': round(sum(times) / len(times), 3) if times else 0,
           'total_s': round(time.time() - t0, 2), 'bytes': tot, 'max_rows': max(stats['rows'].values() or [0])}
    rep['warnings'] = warns
    for w in warns: print('OG_CARDS WARNING:', w, file=sys.stderr)
    print('og_cards', json.dumps(rep))
    if a.report: json.dump(rep, open(a.report, 'w'), indent=1)
if __name__ == '__main__': main()
