"""make_zip refusal checks: injects a bad file into build/site, expects make_zip to refuse, always cleans up, never leaves a zip."""
import os, sys, subprocess, json, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SITE = f"{ROOT}/build/site"
bk = ""
try:
    c = json.load(open(f"{ROOT}/data/cache/odds_ncaaf.json")); evs = c.get("events", c) if isinstance(c, dict) else c
    bk = evs[0]["bookmakers"][0]["title"]
except Exception: pass
cases = [("private dir", "private/x.txt", b"hello"), ("nested zip", "assets/nested.zip", b"PK"), ("odds_api string", "zz-refuse.txt", b"has odds_api in it")]
if bk: cases.append(("bookmaker name", "zz-refuse.txt", f"bet at {bk}".encode()))
fails = 0
for label, rel, data in cases:
    p = f"{SITE}/{rel}"; os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data)
    try:
        r = subprocess.run([sys.executable, f"{ROOT}/src/make_zip.py", "refusal-test.zip"], capture_output=True, text=True)
        ok = r.returncode != 0 and "refusing" in (r.stdout + r.stderr) and not os.path.exists(f"{ROOT}/dist/refusal-test.zip")
    finally:
        os.remove(p)
        if rel.startswith("private/"): shutil.rmtree(f"{SITE}/private", ignore_errors=True)
    print(("PASS " if ok else "FAIL ") + label); fails += (not ok)
r = subprocess.run([sys.executable, f"{ROOT}/src/make_zip.py", "refusal-test.zip"], capture_output=True, text=True)
print("PASS clean build still zips" if r.returncode == 0 else "FAIL clean build"); os.remove(f"{ROOT}/dist/refusal-test.zip") if os.path.exists(f"{ROOT}/dist/refusal-test.zip") else None
fails += (r.returncode != 0); print("refusal checks:", len(cases) + 1, "fails", fails); sys.exit(1 if fails else 0)
