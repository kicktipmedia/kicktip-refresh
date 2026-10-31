#!/usr/bin/env python3
"""Batch B feature layer (Batch A markup): hand-ports of the build.py audit2 head/footer/sitemap changes onto files where merge3 reported a conflict (live markup differs from S0).
Idempotent. usage: feat.py <siteDir>"""
import sys, re, html
D = sys.argv[1]
def E(t): return html.escape(t)
ORG_LD = ('<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Organization","@id":"https://kicktipmedia.com/#org","name":"KickTip Media","url":"https://kicktipmedia.com/",'
          '"logo":"https://kicktipmedia.com/assets/brand/icon/kicktip-icon-512.png","parentOrganization":{"@type":"Organization","@id":"https://mtnsportsmedia.com/#org","name":"Mtn Sports Media","url":"https://mtnsportsmedia.com/"}},'
          '{"@type":"WebSite","@id":"https://kicktipmedia.com/#site","name":"KickTip Media","url":"https://kicktipmedia.com/","publisher":{"@id":"https://kicktipmedia.com/#org"}}]}</script>')
FOOT_OLD = '<p>from the team behind Mtn Sports Media</p>'; FOOT_NEW = '<p><a href="https://mtnsportsmedia.com/" rel="noopener">from the Mtn Sports Media team</a></p>'
def head(rel, title, desc, ld=''):
    p = D + '/' + rel; t = open(p, encoding='utf-8').read(); o = t
    if 'twitter:title' not in t:
        t = re.sub(r'<title>[^<]*</title>', '<title>' + E(title) + '</title>', t, 1)
        t = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="' + E(title) + '">', t, 1)
        if desc:
            t = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + E(desc) + '">', t, 1)
            t = re.sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="' + E(desc) + '">', t, 1)
        d = re.search(r'<meta name="description" content="([^"]*)">', t).group(1)
        t = t.replace('<meta property="og:image:alt" content="KickTip Media">', '<meta property="og:image:alt" content="KickTip Media, college football playoff simulator">', 1)
        tw = '<meta name="twitter:image" content="https://kicktipmedia.com/assets/brand/social/kicktip-og-1200x630.png">'
        assert t.count(tw) == 1, rel
        t = t.replace(tw, tw + '<meta property="og:locale" content="en_US"><meta property="og:image:type" content="image/png"><meta name="twitter:title" content="' + E(title) + '"><meta name="twitter:description" content="' + d + '">' + ld)
    t = t.replace(FOOT_OLD, FOOT_NEW)
    if t != o: open(p, 'w', encoding='utf-8').write(t); print('patched', rel)
head('index.html', 'KickTip Media | College football playoff simulator', 'KickTip Media is a free college football playoff simulator: Playoff chances, conference races and tiebreaker paths for every FBS team, updated through game day.', ORG_LD)
head('conference/american/simulator/index.html', 'American Conference championship game simulator | KickTip Media', '')
p = D + '/sitemap.xml'; t = open(p).read()
pass  # audit2 R2: lastmod dropped. was: if '<lastmod>' not in t: t = t.replace('</loc></url>', '</loc><lastmod>2026-10-31</lastmod></url>'); open(p, 'w').write(t); print('patched sitemap.xml')
# polish2 fix 2: home example chip: 'TRY THIS EXAMPLE' label + arrow; 'lose one more game' kept together
p = D + '/index.html'; t = open(p, encoding='utf-8').read()
a = '<span>Utah and BYU each lose&nbsp;one&nbsp;more&nbsp;game</span></a>'
if a in t:
    t = t.replace(a, '<span class="ph-ct"><small>Try this example</small><span>Utah and BYU each lose&nbsp;one&nbsp;more&nbsp;game</span></span><span class="ph-ar" aria-hidden="true">&rarr;</span></a>'); open(p, 'w', encoding='utf-8').write(t); print('patched chip')
p = D + '/assets/polish.css'; t = open(p, encoding='utf-8').read()
if '.ph-ct' not in t:
    t += '\n/* audit2 polish2: example chip label + arrow (Creative mock) */\n.ph-ct{flex:1;min-width:0}.ph-ct small{display:block;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#4C5560}.ph-ar{flex:none;font:800 22px/1 system-ui,sans-serif;color:var(--ink)}.ph-chip:hover .ph-ct small{text-decoration:none}\n'
    open(p, 'w', encoding='utf-8').write(t); print('patched polish.css')
# polish2 fix 3: big stat label '12&#8209;team&nbsp;playoff'
import glob as _g
_n = 0
for p in _g.glob(D + '/**/*.html', recursive=True):
    t = open(p, encoding='utf-8').read()
    u = t.replace('<span>Make the 12&#8209;team playoff</span>', '<span>Make the 12&#8209;team&nbsp;playoff</span>').replace('Conference championship and 12&#8209;team playoff, from', 'Conference championship and 12&#8209;team&nbsp;playoff, from')
    if u != t: open(p, 'w', encoding='utf-8').write(u); _n += 1
print('label files', _n)
# polish2: conference standings top 3 on phones + 'Show all N teams' (no-JS: CSS :has on a details element)
import re as _re
_n = 0
for p in _g.glob(D + '/conference/*/index.html'):
    t = open(p, encoding='utf-8').read()
    if 'class="ct-more"' in t: continue
    m = _re.search(r'<ol class="t25-cards kc-list kc-flat"[^>]*></ol>', t)
    if not m: continue
    i = t.rfind('<table>', 0, m.start()); j = t.find('</table>', i)
    rows = t[i:j].count('<tr>') - 1
    if rows <= 3: continue
    t = t[:m.end()] + '<details class="ct-more"><summary>Show all ' + str(rows) + ' teams</summary></details>' + t[m.end():]
    open(p, 'w', encoding='utf-8').write(t); _n += 1
print('conf top3', _n)

# polish-2: games + conference pages need polish.css (card redesign, conference top 3)
import glob as _g, re as _r
for _p in [D+'/games/index.html']+_g.glob(D+'/conference/*/index.html'):
    _s=open(_p).read()
    if 'polish.css' in _s: continue
    _s=_r.sub(r'(<link rel="stylesheet" href="/assets/kt\.css\?v=[^"]*">)', r'\1\n<link rel="stylesheet" href="/assets/polish.css?v=018094b415" data-polish="1">', _s, count=1)
    open(_p,'w').write(_s)
