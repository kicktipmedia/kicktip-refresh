"""Unit checks for the accuracy logger and the snapshot archive (no network). python3 tests/accuracy_logger_test.py"""
import os, sys, json, tempfile, shutil, datetime as dt, subprocess, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src")
fails = []
def ok(n, c, x=""): print(("PASS " if c else "FAIL ") + n, x); c or fails.append(n)
T = tempfile.mkdtemp()
# 1. snapshot archive: old files are moved byte for byte, never deleted; fresh ones stay; chips glob unchanged
os.environ["KT_SNAP_DIR"] = f"{T}/snapshots"
import moves; moves.SNAPDIR = f"{T}/snapshots"
os.makedirs(f"{T}/snapshots/blend")
now = dt.datetime.now(moves.MT)
def mk(d):
    s = dict(model="blend", as_of=d.strftime("%Y-%m-%d %H:%M MT"), p={"A": 0.5}); f = f"{T}/snapshots/blend/{d.strftime('%Y-%m-%d_%H%M')}.json"
    json.dump(s, open(f, "w")); return f, hashlib.sha256(open(f, "rb").read()).hexdigest()
old, h_old = mk(now - dt.timedelta(days=40)); new, _ = mk(now - dt.timedelta(days=1))
moves._archive_old("blend")
a = f"{T}/snapshots-archive/blend/{os.path.basename(old)}"
ok("old snapshot moved to archive", os.path.exists(a) and not os.path.exists(old))
ok("archived bytes identical", os.path.exists(a) and hashlib.sha256(open(a, "rb").read()).hexdigest() == h_old)
ok("recent snapshot untouched", os.path.exists(new))
ok("chip glob sees only live dir", [f for _, f, _ in moves._files("blend")] == [new])
old2, _ = mk(now - dt.timedelta(days=40)); shutil.copy(old2, old2 + ".x"); moves._archive_old("blend")
ok("name clash: nothing deleted", os.path.exists(old2) and os.path.exists(a))
# 2. forecast logger with a synthetic data/out (run in a copy of src so ROOT points at the temp tree)
R = f"{T}/tree"; shutil.copytree(f"{ROOT}/src", f"{R}/src", ignore=shutil.ignore_patterns("__pycache__")); shutil.copytree(f"{ROOT}/data/ref", f"{R}/data/ref")
import models_registry as MR
ref = dt.datetime(2026, 10, 31, 9, 0, tzinfo=moves.MT); os.makedirs(f"{R}/data/out", exist_ok=True); os.makedirs(f"{R}/data/store", exist_ok=True)
json.dump(dict(refreshed_mt="2026-10-31 09:00 MT", errors=[]), open(f"{R}/data/out/refresh_log.json", "w"))
def games(p):
    return [dict(id="1", status="STATUS_SCHEDULED", date_utc="2026-10-31T22:00Z", home="H", away="A", model_home_win_prob=p, model_spread_home=-3.0, model_spread_raw=-3.2),
            dict(id="2", status="STATUS_IN_PROGRESS", date_utc="2026-10-31T16:00Z", home="X", away="Y", model_home_win_prob=0.6, model_spread_home=-2.0, model_spread_raw=-2.1),
            dict(id="3", status="STATUS_SCHEDULED", date_utc="2026-10-31T14:00Z", home="X", away="Z", model_home_win_prob=0.6, model_spread_home=-2.0, model_spread_raw=-2.1),
            dict(id="4", status="STATUS_SCHEDULED", date_utc="2026-11-21T20:00Z", home="X", away="W", model_home_win_prob=0.6, model_spread_home=-2.0, model_spread_raw=-2.1),
            dict(id="5", status="STATUS_FINAL", date_utc="2026-10-30T20:00Z", home="X", away="V", model_home_win_prob=0.6, model_spread_home=-2.0, model_spread_raw=-2.1)]
def write(p):
    for m in MR.MODELS:
        d = f"{R}/data/out" if m["default"] else f"{R}/data/out/m/{m['id']}"; os.makedirs(d, exist_ok=True)
        json.dump(dict(model=m["id"], as_of="2026-10-31 09:00 MT", seasons=10000, seed=2026, teams=[]), open(f"{d}/sim_teams.json", "w"))
        json.dump(dict(model=m["id"], games=games(p)), open(f"{d}/sim_games.json", "w"))
run = lambda: subprocess.run([sys.executable, f"{R}/src/forecast_log.py"], capture_output=True, text=True, env={**os.environ, "KT_FORECAST_LOG": ""})
LOG = f"{R}/data/store/forecast_log.jsonl"
write(0.61); r1 = run(); rows = [json.loads(l) for l in open(LOG)]
ok("rows only for unstarted games in horizon", sorted({r["id"] for r in rows}) == ["1"] and len(rows) == len(MR.MODELS), r1.stdout + r1.stderr)
r = rows[0]; ok("row fields", set(r) == {"run_utc", "run_mt", "as_of", "mv", "m", "id", "ko", "h", "a", "p", "em"} and r["em"] == 3.2 and r["p"] == 0.61 and r["run_mt"].endswith(" MT") and r["run_utc"].endswith("Z"), str(r))
run(); ok("dedup: unchanged forecast adds no row", len(open(LOG).read().splitlines()) == len(MR.MODELS))
write(0.64); run(); ok("changed forecast appends one row per model", len(open(LOG).read().splitlines()) == 2 * len(MR.MODELS))
before = open(LOG).read(); write(0.70); os.remove(f"{R}/data/out/refresh_log.json"); r4 = run()
ok("failure is fail-soft (exit 0, WARNING, log untouched)", r4.returncode == 0 and "WARNING" in r4.stderr and open(LOG).read() == before, r4.stderr)
shutil.rmtree(T); print("ACC_DONE fail=%d" % len(fails)); sys.exit(1 if fails else 0)
