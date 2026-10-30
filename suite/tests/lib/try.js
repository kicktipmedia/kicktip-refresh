const T=require("./tbq.js")(process.env.TREE||"/workspace/kicktip-toolbox8/work/tree");
(async()=>{
 const live=process.argv[2]?process.argv[2].split(","):[];
 T.TB.setLive(live);
 for (const q of process.argv.slice(3)) {
  const m=await T.match(q); console.log("Q:",q,"=>",m?JSON.stringify(m):null);
  if(m&&m.tool&&!m.clarify){ const a=await T.answer(m.tool,m.params); console.log("   ",a.card?(a.card.errors.length?"ERR "+a.card.errors.join("|"):a.card.text):JSON.stringify(a.r)); }
 }
})();
