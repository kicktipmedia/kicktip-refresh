"""Export the compact data bundle the browser simulator needs: data/out/web/bundle.json (public data only; nothing from private/).
Everything the JS engine (src/web/sim.js) needs to replay src/sim.py: model constants, season-to-date counts, remaining games, per-conference
standings state + tiebreak rule lists, team index/names/aliases. Usage: python3 src/export_web.py   (also run by run_all.py)"""
import json, os, sys, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim, rules, aliases, models_registry as MR

ROOT = sim.ROOT; OUT = f"{ROOT}/data/out/web"
def sim_as_of():
    """same stamp as data/out/sim_teams.json (written by the same run), so the bundle, shards and prediction files always carry one as_of"""
    try: return json.load(open(f"{ROOT}/data/out/sim_teams.json"))["as_of"]
    except Exception: return dt.datetime.now(__import__("zoneinfo").ZoneInfo("America/Denver")).strftime("%Y-%m-%d %H:%M MT")
LIVE_ST = ("STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD", "STATUS_DELAYED", "STATUS_SUSPENDED")   # same list as build.py
def _ref_t():
    """UTC time of the last ESPN refresh (data/out/refresh_log.json), used to flag games that have started but are not final in our data"""
    try:
        t = json.load(open(f"{ROOT}/data/out/refresh_log.json"))["refreshed_mt"].replace(" MT", "")
        return dt.datetime.strptime(t, "%Y-%m-%d %H:%M").replace(tzinfo=__import__("zoneinfo").ZoneInfo("America/Denver")).astimezone(dt.timezone.utc)
    except Exception: return None
def inprog(g, ref):
    """c1: 1 = ESPN shows the game live, 2 = kickoff time has passed at the last refresh but no final score yet, 0 = not started (the site treats 1 and 2 as 'started': no pre-game numbers)"""
    if g.get("status", "") in LIVE_ST: return 1
    d = g["date"]; tba = d[11:] in ("04:00Z", "05:00Z")
    try: u = dt.datetime.strptime(d, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
    except Exception: return 0
    ref = ref or dt.datetime.now(dt.timezone.utc)
    return 2 if (not tba and u <= ref and g.get("status", "") not in ("STATUS_POSTPONED", "STATUS_CANCELED")) else 0
r6 = lambda a: [round(float(x), 6) for x in a]

def build(S=None, outdir=OUT):
    S = S or sim.Season(); m = S.m; n = S.n; os.makedirs(outdir, exist_ok=True)
    names = [S.name.get(t, "FCS opponent") for t in range(n)]
    conf_of = [S.cof.get(t, "fcs") for t in range(n)]
    gidx = {g["id"]: k for k, g in enumerate(S.rem)}
    sch = {g["id"]: g for g in S.sched}
    ref = _ref_t()
    games = [dict(id=g["id"], h=int(g["h"]), a=int(g["a"]), neu=int(g["neutral"]), wk=g["week"], date=g["date"],
                  **({"ip": inprog(g, ref)} if inprog(g, ref) else {}),
                  **({"fcs": (sch[g["id"]]["an"] if g["h"] != S.FCS else sch[g["id"]]["hn"])} if S.FCS in (g["h"], g["a"]) else {})) for g in S.rem]
    confs = []
    for ci, c in enumerate(sim.CONFS):
        R = rules.RULES[c]; mem = S.members[c]; pos = {t: i for i, t in enumerate(mem)}; k = len(mem)
        base = [[0] * k for _ in range(k)]
        for g in S.cgames_done[c]:
            w, l = (g["h"], g["a"]) if g["hs"] > g["as_"] else (g["a"], g["h"]); base[pos[w]][pos[l]] += 1
        e = dict(code=c, name=R["name"], fmt=R["fmt"], ci=ci, members=[int(t) for t in mem], base=base,
                 games=[[gidx[g["id"]], pos[g["h"]], pos[g["a"]]] for g in S.cgames_rem[c]])
        if R["fmt"] != "none":
            e.update(neutral=int(bool(R["neutral"])), two=R["two"], multi=R["multi"], ext=int(bool(R.get("extended_tie_group"))))
            if R["fmt"] == "div":
                dmap = {x: dn for dn, lst in R["divisions"].items() for x in lst}
                dn = sorted(set(dmap.values())); e["div"] = [dn.index(dmap[names[t]]) for t in mem]; e["host"] = R["host"]
        confs.append(e)
    nd = S.ix[S.conf["Notre Dame Fighting Irish"]["id"]]
    played = [[int(g["h"]), int(g["a"]), int(g["hs"]), int(g["as_"]), g["week"]] for g in S.done]     # c1: [home, away, home score, away score, week] so "already played" can show the result
    bundle = dict(
        v=1, label="KickTip simulator bundle (public model data)", as_of=sim_as_of(), model_id=S.model,
        model_label=MR.BY_ID[S.model]["name"] if S.model in MR.BY_ID else str(S.model), model_default=bool(S.model == MR.DEFAULT_ID),     # c1: the chat names the model it used
        n=n, fcs=int(S.FCS), nd=int(nd), teams=[dict(n=names[t], c=conf_of[t]) for t in range(n)],
        model=dict(s=r6(S.s), hfa=float(S.hfa), sigma=float(S.SIG), **({"gs": r6(S.s_g), "ghfa": float(S.hfa_g), "gsigma": float(S.SIG_g)} if S.model else {}), bench=float(S.bench), rating=r6(S.rating), colley=r6(m["colley"]),
                   resume_sd=float(m["resume_sd"]), sor_sd=float(m["sor_sd"]), colley_sd=float(m["colley_sd"]), colley_games=[int(x) for x in S.colley_games]),
        now=dict(w=[int(x) for x in S.w_now], fcsw=[int(x) for x in S.fcsw_now], fbsw=[int(x) for x in S.fbsw_now],
                 gtot=[int(x) for x in (S.g_now + S.g_rem)], fcsg=[int(x) for x in (S.fcsg_now + S.fcsg_rem)], fbsg=[int(x) for x in (S.fbsg_now + S.fbsg_rem)]),
        games=games, confs=confs, played=played, aliases=aliases.build(names, conf_of, S.FCS))
    json.dump(bundle, open(f"{outdir}/bundle.json", "w"), separators=(",", ":"))
    print("bundle: %d KB, %d teams, %d remaining games" % (os.path.getsize(f"{outdir}/bundle.json") / 1024, n - 1, len(games)))
    return bundle

if __name__ == "__main__": build()
