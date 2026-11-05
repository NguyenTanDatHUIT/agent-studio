// In-memory DOM/state checks; this does not claim browser pixel/layout verification.
// NODE_PATH=<directory containing jsdom> node tests/flow_ui.cjs
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');

(async()=>{
  const assets=path.join(__dirname,'..','agent_orchestrator','web_assets');
  const dom=new JSDOM(fs.readFileSync(path.join(assets,'index.html'),'utf8'),{url:'http://127.0.0.1:8765/#token=fixture',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,d=w.document,errors=[],timers=[];
  w.addEventListener('error',e=>errors.push(e.error||e.message));
  w.ResizeObserver=class{observe(){}};w.HTMLElement.prototype.scrollIntoView=()=>{};
  w.setTimeout=(fn,delay)=>{if(delay===3000)timers.push(fn);return 1;};
  w.requestAnimationFrame=fn=>{fn();return 1;};
  const style=d.createElement('style');style.textContent=fs.readFileSync(path.join(assets,'style.css'),'utf8');d.head.append(style);
  // jsdom does not lay out elements. Derive rectangles from the actual fixed-board CSS
  // only to check connector endpoint math and binding, not screen overflow/pixels.
  w.Element.prototype.getBoundingClientRect=function(){const s=w.getComputedStyle(this),left=parseFloat(s.left)||0,top=parseFloat(s.top)||0,width=parseFloat(s.width)||0,height=parseFloat(s.height)||0;return {left,top,width,height,right:left+width,bottom:top+height};};
  const task=(id,provider,status)=>({id,provider,status,prompt:'Flow fixture '+provider,allow_paths:['src'],tests:['unit'],base:'0'.repeat(40),cancel_requested:false,result:null});
  const a='a'.repeat(24),b='b'.repeat(24),c='c'.repeat(24);
  let tasks=[task(a,'claude','queued'),task(b,'codex','queued')],events=[];
  w.fetch=async input=>({ok:true,json:async()=>input==='/api/config'?{repo:'C:/fixture',base_ref:'HEAD',providers:{claude:true,codex:true},tests:['unit'],execution_enabled:true}:input==='/api/tasks'?tasks:input==='/api/activity'?events:{available:false,text:'',truncated:false}});
  w.eval(fs.readFileSync(path.join(assets,'app.js'),'utf8'));
  const q=s=>d.querySelector('[data-view="overview"] '+s),all=s=>[...d.querySelectorAll('[data-view="overview"] '+s)];
  const flush=async()=>{for(let i=0;i<10;i++)await new Promise(resolve=>setImmediate(resolve));};
  const poll=async()=>{const fn=timers.pop();assert(fn,'poll callback exists');await fn();await flush();};
  await flush();
  assert.equal(all('.flow-node').length,7);assert.equal(all('.flow-path').length,7);
  assert.equal(all('.is-running').length,0);assert.equal(all('.flow-path.is-active').length,0);
  assert.equal(w.getComputedStyle(q('.flow-board')).width,'1274px');
  assert.equal(w.getComputedStyle(q('.flow-board')).display,'block');
  assert.equal(w.getComputedStyle(q('.flow-scroller')).overflowX,'auto');
  assert.equal(w.getComputedStyle(q('[data-node="claude"]')).width,'218px');
  assert.equal(w.getComputedStyle(q('[data-node="codex"]')).left,'264px');
  assert(q('.flow-connections__base [data-edge="agent0-claude"]').getAttribute('d').startsWith('M196,206 '));
  assert(q('.flow-connections__base [data-edge="agent0-claude"]').getAttribute('d').endsWith('264,136'));
  assert(q('.flow-connections__base [data-edge="review-export"]').getAttribute('d').endsWith('1074,206'));
  const stable=q('.flow-path[data-edge="codex-testcodex"]');
  tasks=[task(c,'claude','queued'),task(a,'claude','running'),task(b,'codex','running')];
  events=[{seq:3,task_id:b,kind:'test_started'},{seq:2,task_id:a,kind:'worker_started'}];
  await poll();
  assert(q('[data-node="claude"]').classList.contains('is-running'));
  assert.equal(q('[data-node="claude"]').dataset.taskId,a,'display running task before newer queued task');
  assert(!q('[data-node="codex"]').classList.contains('is-running'));
  assert(q('[data-node="testcodex"]').classList.contains('is-running'));
  assert.deepEqual(all('.flow-path.is-active').map(e=>e.dataset.edge).sort(),['agent0-claude','codex-testcodex']);
  assert.equal(q('.flow-path[data-edge="codex-testcodex"]'),stable,'polling preserves SVG path identity');
  q('[data-node="claude"]').click();await flush();
  assert(d.querySelector('[data-task-detail]').textContent.includes('orch/'+a),'same task opened as displayed');
  d.querySelector('[data-page="overview"]').click();
  assert(q('[data-node="claude"]').classList.contains('is-selected'));
  assert(!q('[data-node="testclaude"]').classList.contains('is-selected'));
  tasks=tasks.map(t=>({...t,status:t.provider==='claude'?'awaiting_review':'failed',result:{tests:[{exit_code:t.provider==='claude'?0:1,reason:null}]}}));
  await poll();
  assert.equal(all('.is-running').length,0,'stopped/review tasks do not animate stale start events');
  assert.equal(all('.flow-path.is-active').length,0);
  assert(q('[data-node="review"]').textContent.includes('chờ duyệt'));
  tasks=[task(a,'claude','running')];events=[];await poll();
  assert.equal(all('.is-running').length,0,'unknown phase cannot fabricate running stage');
  assert.equal(all('.flow-path.is-active').length,0);
  assert(style.textContent.includes('@media (prefers-reduced-motion: reduce)'));
  assert(style.textContent.includes('animation: none !important'));
  assert.deepEqual(errors,[]);
  console.log('PASS: fixed board CSS, 7 nodes/7 edges, endpoint math, horizontal scroller, real event mapping, running-task selection, selected vs running, stable SVG, stopped/review/unknown states, existing task handler, reduced-motion rules.');
  dom.window.close();
})().catch(error=>{console.error(error);process.exit(1);});
