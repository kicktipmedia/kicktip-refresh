"""Host-switch test. python3 tests/host_test.py <zipname-in-dist> [--base <path-to-base-zip>]
 1. no old host string (src/site_config.OLD_HOSTS) in ANY shipped file (bytes), except files listed in ALLOWED_OLD_HOST_FILES
 2. every page except 404: canonical and og:url == SITE_URL + its own path (index.html -> dir with trailing slash, others as-is); 404 has neither
 3. og:image / twitter:image absolute on SITE_URL and the file exists in the zip
 4. robots.txt exact form; sitemap = every page except 404, absolute SITE_URL, none under /data/
 5. no robots meta/noindex in any HTML; _headers has exactly one X-Robots-Tag under /data/*
 6. every absolute SITE_URL link in any HTML/XML/JS resolves to a file in the zip; no www.<host> string
 7. with --base: every file identical to base after replacing the old host with SITE_URL (nothing else changed), same file list, _headers/kt.js/kt.css/gate byte-identical
Exit 1 on any failure."""
import sys, os, re, zipfile, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src")
from site_config import SITE_URL, OLD_HOSTS, ALLOWED_OLD_HOST_FILES
args = sys.argv[1:]; base = None
if "--base" in args: i = args.index("--base"); base = args[i + 1]; del args[i:i + 2]
Z = zipfile.ZipFile(f"{ROOT}/dist/{args[0]}" if args and not os.path.isabs(args[0]) else args[0]); names = Z.namelist(); S = set(names)
bad = []; n_ok = 0
def ok(k, c, d=""):
    global n_ok
    if c: n_ok += 1; print("ok  ", k)
    else: bad.append(k); print("FAIL", k, str(d)[:300])
def page_url(n): return SITE_URL + "/" + (n[:-10] if n.endswith("index.html") else n)
def exists_for(url):
    p = url[len(SITE_URL):]
    if p in ("", "/"): return "index.html" in S
    p = p.lstrip("/")
    return p in S or (p.endswith("/") and p + "index.html" in S) or (p + "/index.html" in S)
# 1
old = [(n, h) for n in names for h in OLD_HOSTS if h.encode() in Z.read(n).lower() and n not in ALLOWED_OLD_HOST_FILES]
ok("1 no old-host string in any shipped file (allowed: %s)" % (sorted(ALLOWED_OLD_HOST_FILES) or "none"), not old, old[:5])
# 2,3
htmls = [n for n in names if n.endswith(".html")]; b2 = []; b3 = []
for n in htmls:
    t = Z.read(n).decode("utf-8")
    cans = re.findall(r'<link rel="canonical" href="([^"]*)"', t); ogs = re.findall(r'<meta property="og:url" content="([^"]*)"', t)
    if n == "404.html":
        if cans or ogs: b2.append(n)
    else:
        if cans != [page_url(n)] or ogs != [page_url(n)]: b2.append((n, cans, ogs))
    for pat in (r'<meta property="og:image" content="([^"]*)"', r'<meta name="twitter:image" content="([^"]*)"'):
        v = re.findall(pat, t)
        if len(v) != 1 or not v[0].startswith(SITE_URL + "/assets/") or v[0][len(SITE_URL) + 1:] not in S: b3.append((n, v))
ok(f"2 canonical + og:url == {SITE_URL}+path on {len(htmls) - 1} pages, 404 has neither", not b2, b2[:3])
ok("3 og:image and twitter:image on SITE_URL and file in zip (%d pages)" % len(htmls), not b3, b3[:3])
# 4
ok("4a robots.txt exact", Z.read("robots.txt").decode() == f"User-agent: *\nAllow: /\nDisallow: /data/\nDisallow: /api/\n\nSitemap: {SITE_URL}/sitemap.xml\n", Z.read("robots.txt"))
locs = re.findall(r"<loc>([^<]+)</loc>", Z.read("sitemap.xml").decode())
want = sorted(page_url(n) for n in htmls if n != "404.html")
ok(f"4b sitemap lists exactly the {len(want)} indexable pages on SITE_URL, none under /data/", sorted(locs) == want and not any("/data/" in u for u in locs), (len(locs), len(want)))
# 5
ok("5a no robots meta / noindex in any HTML", not [n for n in htmls if re.search(r'<meta name="robots"|noindex', Z.read(n).decode("utf-8"), re.I)])
H = Z.read("_headers").decode()
ok("5b _headers: one X-Robots-Tag, under /data/*", H.count("X-Robots-Tag") == 1 and "/data/*\n  X-Robots-Tag: noindex, nofollow\n" in H)
# 6
dead = []; www = []
for n in names:
    if n.endswith((".html", ".xml", ".txt", ".js", ".json", ".webmanifest")):
        t = Z.read(n).decode("utf-8", "replace")
        if re.search(r"www\." + re.escape(SITE_URL.split("//")[1]), t): www.append(n)
        for u in set(re.findall(re.escape(SITE_URL) + r"[A-Za-z0-9._~/%-]*", t)):
            if u != SITE_URL and not exists_for(u) and not (n == "_worker.js" and u.startswith(SITE_URL + "/api/")): dead.append((n, u))
        if n == "_worker.js":   # server code: only /api/ URLs are routes, anything else must resolve; the bare-origin constant is fine
            dead = [(m, u) for m, u in dead if not (m == n and u == SITE_URL + ".")]
ok("6a every absolute SITE_URL link resolves to a file in the zip", not dead, dead[:3])
ok("6b no www.<host> string", not www, www[:3])
# 7
if base:
    B = zipfile.ZipFile(base); bn = B.namelist()
    ok("7a same file list as base (%d files)" % len(bn), sorted(bn) == sorted(names), set(bn) ^ set(names))
    changed = []; other = []
    for n in bn:
        if n not in S: continue
        bb = B.read(n); nb = Z.read(n)
        exp = bb
        for h in OLD_HOSTS: exp = exp.replace(b"https://" + h.encode(), SITE_URL.encode())
        if exp != nb: other.append(n)
        if bb != nb: changed.append(n)
    ok("7b every file == base with only the host string swapped (%d files differ from base)" % len(changed), not other, other[:5])
    exempt = [n for n in changed if not n.endswith((".html", ".xml", ".txt"))]
    ok("7c only HTML/sitemap/robots changed; _headers, kt.js, kt.css, lg.js, data/*, images byte-identical", not exempt, exempt[:5])
print(f"{n_ok} ok, {len(bad)} failed"); sys.exit(1 if bad else 0)
