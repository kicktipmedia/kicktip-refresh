"""Method-page section crops (#models, #accuracy, #changed) of build/site: python3 tests/crops_v6a_method.py [out_dir]"""
import sys, os; sys.path.insert(0, "/workspace/kicktip-v6a/tests"); import serve
from playwright.sync_api import sync_playwright
OUTD = sys.argv[1] if len(sys.argv) > 1 else "crops"
R="/workspace/kicktip-v6a"; srv, BASE = serve.start(f"{R}/build/site")
with sync_playwright() as p:
    b=p.chromium.launch()
    for W,S in ((320,2),(390,2),(1280,1)):
        c=b.new_context(viewport={"width":W,"height":900},device_scale_factor=S); pg=c.new_page(); pg.goto(BASE+"/method/"); pg.wait_for_timeout(700)
        for sid in ("models","accuracy","changed"):
            bb=pg.evaluate("""id=>{const h=document.getElementById(id); let n=h.nextElementSibling; while(n && n.tagName!=='H2') n=n.nextElementSibling; const a=h.getBoundingClientRect().top+scrollY; const z=n? n.getBoundingClientRect().top+scrollY : a+1200; const r=h.getBoundingClientRect(); return [Math.max(0,r.left+scrollX-8), a-8, Math.min(innerWidth, 1100), z-a]}""", sid)
            pg.screenshot(path=f"{R}/{OUTD}/method-{sid}-after-{W}.png", full_page=True, clip={"x":0,"y":bb[1],"width":W,"height":bb[3]})
        c.close()
    b.close()
srv.shutdown()
