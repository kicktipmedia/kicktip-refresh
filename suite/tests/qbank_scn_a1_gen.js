/* generates tests/qbank_scn_a1.json (QA bank rows with expected behavior from this build) usage: node tests/qbank_scn_a1_gen.js TREE */
const H = require("./lib/scn_harness.js")(require("path").resolve(process.argv[2])), EX = H.EX;
const Q = [
 // the thread's own questions
 "What if BYU, Utah, and Texas tech all end with just one loss?", "What if BYU, Utah and Texas Tech all end with one loss?", "What if BYU and Texas Tech both end with just one loss?", "what if BYU wins out and Texas Tech loses to Arizona",
 "What if BYU ends with just one loss?", "What if Utah finishes with just one loss?", "What if BYU wins out?", "What if BYU loses out?", "What if BYU ends with 3 losses?", "What if BYU finishes with no losses?", "What if Utah finishes with no losses?",
 // Big 12
 "what if Utah and Texas Tech win out", "what if Arizona State and Houston win out", "what if Texas Tech loses out", "what if Arizona ends with 2 losses", "what if Kansas State wins out",
 // other conferences: settled and tie, in/out on records, branches
 "what if New Mexico State and Western Kentucky win out", "what if Liberty and Jacksonville State win out", "what if Miami (OH) and Toledo win out", "what if Oklahoma State and Utah win out",
 "what if Ohio State and Indiana both win out", "what if Indiana wins out", "what if Ohio State ends with 2 losses", "what if Georgia wins out", "what if Alabama and Ole Miss win out", "what if Vanderbilt wins out", "what if Texas wins out",
 "what if Wake Forest ends with 2 losses", "what if SMU ends with 2 losses", "what if Miami wins out", "what if Duke loses out", "what if Boise State ends with 2 losses", "what if James Madison ends with 2 losses", "what if Tulane wins out", "what if South Florida and Memphis win out", "what if Notre Dame wins out",
 // not a card: one game, two conferences, four teams, clarify, unparsed
 "what if BYU beats Utah", "what if BYU beats Texas Tech and Utah beats Iowa State", "what if BYU wins its next game", "what if Georgia and Ohio State win out", "what if BYU, Utah, Texas Tech and Arizona win out", "what if BYU wins 3 of their remaining 5", "what if BYU and Utah each finish with two losses", "what if BYU ends with 9 losses", "what if the sun explodes"
];
const rows = Q.map((q, i) => { const r = H.run(q); let kind, exp = {};
  if (r.stage === "build" && r.f.ok !== false) { const f = r.f; kind = "card"; exp = { title: EX.title(f), status: f.status, branches: f.branches.length, conference: f.conference.name, lead: EX.lead(f)[0], teams: f.scenario.teams, pair: f.branches.length === 1 ? f.branches[0].pair : undefined, tie_steps: f.branches.map(b => b.tie.length ? b.tie[0].steps.filter(s => s.kind === "decisive").map(s => s.n) : []), if_tied_steps: f.branches.map(b => b.if_tied ? b.if_tied.steps.length : 0) }; }
  else if (r.stage === "build") { kind = "nocard"; exp = { reason: r.f.reason }; }
  else if (r.stage === "resolve") { kind = "clarify"; exp = { reason: r.clarify.reason }; }
  else { kind = "unchanged"; exp = { note: "the standard parser does not read this one; it takes the same path as router2c (AI mode or the not-understood line)" }; }
  return { id: "scn" + String(i + 1).padStart(2, "0"), text: q, kind, expect: exp }; });
require("fs").writeFileSync(require("path").join(__dirname, "qbank_scn_a1.json"), JSON.stringify({ about: "scn_a1 QA bank: question, the kind of answer the home What-If panel gives (card | clarify | nocard | unchanged), and the facts to check on the card. Every row also needs: no /api/ask call, text ASCII, no banned word.", rows }, null, 1) + "\n");
const c = {}; rows.forEach(r => c[r.kind] = (c[r.kind] || 0) + 1); console.log(rows.length + " rows", JSON.stringify(c));
