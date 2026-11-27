/* WARN-ONLY (never deploy-blocking): no raw "None", no games-count cell in a row with no rank, and no "(0 FBS games)"
 * in any rendered schedule_strength card or list, and no raw "None" in team_compare cards.
 * schedule_strength: every team (3 views), every conference (both views, both orders), national lists (n 1/10/25).
 * team_compare: every FBS team against the next team by slug, aspects "all" and "schedule".
 * Prints "WARN sos_none: ..." lines and ALWAYS exits 0, even on a crash: a copy issue must never freeze KickTip
 * (RUNBOOK, pre-deploy gate). tools/suite_subset.sh runs it with warn_only, outside SUITE_DONE.
 * usage: node tests/sos_none_warn.js <site tree> */
"use strict";
(async () => {
  const bad = []; let cards = 0, tcCards = 0;
  try {
    const T = require("./lib/tbq.js")(process.argv[2]), B = T.raw("sim-bundle");
    const cardOk = (what, a) => { const errs = (a.card && a.card.errors) || []; if (!a.card || errs.length) { bad.push(what + " card errors " + errs.slice(0, 2).join("; ")); return false; } return true; };
    const chk = (what, a) => {
      if (!a.r.ok) return; cards++;
      if (!cardOk(what, a)) return;
      if (/\bNone\b/.test(a.card.text) || /\bNone\b/.test(a.card.html)) bad.push(what + " shows None");
      (a.r.facts.rows || []).forEach((x, k) => { if (x.rank === null && a.card.parts.some(p => p.where === "row" + k + "c1" && p.val === "games")) bad.push(what + " row " + (x.slug || x.name) + " prints a games count with no rank"); });
      if (a.r.facts.mode === "team" && /\(0 FBS games\)/.test(a.card.text)) bad.push(what + " prints (0 FBS games)");
    };
    const fbs = []; for (let i = 0; i < B.teams.length; i++) if (i !== B.fcs) fbs.push(B.teams[i].g);
    for (const g of fbs) for (const view of ["remaining", "played", "both"]) chk("team " + g + "/" + view, await T.answer("schedule_strength", { team: g, view }));
    for (const c of [...new Set(B.teams.map(t => t.c))]) for (const view of ["remaining", "played"]) for (const order of ["toughest", "easiest"]) chk("conf " + c + "/" + view + "/" + order, await T.answer("schedule_strength", { conference: c, view, order }));
    for (const view of ["remaining", "played"]) for (const order of ["toughest", "easiest"]) for (const n of [1, 10, 25]) chk("national " + view + "/" + order + "/" + n, await T.answer("schedule_strength", { view, order, n }));
    const sl = fbs.slice().sort();
    for (let k = 0; k < sl.length; k++) for (const aspect of ["all", "schedule"]) {
      const what = "team_compare " + sl[k] + "/" + sl[(k + 1) % sl.length] + "/" + aspect, a = await T.answer("team_compare", { teams: [sl[k], sl[(k + 1) % sl.length]], aspect });
      if (!a.r.ok) continue; tcCards++;
      if (!cardOk(what, a)) continue;
      if (/\bNone\b/.test(a.card.text) || /\bNone\b/.test(a.card.html)) bad.push(what + " shows None");
    }
  } catch (e) { bad.push("check crashed: " + (e && e.message || e)); }
  bad.slice(0, 5).forEach(b => console.log("WARN sos_none: " + b));
  console.log("sos_none: " + cards + " SOS cards, " + tcCards + " team_compare cards, " + bad.length + " warnings" + (bad.length ? " (warn-only, does not block publish)" : ""));
  process.exit(0);
})().catch(e => { console.log("WARN sos_none: check crashed: " + (e && e.message || e)); process.exit(0); });
