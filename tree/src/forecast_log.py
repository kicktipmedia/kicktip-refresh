"""Accuracy logger (ACCURACY-SCOPE MVP part 1; Jared Oct 31 2026). Appends pre-kickoff per-game win chances and KickTip's expected margin
to data/store/forecast_log.jsonl (JSON Lines, append-only, one row per model per game per CHANGE). Internal data: never shipped, never read by build.py.
Run after run_all.py (reads data/out/sim_games.json and data/out/m/<id>/sim_games.json). Fail soft: any error prints a WARNING and exits 0.
Row: {"run_utc","run_mt","as_of","mv","m","id","ko","h","a","p","em"}
  run_utc/run_mt = when this logger ran; as_of = model stamp (MT); mv = model version (moves.model_version); m = model id;
  id = ESPN game id; ko = kickoff UTC; h/a = home/away; p = home win chance; em = expected home margin in points (home minus away; = -model_spread_raw).
Only games not started at the results refresh time (same rule as build.py game_state) and kicking off within HORIZON_D days. Dedup key (m,id): a row is written
only when p, em or ko differ from the last logged row for that key."""
import os, sys, json, datetime as dt
from zoneinfo import ZoneInfo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src")
MT = ZoneInfo("America/Denver"); HORIZON_D = 8
LOG = os.environ.get("KT_FORECAST_LOG") or f"{ROOT}/data/store/forecast_log.jsonl"
LIVE = ("STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD", "STATUS_DELAYED", "STATUS_SUSPENDED", "STATUS_FINAL", "STATUS_POSTPONED", "STATUS_CANCELED")

def _last(path):
    last = {}
    if os.path.exists(path):
        for ln in open(path):
            try: r = json.loads(ln); last[(r["m"], r["id"])] = (r["p"], r["em"], r["ko"])
            except Exception: pass
    return last

def main(now=None):
    import models_registry as MR, moves
    now = now or dt.datetime.now(dt.timezone.utc)
    ref = json.load(open(f"{ROOT}/data/out/refresh_log.json"))["refreshed_mt"]
    ref_t = dt.datetime.strptime(ref.replace(" MT", ""), "%Y-%m-%d %H:%M").replace(tzinfo=MT).astimezone(dt.timezone.utc)
    last = _last(LOG); rows = []
    for m in MR.MODELS:
        d = f"{ROOT}/data/out" if m["default"] else f"{ROOT}/data/out/m/{m['id']}"
        st, sg = json.load(open(f"{d}/sim_teams.json")), json.load(open(f"{d}/sim_games.json"))
        assert sg["model"] == m["id"], f"{d}: model {sg['model']} != {m['id']}"
        mv = moves.model_version(m["id"], st["seasons"], st["seed"])
        for g in sg["games"]:
            if g.get("status") in LIVE or g.get("model_home_win_prob") is None: continue
            ko = dt.datetime.strptime(g["date_utc"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
            tba = g["date_utc"][11:] in ("04:00Z", "05:00Z")
            if (not tba and ko <= ref_t) or ko > ref_t + dt.timedelta(days=HORIZON_D): continue
            raw = g.get("model_spread_raw"); raw = g["model_spread_home"] if raw is None else raw
            p, em = round(float(g["model_home_win_prob"]), 4), round(-float(raw), 2) + 0.0
            if last.get((m["id"], g["id"])) == (p, em, g["date_utc"]): continue
            rows.append(dict(run_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), run_mt=now.astimezone(MT).strftime("%Y-%m-%d %H:%M MT"), as_of=st["as_of"], mv=mv,
                             m=m["id"], id=g["id"], ko=g["date_utc"], h=g["home"], a=g["away"], p=p, em=em))
    if rows:
        if os.path.exists(LOG) and os.path.getsize(LOG) > 0:
            with open(LOG, "rb") as f: f.seek(-1, 2); torn = f.read(1) != b"\n"
            if torn: open(LOG, "a").write("\n")      # a crash left a partial last line: end it so the next row stays parseable (the torn line is kept as is)
        with open(LOG, "a") as f:
            for r in rows: f.write(json.dumps(r, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(f"forecast_log: {len(rows)} new rows ({len(last)} keys before) -> {os.path.relpath(LOG, ROOT)}")
    return len(rows)

if __name__ == "__main__":
    try: main()
    except Exception as e: print(f"WARNING forecast_log failed ({type(e).__name__}: {e}); site refresh continues", file=sys.stderr)
    sys.exit(0)
