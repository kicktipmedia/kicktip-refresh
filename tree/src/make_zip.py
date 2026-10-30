"""Zip build/site/ with python zipfile. Flat archive: files at their site-relative paths, no top folder, NO nested zip.
Usage: python3 src/make_zip.py [name]   -> dist/kicktip-site-b4.zip (default)
Refuses (exit 1) if the zip would contain private/, a nested zip, the Odds API key, the string 'odds_api', or any bookmaker name from the odds cache."""
import os, sys, re, json, zipfile, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = f"{ROOT}/build/site"

def secrets():
    """Strings that must never be shipped. Values are never printed."""
    out = ["odds_api", "private/", "requests_remaining", "requests_used", "free plan"]
    try:
        for line in open(f"{ROOT}/private/odds_api.env"):
            if "=" in line:
                v = line.split("=", 1)[1].strip().strip("'\"")
                if len(v) >= 8: out.append(v)
    except OSError: pass
    try:
        c = json.load(open(f"{ROOT}/data/cache/odds_ncaaf.json"))
        evs = c.get("events", c) if isinstance(c, dict) else c
        for e in evs:
            for bk in e.get("bookmakers", []):
                out += [bk.get("key", ""), bk.get("title", "")]
    except Exception: pass
    return sorted({s for s in out if len(s) >= 4})

def make(name="kicktip-site-b4.zip"):
    os.makedirs(f"{ROOT}/dist", exist_ok=True); out = f"{ROOT}/dist/{name}"
    bad = secrets(); n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _, fs in sorted(os.walk(SITE)):
            for f in sorted(fs):
                p = os.path.join(d, f); rel = os.path.relpath(p, SITE)
                if f.endswith(".zip") or rel.startswith("private") or "/private/" in rel: os.remove(out); raise SystemExit("refusing: " + rel)
                data = open(p, "rb").read()
                low = data.lower()
                for s in bad:
                    if s.lower().encode() in low: os.remove(out); raise SystemExit(f"refusing: forbidden string in {rel} (len {len(s)})")
                zi = zipfile.ZipInfo(rel, (2026, 10, 23, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16
                z.writestr(zi, data); n += 1
    sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
    print(out, os.path.getsize(out), "bytes", n, "files sha256", sha); return out

if __name__ == "__main__": make(sys.argv[1] if len(sys.argv) > 1 else "kicktip-site-b4.zip")
