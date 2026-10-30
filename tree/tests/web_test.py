"""Scenario-chat engine tests (Node >= 18; no network, no browser).
  python3 tests/web_test.py            run parse_test.js + parity_test.js against the current data/out files
  python3 tests/web_test.py --rebuild  FIRST re-export data/out/web/bundle.json and rebuild data/out/whatif/ (about 4 min, 8 cores), then run both.
Use --rebuild after any change to src/cfp.py, src/sim.py or src/tiebreak.py (the what-ifs and the Python reference come from them)."""
import subprocess, sys, os
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here); rc = 0
if "--rebuild" in sys.argv:
    r = subprocess.run([sys.executable, os.path.join(root, "src", "run_all.py"), "--whatif-only"]); rc |= r.returncode
    if r.returncode: print("rebuild failed"); sys.exit(1)
for t in ("parse_test.js", "parity_test.js"):
    r = subprocess.run(["node", os.path.join(here, "web", t)], capture_output=True, text=True)
    lines = r.stdout.strip().splitlines(); print(t, "->", lines[-1] if lines else "(no output)")
    if r.returncode: rc = 1; print("\n".join(l for l in r.stdout.splitlines() if l.startswith("FAIL"))[:3000], r.stderr[-1000:])
sys.exit(rc)
