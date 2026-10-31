#!/usr/bin/env python3
"""confsim (cc5) feature layer: Creative rev 4 scenario result view (mock dec020e8) onto the LIVE assets/ccgsim-ui.js + ccgsim.css. Idempotent; every anchor must match exactly once.
usage: feat_c.py <siteDir>"""
import sys, os, re, hashlib
D = sys.argv[1]; K = os.path.dirname(os.path.abspath(__file__))
# skip-if-marker keys on a content hash of the kit: same kit -> no-op; an older cc5 rev already in the base -> fail loudly (no silent skip)
KH = hashlib.sha256(b''.join(open(K + '/' + f, 'rb').read() for f in ('feat_c.py', 'cc5.js', 'cc5.css'))).hexdigest()[:12]
MK = '/* cc5-kit:' + KH + ' */'
def gate(txt, name):
    if MK in txt: print(name, 'already has this kit', KH, '(no-op)'); return False
    if re.search(r'/\* cc5', txt): sys.exit(name + ': base already carries a different cc5 rev (' + ','.join(re.findall(r'cc5-kit:(\w+)', txt)) + '); rebuild on a pre-cc5 base or the live zip from before confsim')
    return True
p = D + '/assets/ccgsim-ui.js'; t = open(p, encoding='utf-8').read()
if gate(t, 'ccgsim-ui.js'):
    def rep(a, b):
        global t
        assert t.count(a) == 1, ('anchor', a[:80], t.count(a)); t = t.replace(a, b)
    rep('  function renderBox(res) {', open(K + '/cc5.js', encoding='utf-8').read() + '\n  function renderBox(res) {')
    rep('html = w4card(t, res); cls = "ccg w4";', 'if (!earlyPair) { html = ccCard(t, res); cls = "ccg w4 cc5"; } else { html = w4card(t, res); cls = "ccg w4"; }')
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
    open(p, 'w', encoding='utf-8').write(t.rstrip('\n') + '\n' + MK + '\n'); print('patched ccgsim-ui.js', KH)
p = D + '/assets/ccgsim.css'; c = open(p, encoding='utf-8').read()
if gate(c, 'ccgsim.css'):
    open(p, 'a', encoding='utf-8').write(open(K + '/cc5.css', encoding='utf-8').read() + MK + '\n'); print('patched ccgsim.css', KH)
