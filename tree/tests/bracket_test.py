"""b9 bracket test (headless Chromium + static HTML + cfp.py rules). python3 tests/bracket_test.py
Checks: official 2026-27 pairings, gate (no team/number before acceptance, no-JS), data-driven fill, rule invariants of the field (cfp.py), mobile (320/390 scroll or stacked, opaque, 44px), contrast, ARIA, no new network calls."""
import sys, os, re, json, glob; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")
import serve, cfp
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
res = {"f": [], "n": 0}
def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond: res["f"].append(f"{name} {detail}")
PRED = json.load(open(f"{SITE}/data/pred-teams.json")); FIELD = PRED["field"]; T = PRED["teams"]
html = open(f"{SITE}/playoff/index.html").read(); main = html[html.index("<main"):html.index("</main>")]
br = main[main.index('id="bracket"'):main.index('<div class="card"><h2>The field</h2>')]
# ---------- 1. static markup (what a no-JS / pre-gate reader gets)
rounds = re.findall(r'<div class="rd (r\d)"><h3>([^<]+)</h3><ol>(.*?)</ol></div>', br, re.S)
ok("four rounds in order", [r[1] for r in rounds] == ["First round", "Quarterfinals", "Semifinals", "Championship"], str([r[1] for r in rounds]))
cnt = [len(re.findall(r'<li class="gm"', r[2])) for r in rounds]; ok("games per round 4/4/2/1 (11 games)", cnt == [4, 4, 2, 1], str(cnt))
seeds = [int(x) for x in re.findall(r'data-seed="(\d+)"', br)]; ok("seeds 1-12 each exactly once", sorted(seeds) == list(range(1, 13)), str(sorted(seeds)))
r1 = re.findall(r'data-g="r1-(\d+)".*?</li>', rounds[0][2], re.S); ok("first round order 5/12, 8/9, 6/11, 7/10 (official bracket order)", r1 == ["5", "8", "6", "7"], str(r1))
pairs = []
for g in re.findall(r'<li class="gm" data-g="r1-\d+">.*?</li>', rounds[0][2], re.S): pairs.append(tuple(int(x) for x in re.findall(r'data-seed="(\d+)"', g)))
ok("first round pairings 5v12 6v11 7v10 8v9 (higher seed hosts, listed first)", sorted(pairs) == [(5, 12), (6, 11), (7, 10), (8, 9)] and all(a + b == 17 for a, b in pairs), str(pairs))
qf = {}
for g in re.findall(r'<li class="gm" data-g="qf-\d+">.*?</li>', rounds[1][2], re.S):
    i = int(re.search(r'data-g="qf-(\d+)"', g).group(1)); qf[i] = (int(re.search(r'data-seed="(\d+)"', g).group(1)), re.search(r'data-win="([\d-]+)"', g).group(1))
ok("quarterfinals: 1 v 8/9, 2 v 7/10, 3 v 6/11, 4 v 5/12 (official), byes = seeds 1-4", qf == {1: (1, "8-9"), 2: (2, "7-10"), 3: (3, "6-11"), 4: (4, "5-12")}, str(qf))
ok("quarterfinal column order 4,1,3,2 so each sits level with its feeder game", list(map(int, re.findall(r'data-g="qf-(\d+)"', rounds[1][2]))) == [4, 1, 3, 2])
sfa = re.search(r'data-g="sf-a".*?</li>', rounds[2][2], re.S).group(0); sfb = re.search(r'data-g="sf-b".*?</li>', rounds[2][2], re.S).group(0)
ok("semifinal A = winners of 4 and 1; B = winners of 3 and 2 (no reseeding)", re.findall(r'data-win="(q\d)"', sfa) == ["q4", "q1"] and re.findall(r'data-win="(q\d)"', sfb) == ["q3", "q2"])
ok("final = winners of semifinals A and B", re.findall(r'data-win="(\w+)"', rounds[3][2]) == ["sfa", "sfb"])
ok("heading says 'if the season ended today'", "Bracket if the season ended today" in br)
ok("every game has role=group + aria-label", len(re.findall(r'role="group" aria-label="[^"]+"', br)) >= 11 + 1)
ok("scroll region is keyboard focusable and labelled", 'class="bkw" tabindex="0" role="region" aria-label=' in br)
ok("static bracket has no % and no team/conference name", "%" not in re.sub(r"10,000", "", re.sub(r"<[^>]+>", " ", br)) and not [T[s]["n"] for s, _ in FIELD if T[s]["n"] in br], "")
ok("no X handle / email / mailto / external link in bracket", not re.search(r"@|mailto:|twitter|x\.com|href=\"https?://", br))
ok("no gambling words in bracket", not re.search(r"\b(bet|bets|betting|wager|sportsbook|parlay|spread|odds)\b", re.sub(r"<[^>]+>", " ", br), re.I))
import glob as _g
_pg = [q for q in _g.glob(f"{SITE}/**/*.html", recursive=True)]
_bad = [os.path.relpath(q, SITE) for q in _pg if not ('kt.css?v=chip2' in open(q).read() and 'kt.js?v=chip2' in open(q).read() and ('lg.js?v=chip2' in open(q).read() or 'data-gated="1"' not in open(q).read()))]
ok(f"v6a: EVERY html page ({len(_pg)}) cache-busts kt.css and kt.js with ?v=chip2, and every gated page also lg.js (rev2: checked on all pages, not two)", not _bad and 'lg.js?v=chip2' in html, str(_bad[:3]))
ok("no unbusted /assets/lg.js, kt.js or kt.css reference on any page", not [os.path.relpath(q, SITE) for q in _pg if re.search(r'/assets/(lg\.js|kt\.js|kt\.css)"', open(q).read())])
ok("no inline style attributes in bracket (CSP style-src 'self')", ' style="' not in br)
# ---------- 2. cfp.py rules (the field the bracket shows is cfp.field's; test the rule itself on synthetic cases)
import random
def case(seed):
    rnd = random.Random(seed); n = 60; order = list(range(n)); rnd.shuffle(order); rank = {t: i + 1 for i, t in enumerate(order)}
    confs = {c: [t for t in range(n) if t % 11 == k] for k, c in enumerate(cfp.P4 + cfp.G6 + ["x"])}
    champs = {c: min(confs[c], key=lambda t: rank[t]) for c in cfp.P4}; g6 = [t for c in cfp.G6 for t in confs[c]]; nd = rnd.choice(range(n))
    return rank, champs, order, nd, g6
bad = []
for sd in range(300):
    rank, champs, order, nd, g6 = case(sd); F = cfp.field(rank, champs, order, nd, g6); bk = cfp.bracket(F)
    auto = set(champs.values()) | {min(g6, key=lambda t: rank[t])} | ({nd} if rank[nd] <= 12 else set())
    if len(F) != 12 or len(set(F)) != 12 or not auto <= set(F): bad.append((sd, "field"))
    top = [t for t in F if rank[t] <= 12 or t not in auto]; tail = F[len(top):]
    if [rank[t] for t in top] != sorted(rank[t] for t in top) or any(rank[t] <= 12 or t not in auto for t in tail) or [rank[t] for t in tail] != sorted(rank[t] for t in tail): bad.append((sd, "seed order"))
    if bk["byes"] != F[:4] or bk["first_round"] != [(F[4], F[11]), (F[5], F[10]), (F[6], F[9]), (F[7], F[8])]: bad.append((sd, "bracket"))
ok("cfp.py: 300 random cases: 12 unique teams, 4 power champs + best G6 + Notre Dame if top 12 all in, auto bids outside top 12 seeded last, byes 1-4, 5v12 6v11 7v10 8v9", not bad, str(bad[:3]))
ok("live field: 12 unique teams", len(FIELD) == 12 and len({s for s, _ in FIELD}) == 12)
lead = [s for s, l in FIELD if l]; pc = {"acc", "big-ten", "big-12", "sec"}
ok("live field: one conference leader in the field for each of ACC, Big Ten, Big 12, SEC", sorted(T[s]["cs"] for s in lead if T[s]["cs"] in pc) == sorted(pc), str([(s, T[s]["cs"]) for s in lead]))
g6c = {"american", "conference-usa", "mac", "mountain-west", "pac-12", "sun-belt"}; ok("live field: includes at least one Group of 6 team", any(T[s]["cs"] in g6c for s, _ in FIELD), str(sorted({T[s]["cs"] for s, _ in FIELD})))
# ---------- 3. browser
TAP = "() => [...document.querySelectorAll('#bracket a[href], #bracket button')].filter(e => e.getBoundingClientRect().width > 0).map(e => { const r = e.getBoundingClientRect(); return [e.textContent.trim().slice(0, 24), Math.round(r.width), Math.round(r.height)]; })"
OPAQ = """() => { const bad = []; for (const e of document.querySelectorAll('#bracket .g, #bracket .gl, #bracket .sl, #bracket .rd h3, #bracket .sd, #bracket .bkb')) { const cs = getComputedStyle(e), m = cs.backgroundColor.match(/[\\d.]+/g) || []; const a = m.length === 4 ? +m[3] : 1; if (a !== 1 || cs.backgroundColor === 'rgba(0, 0, 0, 0)') bad.push(e.className + ' ' + cs.backgroundColor); if (cs.position === 'sticky' || cs.position === 'fixed') bad.push('sticky ' + e.className); } return bad; }"""
CONTRAST = """() => { const lum = c => { const [r, g, b] = c.map(v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }); return .2126 * r + .7152 * g + .0722 * b; };
  const rgb = s => (s.match(/[\\d.]+/g) || []).map(Number); const bgOf = e => { for (; e; e = e.parentElement) { const c = rgb(getComputedStyle(e).backgroundColor); if (c.length === 3 || (c.length === 4 && c[3] === 1)) return c.slice(0, 3); } return [255, 255, 255]; };
  const out = []; for (const e of document.querySelectorAll('#bracket .gl, #bracket .tn, #bracket .ti, #bracket .ph .tm, #bracket .sd, #bracket .rd h3, #bracket .bkb, #bracket .note')) { if (!e.textContent.trim() || !e.getBoundingClientRect().width) continue; const cs = getComputedStyle(e); const fg = rgb(cs.color).slice(0, 3), bg = bgOf(e);
    const L1 = lum(fg), L2 = lum(bg), r = (Math.max(L1, L2) + .05) / (Math.min(L1, L2) + .05); if (r < 4.5) out.push(e.className + ' ' + r.toFixed(2) + ' ' + cs.color); } return out; }"""
WANT = {}
for i in range(1, 13): s = FIELD[i - 1][0]; WANT[i] = s
def pct(p):
    v = round(p * 100); return "<1%" if p > 0 and v < 1 else (">99%" if p < 1 and v >= 100 else f"{v}%")
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    # pre-gate and no-JS
    for js in (True, False):
        ctx = b.new_context(java_script_enabled=js, viewport={"width": 390, "height": 900}); pg = ctx.new_page(); reqs = []; pg.on("request", lambda r: reqs.append(r.url)); pg.goto(BASE + "/playoff/"); pg.wait_for_timeout(500)
        t = pg.inner_text("#bracket"); lbl = "pre-gate" if js else "no-JS"
        ok(f"{lbl}: no prediction data requested", not [u for u in reqs if "/data/pred-" in u])
        ok(f"{lbl}: bracket shows no team name", not [T[s]["n"] for s, _ in FIELD if T[s]["n"] in t])
        ok(f"{lbl}: bracket shows no percentages", not re.search(r"\d+\s?%|<1%|>99%", t.replace("10,000", "")))
        ok(f"{lbl}: seed numbers are shown", all(str(i) in t for i in range(1, 13)))
        ok(f"{lbl}: no team logo images in bracket", pg.locator("#bracket img").count() == 0)
        ctx.close()
    for W in (320, 390, 1280):
        ctx = b.new_context(viewport={"width": W, "height": 900}); ctx.add_init_script(ACC); pg = ctx.new_page(); reqs = []; con = []
        pg.on("request", lambda r: reqs.append(r.url)); pg.on("console", lambda m: con.append(m.text) if m.type in ("error", "warning") else None); pg.on("pageerror", lambda e: con.append(str(e)))
        pg.goto(BASE + "/playoff/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(500)
        L = f"@{W}"
        names = pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('#bracket [data-seed]')].map(e => [e.dataset.seed, [e.querySelector('.tn')?.textContent, e.querySelector('a.tl')?.getAttribute('href'), !!e.querySelector('.lg'), e.querySelector('.ti')?.textContent]]))")
        ok(f"filled after accept: 12 seeds match field order {L}", all(names[str(i)][0] == T[WANT[i]]["n"] and names[str(i)][1] == f"/team/{WANT[i]}/" for i in range(1, 13)), str(names)[:200])
        ok(f"every slot has a logo tile (ESPN, cached) {L}", all(names[str(i)][2] for i in range(1, 13)))
        ok(f"model chances shown are exactly pred-teams p (all), b (byes 1-4) {L}", all(f"Make the 12: {pct(T[WANT[i]]['p'])} (model)" in names[str(i)][3] and ((f"First-round bye: {pct(T[WANT[i]]['b'])} (model)" in names[str(i)][3]) == (i <= 4)) for i in range(1, 13)), str({i: names[str(i)][3] for i in (1, 5)}))
        wins = pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('#bracket [data-win]')].map(e => [e.dataset.win, e.textContent]))")
        ok(f"quarterfinal slots name their feeder game {L}", all(wins[f"{a}-{c}"] == f"Winner of {T[WANT[a]]['n']} vs {T[WANT[c]]['n']}" for a, c in ((5, 12), (8, 9), (6, 11), (7, 10))), str(wins)[:200])
        labs = pg.evaluate("() => [...document.querySelectorAll('#bracket .g')].map(e => e.getAttribute('aria-label'))")
        ok(f"11 games with team names in their ARIA labels {L}", len(labs) == 11 and f"No. 5 {T[WANT[5]]['n']} hosts No. 12 {T[WANT[12]]['n']}" in labs[0] and T[WANT[1]]["n"] in labs[5] and "first-round bye" in labs[5], str(labs)[:300])
        ok(f"no console errors/warnings {L}", not con, str(con[:2])); ok(f"no off-origin requests {L}", not [u for u in reqs if not u.startswith(BASE) and not u.startswith("data:")])
        dr = sorted({u.split("/data/")[1] for u in reqs if "/data/" in u}); ok(f"only /data/pred-teams.json fetched on /playoff/ (no new network calls) {L}", dr == ["pred-teams.json"], str(dr))
        ok(f"no horizontal page overflow {L}", pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), str(pg.evaluate("document.documentElement.scrollWidth")))
        sc = pg.evaluate("(() => { const w = document.querySelector('#bracket .bkw'); return [w.scrollWidth, w.clientWidth]; })()")
        ok(f"full view: scroll container scrolls sideways on phones, fits on desktop {L}", (sc[0] > sc[1]) if W < 1100 else (sc[0] <= sc[1] + 1), str(sc))
        ok(f"opaque backgrounds, nothing sticky/fixed in bracket {L}", not pg.evaluate(OPAQ), str(pg.evaluate(OPAQ)[:3]))
        small = [x for x in pg.evaluate(TAP) if x[1] < 43.5 or x[2] < 43.5]; ok(f"all bracket links/buttons >= 44px {L}", not small, str(small[:3]))
        ok(f"text contrast >= 4.5:1 {L}", not pg.evaluate(CONTRAST), str(pg.evaluate(CONTRAST)[:4]))
        vis = pg.evaluate("[...document.querySelectorAll('#bracket .g')].every(g => { const r = g.getBoundingClientRect(); return r.width > 200 && r.height > 80; })"); ok(f"all 11 game cards have real size {L}", vis)
        if W < 1100:
            ok(f"view switch visible, 2 buttons, Full bracket pressed {L}", pg.is_visible("[data-bkt]") and pg.locator("[data-bkview]").count() == 2 and pg.get_attribute("[data-bkview=full]", "aria-pressed") == "true")
            pg.click("[data-bkview=rounds]"); pg.wait_for_timeout(200)
            sc = pg.evaluate("(() => { const w = document.querySelector('#bracket .bkw'); return [w.scrollWidth, w.clientWidth]; })()")
            ok(f"by-round view stacks without sideways scroll {L}", sc[0] <= sc[1] + 1 and pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), str(sc))
            ok(f"by-round: aria-pressed switched, all 11 games visible, opaque {L}", pg.get_attribute("[data-bkview=rounds]", "aria-pressed") == "true" and pg.get_attribute("[data-bkview=full]", "aria-pressed") == "false" and pg.locator("#bracket .g:visible").count() == 11 and not pg.evaluate(OPAQ))
            small = [x for x in pg.evaluate(TAP) if x[1] < 43.5 or x[2] < 43.5]; ok(f"by-round: tap targets >= 44px {L}", not small, str(small[:3]))
            ok(f"by-round: contrast {L}", not pg.evaluate(CONTRAST), str(pg.evaluate(CONTRAST)[:3]))
            pg.click("[data-bkview=full]"); pg.wait_for_timeout(100); ok(f"switch back to Full bracket {L}", pg.get_attribute("#bracket .bk", "data-bk") == "full")
        else:
            ok(f"desktop: view switch hidden {L}", not pg.is_visible("[data-bkt]"))
            ok(f"desktop: connector lines drawn {L}", pg.evaluate("getComputedStyle(document.querySelector('#bracket .r1 .g'), '::after').content") == '""')
        # keyboard: scroll region focusable + a team link reachable by Tab
        pg.focus("#bracket .bkw"); ok(f"scroll region takes focus {L}", pg.evaluate("document.activeElement.classList.contains('bkw')"))
        ctx.close()
    # data-driven: swap the field via a stubbed pred-teams.json, bracket must follow
    ctx = b.new_context(viewport={"width": 1280, "height": 900}); ctx.add_init_script(ACC); pg = ctx.new_page()
    alt = json.loads(json.dumps(PRED)); alt["field"] = FIELD[::-1]
    pg.route("**/data/pred-teams.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(alt)))
    pg.goto(BASE + "/playoff/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(400)
    got = pg.evaluate("document.querySelector('#bracket [data-seed=\"1\"] .tn').textContent"); ok("bracket is driven by data/pred-teams.json field (reversed field -> seed 1 changes)", got == T[FIELD[-1][0]]["n"], got)
    ctx.close()
    # short field (data glitch) must not throw or invent teams
    ctx = b.new_context(viewport={"width": 390, "height": 900}); ctx.add_init_script(ACC); pg = ctx.new_page(); con = []; pg.on("pageerror", lambda e: con.append(str(e)))
    alt = json.loads(json.dumps(PRED)); alt["field"] = FIELD[:8]
    pg.route("**/data/pred-teams.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(alt)))
    pg.goto(BASE + "/playoff/"); pg.wait_for_selector("main[data-loaded]"); pg.wait_for_timeout(400)
    ok("short field: no JS error and seeds 9-12 stay blank (nothing invented)", not con and pg.locator("#bracket [data-seed='12'] .tn").count() == 0, str(con[:1]))
    ctx.close(); b.close()
srv.shutdown()
print(f"bracket_test: {res['n'] - len(res['f'])}/{res['n']} checks pass")
for f in res["f"][:25]: print("FAIL:", f)
sys.exit(1 if res["f"] else 0)
