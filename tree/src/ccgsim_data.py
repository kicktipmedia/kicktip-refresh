"""Game data for the official-rules conference title-game simulator -> data/ccg-sim.json (all ten FBS conferences).
Pure results data: conference games that count in the standings (played: w 1 = home won, 0 = away won; remaining: w null), each team's non-conference record, divisions.
No rating, model number or line is in this file. The ESPN-line pre-fill is done in the browser from /data/pred-lines.json (see src/assets/ccgsim-ui.js)."""
import os, sys, json, re, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src")
# ESPN flags these as conference games but the conference's own published schedule says they are not (checked against the conference release; a build-time check below catches any other team that ends up with more conference games than the rules allow).
NOT_CONF = {"401864549": "Mountain West: North Dakota State at San Jose State (Nov 27) is a non-conference game (themw.com 2026 schedule release: 40 conference games, 8 per team; gobison.com 2026 schedule)"}
CODES = ("acc", "big10", "big12", "sec", "American", "usa", "midam", "mwest", "pac12", "belt")

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def make(cmap, sched, cut_weeks=None, divisions=None, asof=""):
    """cmap: team full name -> {conf, loc, id}; sched: data/store/schedule.json list; cut_weeks: {code: last week that counts}; divisions: {code: {div: [full names]}}."""
    cut_weeks = cut_weeks or {}; divisions = divisions or {}
    conf_of = {n: v["conf"] for n, v in cmap.items()}; by_id = {v["id"]: n for n, v in cmap.items()}
    out = {}
    for code in CODES:
        members = sorted((n for n, v in cmap.items() if v["conf"] == code), key=lambda n: cmap[n]["loc"])
        ix = {n: i for i, n in enumerate(members)}
        teams = [dict(i=i, name=n, short=cmap[n]["loc"], slug=slugify(cmap[n]["loc"])) for i, n in enumerate(members)]
        games = []; nc = [dict(w=0, fcsw=0, fcsg=0, g=0, left=0) for _ in members]
        cut = cut_weeks.get(code, 13)
        for g in sched:
            if g.get("status") in ("STATUS_CANCELED",): continue
            h, a = by_id.get(g["home"]), by_id.get(g["away"])
            hin, ain = h in ix, a in ix
            if not (hin or ain): continue
            counts = hin and ain and g["espn_conf"] and g["week"] <= cut and g["id"] not in NOT_CONF
            if counts:
                w = (1 if g["hs"] > g["as_"] else 0) if g["done"] else None
                games.append(dict(id=g["id"], h=ix[h], a=ix[a], w=w, wk=g["week"], date=g["date"], neu=bool(g["neutral"]), k=f"{slugify(cmap[h]['loc'])}~{slugify(cmap[a]['loc'])}"))
            else:
                for t, o, hs, as_ in ((h, a, g["hs"], g["as_"]), (a, h, g["as_"], g["hs"])):
                    if t not in ix: continue
                    r = nc[ix[t]]
                    if g["done"]:
                        r["g"] += 1; fcs = o is None
                        if fcs: r["fcsg"] += 1
                        if hs > as_:
                            r["w"] += 1
                            if fcs: r["fcsw"] += 1
                    else: r["left"] += 1
        games.sort(key=lambda g: (g["date"], g["id"]))
        div = None
        if code in divisions:
            dm = {n: d for d, ns in divisions[code].items() for n in ns}; div = [dm[n] for n in members]
        out[code] = dict(teams=teams, div=div, games=games, nc=nc)
    return dict(asof=asof, confs=out)

def build_data():
    import rules
    cmap = json.load(open(f"{ROOT}/data/ref/conf_2026.json")); sched = json.load(open(f"{ROOT}/data/store/schedule.json"))
    cut = {k: v["standings_max_week"] for k, v in rules.RULES.items() if "standings_max_week" in v}
    divs = {k: v["divisions"] for k, v in rules.RULES.items() if "divisions" in v}
    try: asof = json.load(open(f"{ROOT}/data/out/refresh_log.json"))["refreshed_mt"]
    except Exception: asof = ""
    import ccg_rules; GPT = {k: v["games_per_team"] for k, v in ccg_rules.load().items()}
    d = make(cmap, sched, cut, divs, asof)
    for code, v in d["confs"].items():   # sanity: nobody may have more conference games than the rules' schedule length (ACC's 8-game teams are fewer, which is real)
        cnt = {}
        for g in v["games"]: cnt[g["h"]] = cnt.get(g["h"], 0) + 1; cnt[g["a"]] = cnt.get(g["a"], 0) + 1
        over = [v["teams"][i]["short"] + " " + str(n) for i, n in cnt.items() if n > GPT[code]]
        if over: print(f"WARNING ccg-sim data: {code}: more conference games than games_per_team: {', '.join(over)}; check for a non-conference game ESPN flags as conference (add it to NOT_CONF)")
    return d
def main():
    d = build_data()
    json.dump(d, open(f"{ROOT}/data/ccg-sim.json", "w"), separators=(",", ":"))
    return d
if __name__ == "__main__":
    d = main()
    for c, v in d["confs"].items():
        pl = sum(1 for g in v["games"] if g["w"] is not None); print(c, len(v["teams"]), "teams", len(v["games"]), "games,", pl, "played,", len(v["games"]) - pl, "left")
