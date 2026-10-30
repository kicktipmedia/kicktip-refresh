"""Standings and 'paths to the title game' JSON from a simulation result (sim.run())."""
import json, os, numpy as np
import sim, rules
from sim import CONFS, OUT

def write_standings(R, outdir=OUT):
    S = R["S"]; N = R["N"]; stand = {}; paths = {}
    for c in CONFS:
        Rl = rules.RULES[c]; mem = S.members[c]; pos = {t: i for i, t in enumerate(mem)}
        cw = {t: 0 for t in mem}; cl = {t: 0 for t in mem}; h2h = {t: {} for t in mem}
        for g in S.cgames_done[c]:
            w, l = (g["h"], g["a"]) if g["hs"] > g["as_"] else (g["a"], g["h"]); cw[w] += 1; cl[l] += 1
            h2h[w][S.name[l]] = "W"; h2h[l][S.name[w]] = "L"
        rem = {t: [] for t in mem}
        for g in S.cgames_rem[c]:
            rem[g["h"]].append(dict(opp=S.name[g["a"]], site="H" if not g["neutral"] else "N", week=g["week"]))
            rem[g["a"]].append(dict(opp=S.name[g["h"]], site="A" if not g["neutral"] else "N", week=g["week"]))
        rows = []
        for t in mem:
            pc = float(R["ccg_in"][c][:, t].mean()) if Rl["fmt"] != "none" else None
            gp = cw[t] + cl[t]
            rows.append(dict(team=S.name[t], conf_w=cw[t], conf_l=cl[t], conf_pct=round(cw[t] / gp, 3) if gp else None, overall=f"{int(S.w_now[t])}-{int(S.g_now[t] - S.w_now[t])}",
                             conf_remaining=rem[t], head_to_head_so_far=h2h[t], p_ccg=round(pc, 4) if pc is not None else None,
                             p_title=round(float((R["champ"][c] == t).mean()), 4) if pc is not None else None))
        rows.sort(key=lambda r: (-(r["conf_pct"] or 0), -(r["p_ccg"] or 0)))
        stand[c] = dict(conference=Rl["name"], format=Rl["fmt"], title_game=Rl["ccg"], rules_sources=Rl["sources"], flags=Rl["flags"],
                        note="Order = conference win pct, then simulated CCG chance. It is a provisional order, not a tiebreak-applied seeding.", standings=rows)
        if Rl["fmt"] == "none": continue
        for t in mem:
            cwt = R["cwins"][c][:, pos[t]]; inn = R["ccg_in"][c][:, t]
            table = []
            for k in range(int(cwt.min()), int(cwt.max()) + 1):
                msk = cwt == k
                if msk.sum() == 0: continue
                table.append(dict(final_conf_wins=k, share_of_sims=round(float(msk.mean()), 4), p_ccg=round(float(inn[msk].mean()), 3) if msk.sum() >= 30 else None, sims=int(msk.sum())))
            p = float(inn.mean())
            need = next((r["final_conf_wins"] for r in table if r["p_ccg"] is not None and r["p_ccg"] >= 0.5), None)
            maxw = cw[t] + len(rem[t])
            status = "effectively clinched (>=99.95%)" if p >= .9995 else "effectively eliminated (<0.05%)" if p < .0005 else "alive"
            paths[S.name[t]] = dict(conference=Rl["name"], conf_record=f"{cw[t]}-{cl[t]}", remaining=rem[t], best_case_conf_record=f"{maxw}-{cl[t]}",
                                    p_ccg=round(p, 4), status=status, conf_wins_needed_for_even_odds=need, by_final_conf_wins=table,
                                    p_ccg_if_wins_out=next((r["p_ccg"] for r in table if r["final_conf_wins"] == maxw), None))
    json.dump(stand, open(f"{outdir}/standings.json", "w"), indent=1)
    json.dump(dict(label="Simulated paths (MODEL). p_ccg per final conference win total comes from the same simulated seasons; null = fewer than 30 sims.", teams=paths), open(f"{outdir}/paths.json", "w"), indent=1)
    return stand, paths
