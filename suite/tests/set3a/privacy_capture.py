import time, json
from playwright.sync_api import sync_playwright
U = "https://set3a.kicktip.pages.dev/"; reqs = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 390, "height": 900})
    pg.on("request", lambda r: reqs.append((r.method, r.url, r.post_data or "")))
    pg.goto(U, wait_until="networkidle")
    pg.evaluate("() => ['utah','byu','indiana','notre-dame'].forEach(s => window.KTMyTeams.toggle(s))")
    n0 = len(reqs)
    pg.evaluate("() => document.getElementById('kpill').click()"); time.sleep(2.5); pg.keyboard.press("Escape"); time.sleep(0.5)
    pg.click("[data-mt-digest]"); pg.wait_for_selector(".tbox", timeout=15000); time.sleep(2)
    after = reqs[n0:]
    posts = [r for r in after if r[0] != "GET"]
    leak = [r for r in after if any(s in (r[1] + r[2]) for s in ("utah", "byu", "indiana", "notre-dame"))]
    print("requests after save:", len(after), "non-GET:", json.dumps(posts)); print("requests carrying a saved slug:", leak)
    print("api/ask POSTs:", [r for r in after if "/api/ask" in r[1] and r[0] == "POST"])
    b.close()
