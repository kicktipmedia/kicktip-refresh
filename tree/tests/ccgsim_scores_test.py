"""wkfinal1: data/ccg-sim.json carries the final score (hs home, as away) of every played conference game and none on remaining games;
w still says who won (1 home, 0 away) and matches the score. python3 tests/ccgsim_scores_test.py"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src")
import ccgsim_data as c
cmap = {"Home U": {"conf": "big12", "loc": "Home", "id": "1"}, "Away U": {"conf": "big12", "loc": "Away", "id": "2"}}
sched = [dict(id="9", week=11, date="2026-11-14T03:15Z", home="1", away="2", hs=42, as_=32, done=True, neutral=False, espn_conf=True, status="STATUS_FINAL"),
         dict(id="10", week=12, date="2026-11-21T19:00Z", home="2", away="1", hs=0, as_=0, done=False, neutral=False, espn_conf=True, status="STATUS_SCHEDULED")]
g = c.make(cmap, sched)["confs"]["big12"]["games"]; fails = []
p, r = [x for x in g if x["id"] == "9"][0], [x for x in g if x["id"] == "10"][0]
if not (p["hs"] == 42 and p["as"] == 32 and p["w"] == 1): fails.append("played game score/w: %r" % p)
if "hs" in r or "as" in r or r["w"] is not None: fails.append("remaining game must have no score: %r" % r)
print("3 checks, %d failed" % len(fails)); [print("FAIL", f) for f in fails]; sys.exit(1 if fails else 0)
