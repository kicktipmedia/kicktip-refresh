"""b6 crops -> crops-b6/: runs crops_b5 (pages, gate, logo placements, credit, fallback) then adds header, footer lockup, favicon/touch/OG, logos-in-use sample."""
import sys, os, re, subprocess, shutil, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import serve
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops-b6"; SITE = f"{ROOT}/build/site"
VER = "gate1"   # the acceptance gate is retired; kept so older call sites still resolve
ACC = "0;"   # nothing to accept any more (gate retired)
if not os.environ.get("SKIP5"): subprocess.run([sys.executable, f"{ROOT}/tests/crops_b5.py", "crops-b6"], check=True, stdout=subprocess.DEVNULL)
srv, BASE = serve.start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, s in ((1280, 1), (390, 2)):
        for name, path in (("home", "/"), ("team-utah", "/team/utah/"), ("conference-big12", "/conference/big-12/")):
            ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=s); ctx.add_init_script(ACC); pg = ctx.new_page(); pg.goto(BASE + path); pg.wait_for_timeout(500)
            pg.locator("header.hd").screenshot(path=f"{OUT}/header-{name}-{w}@{s}x.png")
            pg.locator("footer.ft").scroll_into_view_if_needed(); pg.wait_for_timeout(300); pg.locator("footer.ft").screenshot(path=f"{OUT}/footer-lockup-{name}-{w}@{s}x.png"); ctx.close()
    b.close()
# brand files as shipped (byte copies for the OG; sheet for favicon/touch)
shutil.copyfile(f"{SITE}/assets/brand/social/kicktip-og-1200x630.png", f"{OUT}/og-image-as-shipped.png")
sheet = Image.new("RGB", (620, 260), (241, 243, 244)); d = ImageDraw.Draw(sheet); x = 10
for lab, f in (("favicon 16", "kicktip-icon-16.png"), ("32 (lead)", "kicktip-icon-32.png"), ("48", "kicktip-icon-48.png"), ("64", "kicktip-icon-64.png"), ("touch 180", "kicktip-apple-touch-180.png")):
    im = Image.open(f"{SITE}/assets/brand/icon/{f}").convert("RGBA"); sheet.paste(im, (x, 40), im); d.text((x, 10), lab, fill=(18, 21, 25)); x += im.width + 18
ic = Image.open(f"{SITE}/favicon.ico"); d.text((10, 230), f"/favicon.ico sizes: {sorted(ic.info.get('sizes', []))}", fill=(18, 21, 25)); sheet.save(f"{OUT}/favicon-touch-sheet.png")
# logos-in-use sample: real tiles from the build with names beside them
from html import unescape
rows = [("utah", "Utah"), ("alabama", "Alabama"), ("army", "Army"), ("vanderbilt", "Vanderbilt"), ("wake-forest", "Wake Forest"), ("tcu", "TCU")]
ctx_html = '<!doctype html><link rel="stylesheet" href="/assets/kt.css"><body style="background:#fff;padding:16px"><div style="display:grid;grid-template-columns:repeat(3,230px);gap:12px">'
import glob
tiles = []
for slug, nm in rows:
    t = open(f"{SITE}/team/{slug}/index.html", encoding="utf-8").read(); m = re.search(r'<span class="lg s80".*?</span>', t, re.S)
    if m: tiles.append(m.group(0).replace('s80', 's48'))
    else: tiles.append("")
ctx_html += "".join(f'<div style="display:flex;align-items:center;gap:10px">{tl}<b>{nm}</b></div>' for tl, (_, nm) in zip(tiles, rows)) + '</div><p class="cred">Team, conference and league logos courtesy of ESPN</p></body>'
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 760, "height": 260}, device_scale_factor=2); pg.route("**/_sample/x.html", lambda r: r.fulfill(status=200, content_type="text/html", body=ctx_html)); pg.goto(BASE + "/_sample/x.html"); pg.wait_for_timeout(500); pg.screenshot(path=f"{OUT}/logos-in-use-sample.png"); b.close()
print(len(os.listdir(OUT)))
