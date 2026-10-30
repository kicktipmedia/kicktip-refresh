"""Content audit of dist/kicktip-site-b4.zip (override: python3 tests/audit.py <zipname>) (text files only). Exit 1 on any hit."""
import zipfile, re, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{ROOT}/src"); import make_zip; from site_config import SITE_URL
Z = zipfile.ZipFile(f"{ROOT}/dist/" + (sys.argv[1] if len(sys.argv) > 1 else "kicktip-site-b4.zip"))
names = Z.namelist(); hits = []
def hit(k, f, ctx): hits.append(f"{k} | {f} | {ctx[:100]}")
BOOKS = r"draftkings|fanduel|betmgm|caesars|bet365|espn\s?bet|bovada|pointsbet|barstool|betrivers|fanatics|unibet|betonline|mybookie|lowvig|wynn|hard\s?rock|betus|williamhill|superbook|circa|bally|sportsbook"
BANNED = {
  "sportsbook brand": r"draftkings|fanduel|betmgm|caesars|bet365|espn\s?bet|bovada|pointsbet|barstool|betrivers|fanatics|unibet|betonline|mybookie|lowvig|betus|williamhill|superbook|circa sports|bally bet",
  "promo/affiliate": r"promo\s?code|bonus code|sign[- ]?up bonus|free bet|bet now|place (your )?bets? (now|today)|affiliate link|odds boost|risk[- ]free",
  "MG/Utah": r"mountain gridiron|utah football",
  "accent": r"r\u00e9sum\u00e9|resum\u00e9",
  "emoji": "[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2B06\u2B07\uFE0F]",
  "key": r"odds_api|api[_-]?key|apikey|private/|requests_remaining|requests_used|x-requests|free plan|api quota",
  "dev note (reader-facing text must not carry build notes)": r"\bVERIFY\b|confirm on the conference site|could not be downloaded|url not retained|time to verify|placeholder only|kickoff not confirmed|not confirmed\b|secondary or mirror|secondary (article|summar|reference)|mirror of|prior-year text|unverified|not linked\)|Pick.em|\b1 books\b|class=['\"][^'\"]*['\"]\s+class=",
}
EXT = (".html", ".css", ".js", ".json", ".txt", ".xml", ".svg", "_headers")
mentions = {"sportsbook(word)": 0}; odds_links = []
for n in names:
    if n.endswith(".zip"): hit("nested zip", n, "")
    if n.startswith("private"): hit("private", n, "")
    if not n.endswith(EXT): continue
    t = Z.read(n).decode("utf-8", "replace")
    for k, rx in BANNED.items():
        for m in re.finditer(rx, t, re.I):
            c = t[max(0, m.start() - 90):m.end() + 40].replace("\n", " ")
            if k == "promo/affiliate" and re.search(r"\b(no|not|never|without|nor)\b", c, re.I): continue   # negated statement (disclaimer: 'no sportsbook affiliates, ads, bonuses or promo codes')
            hit(k, n, c)
    # the word 'sportsbook' only allowed in negating disclaimer/method statements
    for m in re.finditer(r"sportsbook|bookmaker|betting site", t, re.I):
        ctxt = t[max(0, m.start() - 120):m.end() + 260].replace("\n", " "); mentions["sportsbook(word)"] += 1
        if not re.search(r"\b(not|no|never|nor|without|does not|do not|neither)\b", ctxt, re.I): hit("unqualified sportsbook word", n, ctxt)
    for u in re.findall(r"""(?:href|src)=["'](https?://[^"']+)""", t): 
        if "the-odds-api" in u or "theoddsapi" in u: odds_links.append((n, u))
# off-origin: any absolute URL in href/src/fetch/css url() ; list distinct hosts of external links
hosts = {}
for n in names:
    if n.endswith((".html", ".js", ".css")):
        t = Z.read(n).decode("utf-8", "replace")
        for u in re.findall(r"""(?:href|src)=["'](https?://[^"'/]+)""", t): hosts.setdefault(u.split("//")[1], set()).add(n)
        for u in re.findall(r"""url\((https?://[^)]+)""", t): hit("css external url", n, u)
        if n.endswith((".js", ".css")): 
            for u in re.findall(r"https?://[^\s'\"]+", t): hit("absolute url in js/css", n, u)
        if re.search(r"<script[^>]*src=[\"']https?:|<link[^>]*href=[\"']https?:[^>]*stylesheet|@import", t): hit("external asset", n, "")
        if re.search(r"<script(?![^>]*src)[^>]*>|\sstyle=\"|\son(click|load|error)=", t): hit("inline script/style/handler (CSP)", n, "")
# pages: required content
pages = [n for n in names if n.endswith("index.html")]
for n in pages:
    t = Z.read(n).decode("utf-8", "replace")
    if "from the team behind Mtn Sports Media" in t: pass
    if re.search(r"<img[^>]+(logo|crest|mascot)", t, re.I) and "kicktip" not in t.lower(): hit("logo img?", n, "")
    if not re.search(r"(?i)sources", t) or not re.search(r"(?i)last updated|updated", t): hit("missing sources/updated", n, "")
    if n.startswith(("conference/", "team/", "playoff/")) or n == "index.html":
        if "disclaimer" not in t.lower() or "/method/" not in t: hit("missing banner links", n, "")
# MSM mentions: exactly the footer line on every page; the home page also has the State sites tile (home = 2, every other page = 1)
FOOT = "from the team behind Mtn Sports Media"; msm = {}; msm_pages = {}
for n in pages:
    t = Z.read(n).decode("utf-8", "replace"); c = len(re.findall(r"Mtn Sports Media|MSM", t)); msm[n] = c
    want = 2 if n == "index.html" else 1
    if c != want or t.count(FOOT) != 1: msm_pages[n] = c
    if n == "index.html":
        m = re.search(r'<div class="st"><span class="tag live">Live</span><b>Mtn Sports Media</b>Utah</div>', t)
        if not m: hit("State sites MSM tile wrong or missing", n, "")
        if t.count('class="st"') != 3 or t.count("Coming soon") != 2: hit("State sites card should have 3 tiles, 2 Coming soon", n, "")
        if "coming from the team" in t.lower(): hit("banned wording 'coming from the team'", n, "")
    elif "State sites" in t: hit("State sites card outside home", n, "")
for n, c in msm_pages.items(): hit("MSM mention count/placement", n, str(c))

# ---- b3: logo/brand assets (KickTip's own files, not school logos), fonts, method page items, gate unchanged
import hashlib
PK = "/workspace/hub/creative-v11d-kicktip-logo-pkg"
sh = lambda b: hashlib.sha256(b).hexdigest()
# b6: V2 brand files byte-identical to the package; no Tag Badge files; only the allowed images
BRAND = {"assets/brand/logo/kicktip-header-nosub-transparent.png": "logo/kicktip-header-nosub-transparent.png", "assets/brand/logo/kicktip-media-lockup-transparent.png": "logo/kicktip-media-lockup-transparent.png", "favicon.ico": "icon/favicon.ico"}
for f in os.listdir(f"{PK}/icon"): BRAND[f"assets/brand/icon/{f}"] = f"icon/{f}"
for f in os.listdir(f"{PK}/social"): BRAND[f"assets/brand/social/{f}"] = f"social/{f}"
for n, src in BRAND.items():
    if n not in names: hit("brand asset missing", n, "")
    elif sh(Z.read(n)) != sh(open(f"{PK}/{src}", "rb").read()): hit("brand asset differs from V2 package", n, "")
if any(n.startswith(("assets/logo/", "assets/social/")) or n.endswith((".svg", ".jpg")) and n != "assets/img/hero.jpg" for n in names): hit("old Tag Badge / non-package brand file shipped", "zip", "")
if any(re.search(r"BRAND-GUIDE|MANIFEST|README|proofs/|JARED|-source\.jpg", n) for n in names): hit("internal brand doc/proof/source shipped", "zip", "")
for n in names:   # allowed images: V2 brand files, hero photo, ESPN logos (checked byte-for-byte in site_test)
    if re.search(r"\.(png|jpe?g|gif|webp|svg|ico)$", n) and not (n in BRAND or n == "assets/img/hero.jpg" or n.startswith("assets/logos/")): hit("unexpected image asset", n, "")
for f in ("BarlowCondensed-Bold", "BarlowCondensed-BoldItalic", "SourceSans3-400", "SourceSans3-600", "SourceSans3-700"):
    if f"assets/fonts/{f}.woff2" not in names: hit("font missing", f, "")
css = Z.read("assets/kt.css").decode()
if css.count("@font-face") != 5 or re.search(r"url\((?!fonts/)[^)]*woff", css): hit("font-face not 5 relative self-hosted rules", "assets/kt.css", "")
for n in pages:
    t = Z.read(n).decode("utf-8", "replace")
    need = ("/assets/brand/icon/kicktip-icon-32.png", "/favicon.ico", "/assets/brand/icon/kicktip-apple-touch-180.png", "/site.webmanifest", "kicktip-header-nosub-transparent.png", "/assets/brand/social/kicktip-og-1200x630.png", "twitter:image")
    if any(x not in t for x in need) or re.search(r"Tag Badge|assets/logo/|assets/social/|kicktip-lockup-dark", t): hit("head/header brand wiring wrong", n, "")
    if re.search(r"""<meta name="robots"|noindex""", t): hit("noindex on a page", n, "")
    if n != "404.html" and ('<link rel="canonical" href="' + SITE_URL + '/' + (n[:-10] if n.endswith("index.html") else n) + '">' not in t or ('og:url" content="' + SITE_URL + '/' + (n[:-10] if n.endswith("index.html") else n) + '"') not in t): hit("canonical/og:url missing or inconsistent", n, "")
m = Z.read("method/index.html").decode()
if "Predictions are for information only, not betting advice." not in m: hit("method banner missing", "method/index.html", "")
if "Rules sources at a glance" not in m or "Unverified" in m: hit("method rules-sources note missing or stale Unverified note present", "method/index.html", "")
for n in pages:
    if re.search(r"uses the (MSM|Mtn Sports Media)|MSM rating|Mtn Sports Media rating", Z.read(n).decode("utf-8", "replace"), re.I): hit("MSM rating credit", n, "")
b4c = zipfile.ZipFile(f"{ROOT}/dist/kicktip-site-b4c.zip"); kj3 = Z.read("assets/kt.js").decode()
import subprocess, tempfile
_t = tempfile.mkdtemp(); open(f"{_t}/kt.js", "w").write(b4c.read("assets/kt.js").decode())
subprocess.run(["patch", "-s", f"{_t}/kt.js", f"{ROOT}/tests/b5-kt.js.patch"], check=True)
_b8 = zipfile.ZipFile(f"{ROOT}/dist/kicktip-site-b8.zip").read("assets/kt.js").decode()
if open(f"{_t}/kt.js").read() != _b8: hit("b8 kt.js differs from b4c + the b5 logo patch (baseline moved)", "assets/kt.js", "")
# b9: kt.js may differ from b8 ONLY by the bracket() filler and the one call that replaced the old data-seed line
_i, _j = kj3.find("  /* b9 bracket:"), kj3.find("  function destiny(T) {")
_old_line = [l for l in _b8.split("\n") if l.startswith("    f = f || []; [].forEach.call(D.querySelectorAll('[data-seed]')")]
_norm = kj3[:_i] + kj3[_j:] if _i > 0 and _j > _i else kj3
if _old_line: _norm = _norm.replace("    f = f || []; bracket(T, f);", _old_line[0])
if _norm != _b8: hit("kt.js differs from b8 beyond the b9 bracket filler", "assets/kt.js", "")
for n in names:
    if n.startswith("data/pred-games") and re.search(r"\[[^\[\]]*,\s*1\]", Z.read(n).decode()): hit("pred-games has a one-book market line", n, "")
g = re.search(r"kicktip_gate", kj3) and re.search(r"12\s*\*\s*3600", kj3) and "sessionStorage" in kj3
if not g: hit("gate storage logic markers missing", "assets/kt.js", "")
print("files", len(names), "html pages", len(pages))
print("sportsbook/bookmaker/betting-site word occurrences (all negated):", mentions["sportsbook(word)"])
print("external link hosts:", {h: len(v) for h, v in hosts.items()})
print("The Odds API links:", len(odds_links))
print("MSM mentions per page: home", msm.get("index.html"), "| others all 1:", all(c == 1 for k, c in msm.items() if k != "index.html"), "| violations:", msm_pages)
# ---- b6 indexing + privacy of contact details (zip level)
H = Z.read("_headers").decode()
if H.count("X-Robots-Tag") != 1 or "/data/*\n  X-Robots-Tag: noindex, nofollow\n" not in H: hit("X-Robots-Tag must appear once, under /data/* only", "_headers", "")
if Z.read("robots.txt").decode() != "User-agent: *\nAllow: /\nDisallow: /data/\nDisallow: /api/\n\nSitemap: " + SITE_URL + "/sitemap.xml\n": hit("robots.txt not the approved indexable form", "robots.txt", "")
_sm = re.findall(r"<loc>([^<]+)</loc>", Z.read("sitemap.xml").decode())
if len(_sm) != 153 or len(set(_sm)) != 153 or any(not u.startswith(SITE_URL + "/") or "/data/" in u or "404" in u for u in _sm): hit("sitemap URL set wrong", "sitemap.xml", str(len(_sm)))
for u in _sm:
    f = u[len(SITE_URL + "/"):] + "index.html" if u.endswith("/") else u[len(SITE_URL + "/"):]
    if f not in names: hit("sitemap URL does not resolve to a page in the zip", u, "")
if re.search(r"go-live|launch|staged|noindex|internal", Z.read("robots.txt").decode() + Z.read("sitemap.xml").decode(), re.I): hit("internal wording in robots/sitemap", "", "")
for n in names:
    if n.endswith((".html", ".js", ".css", ".xml", ".txt", ".json", ".webmanifest")) or n == "_headers":
        t = Z.read(n).decode("utf-8", "replace")
        if re.search(r"mailto:|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}|(?:x|twitter)\.com/|twitter:(?:site|creator)", t, re.I): hit("X handle/link or email address present", n, "")
print("robots.txt:", Z.read("robots.txt").decode().strip().replace("\n", " | "))
for h in hits[:40]: print("HIT", h)
print("TOTAL HITS", len(hits)); sys.exit(1 if hits else 0)
