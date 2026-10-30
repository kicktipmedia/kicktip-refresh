const fs=require('fs'),vm=require('vm'),path=require('path');
module.exports=function(tree){
 const load=(f)=>{const c=vm.createContext({window:{},console});vm.runInContext(fs.readFileSync(path.join(tree,f),'utf8'),c);return c;};
 const pc=load('assets/ks/parse.js'); const KP=pc.KTParse||pc.window.KTParse;
 const KS=require(path.resolve(tree,'assets/ks/scenario.js'));
 const KTCcg=require(path.resolve(tree,'assets/ccgsim.js'));
 const EX=fs.existsSync(path.resolve(tree,'assets/ks/explain.js'))?require(path.resolve(tree,'assets/ks/explain.js')):null;
 const B=JSON.parse(fs.readFileSync(path.join(tree,'data/sim-bundle.json')));
 B.teams.forEach(t=>{t.f=t.n;if(t.s)t.n=t.s;});
 const ccg=JSON.parse(fs.readFileSync(path.join(tree,'data/ccg-sim.json'))), rules=JSON.parse(fs.readFileSync(path.join(tree,'data/ccg-rules.json')));
 function run(q,extra){const p=KP.parse(q,B.aliases,{choices:{}});if(p.refusal||p.clarify)return{stage:'parse',p};const res=KS.resolve(p,B);if(!res.ok)return{stage:'resolve',clarify:res.clarify,p};
  const t0=Date.now();const f=EX.build(Object.assign({parsed:p,res,bundle:B,ccg,rules,KTCcg},extra||{}));return{stage:'build',f,ms:Date.now()-t0,p,res};}
 return {KP,KS,KTCcg,EX,B,ccg,rules,run};
};
