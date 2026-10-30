"""b7: the hero background in the zip is Creative's file byte-for-byte, and the old circuit art is gone. python3 tests/hero_test.py [zipname]"""
import sys, os, zipfile, hashlib, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Z = zipfile.ZipFile(f"{ROOT}/dist/{sys.argv[1] if len(sys.argv) > 1 else 'kicktip-site-b7.zip'}")
SHA12, SIZE, OLD12 = "37a4b8dff096", 124003, "4d26880410d9"; f = []
b = Z.read("assets/img/hero.jpg"); h = hashlib.sha256(b).hexdigest()
if h[:12] != SHA12: f.append(f"hero.jpg sha-12 {h[:12]} != {SHA12}")
if len(b) != SIZE: f.append(f"hero.jpg size {len(b)} != {SIZE}")
if h[:12] == OLD12: f.append("old circuit art shipped")
imgs = sorted(n for n in Z.namelist() if n.startswith("assets/img/")); 
if imgs != ["assets/img/hero.jpg"]: f.append(f"assets/img has extra files: {imgs}")
if any(n.lower().find("hero") >= 0 and n != "assets/img/hero.jpg" for n in Z.namelist()): f.append("extra hero-named file in zip")
css = Z.read("assets/kt.css").decode(); refs = re.findall(r"url\(img/hero\.jpg\)", css)
if len(refs) != 2: f.append(f"hero.jpg referenced {len(refs)}x in kt.css (expect 2: desktop + 700px rule)")
if "HERO BACKGROUND" not in css: f.append("marker comment missing")
if any("hero.jpg" in Z.read(n).decode("utf8", "ignore") for n in Z.namelist() if n.endswith((".html", ".js", ".xml", ".txt", ".json", ".webmanifest"))): f.append("hero.jpg referenced outside kt.css (HTML/OG/JS)")
print(f"hero_test: {5 - len(f) if len(f) < 5 else 0}/5 groups pass"); [print("FAIL:", x) for x in f]; sys.exit(1 if f else 0)
