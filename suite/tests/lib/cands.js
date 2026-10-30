/* debug: list every rule that fires on a phrase (live tools = argv[2] csv). node cands.js <live csv> "question" ... */
const T=require("./tbq.js")(process.env.TREE||"/workspace/kicktip-toolbox8/work/tree");
(async()=>{
 const live=process.argv[2]?process.argv[2].split(","):[]; T.TB.setLive(live);
 const d=await T.data(["sim-bundle"]); const R=T.TB.rulesFor();
 for (const q of process.argv.slice(3)) {
  const page=process.env.PAGE?JSON.parse(process.env.PAGE):{mode:"home"};
  const mc=T.TB.matchContext(q,page,d); const out=[];
  Object.keys(R).forEach(tid=>{const tool=T.TB.get(tid); if(!tool||tool.live===false||(tool.modes&&tool.modes.indexOf(mc.page.mode||"home")<0))return; R[tid].forEach(r=>{let o=null;try{o=r.test(mc.n,mc);}catch(e){o="ERR "+e.message} if(o)out.push(tid+":"+r.id+"@"+r.conf+" "+JSON.stringify(o).slice(0,120));});});
  console.log("Q:",q,"| hint:",T.TB.hint(q),"\n   "+(out.join("\n   ")||"(none)"));
 }})();
