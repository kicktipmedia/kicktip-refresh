#!/usr/bin/env python3
"""confsim (cc5) feature layer: Creative rev 4 scenario result view (mock dec020e8) + rev 5 result-first banner, home Conference Simulator tile and conference pages that open on the simulator
(Creative rev 5 mocks, Jared GO 1:24 PM MT Oct 31) onto the LIVE site: assets/ccgsim-ui.js + ccgsim.css patched; new assets cc5home.js, cc5conf.js, cc5pages.css;
index.html + conference/<slug>/index.html get <link>/<script> tags only, on their head/script lines (not the body content line, so the refresh 3-way HTML merge stays clean).
Idempotent; every anchor must match exactly once.
usage: feat_c.py <siteDir>"""
import sys, os, re, hashlib
D = sys.argv[1]; K = os.path.dirname(os.path.abspath(__file__))
KF = ('feat_c.py', 'cc5.js', 'cc5.css', 'cc5home.js', 'cc5conf.js', 'cc5pages.css','cc5pre.js')   # rebuild_c.sh checks the same list against HEAD
# skip-if-marker keys on a content hash of the kit: same kit -> no-op; an older cc5 rev already in the base -> fail loudly (no silent skip)
KH = hashlib.sha256(b''.join(open(K + '/' + f, 'rb').read() for f in KF)).hexdigest()[:12]
MK = '/* cc5-kit:' + KH + ' */'
def gate(txt, name):
    if MK in txt: print(name, 'already has this kit', KH, '(no-op)'); return False
    if re.search(r'/\* cc5', txt): sys.exit(name + ': base already carries a different cc5 rev (' + ','.join(re.findall(r'cc5-kit:(\w+)', txt)) + '); this kit cannot re-apply over it: build the newer rev with an upgrade kit for that base (cc5 old rev -> new rev)')
    return True
p = D + '/assets/ccgsim-ui.js'; t = open(p, encoding='utf-8').read()
if gate(t, 'ccgsim-ui.js'):
    def rep(a, b):
        global t
        assert t.count(a) == 1, ('anchor', a[:80], t.count(a)); t = t.replace(a, b)
    rep('  function renderBox(res) {', open(K + '/cc5.js', encoding='utf-8').read() + '\n  function renderBox(res) {')
    rep('html = w4card(t, res); cls = "ccg w4";', 'if (!earlyPair) { html = ccCard(t, res); cls = "ccg w4 cc5"; } else { html = w4card(t, res); cls = "ccg w4"; ccChg(""); }')
    rep('  function renderTable(res) {\n', '  function renderTable(res) {\n    if (BASE !== undefined) { ccTable(res); return; }   /* cc5 */\n')
    old_st = ('\'<h2 id="sh">Standings</h2><details class="dtl"><summary>How ties are broken</summary><div id="steps"></div></details>\' +\n'
              '      \'<div class="tw2"><table class="xst" aria-labelledby="sh"><thead><tr><th class="r" scope="col">Rank</th><th scope="col">Team</th><th class="c" scope="col">Conf.</th></tr></thead><tbody id="stb"></tbody></table></div>\' +\n'
              '      \'<button type="button" class="sbtn more" id="smore" aria-expanded="false" aria-controls="stb"></button>\' +\n')
    new_st = ('\'<section class="cc5st" aria-labelledby="sh"><h2 id="sh">Standings</h2><p class="cc5lg" id="cclg" hidden><span><b></b>Changed in this scenario</span><span>&#9650;&#9660; places moved</span><span>&ldquo;was&rdquo; = starting results</span></p>\' +\n'
              '      \'<div class="tw2"><table class="xst cc5x" aria-labelledby="sh"><thead><tr><th class="pl" scope="col">#</th><th scope="col">Team</th><th class="n" scope="col">\' + NB(NAME) + \'</th><th class="n o" scope="col">All</th></tr></thead><tbody id="stb"></tbody></table></div>\' +\n'
              '      \'<button type="button" class="sbtn more" id="smore" aria-expanded="false" aria-controls="stb" hidden></button>\' +\n'
              '      \'<p class="cc5n">\' + (R.fmt === "div" ? "Ties below each division champion are shown as tied (T). The tool settles only the two championship spots." : "Ties below the top two are shown as tied (T). The tool settles only the two championship spots.") + \'</p><p class="cc5n" id="ccnc" hidden>* All = this result plus nonconference games played so far; some nonconference games are still to play.</p>\' +\n'
              '      \'<p class="cc5n cc5stamp">Updated \' + esc(String(D.asof || "").replace(/^\\d{4}-(\\d\\d)-(\\d\\d) (\\d\\d?):(\\d\\d) MT$/, function (m, mo, d, hh, mi) { var H = +hh; return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][+mo - 1] + " " + (+d) + ", " + ((H % 12) || 12) + ":" + mi + " " + (H < 12 ? "AM" : "PM") + " MT"; })).replace(/ /g, "&nbsp;").replace(/,&nbsp;/, ", ") + \'</p></section>\' +\n'
              '      \'<details class="dtl"><summary>How ties are broken</summary><div id="steps"></div></details>\' +\n')
    rep(old_st, '')
    ns = '            \'<p class="ns">Nothing is stored. Your changes stay on this page and clear when you leave or reload.</p></div></div>\';\n'
    rep(ns, '            \'<p class="ns">Nothing is stored. Your changes stay on this page and clear when you leave or reload.</p>\' +\n' + new_st + '      \'</div></div>\';\n')   # Jared 12:52 PM MT: standings at the very bottom, after the card and the whole game switcher
    rep('Random</button></div></div>\' +\n', 'Random</button></div><a class="cc5jl" href="#sh">See final standings &darr;</a></div>\' +\n')   # rev 4: jump link under the buttons
    rep('<p class="slk"><a href="#sh">See standings</a></p>', '')   # rev 4: the one jump link sits under the buttons
    rep('    picks = Object.assign({}, fav.picks);\n    shell();', '    picks = Object.assign({}, fav.picks); BASE = K.solve(R, conf, fav.picks);   /* cc5 baseline: the starting results */\n    shell();')
    t = t.replace('  var BASE = null, NB', '  var BASE, NB')
    # rev 5: result banner first (out of the rail, before .simgrid; the AI box still lands between it and the grid), "Your changes" in the rail, Download image + Share buttons
    rep('<div class="simgrid"><div class="rail" id="rail"><div class="strip" id="strip"></div><div class="ccg" id="ccg" tabindex="-1"></div><p class="vh" id="ann"',
        '<div class="ccg" id="ccg" tabindex="-1"></div><div class="simgrid"><div class="rail" id="rail"><div class="strip" id="strip"></div><div class="cc5chg" id="cc5chg"></div><p class="vh" id="ann"')
    rep('    if (b.getAttribute("data-w4") === "share") { w4share(); return; }\n',
        '    if (b.getAttribute("data-w4") === "share") { w4share(); return; }\n    if (b.getAttribute("data-w4") === "dl") { ccDl(); return; } if (b.getAttribute("data-w4") === "sh5") { ccShare(); return; }   /* cc5 rev 5 */\n')
    rep('document.querySelector(".slk").hidden = true;', '(document.querySelector(".slk") || {}).hidden = true;')   # rev 4 removed .slk; no-games-left case
    open(p, 'w', encoding='utf-8').write(t.rstrip('\n') + '\n' + MK + '\n'); print('patched ccgsim-ui.js', KH)
p = D + '/assets/ccgsim.css'; c = open(p, encoding='utf-8').read()
if gate(c, 'ccgsim.css'):
    open(p, 'a', encoding='utf-8').write(open(K + '/cc5.css', encoding='utf-8').read() + MK + '\n'); print('patched ccgsim.css', KH)

# rev 5: new assets (kit hash marker; a different cc5 rev already present -> stop, same rule as above)
import glob, json, html as H
def put(rel, body):
    q = D + '/' + rel
    if os.path.exists(q):
        if gate(open(q, encoding='utf-8').read(), rel): sys.exit(rel + ': exists in the base without a cc5 marker; refusing to overwrite')
        return
    open(q, 'w', encoding='utf-8').write(body.rstrip('\n') + '\n' + MK + '\n'); print('wrote', rel)
M = {}
for sp in sorted(glob.glob(D + '/conference/*/simulator/index.html')):
    s = open(sp, encoding='utf-8').read(); m = re.search(r'id="sim" data-code="([A-Za-z0-9-]+)" data-name="([^"]+)"', s); assert m, sp
    M[sp.split('/')[-3]] = [m[1], H.unescape(m[2])]
assert len(M) == 10, ('simulator pages', sorted(M))
cj = open(K + '/cc5conf.js', encoding='utf-8').read(); assert cj.count('/*CC5MAP*/{}') == 1
put('assets/cc5conf.js', cj.replace('/*CC5MAP*/{}', json.dumps(M, ensure_ascii=True, separators=(',', ':'), sort_keys=True)))
put('assets/cc5home.js', open(K + '/cc5home.js', encoding='utf-8').read())
put('assets/cc5pages.css', open(K + '/cc5pages.css', encoding='utf-8').read())
put('assets/cc5pre.js', open(K + '/cc5pre.js', encoding='utf-8').read())   # rev 5.1: head script, html.cc5js for the load-time height reservation
TOK = '?v=0000000000'   # bump_all.py sets the real tokens
def tag(rel, pairs):
    q = D + '/' + rel; s = open(q, encoding='utf-8').read()
    if '/assets/cc5' in s: print(rel, 'already has the cc5 tags (no-op)'); return
    for pat, add in pairs:
        ms = list(re.finditer(pat, s)); assert len(ms) == 1, (rel, pat, len(ms)); e = ms[0].end()
        ln = s.count('\n', 0, e) + 1; assert len(s.split('\n')[ln - 1]) < 5000, (rel, 'anchor on a body content line', ln)
        s = s[:e] + add + s[e:]
    open(q, 'w', encoding='utf-8').write(s)
tag('index.html', [(r'<script src="/assets/hdr\.js\?v=\w{10}"></script>', '<script src="/assets/cc5pre.js' + TOK + '"></script>'), (r'<link rel="stylesheet" href="/assets/pk-tiles\.css\?v=\w{10}">', '<link rel="stylesheet" href="/assets/cc5pages.css' + TOK + '">'),
                   (r'<script src="/assets/nr\.js\?v=\w{10}" defer></script>', '<script src="/assets/ccgsim.js' + TOK + '" defer></script><script src="/assets/cc5home.js' + TOK + '" defer></script>')])
for slug in sorted(M):
    tag('conference/' + slug + '/index.html', [(r'<script src="/assets/hdr\.js\?v=\w{10}"></script>', '<script src="/assets/cc5pre.js' + TOK + '"></script>'), (r'<link rel="stylesheet" href="/assets/kc\.css\?v=\w{10}">', '<link rel="stylesheet" href="/assets/ccgsim.css' + TOK + '"><link rel="stylesheet" href="/assets/cc5pages.css' + TOK + '">'),
        (r'<script src="/assets/asof\.js\?v=\w{10}" defer></script>', '<script src="/assets/ccgsim.js' + TOK + '" defer></script><script src="/assets/ai-client.js' + TOK + '" defer></script><script src="/assets/cc5conf.js' + TOK + '" defer></script><script src="/assets/ccgsim-ui.js' + TOK + '" defer></script>')])
print('tagged index.html +', len(M), 'conference pages')
