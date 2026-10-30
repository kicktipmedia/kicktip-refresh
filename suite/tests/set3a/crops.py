import sys, time
from playwright.sync_api import sync_playwright
U = "https://set3a.kicktip.pages.dev/"; OUT = "/workspace/kicktip-set3a/shots"
def ask(pg, q):
    pg.fill("#kask", q); pg.press("#kask", "Enter")
    pg.wait_for_selector(".tbox", timeout=15000); time.sleep(0.8)
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (390, 1280):
        pg = b.new_page(viewport={"width": w, "height": 900 if w == 390 else 1000}); pg.goto(U, wait_until="networkidle")
        pg.evaluate("""() => { ['utah','byu','indiana','notre-dame'].forEach(s => { try { window.KTMyTeams.toggle(s); } catch (e) {} }); }""")
        print(w, "saved", pg.evaluate("() => window.KTMyTeams.get().teams"))
        pg.evaluate("() => document.getElementById('kpill').click()"); time.sleep(2.5)
        pg.keyboard.press("Escape"); time.sleep(0.5)
        chip = pg.query_selector("[data-mt-digest]"); print(w, "chip", bool(chip))
        if chip:
            pg.evaluate("() => document.getElementById('my-teams').scrollIntoView()"); time.sleep(0.4)
            pg.locator("#my-teams").screenshot(path=f"{OUT}/chip-{w}.png")
            chip.click(); pg.wait_for_selector(".tbox", timeout=15000); time.sleep(0.8)
        else:
            pg.evaluate("() => document.getElementById('kpill').click()"); time.sleep(1); ask(pg, "How are my teams doing?")
        c = pg.query_selector_all(".tbox")[-1]; c.scroll_into_view_if_needed(); c.screenshot(path=f"{OUT}/my_teams-{w}.png"); print(w, "mt:", c.inner_text()[:600].replace("\n", " | "))
        ask(pg, "What are the CFP rankings?")
        c = pg.query_selector_all(".tbox")[-1]; c.scroll_into_view_if_needed(); c.screenshot(path=f"{OUT}/cfp_notyet-{w}.png"); print(w, "cr:", c.inner_text()[:400].replace("\n", " | "))
        pg.close()
    b.close()
