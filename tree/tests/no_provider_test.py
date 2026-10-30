"""No odds-provider name in any shipped file (everything under build/site: html, js, json, css, txt, xml, webmanifest, _headers). Case-insensitive 'odds api' / 'odds-api' / 'odds_api' / 'the-odds'. python3 tests/no_provider_test.py"""
import os, re, sys, glob, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
P = re.compile(r"odds[\s_\-]*api|the-odds", re.I); bad = []; n = 0
for f in glob.glob(f"{SITE}/**/*", recursive=True):
    if os.path.isfile(f) and not f.endswith((".png", ".woff2", ".ico", ".jpg", ".webp")):
        n += 1
        if P.search(open(f, encoding="utf-8", errors="replace").read()): bad.append(f[len(SITE):])
# generated labels: market_label in every pred-games*.json must come from the generator's scrubbed wording; and the generator inputs/outputs under data/out (odds*.json) carry no provider name either
import json
for f in glob.glob(f"{SITE}/data/**/pred-games.json", recursive=True):
    ml = json.load(open(f)).get("market_label", "")
    n += 1
    if P.search(ml) or (ml and not ml.startswith("Market line (public sources, as of ")): bad.append(f[len(SITE):] + " market_label=" + ml)   # odds build: the label is no longer shipped (lines live in pred-lines.json); if present it must stay provider-free
for f in glob.glob(f"{ROOT}/data/out/odds*.json"):
    n += 1
    if P.search(open(f, encoding="utf-8").read()): bad.append("data/out/" + os.path.basename(f))
# explicit /top25/ exceptions: ESPN is credited for poll ranks, and the poll names (AP Top 25, Coaches Poll) appear as plain labels, on /top25/ only (page, its script, its styles, its data file)
POLL = re.compile(r"Coaches|AP Top 25|AP poll|\bAP rank|Poll ranks \(", re.I); TOP25_OK = {"/top25/index.html", "/assets/top25.js", "/assets/top25.css", "/data/polls.json"}
for f in glob.glob(f"{SITE}/**/*", recursive=True):
    if os.path.isfile(f) and f.endswith((".html", ".js", ".css", ".json", ".txt", ".xml")):
        n += 1
        if POLL.search(open(f, encoding="utf-8", errors="replace").read()) and f[len(SITE):] not in TOP25_OK: bad.append(f[len(SITE):] + " (poll name or poll credit outside /top25/)")
# L3: ESPN may be named (it is the source of the market numbers) but no other provider or book name, anywhere shipped
BOOKS = re.compile(r"draftkings|fanduel|betmgm|caesars|bovada|betonline|mybookie|pointsbet|barstool|espn[\s_\-]*bet|betrivers|fanatics|unibet|betus|lowvig|williamhill|wynnbet|superbook|the[\s_\-]odds", re.I)
for f in glob.glob(f"{SITE}/**/*", recursive=True):
    if os.path.isfile(f) and not f.endswith((".png", ".woff2", ".ico", ".jpg", ".webp")):
        m = BOOKS.search(open(f, encoding="utf-8", errors="replace").read())
        if m: bad.append(f[len(SITE):] + ": " + m.group())
print(f"no_provider_test: {n} shipped text files scanned, {len(bad)} with a provider name", bad[:5]); sys.exit(1 if bad else 0)
