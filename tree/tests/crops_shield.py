"""Shield spinner crops -> crops/shield-*.png and looping gifs crops/shield-*.gif. python3 tests/crops_shield.py
The sim data request is held (never answered) so the 'loading' running state stays on screen; animations are frozen at chosen times with the Web Animations API (document.getAnimations)."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/crops"; os.makedirs(OUT, exist_ok=True)
srv, BASE = serve.start()
FREEZE = "t => document.getAnimations().forEach(a => { a.pause(); a.currentTime = t; })"
def open_panel(b, w, path, reduced=False, hold=True, dsf=1):
    ctx = b.new_context(viewport={"width": w, "height": 900 if w > 700 else 820}, reduced_motion="reduce" if reduced else "no-preference", device_scale_factor=dsf); pg = ctx.new_page()
    held = []
    if hold: pg.route("**/data/sim-bundle.json", lambda r: held.append(r))
    pg.goto(BASE + path); pg.wait_for_selector("#kpill:not([hidden])"); pg.click("#kpill"); pg.wait_for_selector("#kask"); pg.wait_for_timeout(300)
    return ctx, pg, held
with sync_playwright() as p:
    b = p.chromium.launch(); frames_btn = []; frames_card = []; frames_both = []
    for w in (320, 390, 430, 1280):
        ctx, pg, held = open_panel(b, w, "/playoff/")
        pg.fill("#kask", "What if BYU loses?")
        pg.locator(".cmp").screenshot(path=f"{OUT}/shield-idle-{w}.png")
        pg.click("#kform .snd"); pg.wait_for_selector(".spin"); pg.wait_for_timeout(150)
        for name, t in (("a-trace-mid", 400), ("b-closed-hold", 950), ("c-untrace", 1500)):
            pg.evaluate(FREEZE, t)
            pg.locator(".cmp").screenshot(path=f"{OUT}/shield-running-{name}-{w}.png")
            pg.locator("#kbd .ac").screenshot(path=f"{OUT}/shield-card-{name}-{w}.png")
        pg.screenshot(path=f"{OUT}/shield-panel-running-{w}.png")
        ctx.close()
        ctx, pg, held = open_panel(b, w, "/playoff/", reduced=True)
        pg.fill("#kask", "What if BYU loses?"); pg.click("#kform .snd"); pg.wait_for_selector(".spin"); pg.wait_for_timeout(300)
        pg.locator(".cmp").screenshot(path=f"{OUT}/shield-reduced-button-{w}.png"); pg.locator("#kbd .ac").screenshot(path=f"{OUT}/shield-reduced-card-{w}.png")
        ctx.close()
    # the Top 25 page too (same shared asset)
    ctx, pg, held = open_panel(b, 390, "/top25/"); pg.fill("#kask", "What if BYU loses?"); pg.click("#kform .snd"); pg.wait_for_selector(".spin"); pg.wait_for_timeout(150)
    pg.evaluate(FREEZE, 950); pg.screenshot(path=f"{OUT}/shield-top25-running-390.png"); ctx.close()
    # real running view (progress bar) frozen
    ctx, pg, held = open_panel(b, 390, "/playoff/", hold=False); pg.fill("#kask", "What if BYU loses?"); pg.click("#kform .snd"); pg.wait_for_selector(".prog"); pg.evaluate(FREEZE, 950)
    pg.locator(".cmp").screenshot(path=f"{OUT}/shield-simview-button-390.png"); pg.locator("#kbd .ac").screenshot(path=f"{OUT}/shield-simview-card-390.png"); ctx.close()
    # gifs: 2x, 30 frames over one 1.8s cycle
    ctx, pg, held = open_panel(b, 390, "/playoff/", dsf=2); pg.fill("#kask", "What if BYU loses?"); pg.click("#kform .snd"); pg.wait_for_selector(".spin"); pg.wait_for_timeout(150)
    bb = pg.locator("#kform .snd").bounding_box(); cb = pg.locator(".spin").bounding_box()
    for i in range(30):
        pg.evaluate(FREEZE, i * 60)
        frames_btn.append(Image.open(io.BytesIO(pg.screenshot(clip={"x": bb["x"] - 6, "y": bb["y"] - 6, "width": bb["width"] + 12, "height": bb["height"] + 12}))).convert("RGB"))
        frames_card.append(Image.open(io.BytesIO(pg.screenshot(clip=cb))).convert("RGB"))
    ctx.close(); b.close()
for name, fr in (("button", frames_btn), ("card", frames_card)):
    fr[0].save(f"{OUT}/shield-{name}-loop.gif", save_all=True, append_images=fr[1:], duration=60, loop=0, optimize=False)
print(sorted(f for f in os.listdir(OUT) if f.startswith("shield")))
