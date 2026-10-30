"""/top25/ test (KickTip Top 25 vs the AP and Coaches polls). python3 tests/top25_test.py
Data (build/site/data/*.json against data/out/*), order, ties, difference arithmetic on EVERY row, NR / dash handling, as-of labels from data, stale-poll rule, scenario control, 44px, contrast,
no storage written, no request before interaction beyond the data files, no third-party request, heading order, links, wording."""
import sys, os, re, json, glob, datetime as dt
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
res = {"failures": [], "n": 0}
def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond: res["failures"].append(f"{name} {detail}"); print("FAIL", name, str(detail)[:400])
J = lambda p: json.load(open(p, encoding="utf-8"))
MINUS = "\u2212"; MT = ZoneInfo("America/Denver")
MODELS = {"blend": ("data", f"{ROOT}/data/out"), "elo": ("data/m/elo", f"{ROOT}/data/out/m/elo"), "eff": ("data/m/eff", f"{ROOT}/data/out/m/eff")}
def pct(p):
    if p is None: return "n/a"
    v = round(p * 100 + 1e-9) if False else int(p * 100 + 0.5)
    if p > 0 and v < 1: return "<1%"
    if p < 1 and v >= 100: return ">99%"
    return f"{v}%"
def jsround(p): import math; return math.floor(p * 100 + 0.5)
def pct(p):   # same rule as kt.js (Math.round)
    if p is None: return "n/a"
    v = jsround(p)
    if p > 0 and v < 1: return "<1%"
    if p < 1 and v >= 100: return ">99%"
    return f"{v}%"
polls = J(f"{SITE}/data/polls.json")["polls"]; srcp = J(f"{ROOT}/data/out/polls.json")["polls"] if os.path.exists(f"{ROOT}/data/out/polls.json") else {}
pt0 = J(f"{SITE}/data/pred-teams.json"); T0 = pt0["teams"]
# ---------------- data files
for mid, (dd, od) in MODELS.items():
    tp = J(f"{SITE}/{dd}/pred-top25.json"); pt = J(f"{SITE}/{dd}/pred-teams.json")["teams"]; b = J(f"{SITE}/{dd}/sim-bundle.json"); st = J(f"{od}/sim_teams.json")["teams"]
    ok(f"{mid}: pred-top25 names its model", tp["model"] == mid and tp["rank_by"] == "gs")
    ok(f"{mid}: 138 FBS teams, each once", len(tp["teams"]) == 138 and len({e[0] for e in tp["teams"]}) == 138 and set(e[0] for e in tp["teams"]) == set(pt))
    g = b["model"].get("gs") or b["model"]["s"]; by = {t["g"]: i for i, t in enumerate(b["teams"]) if "g" in t}
    exp = sorted(by, key=lambda s: (-round(g[by[s]], 4), -pt[s]["p"], pt[s]["n"]))
    ok(f"{mid}: rank order = sort by model strength (gs or s), ties by Make the 12 then name", [e[0] for e in tp["teams"]] == exp)
    ok(f"{mid}: shipped strengths are non-increasing", all(tp["teams"][i][3] >= tp["teams"][i + 1][3] for i in range(137)))
    sm = {SLUG: t for t in st for SLUG in [None]}  # placeholder to keep names
    rec = {t["team"]: (t["overall_w"], t["overall_l"]) for t in st}
    full2slug = {t["n"]: t["g"] for t in b["teams"] if "g" in t}
    ok(f"{mid}: records equal sim_teams overall W-L", all(rec[n] == tuple(next(e[1:3] for e in tp["teams"] if e[0] == full2slug[n])) for n in rec if n in full2slug), "")
    ok(f"{mid}: strength used is the data's (matches bundle to 4 dp)", all(abs(e[3] - g[by[e[0]]]) < 6e-5 for e in tp["teams"]))
ok("asof label comes from the run as_of", J(f"{SITE}/data/pred-top25.json")["asof"] == dt.datetime.strptime(J(f"{ROOT}/data/out/sim_teams.json")["as_of"].replace(" MT", ""), "%Y-%m-%d %H:%M").strftime("%b %-d, %-I:%M %p").replace(" 0", " "))
# ties: synthetic bundle through the real function
sys.argv = [sys.argv[0]]
import importlib.util
spec = importlib.util.spec_from_file_location("kbuild", f"{ROOT}/src/build.py"); kb = importlib.util.module_from_spec(spec); sys.modules["kbuild"] = kb
os.environ["KT_SITE_DIR"] = "/tmp/kt_top25_tie_site"; spec.loader.exec_module(kb)
bb = J(f"{SITE}/data/sim-bundle.json"); g = bb["model"]["gs"]; ix = {t["g"]: i for i, t in enumerate(bb["teams"]) if "g" in t}
names = sorted(ix); a, c, d = names[10], names[11], names[12]
for s in (a, c, d): g[ix[s]] = 3.14159
kb.BUNDLES["blend"] = bb; fake = {"teams": {s: dict(p=0.5) for s in ix}}; fake["teams"][c]["p"] = 0.9; fake["teams"][a]["p"] = 0.5; fake["teams"][d]["p"] = 0.5
for s in ix: fake["teams"][s]["p"] = fake["teams"][s]["p"] if s in (a, c, d) else 0.1
out = kb.build_top25("blend", fake)["teams"]; got = [e[0] for e in out if e[0] in (a, c, d)]
shortn = {v["slug"]: v["short"] for v in kb.TEAMS.values()}
ok("tie on strength: higher Make the 12 first, then name", got[0] == c and got[1:] == sorted([a, d], key=lambda s: shortn[s]), got)
mk = lambda wk, pub: dict(released=True, week=wk, published=pub, ranks=[dict(r=1, espn=str(next(iter(kb.TEAMS.values()))["espn"]), rec="1-0")])
mix = kb.build_polls({"polls": {"ap": mk("9", "2026-10-25T19:00Z"), "coaches": mk("8", "2026-10-18T20:00Z")}})["polls"]
ok("stale rule: AP week 9 + Coaches still week 8 -> Coaches is 'not released yet' (week 8 rank never shown under week 9)", mix["ap"]["released"] and not mix["coaches"]["released"] and "ranks" not in mix["coaches"])
same = kb.build_polls({"polls": {"ap": mk("8", "2026-10-18T21:15Z"), "coaches": mk("8", "2026-10-18T20:00Z")}})["polls"]
ok("same week: both shown, each with its own MT time (AP Oct 18, 3:15 PM; Coaches Oct 18, 2:00 PM)", same["ap"]["asof"] == "Oct 18, 3:15 PM" and same["coaches"]["asof"] == "Oct 18, 2:00 PM")
none = kb.build_polls({"polls": {}})["polls"]; ok("no polls file: both 'not released yet'", not none["ap"]["released"] and not none["coaches"]["released"])
# ---------------- expected per-row values (independent of the page code)
def label(iso): return dt.datetime.strptime(iso, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc).astimezone(MT).strftime("%b %-d, %-I:%M %p").replace(" 0", " ")
def exp_asof(P):
    def one(k, nm): return f"{nm} poll as of {label(P[k]['pub'])} MT." if P[k]["released"] else f"{nm} poll: not released yet."
    return one("ap", "AP") + " " + one("coaches", "Coaches")
def ranks_of(P, k): return {x[1]: x[0] for x in P[k]["ranks"]} if P[k]["released"] else None
def dtxt(d): return "0" if d == 0 else (f"+{d}" if d > 0 else MINUS + str(-d))
def spots(n): return f"{n} spot" + ("" if n == 1 else "s")
def exp_sent(nm, k, d): return f"KickTip ranks {nm} " + ("the same as " if d == 0 else f"{spots(abs(d))} " + ("higher than " if d > 0 else "lower than ")) + {"ap": "the AP poll", "coaches": "the Coaches poll"}[k] + "."
def exp_words(P, slug, kt):
    seen, parts, any_on = False, [], False; PN = {"ap": "AP", "coaches": "Coaches"}
    for k in ("ap", "coaches"):
        r = ranks_of(P, k)
        if r is None: continue
        any_on = True
        if slug not in r: parts.append(f"not ranked by {PN[k]}"); continue
        d = r[slug] - kt; ph = "the same as" if d == 0 else (f"{abs(d)}" if seen else spots(abs(d))) + (" higher than" if d > 0 else " lower than"); seen = True; parts.append(f"{ph} {PN[k]}")
    if not any_on: return "Poll ranks are not out yet."
    if all(ranks_of(P, k) is None or slug not in ranks_of(P, k) for k in ("ap", "coaches")):
        return "Not ranked by either poll." if all(ranks_of(P, k) is not None for k in ("ap", "coaches")) else "Not ranked by " + ("AP" if ranks_of(P, "ap") is not None else "Coaches") + "."
    s = ", ".join(parts); return (s[0].upper() + s[1:] if parts[0].startswith("not ranked") else "KickTip is " + s) + "."
def expected(P, tp, T):
    rank = {e[0]: i + 1 for i, e in enumerate(tp["teams"])}; ent = {e[0]: e for e in tp["teams"]}
    top = [e[0] for e in tp["teams"][:25]]
    def best(s): return min([r[s] for r in (ranks_of(P, "ap"), ranks_of(P, "coaches")) if r and s in r] or [999])
    out = sorted([s for s in rank if rank[s] > 25 and any(r and s in r for r in (ranks_of(P, "ap"), ranks_of(P, "coaches")))], key=lambda s: (best(s), rank[s], T[s]["n"]))
    return top, out, rank, ent
def check_rows(pg, w, P, tp, T, tag):
    top, outl, rank, ent = expected(P, tp, T); vis_table = w >= 700
    for sec, slugs, tb, ol in (("top", top, "#t25 tbody tr", "#t25l > li"), ("out", outl, "#t25o tbody tr", "#t25ol > li")):
        if sec == "out" and not slugs:
            ok(f"{tag}: outside-25 section hidden when empty", pg.evaluate("document.getElementById('t25out').hidden") is True); continue
        rows = pg.query_selector_all(tb if vis_table else ol); ok(f"{tag}: {sec}: {len(slugs)} rows shown", len(rows) == len(slugs), len(rows))
        for r, s in zip(rows, slugs):
            kt = rank[s]; t = T[s]; e = ent[s]; ap = ranks_of(P, "ap"); co = ranks_of(P, "coaches")
            if vis_table:
                tds = r.query_selector_all("td"); tx = [x.inner_text().strip() for x in tds]
                ok(f"{tag}: {s}: KickTip rank {kt}", tx[0] == str(kt), tx[0]); ok(f"{tag}: {s}: team name", t["n"] in tx[1])
                ok(f"{tag}: {s}: conference and record", tx[6] == t["cn"] and tx[7] == f"{e[1]}-{e[2]}", tx[6:8]); ok(f"{tag}: {s}: Make the 12 equals data", tx[8] == pct(t["p"]), tx[8])
                for j, (k, pr) in enumerate((("ap", ap), ("coaches", co))):
                    pc = tds[2 + j].inner_text().strip(); dc = tds[4 + j]
                    if pr is None: ok(f"{tag}: {s}: {k} not released shows a dash, no rank", "\u2014" in pc and not re.search(r"\d", pc.replace("\u2014", "")) and "\u2014" in dc.inner_text(), (pc, dc.inner_text())); continue
                    if s not in pr:
                        ok(f"{tag}: {s}: {k} NR", pc.startswith("NR") and dc.inner_text().strip().startswith("NR") and not re.search(r"[+\u2212]\d", dc.inner_text()), (pc, dc.inner_text()))
                        continue
                    d = pr[s] - kt; ok(f"{tag}: {s}: {k} rank {pr[s]}", pc == str(pr[s]), pc)
                    pill = dc.query_selector(".t25-pill"); ok(f"{tag}: {s}: {k} difference {dtxt(d)} (poll {pr[s]} minus KickTip {kt})", pill and pill.inner_text() == dtxt(d), pill and pill.inner_text())
                    hid = dc.query_selector(".vh").inner_text(); ok(f"{tag}: {s}: {k} screen-reader sentence", hid == exp_sent(t["n"], k, d), hid)
            else:
                ok(f"{tag}: {s}: card words", r.query_selector(".t25-words").inner_text().strip() == exp_words(P, s, kt), r.query_selector(".t25-words").inner_text())
                cells = [c.inner_text().replace("\n", " ").strip() for c in r.query_selector_all(".t25-c")]
                want = [f"KickTip {kt}"] + [f"{lab} " + ("\u2014" if pr is None else str(pr[s]) if s in pr else "NR") for lab, pr in (("AP", ap), ("Coaches", co))]
                ok(f"{tag}: {s}: three cells", cells == want, (cells, want)); ok(f"{tag}: {s}: big rank", r.query_selector(".t25-rk b").inner_text() == str(kt))
                ok(f"{tag}: {s}: sub line", r.query_selector(".t25-sub").inner_text().strip() == f"{t['cn']} \u00b7 {e[1]}-{e[2]}", r.query_selector(".t25-sub").inner_text())
def lumjs():
    return """()=>{const parse=c=>{const m=c.match(/rgba?\\(([^)]+)\\)/);const p=m[1].split(',').map(Number);return p.length<4?[...p,1]:p};
const bgOf=e=>{while(e){const c=parse(getComputedStyle(e).backgroundColor);if(c[3]>0)return c;e=e.parentElement}return [255,255,255,1]};
const lum=c=>{const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2])};
const out=[];for(const e of document.querySelectorAll('.t25 .t25-asof, .t25-def, .t25-sub, .t25-words, .t25-c span, .t25-c b, .t25-pill, .t25-rk b, .t25-rk span, .t25-btn, .t25-det dt, .t25-det dd, .t25-tw th, .t25-tw td, .t25 .note, .lk, .rn')){
const r=e.getBoundingClientRect();if(!r.width||!r.height)continue;if(!e.childNodes.length||![...e.childNodes].some(n=>n.nodeType==3&&n.textContent.trim()))continue;
const fg=parse(getComputedStyle(e).color),bg=bgOf(e);const a=lum(fg),b=lum(bg);const cr=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);out.push([e.className||e.tagName,Math.round(cr*100)/100,getComputedStyle(e).fontSize])}return out}"""
EXTRA_OK = re.compile(r"^(https?://127\.0\.0\.1:\d+)?/(top25/$|assets/|data/(pred-teams|pred-top25|polls)\.json|data/m/(elo|eff)/pred-(teams|top25)\.json|favicon)")
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 390, 430, 1280):
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); reqs = []; errs = []
        pg.on("request", lambda r: reqs.append(r.url)); pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(BASE + "/top25/"); pg.wait_for_selector("main[data-t25]", timeout=10000); pg.wait_for_timeout(500)
        tag = f"@{w}"
        ok(f"{tag}: no console errors", not errs, errs)
        ok(f"{tag}: no horizontal overflow", pg.evaluate("document.documentElement.scrollWidth") <= w, pg.evaluate("document.documentElement.scrollWidth"))
        ok(f"{tag}: no overflow outside scroll boxes", not pg.evaluate("""()=>[...document.querySelectorAll('body *')].filter(e=>!e.closest('.tw')&&getComputedStyle(e).position!='fixed'&&getComputedStyle(e).display!='none'&&e.getBoundingClientRect().width>0&&e.getBoundingClientRect().right>innerWidth+1&&!e.closest('.vh')&&!e.classList.contains('vh')).map(e=>e.className||e.tagName).slice(0,5)"""))
        bad = [u for u in reqs if not EXTRA_OK.match(u)]; ok(f"{tag}: arrival requests are only assets and the three data files (no third party, no simulator, bundle, shards)", not bad, bad[:5])
        ok(f"{tag}: data requests on arrival", sorted(re.sub(r"^.*?/data/", "", u) for u in reqs if "/data/" in u) == ["polls.json", "pred-teams.json", "pred-top25.json"], [u for u in reqs if "/data/" in u])
        ok(f"{tag}: nothing written to localStorage, sessionStorage or cookies on arrival", pg.evaluate("localStorage.length==0&&sessionStorage.length==0&&document.cookie===''"))
        # layout: exactly one of table/cards in the tree
        tv = pg.evaluate("getComputedStyle(document.querySelector('.t25-tw')).display"); cv = pg.evaluate("getComputedStyle(document.getElementById('t25l')).display")
        ok(f"{tag}: table xor cards (never both in the accessibility tree)", (tv != "none") == (w >= 700) and (cv != "none") == (w < 700), (tv, cv))
        check_rows(pg, w, polls, J(f"{SITE}/data/pred-top25.json"), T0, f"{tag} live")
        ok(f"{tag}: as-of strip text from data", pg.inner_text("[data-t25asof]").replace("\n", " ").strip().startswith(exp_asof(polls)) and pg.inner_text("[data-t25asof]").replace("\n", " ").strip().endswith(f"KickTip updated {J(f'{SITE}/data/pred-top25.json')['asof']} MT."), pg.inner_text("[data-t25asof]"))
        lines = pg.evaluate("[...document.querySelectorAll('[data-t25asof] > span')].map(s=>s.getBoundingClientRect().top)")
        ok(f"{tag}: as-of strip is {'two lines' if w < 700 else 'one line'}", (lines[0] != lines[1]) if w < 700 else abs(lines[0] - lines[1]) < 3, lines)
        ok(f"{tag}: sibling order: model strip, as-of strip, Run card, list card", pg.evaluate("""()=>{const q=s=>document.querySelector(s);const o=[q('[data-mdl]'),q('[data-t25asof]'),q('.t25-run'),q('#t25l').closest('.card')];return o.every(Boolean)&&o.every((e,i)=>i==0||(o[i-1].compareDocumentPosition(e)&4)>0)}"""))
        ok(f"{tag}: Run card is directly above the list card", pg.evaluate("document.querySelector('.t25-run').nextElementSibling===document.getElementById('t25l').closest('.card')"))
        # headings, run card copy
        hs = pg.evaluate("[...document.querySelectorAll('h1,h2,h3')].filter(h=>h.offsetParent!==null).map(h=>h.tagName+':'+h.textContent.trim())")
        want_h = ["H1:KickTip Top 25", "H2:Run a scenario", "H2:The KickTip Top 25"] + (["H2:Ranked in a poll, outside the KickTip 25"] if pg.evaluate("!document.getElementById('t25out').hidden") else [])
        ok(f"{tag}: one H1, h2s only below it, in order", hs == want_h, hs)
        ok(f"{tag}: Run card heading, line, button, full terms line", pg.text_content(".t25-run h2") == "Run a scenario" and "Pick a game result and see how chances change. Ratings and ranks here do not change." in pg.inner_text(".t25-run") and pg.inner_text(".t25-btn") == "Run scenario" and pg.inner_text(".t25-run .rn").startswith("By tapping Run, you accept the terms: KickTip is information only, not a betting site, and no decision should be made based on this material.") and pg.inner_text(".t25-run .rn").endswith("Full terms"), pg.inner_text(".t25-run"))
        ok(f"{tag}: terms line is directly under the button", pg.evaluate("document.querySelector('.t25-btn').nextElementSibling.classList.contains('rn')"))
        bt = pg.evaluate("(()=>{const e=document.querySelector('.t25-btn'),c=getComputedStyle(e),r=e.getBoundingClientRect();return [r.height,c.backgroundColor,c.color]})()")
        ok(f"{tag}: Run scenario button 44px, graphite fill, white text", bt[0] >= 44 and bt[1] == "rgb(38, 43, 49)" and bt[2] == "rgb(255, 255, 255)", bt)
        # 44px targets (visible ones)
        small = pg.evaluate("""()=>[...document.querySelectorAll('.t25 a, .t25 button, .t25-c, .ldm a')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&e.closest('.ban')==null&&(r.height<43.5||(r.width<43.5&&!e.closest('.rn')&&e.tagName!='A'))}).map(e=>(e.className||e.tagName)+':'+Math.round(e.getBoundingClientRect().width)+'x'+Math.round(e.getBoundingClientRect().height)).slice(0,6)""")
        ok(f"{tag}: tap targets and rank cells >= 44px", not small, small)
        cr = pg.evaluate(lumjs()); ok(f"{tag}: contrast >= 4.5:1 (3:1 for 24px+ type)", all(c >= (3 if float(f.replace('px', '')) >= 24 else 4.5) for _, c, f in cr), [c for c in cr if c[1] < 4.5][:4])
        if w < 700:
            first = pg.query_selector("#t25l > li"); cells = first.query_selector_all(".t25-c"); bx = [c.bounding_box() for c in cells]
            ok(f"{tag}: three rank cells on one row, equal width", len({round(x['y']) for x in bx}) == 1 and max(x['width'] for x in bx) - min(x['width'] for x in bx) < 1.5, bx)
            st_ = pg.evaluate("(li=>{const k=li.querySelector('.t25-k'),a=li.querySelectorAll('.t25-c')[1],kc=getComputedStyle(k),ac=getComputedStyle(a);return [kc.backgroundColor,kc.color,ac.borderTopColor,ac.borderTopWidth,getComputedStyle(li.querySelector('.t25-rk b')).fontSize,getComputedStyle(li.querySelector('.t25-c b')).fontSize,getComputedStyle(li.querySelector('.t25-c span')).fontSize]})", first)
            ok(f"{tag}: KickTip cell graphite/white, AP outlined 1px #DDE3E6, 36px rank, 24px values, 13px labels", st_[0] == "rgb(38, 43, 49)" and st_[1] == "rgb(255, 255, 255)" and st_[2] == "rgb(221, 227, 230)" and st_[3] == "1px" and st_[4] == "36px" and st_[5] == "24px" and st_[6] == "13px", st_)
            ch = first.query_selector(".t25-chv"); det = first.query_selector(".t25-det"); ok(f"{tag}: details closed", det.is_hidden() and ch.get_attribute("aria-expanded") == "false")
            ch.click(); t0 = T0[polls["ap"]["ranks"][0][1]] if False else None
            ok(f"{tag}: chevron opens Make the 12, bye, Reach CCG, Win conference, Team page", det.is_visible() and ch.get_attribute("aria-expanded") == "true" and [x.inner_text() for x in det.query_selector_all("dt")] == ["Make the 12", "First-round bye", "Reach CCG", "Win conference"] and det.query_selector(".t25-tp").inner_text() == "Team page")
            s0 = J(f"{SITE}/data/pred-top25.json")["teams"][0][0]; t0 = T0[s0]
            ok(f"{tag}: opened values equal data", [x.inner_text() for x in det.query_selector_all("dd")] == [pct(t0["p"]), pct(t0["b"]), pct(t0["c"]), pct(t0["w"])], [x.inner_text() for x in det.query_selector_all("dd")])
            ch.click(); ok(f"{tag}: chevron closes", det.is_hidden())
            ok(f"{tag}: no segmented 'Number shown' control", "Number shown" not in pg.content())
        else:
            hd = [x.inner_text().replace("\n", " ").strip() for x in pg.query_selector_all("#t25 thead th")]
            ok(f"{tag}: desktop headers spelled out, in order", [h.lower() for h in hd] == ["kicktip rank", "team", "ap rank", "coaches rank", "kicktip vs ap", "kicktip vs coaches", "conference", "record", "make the 12 model"] and [x.text_content() for x in pg.query_selector_all("#t25 thead th")][:8] == ["KickTip rank", "Team", "AP rank", "Coaches rank", "KickTip vs AP", "KickTip vs Coaches", "Conference", "Record"], hd)
        txt0 = pg.inner_text("main .card:has(#t25l)")
        ok(f"{tag}: definition line and CCG line once", txt0.count("KickTip vs AP: poll rank minus KickTip rank. A plus means KickTip ranks the team higher than the poll, a minus means lower, 0 means the same. NR means not ranked by that poll.") == 1 and txt0.count("CCG = conference championship game") == 1)
        ok(f"{tag}: See every team by conference link after the list", pg.evaluate("(()=>{const a=[...document.querySelectorAll('.cta a')].find(x=>x.textContent=='See every team by conference');return !!a&&(document.getElementById('t25l').compareDocumentPosition(a)&4)>0&&a.getAttribute('href')=='/#conferences'})()"))
        # scenario control: opens the existing panel; nothing fetched; page numbers unchanged
        before = pg.inner_text("main .card:has(#t25l)"); n0 = len(reqs)
        pg.click("[data-t25run]"); pg.wait_for_timeout(600)
        ok(f"{tag}: Run scenario opens the Ask KickTip scenario panel", pg.evaluate("(()=>{const k=document.getElementById('kp');return !!k&&!k.hidden&&document.getElementById('kpill').getAttribute('aria-expanded')=='true'})()") and pg.evaluate("!!document.querySelector('#kp .cx') && !!document.getElementById('kask')"))
        newr = [u for u in reqs[n0:] if re.search(r"/assets/ks/|chat-worker|sim-bundle|/whatif/", u)]; ok(f"{tag}: opening the panel fetches no simulator, bundle or shards", not newr, newr)
        ok(f"{tag}: panel open leaves the page's ranks and numbers unchanged", pg.inner_text("main .card:has(#t25l)") == before)
        ok(f"{tag}: still nothing in storage after opening the panel", pg.evaluate("localStorage.length==0&&sessionStorage.length==0&&document.cookie===''"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        ok(f"{tag}: panel closes (Esc) and focus returns", pg.evaluate("document.getElementById('kp').hidden"))
        ctx.close()
    # ---- poll-state variants (route the polls file): not released, one poll, stale rule, NR, outside-25, empty outside, load failure
    tp0 = J(f"{SITE}/data/pred-top25.json"); order = [e[0] for e in tp0["teams"]]
    def variant(P, w, name, mutate=None):
        ctx = b.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page()
        if P == "fail": pg.route("**/data/polls.json", lambda r: r.fulfill(status=404, body="no"))
        else: pg.route("**/data/polls.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps({"polls": P})))
        pg.goto(BASE + "/top25/"); pg.wait_for_selector("main[data-t25]", timeout=10000); pg.wait_for_timeout(300); return ctx, pg
    notout = {"ap": dict(name="AP Top 25", released=False), "coaches": dict(name="Coaches Poll", released=False)}
    for w in (390, 1280):
        ctx, pg = variant(notout, w, "none")
        ok(f"@{w} no polls: strip says not released yet for both", pg.inner_text("[data-t25asof]").replace("\n", " ").startswith("AP poll: not released yet. Coaches poll: not released yet."), pg.inner_text("[data-t25asof]"))
        check_rows(pg, w, notout, tp0, T0, f"@{w} none"); ok(f"@{w} no polls: no 'NR' and no stale rank anywhere in the list", not re.search(r"\bNR\b", pg.inner_text("#t25 tbody") + pg.inner_text("#t25l")))
        ctx.close()
    # AP out, Coaches not; rank 31 team in AP; NR for a top-25 team; same-rank and signed examples built from the real order
    apx = [[1, order[3], "7-0"], [2, order[0], "7-0"], [3, order[30], "6-1"], [4, order[1], "6-1"], [5, order[24], "6-1"]]
    half = {"ap": dict(name="AP Top 25", released=True, week="9", asof="Oct 25, 1:00 PM", pub="2026-10-25T19:00Z", ranks=apx), "coaches": dict(name="Coaches Poll", released=False)}
    for w in (320, 1280):
        ctx, pg = variant(half, w, "half")
        ok(f"@{w} AP only: strip", pg.inner_text("[data-t25asof]").replace("\n", " ").startswith("AP poll as of Oct 25, 1:00 PM MT. Coaches poll: not released yet."), pg.inner_text("[data-t25asof]"))
        check_rows(pg, w, half, tp0, T0, f"@{w} half"); ok(f"@{w} AP only: team ranked 31st by KickTip appears in the outside-25 section with its KickTip rank", pg.evaluate("!document.getElementById('t25out').hidden") and "31" in pg.inner_text("#t25out"))
        ctx.close()
    # both polls with real ranks including: +3, -4, 0, NR in one poll, NR in both
    both = {"ap": dict(name="AP Top 25", released=True, week="9", asof="Oct 25, 1:00 PM", pub="2026-10-25T19:00Z", ranks=[[order[0] and 1 + 0, order[3], "x"], [2, order[1], "x"], [3, order[2], "x"], [4, order[6], "x"], [5, order[40], "x"]] + [[6 + i, order[7 + i], "x"] for i in range(3)]),
            "coaches": dict(name="Coaches Poll", released=True, week="9", asof="Oct 25, 12:00 PM", pub="2026-10-25T18:00Z", ranks=[[1, order[0], "x"], [2, order[2], "x"], [3, order[41], "x"], [4, order[1], "x"]])}
    for w in (320, 430, 1280):
        ctx, pg = variant(both, w, "both"); check_rows(pg, w, both, tp0, T0, f"@{w} both")
        if w == 1280:
            ok("@1280 the arithmetic examples hold: KickTip 4 / AP 1 gives -3 style and +/0 forms present", all(any(x in pg.inner_text("#t25 tbody") for x in (s,)) for s in (MINUS, "+", "NR")))
        ok(f"@{w} both polls: outside-25 section shows teams ordered by best poll rank", pg.evaluate("!document.getElementById('t25out').hidden")); ctx.close()
    ctx, pg = variant("fail", 390, "fail"); ok("@390 polls file fails to load: dashes, KickTip ranks still shown, no crash", pg.query_selector_all("#t25l > li").__len__() == 25 and "not released yet" in pg.inner_text("[data-t25asof]")); ctx.close()
    # ---- model switch re-ranks; storage written only by the pick
    ctx = b.new_context(viewport={"width": 1280, "height": 900}); pg = ctx.new_page(); pg.goto(BASE + "/top25/"); pg.wait_for_selector("main[data-t25]", timeout=10000)
    for mid in ("elo", "eff"):
        pg.click("[data-more]") if pg.evaluate("document.getElementById('mdmore').hidden") else None; pg.click(f"button[data-m='{mid}']"); pg.wait_for_timeout(800)
        tpm = J(f"{SITE}/data/m/{mid}/pred-top25.json"); Tm = J(f"{SITE}/data/m/{mid}/pred-teams.json")["teams"]
        rows = [r.query_selector_all("td")[1].inner_text().strip() for r in pg.query_selector_all("#t25 tbody tr")]
        ok(f"model {mid}: the 25 rows follow that model's order and its Make the 12", rows == [Tm[e[0]]["n"] for e in tpm["teams"][:25]] and [r.query_selector_all("td")[8].inner_text().strip() for r in pg.query_selector_all("#t25 tbody tr")] == [pct(Tm[e[0]]["p"]) for e in tpm["teams"][:25]])
        ok(f"model {mid}: the page states the model", mid in pg.evaluate("document.querySelector('[data-t25model]').textContent").lower() or Tm and pg.evaluate("document.querySelector('[data-t25model]').textContent").startswith("Ranked by the "), pg.evaluate("document.querySelector('[data-t25model]').textContent"))
        ok(f"model {mid}: team links carry ?model={mid}", all(f"model={mid}" in a.get_attribute("href") for a in pg.query_selector_all("#t25 tbody a.tl")))
    ok("model pick wrote only the model key", pg.evaluate("Object.keys(localStorage)") == [json.load(open(f'{ROOT}/src/model_registry.json'))['store_key']] if os.path.exists(f"{ROOT}/src/model_registry.json") else len(pg.evaluate("Object.keys(localStorage)")) == 1)
    ctx.close()
    b.close()
# ---------------- static checks on the built files
H = open(f"{SITE}/top25/index.html", encoding="utf-8").read()
ok("title, description, canonical, indexable", "<title>KickTip Top 25 vs the AP and Coaches polls | KickTip Media</title>" in H and 'content="KickTip&#x27;s Top 25 ranked by the KickTip blend rating, compared with the recent AP and Coaches polls. Information only."' in H.replace("&#39;", "&#x27;") and '<link rel="canonical" href="https://kicktipmedia.com/top25/">' in H and "noindex" not in H)
ok("meta + og description say 'recent' AP and Coaches polls, never 'latest' (the polls file is not refreshed live)", H.count("compared with the recent AP and Coaches polls") == 2 and not re.search(r"latest\s+AP", H))
ok("eyebrow and hero lines", 'class=kick>KickTip rating' in H and "<h1>KickTip Top 25</h1>" in H and "The KickTip Top 25, compared with the AP and Coaches polls. A computer rating, not a poll.</p><p>KickTip ranks teams by a computer rating built from game results, with no voters, so it can differ from the polls." in H)
ok("sources strip credits ESPN for the polls", "Poll ranks (AP Top 25, Coaches Poll) via ESPN. Team, conference and league logos courtesy of ESPN." in H)
ok("no inline style attribute, no inline script, no third-party URL in the page", " style=" not in H and not re.search(r"<script(?![^>]*src=)", H) and not re.findall(r'(?:src|href)="https?://(?!kicktipmedia\.com)[^"]*"', H))
ok("no prediction number in the HTML (list is filled from data files)", "<tbody></tbody>" in H and '<ol class="t25-cards" id="t25l"></ol>' in H)
ok("noscript note present", "Turn on JavaScript to view predictions" in H)
sm = open(f"{SITE}/sitemap.xml").read(); ok("sitemap lists /top25/", "<loc>https://kicktipmedia.com/top25/</loc>" in sm)
hh = open(f"{SITE}/index.html", encoding="utf-8").read(); ok("home: 'See the KickTip Top 25' CTA right after the Top chances card's field + games links", re.search(r'See the 12-team field and bracket</a> &middot; <a href="/games/">See this week&#8217;s games</a></p><p class="cta"><a href="/top25/">See the KickTip Top 25</a></p>', hh) is not None)
pp = open(f"{SITE}/playoff/index.html", encoding="utf-8").read(); ok("playoff: intro link to /top25/", 'href="/top25/">See the KickTip Top 25</a>' in pp)
ft = [k for k in glob.glob(f"{SITE}/**/*.html", recursive=True) if '<a href="/top25/">Top 25</a><a href="/games/">This week&#8217;s games</a></p>' not in open(k, encoding="utf-8").read()]; ok("footer Top 25 link on every page", not ft, ft[:3])
nav = [k for k in glob.glob(f"{SITE}/**/*.html", recursive=True) if re.search(r'<nav class="nav".*?</nav>', open(k, encoding="utf-8").read(), re.S).group(0).count("top25")]; ok("not in the header nav", not nav, nav[:3])
poll_words = re.compile(r"Coaches|AP Top 25|AP poll|\bAP rank", re.I)
leak = [f[len(SITE):] for f in glob.glob(f"{SITE}/**/*", recursive=True) if os.path.isfile(f) and f.endswith((".html", ".js", ".json", ".css", ".xml")) and poll_words.search(open(f, encoding="utf-8", errors="replace").read())]
ok("poll names and the ESPN poll credit appear only on /top25/ (page, its script and its data)", set(leak) <= {"/top25/index.html", "/assets/top25.js", "/data/polls.json", "/assets/top25.css"}, leak)
vis = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript>.*?</noscript>", "", H, flags=re.S)
mine = re.sub(r'<div class="ban".*?</div>|<footer.*?</footer>|<div class="tb".*?</div></div>', "", vis, flags=re.S)
words = re.findall(r"\b(picks?|locks?|value|edge|bets?|betting|play|best|top pick|odds|sportsbooks?|wager|predicts?|winner|lines?|spread)\b", re.sub(r"Pick a game result and see how chances change\.", "", re.sub(r"[^<>]*not a betting site[^<>]*", "", mine)), re.I)
ok("page copy avoids pick/lock/value/edge/bet/play/best/odds/sportsbook/predict/winner/line/spread", not words, words)
bw = re.findall(r"\b(picks?|locks?|value|edge|bets?|odds|sportsbooks?|predicts?|winner|best)\b", open(f"{SITE}/assets/top25.js").read(), re.I); ok("top25.js carries none of those words", not bw, bw)
ok("no 'pages.dev', no accented resume, no 'title game' on the page or its assets", not re.search(r"pages\.dev|r\u00e9sum\u00e9|title game", H + open(f"{SITE}/assets/top25.js").read() + open(f"{SITE}/assets/top25.css").read()))
ok("true minus only (no hyphen-minus used as a sign) in top25.js", "MINUS = '\\u2212'" in open(f"{SITE}/assets/top25.js").read())
print(f"top25_test: {res['n']} checks, {len(res['failures'])} failures"); json.dump(res, open(f"{ROOT}/tests/last_top25_test.json", "w"), indent=1); sys.exit(1 if res["failures"] else 0)
