"""Static greps over build/site (incl. data/*.json): provider names, banned words in the lines UI, 32-hex strings, pages.dev, hashed asset refs, JSON shape; make_zip forbidden-string scan."""
import os, re, sys, json, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"; res = []
def ok(n, c, d=""): res.append((n, bool(c), d)); print(("PASS " if c else "FAIL ") + n + (" " + d if not c else ""))
files = [os.path.join(dp, f) for dp, _, fs in os.walk(SITE) for f in fs]
txt = {f: open(f, encoding="utf-8", errors="ignore").read() for f in files if f.endswith((".html", ".json", ".js", ".css", ".txt", ".xml", ".webmanifest")) or os.path.basename(f) == "_headers"}
PROV = re.compile(r"draftkings|fanduel|betmgm|caesars|espn bet|bet365|pointsbet|betrivers|circa sports|barstool|fanatics|bovada|betonline|william hill|unibet|wynn|hard rock bet|\bbetfred\b|the odds api|the-odds-api|odds api|oddsapi|consensus", re.I)
hits = [(os.path.relpath(f, SITE), m.group()) for f, t in txt.items() for m in PROV.finditer(t)]
ok("provider-name grep over build/site (html, json, js, css): named books, 'The Odds API', 'consensus'", not hits, str(hits[:10]))
gen = [(os.path.relpath(f, SITE)) for f, t in txt.items() if f.endswith(".json") and re.search(r"sportsbook|bookmaker|provider", t, re.I)]
ok("no generic provider words in any public JSON", not gen, str(gen))
# the generic words 'sportsbook'/'bookmaker' remain only in the pre-existing disclaimer, method and chat-refusal text (same as /workspace/kicktip-c1d)
jh = [f for f in files if f.endswith(".json") and re.search(r'"(provider|bookmaker|book|books|n_books|source|sportsbook)"\s*:', txt.get(f, ""))]
ok("no provider/books keys in any JSON", not jh, str(jh[:5]))
# Lines UI banned words: words in the HTML visible text of the games page / team page / conference page lines pieces + kt.js strings used in lines UI
js = txt[f"{SITE}/assets/kt.js"]; a = js.index("/* ---------- market line"); b = js.index("function render(d)"); lines_js = js[a:b]
strs = " ".join(re.findall(r"'([^']*)'", lines_js))
BAN = re.compile(r"\b(pick|picks|lock|locked|value|edge|bet|bets|play|best bet|top|biggest gaps|sportsbook|book|books)\b", re.I)
ok("banned words absent from kt.js lines-UI strings", not [m.group() for m in BAN.finditer(strs)], str(set(m.group() for m in BAN.finditer(strs))))
def vis(h): return re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[\s\S]*?</\1>", " ", h))
d = lambda s: re.sub(r"not betting advice|not a betting site|place bets", "", s, flags=re.I)
bad = {}
for p in ("games", "team/utah", "conference/big-12"):
    h = txt[f"{SITE}/{p}/index.html"]; m = re.search(r"<main[\s\S]*</main>", h).group(); m = re.sub(r'<div class="ban"[\s\S]*?</div>', "", m); m = re.sub(r'<div class="lock"[\s\S]*?</noscript></div>', "", m)
    if p != "games": m = " ".join(re.findall(r"<article class=\"gc\"[\s\S]*?</article>", m) + re.findall(r'<p class="note"><b>How to read the lines\.[\s\S]*?</p>', m))
    hit = set(x.group().lower() for x in BAN.finditer(d(vis(m))) if x.group().lower() != "locked" or p == "games")
    if hit: bad[p] = hit
ok("banned words absent from the lines UI in static HTML (games page main; game cards and line note on team and conference pages; disclaimer wording excluded)", not bad, str(bad))
STRIP = "Market lines: ESPN, numbers only, shown when posted."
dyn_pages = [f for f, t in txt.items() if f.endswith(".html") and "Market lines:" in t]   # 152 pages with the Sources strip + the method page list
ok("exact Sources strip wording ('Market lines: ESPN, ...') on every page that carries the strip", len(dyn_pages) == 153 and all(STRIP in txt[f] for f in dyn_pages), str(len(dyn_pages)))
ok("old strip wording 'Market lines: public sources' gone everywhere", not [f for f, t in txt.items() if "Market lines: public sources" in t])
# M1: the method page's 'Right now that is X of the Y games that have not started' must agree with the shipped data (pred-games.json = unstarted games, pred-lines.json = lines)
_g = json.load(open(f"{SITE}/data/pred-games.json"))["g"]; _l = json.load(open(f"{SITE}/data/pred-lines.json"))["l"]
_m = re.search(r"Right now that is (\d+) of the (\d+) games that have not started", txt[f"{SITE}/method/index.html"])
ok("method page line counts are generated and match the data", bool(_m) and int(_m.group(1)) == sum(1 for k in _g if k in _l) and int(_m.group(2)) == len(_g), str((_m.groups() if _m else None, sum(1 for k in _g if k in _l), len(_g))))
ok("method page no longer says 'We do not name'", "We do not name" not in txt[f"{SITE}/method/index.html"])
ok("no 32-hex strings anywhere", not [(os.path.relpath(f, SITE)) for f, t in txt.items() if re.search(r"(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])", t)])
ok("no pages.dev string", not [(os.path.relpath(f, SITE)) for f, t in txt.items() if "pages.dev" in t])
# pred-lines shape
L = json.load(open(f"{SITE}/data/pred-lines.json")); ok("pred-lines.json: only l (no version key, no provider or book fields)", set(L) == {"l"})
ok("pred-lines.json: every entry is [number, int epoch, int epoch]", all(len(v) == 3 and isinstance(v[0], (int, float)) and isinstance(v[1], int) and isinstance(v[2], int) for v in L["l"].values()))
ok("no data/m/*/pred-lines.json (market data is model-independent)", not glob.glob(f"{SITE}/data/m/*/pred-lines.json"))
G = json.load(open(f"{SITE}/data/pred-games.json")); ok("pred-games.json carries no market numbers (g = [win, line, raw])", all(len(v) == 3 for v in G["g"].values()) and "market_label" not in G and "market_asof" not in G)
# hashed asset refs
refs = {}
for f, t in txt.items():
    if f.endswith(".html"):
        for m in re.finditer(r'/assets/((?:ks/)?[\w-]+\.(?:js|css))(\?v=[0-9a-f]{10})?["\']', t): refs.setdefault(m.group(1), set()).add(m.group(2))
ok("every html reference to a js/css asset carries ?v=<10 hex> (one token per file)", refs and all(len(v) == 1 and None not in v for v in refs.values()), str(refs))
for f in ("assets/chat.js", "assets/chat-worker.js"): ok(f"{f}: inner references hashed", not re.search(r"/assets/ks/\w+\.js['\"]|/assets/chat-worker\.js['\"]", txt[f"{SITE}/{f}"]))
ok("old hand-set tokens gone (?v=chip2, c1c, b9, gfx1, gate1)", not [f for f, t in txt.items() if re.search(r"\?v=(chip\d|c1\w?|b\d|gfx\d|gate\d)[\"'&]", t)])
# make_zip.py forbidden-string scan, WITHOUT make_zip's secrets(): that function opens private/odds_api.env, which this build must never read. Same strings, minus the key value; the bookmaker names/keys come from the odds cache (data/cache, not private/).
bad = ["odds_api", "private/", "requests_remaining", "requests_used", "free plan"]
try:
    c = json.load(open(f"{ROOT}/data/cache/odds_ncaaf.json")); evs = c.get("events", c) if isinstance(c, dict) else c
    for e in evs:
        for bk in e.get("bookmakers", []): bad += [bk.get("key", ""), bk.get("title", "")]
except Exception as ex: print("note: odds cache not read:", type(ex).__name__)
bad = sorted({x for x in bad if len(x) >= 4}); allb = {f: open(f, "rb").read().lower() for f in files}
zhits = [(os.path.relpath(f, SITE), x) for f, b in allb.items() for x in bad if x.lower().encode() in b]
ok(f"make_zip forbidden-string scan ({len(bad)} strings, key value excluded by design) over every file in build/site", not zhits, str(zhits[:6]))
ok("no private/ path or nested zip in build/site", not [f for f in files if f.endswith(".zip") or "/private/" in f])
# method page: the market-line section copy (visible text) has no banned word
import html as _h
_m = txt[f"{SITE}/method/index.html"]; _i = _m.index("The model line, the market line"); _j = _m.index("Tiebreakers", _i)
_vis = _h.unescape(re.sub(r"<[^>]+>", " ", _m[_i:_j]))
_ban = re.compile(r"\b(pick|picks|lock|locked|value|edge|bet|bets|play|best bet|top|biggest gaps|sportsbook|book|books|provider)\b", re.I)
ok("method page market-line section: banned words absent", not [m.group() for m in _ban.finditer(_vis)], str([m.group() for m in _ban.finditer(_vis)]))
ok("no 'Last value' anywhere in build/site", not [os.path.relpath(f, SITE) for f, t in txt.items() if "Last value" in t])
json.dump(res, open(f"{ROOT}/tests/last_odds_static.json", "w"), indent=1); bad = [r for r in res if not r[1]]; print(f"{len(res)-len(bad)}/{len(res)} passed"); sys.exit(1 if bad else 0)
