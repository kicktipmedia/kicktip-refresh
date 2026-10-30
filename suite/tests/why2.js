// why2: Who to root for Why? generator (assets/pk.js KTWhy). usage: node tests/why2.js TREE
const fs=require('fs'),R=process.argv[2];let n=0,f=0;const chk=(m,ok,d)=>{n++;if(!ok){f++;console.log('FAIL',m,d===undefined?'':JSON.stringify(d).slice(0,300))}};
const src=fs.readFileSync(R+'/assets/pk.js','utf8');const i=src.indexOf('  var KTWhy = (function'),j=src.indexOf('  /* why2 end */');chk('generator block present',i>0&&j>i);
const KTWhy=new Function(src.slice(i,j)+';return KTWhy;')();
const J=x=>JSON.parse(fs.readFileSync(R+'/data/'+x,'utf8'));const P=J('pred-teams.json'),TD=J('tile-data.json'),B=J('sim-bundle.json');const T=P.teams,F=P.field,G=KTWhy.pairs(B),NS={};for(const k in T)NS[T[k].n]=k;
const pos=s=>F.findIndex(x=>x[0]===s)+1;
const BAN=/\b(bet|bets|betting|wager\w*|spreads?|parlays?|pick\w*|CCG|title game)\b|\bthe 12\b(?!-team)|\(model\)|\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun(?! Belt))\b|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d|\d{4}-\d\d/;
const seen=new Set();let rows=0;
for(const s in TD.teams){const td=TD.teams[s];if(!T[s])continue;const ccgm=td.m==='ccg';(td.r||[]).forEach(r=>{rows++;const o={s,a:NS[r.a]||null,x:NS[r.x]||null,an:r.a,xn:r.x,own:r.o===1,T,F,G,ccgm};const w=KTWhy.why(o);seen.add(w.replace(/[A-Z][\w.&' -]*/g,'N'));
 const tag=s+': '+r.a+' over '+r.x;
 chk(tag+' resolves names',!!o.x&&!!o.a,[r.a,r.x]);
 chk(tag+' text, 1-2 sentences',typeof w==='string'&&w.length>10&&w.length<=280&&(w.replace(/No\. /g,'No ').match(/[.!?](\s|$)/g)||[]).length<=2,w);
 chk(tag+' copy rules',!BAN.test(w),w);
 chk(tag+' no boilerplate',!/simulated seasons|That gap is/.test(w),w);
 chk(tag+' no bad article',!/\ban [BCDGJKPQTVWYZ][a-z]|\ba [AEIO][a-z]|\ban U[A-Z]|\ba (LSU|SMU|FIU|FAU|NC State)\b/.test(w),w);
 const mr=w.match(/is an? ([\w &.-]+?) rival/);if(mr)chk(tag+' rival claim matches data',T[o.x].cs===T[s].cs&&T[s].cn===mr[1],[mr[1],T[o.x].cs,T[s].cs]);else chk(tag+' rival not missed',r.o===1||!(T[o.x].cs===T[s].cs&&T[s].cs!=='independents'),w);
 for(const m of w.matchAll(/(\b[\w.&' ]+?) is No\. (\d+) in KickTip\u2019s projected 12-team field/g)){chk(tag+' field position claim',pos(NS[m[1].trim()]||o.x)===+m[2],[m[1],m[2]])}
 const ms=w.match(/\(([\w.&' ]+) is No\. (\d+)\)/);if(ms)chk(tag+' own field position',pos(s)===+ms[2],ms);
 const mp=w.match(/played (.+?) this season/);if(mp)chk(tag+' past-opponent claim',(G[s]||[]).includes(o.a),mp[1]);
 const mk=w.match(/is No\. (\d+) by playoff chances, just outside/);if(mk){let rk=1;for(const k in T)if(T[k].p>T[o.x].p)rk++;chk(tag+' rank claim',rk===+mk[1]&&!pos(o.x),[rk,mk[1]])}
 if(r.o===1)chk(tag+' own game says so',/own game/.test(w),w);
});}
chk('rows covered',rows>100,rows);chk('reasons vary (not one sentence for every row)',seen.size>=5,seen.size);
const fb=KTWhy.why({s:'byu',a:null,x:null,an:'Aa',xn:'Zed',own:false,T:{byu:T.byu,zz:{n:'Zed',cs:'x',p:0}},F:[],G:{},ccgm:false});chk('fallback line',fb==='Small ripple effect: a Zed loss slightly opens the at-large pool.',fb);
const ar=KTWhy.why({s:'byu',a:null,x:null,an:'Aa',xn:'UCLA',own:false,T:{byu:T.byu,zz:{n:'UCLA',cs:'x',p:0}},F:[],G:{},ccgm:false});chk('article: a UCLA',/a UCLA loss/.test(ar),ar);
console.log(n+' checks, '+f+' failed');process.exit(f?1:0);
