# wkfinal1 (Nov 14, 2026): simulator week panel shows games already final that week (Tue-Fri) as played; never "No <conf> game" for a team that played.
# Applies the edit to a live assets/ccgsim-ui.js (asserts each anchor occurs once). usage: python3 tools/hotfix/wkfinal1_patch.py <site>/assets/ccgsim-ui.js
# Live-only JS ship (the pipeline copy tree/src/assets/ccgsim-ui.js is older than live and is NOT edited, so the refresh 3-way merge keeps the live file).
import sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read(); o=s
def rep(a,b):
    global s
    assert s.count(a)==1, ('count',s.count(a),a[:80]); s=s.replace(a,b)
# 1 helper: conference games of week w that are already final (played midweek, e.g. Fri Nov 13 Houston at Colorado)
rep('  var rem = function () { return conf.games.filter(function (g) { return g.w === null; }); };\n',
    '  var rem = function () { return conf.games.filter(function (g) { return g.w === null; }); };\n'
    '  /* wkfinal1: games of a shown week that are already final (Tue-Fri games before the Saturday slate). They count as played: their teams are never listed as having no game, the week date range includes them, and they show as "Final: ...". */\n'
    '  var wfin = function (w) { return conf.games.filter(function (g) { return g.w !== null && (g.wk || 0) === w; }); };\n'
    '  function finText(g) { var wn = g.w === 1 ? g.h : g.a, ls = g.w === 1 ? g.a : g.h, ws = g.w === 1 ? g.hs : g.as, lsS = g.w === 1 ? g.as : g.hs, dy = ""; try { dy = dparts(g.date, { weekday: "short" }, g.id).weekday; } catch (e) {} var sc = typeof ws === "number" && typeof lsS === "number"; return "Final: " + (sc ? T(wn) + " " + ws + ", " + T(ls) + " " + lsS : T(wn) + " beat " + T(ls)) + (dy ? " (" + dy + ")" : ""); }\n'
    '  function finSay(f) { return f ? plural(f, "game", "games") + " final" : ""; }\n')
# 2 date range includes finals
rep('function drange(w) { var ds = wgames(w).map(', 'function drange(w) { var ds = wgames(w).concat(wfin(w)).map(')
# 3 aria label
rep('function wsay(w) { var s = wstat(w); return "Week " + w + (s.n ? ", " + drange(w).replace("\\u2013", " to ") + ", " + plural(s.n, "game", "games") : ", no games")',
    'function wsay(w) { var s = wstat(w), f = wfin(w).length; return "Week " + w + (s.n || f ? ", " + drange(w).replace("\\u2013", " to ") + (s.n ? ", " + plural(s.n, "game", "games") : "") + (f ? ", " + finSay(f) : "") : ", no games")')
# 4 tabs
rep('var w = +b.getAttribute("data-w"), s = wstat(w), bd = b.querySelector(".bd");', 'var w = +b.getAttribute("data-w"), s = wstat(w), f = wfin(w).length, bd = b.querySelector(".bd");')
rep('b.querySelector(".c").textContent = s.n ? drange(w) : "No games"; b.classList.toggle("nog", !s.n);',
    'b.querySelector(".c").textContent = s.n || f ? drange(w) : "No games"; b.classList.toggle("nog", !(s.n || f));')
# 5 panel
rep('''    var s = wstat(curW); $("wph").textContent = "Week " + curW;
    $("wsub").textContent = s.n ? drange(curW) + " \\u00B7 " + plural(s.n, "game", "games") + (s.ch ? " \\u00B7 " + s.ch + " changed" : "") : "No " + NAME + " games this week";
    var play = {}; wgames(curW).forEach(function (g) { play[g.h] = 1; play[g.a] = 1; }); var off = conf.teams.filter(function (t, i) { return !play[i]; }).map(function (t) { return t.short; });
    var nb = $("wbye"); nb.hidden = !(s.n && off.length); nb.textContent = off.length ? "No " + NAME + " game: " + list(off) + "." : ""; $("wnone").hidden = !!s.n; $("games").hidden = !s.n;''',
'''    var s = wstat(curW), fl = wfin(curW), any = s.n || fl.length; $("wph").textContent = "Week " + curW;
    $("wsub").textContent = any ? drange(curW) + (s.n ? " \\u00B7 " + plural(s.n, "game", "games") : "") + (fl.length ? " \\u00B7 " + finSay(fl.length) : "") + (s.ch ? " \\u00B7 " + s.ch + " changed" : "") : "No " + NAME + " games this week";
    var play = {}; wgames(curW).concat(fl).forEach(function (g) { play[g.h] = 1; play[g.a] = 1; }); var off = conf.teams.filter(function (t, i) { return !play[i]; }).map(function (t) { return t.short; });
    var fe = $("wfin"); if (fe) { fe.textContent = ""; fl.forEach(function (g, k) { if (k) fe.appendChild(document.createElement("br")); fe.appendChild(document.createTextNode(finText(g))); }); fe.hidden = !fl.length; }
    var nb = $("wbye"); nb.hidden = !(any && off.length); nb.textContent = off.length ? "No " + NAME + " game: " + list(off) + "." : ""; $("wnone").hidden = !!any; $("games").hidden = !s.n;''')
# 6 element
rep('''var WBODY = '<p class="wbye" id="wbye" hidden></p>''', '''var WBODY = '<p class="wbye" id="wfin" hidden></p><p class="wbye" id="wbye" hidden></p>''')
open(p,'w',encoding='utf-8').write(s); print('ok', len(o), len(s))
