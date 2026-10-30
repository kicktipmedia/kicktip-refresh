"""Crops for the phase-2 account surfaces into crops/myteams-*.png at 320/390/430/1280 (HTTPS harness tests/devserver.mjs: mock D1 + mock Google; real Google is never contacted).
python3 tests/crops_myteams_p2.py"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.argv = sys.argv[:1]
__file__ = os.path.join(HERE, "myteams_p2_browser.py")   # helpers (server start, ctl, new_ctx, save_two, sign_in_flow, tx) come from the browser test, up to its run()
exec(open(__file__).read().split("def run(p, w):")[0])
CR = f"{ROOT}/crops"; os.makedirs(CR, exist_ok=True)
def top(pg, name, w): pg.screenshot(path=f"{CR}/myteams-{name}-{w}.png", clip={"x": 0, "y": 0, "width": w, "height": 330 if w < 700 else 200})
def full(pg, name, w): pg.screenshot(path=f"{CR}/myteams-{name}-{w}.png")
try:
    with sync_playwright() as p:
        for w in (320, 390, 430, 1280):
            b = p.chromium.launch(args=["--host-resolver-rules=MAP kicktipmedia.com 127.0.0.1:%d, MAP accounts.google.com 127.0.0.1:%d, MAP * ~NOTFOUND" % (PORT, PORT)])
            # signed out header, sheet default / focus / error / coming soon
            ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(b, w); pg.goto(BASE + "/"); pg.wait_for_selector(".ac-si"); pg.wait_for_selector(".mt-ed"); pg.wait_for_timeout(400)
            top(pg, "header-signedout", w); pg.click(".ac-si"); pg.wait_for_selector(".ac-g"); pg.wait_for_timeout(300)
            pg.evaluate("document.activeElement.blur()"); full(pg, "sheet-default", w)
            pg.keyboard.press("Tab"); pg.keyboard.press("Tab"); pg.keyboard.press("Shift+Tab"); pg.locator(".ac-g").focus(); pg.keyboard.press("Tab"); pg.keyboard.press("Shift+Tab"); full(pg, "sheet-focus", w)
            ctx.close()
            ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(b, w); pg.goto(BASE + "/?signin=error"); pg.wait_for_selector(".ac-err"); pg.wait_for_timeout(300); full(pg, "sheet-error", w); ctx.close()
            ctl("reset"); ctl("config", on="0"); ctx, pg, errs, reqs, st = new_ctx(b, w); pg.goto(BASE + "/"); pg.wait_for_selector(".ac-si"); pg.click(".ac-si"); pg.wait_for_selector(".ac-soon"); pg.wait_for_timeout(300); full(pg, "sheet-soon", w); ctx.close(); ctl("config", on="1")
            # sign in with two device teams -> merge confirm, saved list, header chip, menu, delete confirm
            ctl("reset"); ctx, pg, errs, reqs, st = new_ctx(b, w); pg.goto(BASE + "/"); save_two(pg); pg.wait_for_selector(".mt-c .mt-kv"); pg.wait_for_timeout(600)
            sign_in_flow(pg); pg.wait_for_selector("[data-acct=merge-yes]"); pg.wait_for_timeout(300); full(pg, "merge-confirm", w)
            pg.click("[data-acct=merge-yes]"); pg.wait_for_selector(".ac-chip"); pg.wait_for_timeout(900)
            top(pg, "header-signedin", w); pg.locator("#my-teams").screenshot(path=f"{CR}/myteams-saved-list-{w}.png")
            pg.click(".ac-chip"); pg.wait_for_selector("#ac-menu"); pg.wait_for_timeout(200); full(pg, "account-menu", w); pg.keyboard.press("Escape")
            pg.click(".ac-chip"); pg.click("#ac-menu [data-acct=delete]"); pg.wait_for_selector("[data-acct=delete-yes]"); pg.wait_for_timeout(200); full(pg, "delete-confirm", w); ctx.close()
            b.close()
finally:
    proc.terminate()
print("crops done")
