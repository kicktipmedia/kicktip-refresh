"""p2c crops into crops/ at 320/390/1280: /privacy/ (top, storage table, cookie table), the sticky header with the Sign in control signed out / signed in (bar closed, Menu open, 1280 inline), the sign-in sheet over the header, the account menu, and the My teams page.
HTTPS harness tests/devserver.mjs (mock D1 + mock Google; real Google is never contacted). python3 tests/crops_p2c.py"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.argv = sys.argv[:1]
__file__ = os.path.join(HERE, "myteams_p2_browser.py")
exec(open(__file__).read().split("def run(p, w):")[0])
CR = f"{ROOT}/crops"; os.makedirs(CR, exist_ok=True)
def full(pg, name, w): pg.screenshot(path=f"{CR}/{name}-{w}.png")
def hdr(pg, name, w):
    if w < 760:
        pg.screenshot(path=f"{CR}/header-{name}-closed-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 70})
        pg.click("#kh-btn"); pg.wait_for_selector(".hd--open"); pg.wait_for_timeout(350)
        pg.screenshot(path=f"{CR}/header-{name}-menu-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 470})
        pg.click("#kh-btn"); pg.wait_for_timeout(250)
    else:
        pg.screenshot(path=f"{CR}/header-{name}-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 90})
try:
    with sync_playwright() as p:
        for w in (320, 390, 800, 1280):
            b = p.chromium.launch(args=["--host-resolver-rules=MAP kicktipmedia.com 127.0.0.1:%d, MAP accounts.google.com 127.0.0.1:%d, MAP * ~NOTFOUND" % (PORT, PORT)])
            ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(b, w); pg.goto(BASE + "/privacy/"); pg.wait_for_selector("h1"); pg.wait_for_timeout(400)
            if w != 800:
                pg.screenshot(path=f"{CR}/privacy-top-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 900 if w < 700 else 700})
                for i, nm in enumerate(("storage", "cookie")):   # full-page clip so the sticky bar never covers the table
                    bx = pg.evaluate("(i)=>{const r=document.querySelectorAll('.pvw')[i].getBoundingClientRect();return {x:0,y:r.top+scrollY-34,width:innerWidth,height:r.height+44}}", i)
                    pg.screenshot(path=f"{CR}/privacy-{nm}-table-{w}.png", full_page=True, clip=bx)
                pg.screenshot(path=f"{CR}/privacy-full-{w}.png", full_page=True)
            ctx.close()
            ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(b, w); pg.goto(BASE + "/"); pg.wait_for_selector(".ac-si", state="attached"); pg.wait_for_selector(".mt-ed"); pg.wait_for_timeout(400)
            hdr(pg, "signedout", w)
            if w != 800:
                pg.click(".ac-si"); pg.wait_for_selector(".ac-g"); pg.wait_for_timeout(300); pg.evaluate("document.activeElement.blur()"); full(pg, "sheet-over-header", w)
                pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
                pg.screenshot(path=f"{CR}/myteams-signedout-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 900}) if False else pg.locator("#my-teams").screenshot(path=f"{CR}/myteams-page-signedout-{w}.png")
            ctx.close()
            ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(b, w); pg.goto(BASE + "/"); save_two(pg); pg.wait_for_selector(".mt-c .mt-kv"); pg.wait_for_timeout(500)
            sign_in_flow(pg); pg.wait_for_selector("[data-acct=merge-yes]"); pg.click("[data-acct=merge-yes]"); pg.wait_for_selector(".ac-chip", state="attached"); pg.wait_for_timeout(900)
            hdr(pg, "signedin", w)
            if w != 800:
                pg.locator("#my-teams").screenshot(path=f"{CR}/myteams-page-signedin-{w}.png")
                pg.click(".ac-chip"); pg.wait_for_selector("#ac-menu"); pg.wait_for_timeout(250); full(pg, "account-menu-over-header", w); pg.keyboard.press("Escape")
            ctx.close(); b.close()
finally:
    proc.terminate()
print("crops done")
