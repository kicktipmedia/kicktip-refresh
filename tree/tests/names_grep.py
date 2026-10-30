"""Third-party rating-name grep over build/site (every file) and, if given, a zip. python3 tests/names_grep.py [zip]
Names: SP+, SportSource, ESPN SOR, KPI, Connelly, Massey, FPI, FiveThirtyEight. Prints hits per file; exit 1 if any file other than /method/ has a hit."""
import sys, os, re, glob, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
RX = re.compile(r"SP\+|SportSource|ESPN SOR|\bKPI\b|Connelly|Massey|\bFPI\b|FiveThirtyEight", re.I)
hits = {}
BIN = (".png", ".woff2", ".woff", ".jpg", ".jpeg", ".webp", ".ico", ".gif")   # binary assets: random byte matches, not text
def scan(name, data):
    if name.lower().endswith(BIN): return
    t = data.decode("utf8", "ignore"); m = RX.findall(t)
    if m: hits[name] = sorted(set(x.upper() for x in m))
for p in glob.glob(f"{SITE}/**/*", recursive=True):
    if os.path.isfile(p): scan(os.path.relpath(p, SITE), open(p, "rb").read())
if len(sys.argv) > 1:
    z = zipfile.ZipFile(sys.argv[1]); hits_site = dict(hits); hits.clear()
    for n in z.namelist():
        if not n.endswith("/"): scan(n, z.read(n))
bad = {k: v for k, v in hits.items() if not k.startswith("method/")}
print("files with hits:", len(hits)); [print(" ", k, v) for k, v in sorted(hits.items())]
print("NON-METHOD hits:", len(bad)); sys.exit(1 if bad else 0)
