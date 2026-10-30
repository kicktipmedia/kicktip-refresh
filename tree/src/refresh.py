#!/usr/bin/env python3
"""Phase 0: pull ESPN public JSON once (scoreboard weeks 1-15), cache it, and write the normalized stores.
  data/cache/scoreboard/<year>_wNN.json   raw ESPN scoreboard (completed weeks are never refetched)
  data/store/games_rated.json             completed games with Q3 score + box stats (input to the rating model); grows incrementally
  data/store/schedule.json                every regular-season game (completed + remaining) in a flat normalized form
Usage: python3 src/refresh.py [year]      Fail-soft: any fetch error keeps the cached copy and is logged in data/out/refresh_log.json"""
import json, os, sys, datetime
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import espn
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 2026
CONF = json.load(open(f"{ROOT}/data/ref/conf_2026.json"))
FBS_IDS = {v["id"] for v in CONF.values()}
WEEKS = range(1, 16)

def scoreboard(wk):
    p = f"{ROOT}/data/cache/scoreboard/{YEAR}_w{wk:02d}.json"
    if os.path.exists(p):
        d = json.load(open(p))
        if d.get("events") and all(e["competitions"][0]["status"]["type"]["completed"] for e in d["events"]):
            return d          # whole week final: never refetch
    return espn.fetch(espn.BASE + f"scoreboard?groups=80&week={wk}&year={YEAR}&seasontype=2&limit=400", p, max_age=0)

def norm(e, wk):
    c = e["competitions"][0]
    h = next(x for x in c["competitors"] if x["homeAway"] == "home"); a = next(x for x in c["competitors"] if x["homeAway"] == "away")
    done = c["status"]["type"]["completed"]
    return dict(id=e["id"], week=wk, date=e["date"], home=h["team"]["id"], away=a["team"]["id"], hn=h["team"]["displayName"], an=a["team"]["displayName"],
                hs=int(h["score"]) if done else None, as_=int(a["score"]) if done else None, done=done, neutral=bool(c.get("neutralSite")),
                espn_conf=bool(c.get("conferenceCompetition")), status=c["status"]["type"]["name"],
                live=([int(h["score"] or 0), int(a["score"] or 0)] if c["status"]["type"].get("state") == "in" else None))

def summary(g):
    """Q3 score + box stats for one newly completed game (same fields the MSM pipeline uses)."""
    p = f"{ROOT}/data/cache/summary/{g['id']}.json"
    d = espn.fetch(espn.BASE + f"summary?event={g['id']}", p)
    if d is None: return g
    s = {}
    for t in d.get("boxscore", {}).get("teams", []):
        v = {x["name"]: x["displayValue"] for x in t["statistics"]}
        try: s[t["team"]["id"]] = dict(yds=int(v["totalYards"]), plays=int(v["rushingAttempts"]) + int(v["completionAttempts"].split("/")[1].split("-")[-1]))
        except Exception: pass
    dr = {}
    for x in d.get("drives", {}).get("previous", []):
        tid = x.get("team", {}).get("id"); dr[tid] = dr.get(tid, 0) + 1
    for tid in s: s[tid]["drives"] = dr.get(tid, 0)
    q3 = (0, 0)
    for pl in d.get("scoringPlays", []):
        if pl["period"]["number"] <= 3: q3 = (int(pl["homeScore"]), int(pl["awayScore"]))
    g["box"] = s; g["q3"] = list(q3) if d.get("scoringPlays") is not None else None
    return g

def main():
    os.makedirs(f"{ROOT}/data/out", exist_ok=True)
    t0 = datetime.datetime.now()
    with ThreadPoolExecutor(8) as ex: boards = list(ex.map(scoreboard, WEEKS))
    sched = {}
    for wk, d in zip(WEEKS, boards):
        if not d: continue
        for e in d.get("events", []):
            sched[e["id"]] = norm(e, wk)
    sp = f"{ROOT}/data/store/schedule.json"
    if not sched and os.path.exists(sp): sched = {g["id"]: g for g in json.load(open(sp))}   # fail soft: keep last good
    rated = {g["id"]: g for g in json.load(open(f"{ROOT}/data/store/games_rated.json"))}
    new = [g for g in sched.values() if g["done"] and g["id"] not in rated and (g["home"] in FBS_IDS or g["away"] in FBS_IDS)]
    with ThreadPoolExecutor(8) as ex: new = list(ex.map(summary, new))
    for g in new:
        rated[g["id"]] = dict(id=g["id"], date=g["date"][:10], home=g["home"], away=g["away"], hn=g["hn"], an=g["an"], hs=g["hs"], as_=g["as_"],
                              neutral=g["neutral"], box=g.get("box", {}), q3=g.get("q3"))
    json.dump(sorted(rated.values(), key=lambda g: g["date"]), open(f"{ROOT}/data/store/games_rated.json", "w"))
    json.dump(sorted(sched.values(), key=lambda g: g["date"]), open(sp, "w"))
    now = datetime.datetime.now(__import__('zoneinfo').ZoneInfo('America/Denver'))
    log = dict(refreshed_mt=now.strftime("%Y-%m-%d %H:%M MT"), year=YEAR, schedule_games=len(sched), completed=sum(g["done"] for g in sched.values()),
               new_rated_games=len(new), rated_total=len(rated), errors=espn.LOG, seconds=round((datetime.datetime.now() - t0).total_seconds(), 1))
    json.dump(log, open(f"{ROOT}/data/out/refresh_log.json", "w"), indent=1); print(json.dumps(log, indent=1))
if __name__ == "__main__":
    main()
