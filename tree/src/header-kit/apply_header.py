#!/usr/bin/env python3
"""Apply the KickTip sticky slim header to ANY built KickTip site tree (a build/site directory or an extracted zip). Idempotent: re-running on an already patched tree gives the same bytes.

  python3 src/header-kit/apply_header.py <site_dir> [--variant p|q] [--dry-run]

ONE-LINE SWITCH between Creative's options: change VARIANT below to "q" (or pass --variant q / set KT_HDR=q). P = 56px row, logo + compact Football | Basketball SOON pill + Menu button (default, Creative's choice). Q = 52px row, shield icon + one scrolling strip.

Files touched in the site tree (nothing else is read-modified or written):
  * every *.html that has <header class="hd">: that header block is replaced (same logo/pill/nav links + a Menu button and panel), and two tags are added to <head> right after the kt.css link: <link rel="stylesheet" href="/assets/hdr.css?v=HASH"> and <script src="/assets/hdr.js?v=HASH"></script>
  * assets/hdr.css and assets/hdr.js are added (copied from this folder)
  Not touched: kt.css, kt.js, chat.js, chat.css, _headers, sitemap.xml, any data/, any other page content. Needs the existing /assets/brand/icon/kicktip-icon-transparent.png (live brand asset) for the 320px shield; no new images.
Nothing here deploys or reads private/ files."""
import os, re, sys, glob, hashlib, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT = os.environ.get("KT_HDR", "p")   # <- the one-line switch: "p" (default) or "q"
ICON = "/assets/brand/icon/kicktip-icon-transparent.png"
HDR_RE = re.compile(r'<header class="hd">.*?</header>', re.S)
LINK_RE = re.compile(r'<link rel="stylesheet" href="/assets/hdr\.css[^"]*">|<script src="/assets/hdr\.js[^"]*"></script>')
KT_RE = re.compile(r'(<link rel="stylesheet" href="/assets/kt\.css[^"]*">)')

def h10(path): return hashlib.sha256(open(path, "rb").read()).hexdigest()[:10]

def build_header(old, banner, variant, has_icon):
    q = variant == "q"
    brand_m = re.search(r'<a class="brand".*?</a>', old, re.S); tog_m = re.search(r'<div class="tog".*?</div>', old, re.S); nav_m = re.search(r'<nav class="nav" aria-label="Main">(.*?)</nav>', old, re.S)
    if not (brand_m and tog_m and nav_m): raise ValueError("header has no brand/tog/nav")
    brand = brand_m.group(0)
    if "<picture>" not in brand and has_icon:   # shield icon at <=359px (P) / <=759px (Q); the wordmark stays the img src
        media = "(max-width:759px)" if q else "(max-width:359px)"
        brand = re.sub(r'(<img [^>]*>)', lambda m: f'<picture><source media="{media}" srcset="{ICON}">{m.group(1)}</picture>', brand, count=1)
    links = re.sub(r'(<a [^>]*>)([^<]+)(</a>)', lambda m: f'{m.group(1)}<span>{m.group(2)}</span>{m.group(3)}', nav_m.group(1))   # label in a span: the current-page underline sits under the word only
    nav = f'<nav class="nav" aria-label="Main">{links}</nav>'
    note = ""
    if banner and not q: note = f'<p class="khn"><b>{banner[0]}</b>{banner[1]} <a href="/disclaimer/">Full disclaimer</a></p>'
    btn = ('<button type="button" class="khb" id="kh-btn" aria-expanded="false" aria-controls="kh-panel">'
           '<svg class="b" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" fill="none"/></svg>'
           '<svg class="x" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M5 5l14 14M19 5L5 19" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" fill="none"/></svg>'
           '<span class="tm">Menu</span><span class="tc">Close</span></button>')
    if q:
        return (f'<header class="hd hd--q"><div class="w khw">{brand}\n<div class="kht" role="group" aria-label="Sport and site sections">{tog_m.group(0)}<div class="khp" id="kh-panel">{nav}</div></div></div></header>')
    return (f'<header class="hd"><div class="w khw">{brand}\n{tog_m.group(0)}{btn}<div class="khp" id="kh-panel">{nav}{note}</div></div><div class="khs" id="kh-scrim" aria-hidden="true"></div></header>')

def apply(site, variant=VARIANT, dry=False):
    site = os.path.abspath(site)
    if variant not in ("p", "q"): raise SystemExit("variant must be p or q")
    if not os.path.isdir(f"{site}/assets"): raise SystemExit(f"{site} does not look like a KickTip site (no assets/)")
    has_icon = os.path.exists(f"{site}{ICON}")
    if not has_icon: print("WARN: " + ICON + " missing: no shield swap at narrow widths")
    css, js = f"{site}/assets/hdr.css", f"{site}/assets/hdr.js"
    tmp = {}
    for n in ("hdr.css", "hdr.js"): tmp[n] = open(f"{HERE}/{n}", "rb").read()
    hv = {n: hashlib.sha256(tmp[n]).hexdigest()[:10] for n in tmp}
    tags = f'<link rel="stylesheet" href="/assets/hdr.css?v={hv["hdr.css"]}"><script src="/assets/hdr.js?v={hv["hdr.js"]}"></script>'
    changed, skipped = [], []
    for f in sorted(glob.glob(f"{site}/**/*.html", recursive=True)):
        s = open(f, encoding="utf-8").read(); rel = os.path.relpath(f, site)
        m = HDR_RE.search(s)
        if not m: skipped.append(rel); continue
        bm = re.search(r'<div class="tb"[^>]*><div class="w"><b>(.*?)</b>(.*?)</div></div>', s, re.S)
        new = build_header(m.group(0), (bm.group(1), bm.group(2)) if bm else None, variant, has_icon)
        t = s[:m.start()] + new + s[m.end():]
        t = LINK_RE.sub("", t)
        if not KT_RE.search(t): skipped.append(rel + " (no kt.css link)"); continue
        t = KT_RE.sub(lambda mm: mm.group(1) + tags, t, count=1)
        if t != s:
            changed.append(rel)
            if not dry: open(f, "w", encoding="utf-8").write(t)
    if not dry:
        for n, p in (("hdr.css", css), ("hdr.js", js)): open(p, "wb").write(tmp[n])
    print(f"header variant {variant.upper()}: {len(changed)} pages changed, {len(skipped)} skipped{' (dry run)' if dry else ''}; assets/hdr.css?v={hv['hdr.css']} assets/hdr.js?v={hv['hdr.js']}")
    for s_ in skipped: print("  skipped:", s_)
    return changed

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("site"); ap.add_argument("--variant", default=VARIANT, choices=("p", "q")); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(); apply(a.site, a.variant, a.dry_run)
