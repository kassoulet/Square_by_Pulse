// UI smoke test (headless Chrome, CDP): play / pause / seek of web/index.html.  Exit code 1 on failure.  Adapted from ../../pls_amb/tools/uitest.mjs.
import {spawn} from 'child_process';import fs from 'fs';import http from 'http';import path from 'path';import {fileURLToPath} from 'url';
const root=path.join(path.dirname(fileURLToPath(import.meta.url)),'../web');
const T={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.gz':'application/gzip','.json':'application/json','.wasm':'application/wasm'};
const srv=http.createServer((q,r)=>{let p=path.join(root,q.url.split('?')[0]);if(p.endsWith('/'))p+='index.html';fs.readFile(p,(e,d)=>{if(e){r.writeHead(404);r.end();return;}r.writeHead(200,{'content-type':T[path.extname(p)]||'application/octet-stream'});r.end(d);});}).listen(0);
const PORT=9300+Math.floor(Math.random()*500);
const ch=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--autoplay-policy=no-user-gesture-required','--remote-debugging-port='+PORT,'about:blank'],{stdio:'ignore'});
const wait=ms=>new Promise(r=>setTimeout(r,ms));await wait(2000);
const tabs=await (await fetch('http://localhost:'+PORT+'/json')).json();const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pend={};ws.onmessage=m=>{const d=JSON.parse(m.data);if(d.id&&pend[d.id])pend[d.id](d);if(d.method==='Runtime.exceptionThrown')console.log('EXC',JSON.stringify(d.params.exceptionDetails).slice(0,300));};
const send=(method,params={})=>new Promise(r=>{pend[++id]=r;ws.send(JSON.stringify({id,method,params}))});
const ev=async e=>(await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true})).result.result.value;
await send('Runtime.enable');await send('Page.enable');
let bad=0;const ok=(c,m)=>{console.log(c?'ok  ':'FAIL',m);if(!c)bad++;};
try{
await send('Page.navigate',{url:`http://localhost:${srv.address().port}/index.html`});
for(let i=0;i<100&&!(await ev('window.demoReady===true'));i++)await wait(200);
const cur=()=>ev('+document.getElementById("seek").value');
const click=i=>ev(`document.getElementById("${i}").click()`);
ok(await ev('window.demoReady===true'),'page loads');
await click('pp');await wait(3000);const a=await cur();ok(a>=1&&a<=5,'play advances: '+a);
await click('pp');const p0=await cur();await wait(1500);ok(await cur()===p0,'pause holds: '+p0);
await ev('(()=>{const e=document.getElementById("seek");e.value=100;e.dispatchEvent(new Event("input"));})()');await wait(500);ok(Math.abs(await cur()-100)<2,'seek to 100 s: '+await cur());
await click('f5');await wait(500);ok(Math.abs(await cur()-105)<2,'+5 s: '+await cur());
await click('b5');await wait(500);ok(Math.abs(await cur()-100)<2,'-5 s: '+await cur());
await ev('(()=>{const e=document.getElementById("seek");e.value=222;e.dispatchEvent(new Event("input"));})()');await wait(2500);
const lit=await ev('(()=>{const d=document.getElementById("c").getContext("2d").getImageData(0,0,320,200).data;let n=0;for(let i=0;i<d.length;i+=4)if(d[i]>20)n++;return n})()');ok(lit>2000,'people scene draws at 222 s (lit pixels '+lit+')');
await ev('document.getElementById("c").getContext("2d").clearRect(0,0,320,200)');await ev('(()=>{const e=document.getElementById("seek");e.value=209.5;e.dispatchEvent(new Event("input"));})()');await wait(6000);
const lit2=await ev('(()=>{const d=document.getElementById("c").getContext("2d").getImageData(0,0,320,200).data;let n=0;for(let i=0;i<d.length;i+=4)if(d[i]>20)n++;return n})()');ok(lit2>2000,'recompiled dune scene (207.8-211.8 s) draws: '+lit2+' lit pixels');
await ev('(()=>{const e=document.getElementById("seek");e.value=8;e.dispatchEvent(new Event("input"));})()');await wait(8000);
const o=await ev('(()=>{const k=document.getElementById("c"),d=k.getContext("2d").getImageData(0,0,320,k.height).data;let n=0;for(let i=0;i<d.length;i+=4)if(d[i]>20)n++;return [k.height,n]})()');ok(o[0]===480&&o[1]>2000,'recompiled portrait scene (0-21 s) draws at 8 s: canvas height '+o[0]+', '+o[1]+' lit pixels');
for(const [t,w,nm] of [[75,6000,'0x1faa1 (73-78 s)'],[25,9000,'0x366f2 (21-52 s)'],[55,9000,'0x305f7 (52-73 s)'],[90,9000,'0x2edbd (79-100 s)']]){
await ev('(()=>{const e=document.getElementById("seek");e.value='+t+';e.dispatchEvent(new Event("input"));})()');await wait(w);
const q=await ev('(()=>{const k=document.getElementById("c"),d=k.getContext("2d").getImageData(0,0,320,200).data;let n=0;for(let i=0;i<d.length;i+=4)if(d[i]>20||d[i+1]>20||d[i+2]>20)n++;return n})()');ok(q>300,'recompiled '+nm+' draws at '+t+' s: '+q+' lit pixels');}
}catch(e){console.log('FAIL',e);bad++;}
ch.kill();srv.close();process.exit(bad?1:0);
