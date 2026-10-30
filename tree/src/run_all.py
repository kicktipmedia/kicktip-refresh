"""One command: refresh ESPN data (cached, fail-soft) -> ratings -> simulate -> write data/out/*.json -> write rules/ccg reference JSON.
Usage: python3 src/run_all.py [--seasons 10000] [--seed 2026] [--no-refresh] [--whatif [--whatif-seasons 6000]] [--whatif-only]
  --whatif       optional extra step: rerun the simulator for every remaining game x 2 outcomes -> data/out/whatif/ (about 4 minutes on 8 cores)
  --whatif-only  skip refresh/simulate/write; rebuild only the browser bundle and the what-if files from the current data (daily reuse after a refresh)
The browser bundle (data/out/web/bundle.json, ~70 KB) is written on every normal run."""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moves, sim, outputs, rules, refresh, export_web, whatif, calibrate, models_registry

ROOT = sim.ROOT

def write_reference():
    rs = {c: dict(conference=r["name"], format=r["fmt"], sources=r["sources"], flags=r["flags"], two_team_steps=r.get("two"), multi_team_steps=r.get("multi"),
                  host_steps=r.get("host"), games_counted_in_standings=("through week %d" % r.get("standings_max_week", 13)))
          for c, r in rules.RULES.items()}
    rs["_cfp"] = dict(rules.CFP)
    rs["_note"] = ("Steps named in *_steps are implemented in src/tiebreak.py. 'rating' stands in for every other-public-rating-system / CFP-rank / computer-composite step "
                   "(not reproducible); it uses the KickTip rating. Every flag is an uncertain or approximated item. Verified against official pages 2026-10-23 (MT).")
    json.dump(rs, open(f"{ROOT}/data/rules_sources.json", "w"), indent=1)
    cc = {c: dict(conference=r["name"], date=r["ccg_date"], slot=r["ccg"], format=r["fmt"], neutral_site=r.get("neutral")) for c, r in rules.RULES.items() if r["fmt"] != "none"}
    json.dump(dict(note="Title game slots as announced by each conference (date, time, TV, site); times shown in ET/CT/PT with the MT conversion.", ccg=cc), open(f"{ROOT}/data/ccg.json", "w"), indent=1)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seasons", type=int, default=10000); ap.add_argument("--seed", type=int, default=2026); ap.add_argument("--no-refresh", action="store_true")
    ap.add_argument("--whatif", action="store_true"); ap.add_argument("--whatif-only", action="store_true"); ap.add_argument("--whatif-all", action="store_true"); ap.add_argument("--whatif-seasons", type=int, default=6000); ap.add_argument("--no-drivers", action="store_true")
    a = ap.parse_args(); t0 = time.time(); times = {}
    if a.whatif_only:
        export_web.build(); whatif.build(a.whatif_seasons, a.seed)
        for mod in models_registry.MODELS[1:]:
            if a.whatif_all: whatif.build(a.whatif_seasons, a.seed, model=mod["id"])
        print("done (whatif only)", round(time.time() - t0, 1), "s"); return
    if not a.no_refresh:
        t = time.time(); refresh.main(); times["refresh_s"] = round(time.time() - t, 1)
    t = time.time(); calibrate.main(); times["calibrate_s"] = round(time.time() - t, 1)      # v6a: refit the three models on the current games (fail-closed stamp), BEFORE any simulation
    t = time.time(); R = sim.run(a.seasons, a.seed); times["simulate_s"] = round(R["runtime"], 1)           # default model = KickTip blend
    sim.write_outputs(R); outputs.write_standings(R); write_reference(); export_web.build(R["S"])
    asof = json.load(open(f"{ROOT}/data/out/sim_teams.json"))["as_of"]; t = time.time()
    for mod in models_registry.MODELS[1:]:                                                                  # alternates: same data, same seed, same as_of -> data/out/m/<id>/, data/out/web/m/<id>/
        R2 = sim.run(a.seasons, a.seed, verbose=False, S=sim.Season(mod["id"])); od = f"{ROOT}/data/out/m/{mod['id']}"
        sim.write_outputs(R2, od, asof=asof); outputs.write_standings(R2, od); export_web.build(R2["S"], f"{ROOT}/data/out/web/m/{mod['id']}")
    times["alt_models_s"] = round(time.time() - t, 1)
    import movers; t = time.time(); movers.main(a.seasons, a.seed); times["movers_s"] = round(time.time() - t, 1)      # internal raw-MSM comparison for the method-page sentence (data/ref/movers.json, not shipped)
    t = time.time(); moves.snapshot_all(with_drivers=not a.no_drivers); times["moves_s"] = round(time.time() - t, 1)      # 'why it moved' chip: today's make-12 per model + driver tables (src/moves.py); needs data/store/snapshots to persist between runs
    if a.whatif:
        t = time.time(); whatif.build(a.whatif_seasons, a.seed); times["whatif_s"] = round(time.time() - t, 1)      # blend shards (default location, format unchanged)
        for mod in models_registry.MODELS[1:]:
            if a.whatif_all: whatif.build(a.whatif_seasons, a.seed, model=mod["id"])      # data/out/whatif-models/<id>/ (elo/eff only with --whatif-all; they are not shipped)
        times["whatif_all_s"] = round(time.time() - t, 1)
    times["total_s"] = round(time.time() - t0, 1)
    json.dump(dict(runtime=times, seasons=a.seasons, seed=a.seed, games_rated=R["S"].m["n_games"], remaining_games=len(R["S"].rem),
                   sigma=R["S"].SIG, hfa=round(R["S"].hfa, 3)), open(f"{ROOT}/data/out/run_meta.json", "w"), indent=1)
    print("done", times)

if __name__ == "__main__": main()
