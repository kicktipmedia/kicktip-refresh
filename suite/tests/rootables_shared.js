// rootables-shared: gen_rootables + bake (DEF13) checks. usage: node rootables_shared.js <site>
'use strict';
const fs=require('fs'),path=require('path'),os=require('os'),cp=require('child_process');
const S=path.resolve(process.argv[2]),TOOLS=path.resolve(__dirname,'../../tree/tools');let n=0,f=0;
const ok=(c,m)=>{n++;if(!c){f++;console.log('FAIL',m);}};
const run=(a)=>cp.spawnSync('node',a,{encoding:'utf8'});
// gen_rootables: shared files are current, schema complete
let r=run([TOOLS+'/gen_rootables.js',S,'--check']);ok(r.status===0,'gen_rootables --check '+r.stderr+r.stdout);
const dir=S+'/data/rootables',files=fs.readdirSync(dir).filter(x=>x.endsWith('.json'));ok(files.length>=130,'>=130 shared files');
const TOP=['v','as_of','seasons','slug','team','conf','n_big','n_window','n_hidden','has_own','rows'],ROW=['id','k','t','race','g','pts','root','other','pP','pC'];
for(const x of files){const d=JSON.parse(fs.readFileSync(dir+'/'+x));ok(TOP.every(k=>k in d),'top keys '+x);ok(d.slug+'.json'===x,'slug '+x);
 ok(d.rows.length<=8,'cap 8 '+x);d.rows.forEach((w,i)=>{ok(ROW.every(k=>k in w),'row keys '+x);ok(w.root.n!==d.team&&w.other.n!==d.team,'own game excluded '+x);
  if(i)ok(Math.abs(d.rows[i-1].pts)>=Math.abs(w.pts)-1e-9,'sorted '+x);});}
// bake: current, exact unbake, idempotent (on a temp copy)
r=run([TOOLS+'/bake_static.js',S,'--verify']);ok(r.status===0,'bake --verify '+r.stderr);
const T=fs.mkdtempSync(path.join(process.env.TMPDIR||os.tmpdir(),'rbs-'));cp.execSync(`cp -r "${S}/." "${T}"`);
r=run([TOOLS+'/bake_static.js',T,'--check']);ok(r.status===0,'bake --check '+r.stderr);
const tp=fs.readdirSync(T+'/team').filter(s=>fs.existsSync(`${T}/team/${s}/index.html`));
const snap=tp.map(s=>fs.readFileSync(`${T}/team/${s}/index.html`,'utf8'));
run([TOOLS+'/bake_static.js',T]);ok(tp.every((s,i)=>fs.readFileSync(`${T}/team/${s}/index.html`,'utf8')===snap[i]),'bake idempotent');
r=run([TOOLS+'/bake_static.js',T,'--unbake']);ok(r.status===0,'unbake');
const DEF13='<div class="rn rtg rb-terms">Information only. Don&#39;t make decisions based on this material. <a href="/disclaimer/">Full terms</a></div><noscript><p class="rb-msg">Turn on JavaScript to see Rootables.</p></noscript>';
tp.forEach((s,i)=>{const u=fs.readFileSync(`${T}/team/${s}/index.html`,'utf8'),b=snap[i];
 ok(u.split(DEF13).length===2,'unbaked DEF13 once '+s);ok(!/<!--bk:/.test(u),'no markers after unbake '+s);
 ok((b.match(/<!--bk:13-->/g)||[]).length===1,'one bk:13 '+s);ok((b.match(/rb-terms/g)||[]).length===1,'one terms line '+s);
 ok(!/data-run/.test(b),'no Run tap '+s);ok(!/not a betting site/.test(b.split('<!--bk:13-->')[1].split('<!--/bk-->')[0]),'no extra betting line in Rootables '+s);
 ok(!/[\u00A0]/.test(b.split('<!--bk:13-->')[1].split('<!--/bk-->')[0]),'no literal nbsp '+s);
 const ent=(b.split('<!--bk:13-->')[1].split('<!--/bk-->')[0].match(/&[a-z#0-9]+;/gi)||[]).every(e=>/^&(amp|lt|gt|quot|nbsp|ndash|rsquo|#39|#\d+);$/i.test(e));ok(ent,'entities valid '+s);});
tp.forEach((s,i)=>{const d=JSON.parse(fs.readFileSync(`${S}/data/rootables/${s}.json`));const b=snap[i].split('<!--bk:13-->')[1].split('<!--/bk-->')[0];const nw=d.rows.filter(r=>r.why).length;ok((b.match(/<p class="rv-why"><strong>Why:<\/strong> /g)||[]).length===nw,'one why line per game with a why '+s);ok(!/\u2011/.test(b),'no literal U+2011 '+s);});
r=run([TOOLS+'/bake_static.js',T]);
ok(tp.every((s,i)=>fs.readFileSync(`${T}/team/${s}/index.html`,'utf8')===snap[i]),'unbake->bake round-trip byte-exact');
fs.rmSync(T,{recursive:true,force:true});
console.log(`${n} checks, ${f} failed`);process.exit(f?1:0);
