"""Demo fixture for the chip (NOT shipped, NOT production data): synthetic previous-day snapshots so the chip, the popover, the no-previous-snapshot and the model-change cases can be seen and tested.
Builds build/site-chipdemo (and build/site-chipdemo-all: chips under all three models) with KT_SNAP_DIR=build/chipdemo-snaps. Per model:
  blend: previous day (Oct 23, 11:30 PM MT), same model version  -> chips (deltas below, edge cases 4.99 / 5.00 / 5.01 in both directions)
  elo:   previous day with a DIFFERENT model version              -> model-change day, no chips at all
  eff:   no snapshot                                              -> no previous snapshot, no chips
The driver game is a REAL finished game from data/store/schedule.json with an invented shard effect (fixture only).
python3 tests/chip_fixture.py   (then the site is in build/site-chipdemo)"""
import os, sys, json, subprocess, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src")
LATEST = sorted(os.listdir(f"{ROOT}/data/store/snapshots/blend"))[-1]   # newest stored snapshot = "current" (gate2 data has 3 for Oct 24)
SNAP = f"{ROOT}/build/chipdemo-snaps"; SITE = f"{ROOT}/build/site-chipdemo"
# team full name -> (current minus previous, in make-12 probability); positive = moved up
DELTAS = {"Utah Utes": 0.12, "BYU Cougars": -0.0900, "Georgia Bulldogs": 0.06, "Alabama Crimson Tide": 0.14, "LSU Tigers": -0.10, "Notre Dame Fighting Irish": 0.07,
          "Houston Cougars": 0.0499,                 # 4.99: NO chip
          "Texas Longhorns": 0.05,                   # 5.00: chip +5
          "Ole Miss Rebels": -0.0501,                # 5.01 down: chip -5
          "Wake Forest Demon Deacons": 0.0501,       # 5.01: chip +5
          "Indiana Hoosiers": -0.0499}               # 4.99 down: NO chip
def game():
    sc = json.load(open(f"{ROOT}/data/store/schedule.json"))
    return next(g for g in sc if g["done"] and g["hs"] != g["as_"] and g["week"] >= 7)
def make(all_models=False):
    """all_models=True: elo and eff get chips too (elo = 1.5x the blend moves, eff = the opposite direction where it fits), to test the chip under all three models."""
    shutil.rmtree(SNAP, ignore_errors=True); g = game(); hn, an = g["hn"], g["an"]
    for mid in ("blend", "elo", "eff"):
        if mid == "eff" and not all_models: continue
        cur = json.load(open(f"{ROOT}/data/store/snapshots/{mid}/{LATEST}"))
        import moves; cur["model_version"] = moves.model_version(mid, cur["seasons"], cur["seed"])   # this tree's sim.py adds model_spread_raw, so its engine hash differs from the stored snapshots; the fixture's "now" snapshot carries the current version
        p = {k: v for k, v in cur["p"].items()}
        if mid == "blend" or all_models:
            for k, d in DELTAS.items():
                d = d * 1.5 if mid == "elo" else -d if mid == "eff" else d
                if 0 <= cur["p"][k] - d <= 1: p[k] = round(cur["p"][k] - d, 4)
        s = dict(cur, as_of="2026-10-23 23:30 MT", p=p, rem={g["id"]: [hn, an]} | cur["rem"], dr={g["id"]: {"h": {"Utah Utes": 80, "Notre Dame Fighting Irish": 40, "Alabama Crimson Tide": 20}, "a": {}}})
        if mid == "elo" and not all_models: s["model_version"] = "mv1-oldversion00"
        os.makedirs(f"{SNAP}/{mid}", exist_ok=True); json.dump(s, open(f"{SNAP}/{mid}/2026-10-23_2330.json", "w"), separators=(",", ":"))
        json.dump(cur, open(f"{SNAP}/{mid}/{LATEST}", "w"), separators=(",", ":"))
    if not all_models:
        import moves; os.makedirs(f"{SNAP}/eff", exist_ok=True); e = json.load(open(f"{ROOT}/data/store/snapshots/eff/{LATEST}")); e["model_version"] = moves.model_version("eff", e["seasons"], e["seed"]); json.dump(e, open(f"{SNAP}/eff/{LATEST}", "w"), separators=(",", ":"))
    return g
def build(all_models=False):
    site = SITE + ("-all" if all_models else ""); g = make(all_models); env = dict(os.environ, KT_SNAP_DIR=SNAP, KT_SITE_DIR=site, OMP_NUM_THREADS="1")
    r = subprocess.run([sys.executable, f"{ROOT}/src/build.py"], env=env, capture_output=True, text=True); print(r.stdout[-400:], r.stderr[-400:]); return g
if __name__ == "__main__": build(); build(True)
