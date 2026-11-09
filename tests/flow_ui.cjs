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
  let agent0={connected:false},sessions=[],runners={managed:false,providers:{}},agents=[{agent:2,name:'codex 2',provider:'codex',kind:'queue',remember_context:true}],defaultRemember=true,posts=[],failNext=null;
  // Field names are exactly what /api/conversations returns (store.conversations + `live`), so a rename is caught here.
  let chatStatus={windows:3,tasks:0,workflows:0,can_start:true,reason:null,agent0:true},chatPosts=0,requests=[];
  let conversations=[
    {id:'conv-1',terminal_key:'codex-1',session_id:'s-1',kind:'agent',provider:'codex',agent_n:1,title:'Khởi tạo dự án',task_id:null,cwd:'C:/fixture',status:'closed',live:false,started:'2026-11-08T00:00:00+00:00',last_active:'2026-11-08T00:10:00+00:00',transcript_path:'x'},
    {id:'conv-2',terminal_key:'claude-2',session_id:'s-2',kind:'agent',provider:'claude',agent_n:2,title:'Sửa lỗi test',task_id:a,cwd:'C:/fixture',status:'failed',live:false,started:'2026-11-07T12:00:00+00:00',last_active:'2026-11-07T12:30:00+00:00',transcript_path:'y'},
    {id:'conv-3',terminal_key:'agent0',session_id:'s-3',kind:'agent0',provider:'claude',agent_n:null,title:null,task_id:null,cwd:'C:/fixture',status:'active',live:true,started:'2026-11-06T09:05:00+00:00',last_active:'2026-11-06T09:30:00+00:00',transcript_path:'z'}
  ];
  const routes=input=>{
    if(input==='/api/config')return {repo:'C:/fixture',base_ref:'HEAD',providers:{claude:true,codex:true},tests:['unit'],execution_enabled:true};
    if(input==='/api/tasks'||input==='/api/tasks?scope=all')return tasks;
    if(input==='/api/activity'||input==='/api/activity?scope=all')return events;
    if(input==='/api/runners')return runners;
    if(input==='/api/agent0')return agent0;
    if(input==='/api/terminals')return sessions;
    if(input==='/api/agents')return agents;
    if(input==='/api/settings')return {default_remember:defaultRemember};
    if(input==='/api/workflows'||input==='/api/workflows?scope=all')return [];
    if(input==='/api/chat')return chatStatus;
    if(typeof input==='string'&&input.startsWith('/api/conversations')){
      if(input.includes('/transcript'))return {lines:[{seq:1,timestamp:'2026-11-08T00:01:00Z',text:'$ codex task\nTask started'}],next_after:1,has_more:false};
      const url=new URL('http://localhost'+input);
      const prov=url.searchParams.get('provider');
      return prov?conversations.filter(c=>c.provider===prov):conversations;
    }
    return {available:false,text:'',truncated:false};
  };
  w.fetch=async (input,init)=>{
    requests.push(String(input));
    if(init&&init.method==='POST'){
      posts.push({input,body:JSON.parse(init.body)});
      if(failNext){const error=failNext;failNext=null;return {ok:false,status:400,json:async()=>({error})};}
      if(input==='/api/tasks')return {ok:true,json:async()=>({id:'a'.repeat(24),provider:'codex',agent:2,round:3})};
      if(input==='/api/chat/new'){chatPosts++;return {ok:true,json:async()=>({closed:3,agents_removed:3,agent0:{id:'agent0'}})};}
      if(typeof input==='string'&&input.endsWith('/delete')){const id=input.split('/')[3];conversations=conversations.filter(c=>c.id!==id);return {ok:true,json:async()=>({deleted:1,files_removed:1})};}
      if(input==='/api/conversations/delete-all'){const n=conversations.length;conversations=[];return {ok:true,json:async()=>({deleted:n,files_removed:n,kept_open:0})};}
      if(typeof input==='string'&&input.includes('/resume'))return {ok:true,json:async()=>({id:'codex-1',terminal_id:'codex-1',provider:'codex',title:'Khởi tạo dự án'})};
    }
    return {ok:true,json:async()=>routes(input)};
  };
  if(!w.HTMLDialogElement.prototype.showModal)w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
  if(!w.HTMLDialogElement.prototype.close)w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
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
  // Nothing in the flow may be static sample text: it must follow Agent 0, runners, terminals and config.
  const live=()=>d.querySelector('[data-live-activity]').textContent,node=k=>q(`[data-node="${k}"]`).textContent;
  tasks=[];events=[];await poll();
  assert(node('agent0').includes('Chưa kết nối'),'Agent 0 shown disconnected when no MCP presence');
  assert(q('.flow-idle-placeholder')!==null,'idle placeholder shown when Agent 0 has not called agents');
  assert(q('[data-node="claude"]')===null,'worker nodes not hardcoded when no agent called');
  assert(live().includes('Chưa có terminal nào đang mở')&&live().includes('Chưa có sự kiện'));
  agent0={connected:true,client:'claude-code 2.1',last_tool:'enqueue_task',idle_seconds:7};
  runners={managed:true,providers:{codex:{status:'idle'},claude:{status:'busy'}}};
  await poll();
  assert(node('agent0').includes('enqueue_task')&&node('agent0').includes('7 giây trước'),'Agent 0 node shows the last MCP tool');
  assert(node('codex').includes('Runner sẵn sàng')&&node('claude').includes('Runner đang xử lý'));
  assert(live().includes('Runner codex')&&live().includes('Đã kết nối'));
  sessions=[{id:'codex-1',kind:'agent',provider:'codex',agent:1,task_id:null,title:'Codex 1',alive:true,idle:false,exit_code:null,readonly:false,remember:null},
            {id:'codex-2',kind:'worker',provider:'codex',agent:2,task_id:a,title:'Codex 2',alive:true,idle:false,exit_code:null,readonly:true,remember:true}];
  tasks=[{...task(a,'codex','running'),agent:2,round:2}];events=[{seq:9,task_id:a,kind:'queued',time:'2026-11-07T01:02:03Z'}];
  await poll();
  assert(live().includes('codex-1')&&live().includes('Đang làm')&&live().includes('Đang chạy'),'live panel lists terminals with the ids Agent 0 can use');
  assert(d.querySelectorAll('[data-open-term]').length===2,'each terminal has an open button');
  assert(d.querySelector('[data-toast]').textContent.includes('Terminal mới: Codex 2'),'a new agent window is announced');
  assert(d.querySelector('[data-task-rows]').textContent.includes('codex 2')&&d.querySelector('[data-task-rows]').textContent.includes('vòng 2'),'task list shows the agent number and round');
  assert(live().includes(a.slice(0,8)+' · queued'),'recent events are listed');
  // Window title bar: controls live in the head (minimise, maximise, close); no bottom action bar or typing hint.
  const cards=[...d.querySelectorAll('.ao-terminal')];
  assert.equal(cards.length,3,'Agent 0 placeholder + two sessions');
  assert.equal(d.querySelectorAll('.ao-term-actions').length,0,'bottom action bar removed');
  assert(!d.body.textContent.includes('Gõ yêu cầu giao việc tại đây'),'typing hint removed');
  for(const card of cards){
    const buttons=[...card.querySelectorAll('.ao-terminal-head .ao-winctl .ao-winbtn')];
    assert.equal(buttons.length,4,'settings, minimise, maximise, close');
    assert(buttons[0].dataset.settings&&buttons[1].dataset.collapse&&buttons[2].dataset.focus&&buttons[3].dataset.termToggle,'buttons in order');
    assert(buttons[3].classList.contains('ao-winbtn-close'));
    assert.equal(card.querySelector('.ao-terminal-meta').closest('.ao-terminal-head')!==null,true,'id/status sit in the head');
  }
  const agent0Close=d.querySelector('[data-window="agent0"] .ao-winbtn-close');
  assert(agent0Close.getAttribute('aria-label').startsWith('Mở Agent 0')&&agent0Close.querySelector('[data-lucide="play"],svg'),'closed Agent 0 gets an open button');
  const taskCard=()=>d.querySelector('[data-window="codex-2"]');
  assert(taskCard().querySelector('[data-window-path]').textContent.includes('codex-2 · nhớ ngữ cảnh'),'agent window shows its id and memory mode');
  assert.equal(taskCard().querySelector('[data-window-status]').textContent,'Đang làm');
  assert(taskCard().querySelector('.ao-winbtn-close').getAttribute('aria-label').startsWith('Đóng cửa sổ theo dõi'));
  taskCard().querySelector('[data-collapse]').click();await flush();
  assert(taskCard().classList.contains('is-collapsed'),'minimise collapses the card body');
  assert.equal(taskCard().querySelector('[data-collapse]').getAttribute('aria-pressed'),'true');
  assert(style.textContent.includes('.ao-terminal.is-collapsed .ao-term-host'),'collapsed card hides the terminal via CSS');
  taskCard().querySelector('[data-collapse]').click();await flush();
  assert(!taskCard().classList.contains('is-collapsed'),'second click restores');
  // Sidebar toggle and full-width main area.
  const rootEl0=d.getElementById('ao-studio'),sideBtn=d.querySelector('[data-side-toggle]');
  assert(sideBtn&&sideBtn.getAttribute('aria-expanded')==='true'&&sideBtn.getAttribute('aria-label')==='Đóng thanh bên'&&!rootEl0.classList.contains('ao-side-collapsed'));
  assert(d.querySelector('.ao-top-left .ao-crumb'),'breadcrumb still exists beside the toggle');
  sideBtn.click();await flush();
  assert(rootEl0.classList.contains('ao-side-collapsed')&&sideBtn.getAttribute('aria-expanded')==='false'&&sideBtn.getAttribute('aria-label')==='Mở thanh bên');
  assert.equal(JSON.parse(w.localStorage.getItem('agent-studio-ui')).side,'collapsed','sidebar state is remembered');
  assert([...d.querySelectorAll('.ao-nav button')].every(b=>b.title),'icon-only nav buttons have tooltips');
  sideBtn.click();await flush();
  assert(!rootEl0.classList.contains('ao-side-collapsed')&&JSON.parse(w.localStorage.getItem('agent-studio-ui')).side==='open');
  assert(!/\.ao-main\{max-width:1800px/.test(style.textContent)&&/\.ao-main\{max-width:none/.test(style.textContent),'main area is not capped at 1800px');
  assert(/\.ao-side-collapsed \.ao-shell\{grid-template-columns:62px/.test(style.textContent),'collapsed sidebar becomes a 62px rail');
  // Appearance setting: mode (system/light/dark) and palette (claude/classic), applied at once and remembered.
  const themeModal=d.querySelector('.ao-theme-dialog'),pick=(name,value)=>{const r=themeModal.querySelector(`input[name="${name}"][value="${value}"]`);r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}));};
  assert.equal(rootEl0.dataset.theme,'system');assert.equal(rootEl0.dataset.palette,'claude');
  d.querySelector('[data-theme-open]').click();await flush();
  assert(themeModal.hasAttribute('open')&&themeModal.querySelector('input[name="theme-mode"][value="system"]').checked&&themeModal.querySelector('input[name="theme-palette"][value="claude"]').checked,'dialog shows the current choice');
  assert.equal(themeModal.querySelectorAll('input[type=radio]').length,5,'three modes and two palettes');
  for(const [mode,scheme] of [['dark','dark'],['light','light'],['system','light dark']]){
    pick('theme-mode',mode);
    assert.equal(rootEl0.dataset.theme,mode);assert.equal(d.documentElement.dataset.theme,mode);
    assert.equal(rootEl0.style.getPropertyValue('color-scheme')||scheme,scheme,'color-scheme follows the mode');
    assert.equal(JSON.parse(w.localStorage.getItem('agent-studio-ui')).theme,mode,'mode is remembered');
  }
  pick('theme-palette','classic');
  assert.equal(rootEl0.dataset.palette,'classic');assert.equal(d.documentElement.dataset.palette,'classic');
  assert.equal(JSON.parse(w.localStorage.getItem('agent-studio-ui')).palette,'classic');
  pick('theme-palette','claude');assert.equal(rootEl0.dataset.palette,'claude');
  assert(style.textContent.includes('#ao-studio[data-palette="classic"]'),'classic palette is defined');
  themeModal.removeAttribute('open');
  // Settings dialog: per-agent memory, the Agent 0 default, interactive terminals have nothing to set.
  const modal=d.querySelector('.ao-settings-dialog'),box=()=>modal.querySelector('[data-setting]');
  taskCard().querySelector('[data-settings]').click();await flush();
  assert(modal.hasAttribute('open')&&modal.textContent.includes('Codex 2')&&box().dataset.setting==='remember_context'&&box().checked,'worker settings open with memory on');
  box().checked=false;box().dispatchEvent(new w.Event('change',{bubbles:true}));await flush();
  assert.deepEqual(posts.at(-1),{input:'/api/agents/2/settings',body:{remember_context:false}});
  assert(d.querySelector('[data-toast]').textContent.includes('Đã lưu cài đặt'));
  failNext='boom';box().checked=true;box().dispatchEvent(new w.Event('change',{bubbles:true}));await flush();
  assert.equal(box().checked,false,'a rejected change is rolled back in the checkbox');
  assert(d.querySelector('[data-toast]').textContent.includes('boom'));
  d.querySelector('[data-window="agent0"] [data-settings]').click();await flush();
  assert(modal.textContent.includes('Agent 0')&&box().dataset.setting==='default_remember'&&box().checked);
  box().checked=false;box().dispatchEvent(new w.Event('change',{bubbles:true}));await flush();
  assert.deepEqual(posts.at(-1),{input:'/api/settings',body:{default_remember:false}});
  d.querySelector('[data-window="codex-1"] [data-settings]').click();await flush();
  assert(!box()&&modal.textContent.includes('luôn giữ ngữ cảnh'),'interactive terminal has no memory option');
  // Mouse wheel inside full-screen apps: choice lives in the terminal's settings, defaults to PageUp/PageDown, is remembered.
  const wheelBoxes=()=>[...modal.querySelectorAll('input[name="wheel"]')];
  assert.deepEqual(wheelBoxes().map(x=>x.value),['page','arrows','none']);assert.equal(wheelBoxes().find(x=>x.checked).value,'page','default is PageUp/PageDown, not arrow keys');
  wheelBoxes().find(x=>x.value==='none').checked=true;wheelBoxes().find(x=>x.value==='none').dispatchEvent(new w.Event('change',{bubbles:true}));await flush();
  assert.equal(JSON.parse(w.localStorage.getItem('agent-studio-ui')).wheel,'none','wheel choice is remembered');
  d.querySelector('[data-window="codex-1"] [data-settings]').click();await flush();
  assert.equal(wheelBoxes().find(x=>x.checked).value,'none','dialog reopens with the saved choice');
  wheelBoxes().find(x=>x.value==='page').checked=true;wheelBoxes().find(x=>x.value==='page').dispatchEvent(new w.Event('change',{bubbles:true}));await flush();
  assert.equal(JSON.parse(w.localStorage.getItem('agent-studio-ui')).wheel,'page');
  taskCard().querySelector('[data-settings]').click();await flush();
  assert.equal(wheelBoxes().length,0,'read-only agent windows have no wheel option');
  // "Giao việc tiếp" continues the same agent instead of creating a new one.
  tasks=[{...task(a,'codex','awaiting_review'),agent:2,round:2}];await poll();
  d.querySelector('[data-task]').click();await flush();
  d.querySelector('[data-detail="retry"]').click();await flush();
  const taskForm=d.querySelector('[data-create-form]');
  assert(!taskForm.hidden&&taskForm.elements.provider.disabled&&taskForm.elements.prompt.value==='','follow-up form is for that agent with an empty prompt');
  assert(taskForm.textContent.includes('Giao việc tiếp cho codex 2'));
  taskForm.elements.prompt.value='Add FILE:second';taskForm.dispatchEvent(new w.Event('submit',{cancelable:true}));await flush();
  assert.deepEqual(posts.at(-1).body,{agent:2,prompt:'Add FILE:second',allow_paths:['src'],tests:['unit']},'agent number is sent, provider is not');
  assert(d.querySelector('[data-toast]').textContent.includes('codex 2 làm tiếp'));
  // Rows x columns typed by hand.
  const lin=d.querySelector('[data-console-layout-input]'),grid=d.querySelector('[data-console-grid]'),rootEl=d.getElementById('ao-studio');
  assert(lin&&lin.closest('.ao-layout-group').querySelectorAll('.ao-layout-btn').length===4,'input sits with the four preset buttons');
  const typeLayout=async text=>{lin.value=text;lin.dispatchEvent(new w.Event('change',{bubbles:true}));await flush();};
  const dims=()=>[rootEl.style.getPropertyValue('--console-rows'),grid.style.getPropertyValue('--console-cols')];
  for(const [text,rows,cols,key] of [['1x2','1','2','1x2'],['1 x 2','1','2','1x2'],['  3 x 4 ','3','4','3x4'],['2×3','2','3','2x3'],['6X6','6','6','6x6'],['01x02','1','2','1x2']]){
    await typeLayout(text);
    assert.deepEqual(dims(),[rows,cols],'layout '+text);assert.equal(lin.value,key.replace('x',' x '),'input is normalised');assert(!lin.hasAttribute('aria-invalid'));
  }
  assert.equal(JSON.parse(w.localStorage.getItem('agent-studio-ui')).layout,'1x2','layout is remembered');
  await typeLayout('3x4');
  assert.equal([...d.querySelectorAll('[data-console-layout]')].filter(b=>b.getAttribute('aria-pressed')==='true').length,0,'a custom size leaves every preset unpressed');
  await typeLayout('2x2');
  assert.equal(d.querySelector('[data-console-layout="2x2"]').getAttribute('aria-pressed'),'true','typing a preset size presses its button');
  for(const bad of ['abc','0x2','2x0','7x1','1x7','1x','x2','2 x 2 x 2','1,2','','100x100','1 2']){
    await typeLayout(bad);
    assert.deepEqual(dims(),['2','2'],'invalid input keeps the layout: '+JSON.stringify(bad));
    assert.equal(lin.getAttribute('aria-invalid'),'true');assert(d.querySelector('[data-toast]').classList.contains('error'));
  }
  await typeLayout('1x3');assert(!lin.hasAttribute('aria-invalid'),'a valid entry clears the error mark');
  d.querySelector('[data-console-layout="2x3"]').click();await flush();
  assert.equal(lin.value,'2 x 3','clicking a preset updates the input');
  sessions=[];tasks=[];events=[];await poll();
  assert(node('codex').includes('Runner sẵn sàng'));
  // A task that failed after a clean worker exit (e.g. "no changes") must not be shown as ready code.
  tasks=[{...task(a,'claude','failed'),result:{error:'Worker produced no changes',worker:{exit_code:0,reason:null}}}];events=[];await poll();
  assert(node('claude').includes('Thất bại')&&!node('claude').includes('✓ Code đã sẵn sàng'),'failed task is not marked as ready');

  // History modal and transcript viewer verification
  // History is a sidebar menu entry (a page), not a button inside the settings menu or a modal.
  const histNav=d.querySelector('.ao-nav [data-page="history"]');
  assert(histNav&&histNav.textContent.includes('Lịch sử'),'history is a menu item in the sidebar');
  assert(!d.querySelector('[data-console-action="history"]'),'no history button is left in the toolbar or settings menu');
  assert(!d.querySelector('.ao-console-settings-panel')||!d.querySelector('.ao-console-settings-panel').textContent.includes('Lịch sử'),'the settings menu no longer lists history');
  histNav.click();await flush();
  const histModal=d.querySelector('[data-view="history"]');
  assert(histModal&&!histModal.hidden&&histNav.getAttribute('aria-current')==='page','history page opens from the menu');
  assert(d.querySelector('[data-view="terminals"]').hidden,'the history page replaces the current page');
  const histRows=()=>[...histModal.querySelectorAll('.ao-history-row')];
  assert.equal(histRows().length,3,'three conversation rows rendered');
  // Regression: the list once read created_at/agent_number/terminal_id, which the API never sends (blank time, "Khác" group).
  assert(histRows().every(r=>/^\d{2}:\d{2}$/.test(r.querySelector('.ao-history-time').textContent.trim())),'every row shows its start time');
  const groupTitles=[...histModal.querySelectorAll('.ao-history-group-title')].map(x=>x.textContent.trim());
  assert(groupTitles.length>=2&&!groupTitles.includes('Khác'),'rows are grouped by real dates, not "Khác": '+groupTitles);
  const rowOf=id=>histModal.querySelector(`[data-conv-id="${id}"]`);
  assert(rowOf('conv-3').textContent.includes('Agent 0')&&rowOf('conv-3').textContent.includes('Phiên làm việc'),'untitled Agent 0 row has a fallback title');
  assert(rowOf('conv-3').textContent.includes('Đang mở')&&rowOf('conv-3').querySelector('[data-conv-resume]').disabled&&rowOf('conv-3').querySelector('[data-conv-delete]').disabled,'a live conversation cannot be resumed or deleted');
  assert(rowOf('conv-1').textContent.includes('Đã đóng')&&!rowOf('conv-1').querySelector('[data-conv-resume]').disabled,'a closed conversation can be resumed');
  assert(histModal.textContent.includes('Khởi tạo dự án'),'title is displayed');
  assert(histModal.textContent.includes('Codex 1')&&histModal.textContent.includes('Claude 2'),'agent badges are shown');

  // Filter provider
  const provSelect=histModal.querySelector('[data-history-provider]');
  provSelect.value='claude';provSelect.dispatchEvent(new w.Event('change'));await flush();
  assert.equal(histRows().length,2,'filtering by claude yields its two rows');

  // Template-styled dropdown replaces the native popup but the real <select> stays the source of truth.
  provSelect.value='';provSelect.dispatchEvent(new w.Event('change'));await flush();
  provSelect.dispatchEvent(new w.MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0}));
  const selMenu=d.querySelector('[data-select-menu]');
  assert(selMenu&&selMenu.querySelectorAll('[role="option"]').length===5,'custom menu lists every option of the select');
  assert.equal(selMenu.querySelector('[aria-selected="true"]').textContent,'Tất cả agent','current value is marked');
  provSelect.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));
  provSelect.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));await flush();
  assert.equal(provSelect.value,'agent0','keyboard (arrow + Enter) chooses an item');
  assert(!d.querySelector('[data-select-menu]'),'menu closes after choosing');
  provSelect.dispatchEvent(new w.MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0}));
  d.querySelector('[data-select-menu] [data-i="2"]').dispatchEvent(new w.MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0}));await flush();
  assert.equal(provSelect.value,'claude','clicking an item updates the real select and fires change');
  assert.equal(histRows().length,2,'the change handler ran (filtered to claude)');
  provSelect.dispatchEvent(new w.MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0}));
  provSelect.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
  assert(!d.querySelector('[data-select-menu]')&&provSelect.value==='claude','Escape closes the menu without changing the value');
  provSelect.dispatchEvent(new w.MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0}));
  d.querySelector('.ao-history-toolbar').dispatchEvent(new w.MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0}));
  assert(!d.querySelector('[data-select-menu]'),'clicking elsewhere closes the menu');

  // View transcript dialog
  const viewBtn=histModal.querySelector('[data-conv-view="conv-2"]');
  assert(viewBtn,'view button exists for conv-2');
  viewBtn.click();await flush();
  const transModal=d.querySelector('.ao-transcript-dialog');
  assert(transModal&&transModal.hasAttribute('open'),'transcript dialog opens');
  assert(transModal.querySelector('[data-transcript-content]').textContent.includes('$ codex task'),'transcript content loaded');
  transModal.querySelector('[data-transcript-close]').click();await flush();
  assert(!transModal.hasAttribute('open'),'transcript dialog closes');

  // Delete: cancelling the confirmation sends nothing; confirming removes the row; delete-all needs its own confirmation.
  const before=posts.length;
  w.confirm=()=>false;
  histModal.querySelector('[data-conv-delete="conv-2"]').click();await flush();
  assert.equal(posts.length,before,'declining the confirmation sends no request');
  w.confirm=()=>true;
  provSelect.value='';provSelect.dispatchEvent(new w.Event('change'));await flush();
  histModal.querySelector('[data-conv-delete="conv-2"]').click();await flush();
  assert.equal(posts.at(-1).input,'/api/conversations/conv-2/delete','delete POST sent to API');
  assert.equal(histRows().length,2,'deleted row disappears from the list');
  assert(!histModal.textContent.includes('Sửa lỗi test'));
  w.confirm=()=>false;
  histModal.querySelector('[data-history-clear]').click();await flush();
  assert.notEqual(posts.at(-1).input,'/api/conversations/delete-all','delete-all needs confirmation');
  w.confirm=()=>true;
  const keep=conversations.slice();
  histModal.querySelector('[data-history-clear]').click();await flush();
  assert.deepEqual(posts.at(-1),{input:'/api/conversations/delete-all',body:{confirm:true}});
  assert.equal(histRows().length,0,'list is empty after delete-all');
  conversations=keep;provSelect.value='';provSelect.dispatchEvent(new w.Event('change'));await flush();

  // Resume action
  provSelect.value='';provSelect.dispatchEvent(new w.Event('change'));await flush();
  const resumeBtn=histModal.querySelector('[data-conv-resume="conv-1"]');
  assert(resumeBtn,'resume button exists for conv-1');
  resumeBtn.click();await flush();
  assert.equal(posts.at(-1).input,'/api/conversations/conv-1/resume','resume POST sent to API');
  assert(d.querySelector('[data-toast]').textContent.includes('Đã khôi phục phiên'),'toast confirms resume');
  assert(histModal.hidden&&!d.querySelector('[data-view="terminals"]').hidden,'resuming leaves the history page and shows the terminals');
  // Earlier chats' tasks are hidden by default, with a visible note and one click to bring them back.
  const scopeNote=d.querySelector('[data-scope-note]');
  assert(scopeNote.hidden,'no note when nothing from earlier chats is hidden');
  chatStatus={...chatStatus,hidden:{tasks:5,review:2,workflows:0}};await poll();
  assert(!scopeNote.hidden&&scopeNote.textContent.includes('Đang ẩn 5 nhiệm vụ')&&scopeNote.textContent.includes('2 đang chờ review'),'the note says how much is hidden, including work awaiting review');
  assert(!requests.slice(-12).some(r=>r.includes('scope=all')),'by default only the current chat is requested');
  requests=[];d.querySelector('[data-scope-toggle]').click();await flush();
  assert(['/api/tasks?scope=all','/api/activity?scope=all','/api/workflows?scope=all'].every(r=>requests.includes(r)),'the toggle requests every list with scope=all');
  assert(scopeNote.textContent.includes('Đang hiện cả')&&scopeNote.textContent.includes('Chỉ cuộc trò chuyện hiện tại'),'the note switches to the opposite action');
  requests=[];d.querySelector('[data-scope-toggle]').click();await flush();
  assert(requests.includes('/api/tasks')&&!requests.some(r=>r.includes('scope=all')),'toggling back returns to the current chat only');
  chatStatus={...chatStatus,hidden:{tasks:0,review:0,workflows:0}};await poll();
  assert(scopeNote.hidden,'the note disappears when nothing is hidden');

  // New chat: confirmation modal, blocked while work runs, then closes everything and reopens Agent 0.
  const chatBtn=d.querySelector('[data-console-action="newchat"]');
  assert(chatBtn&&chatBtn.textContent.includes('Cuộc trò chuyện mới'),'new-chat button exists');
  assert(chatBtn.closest('.ao-console-bar-actions')&&!chatBtn.closest('.ao-console-settings-panel'),'new-chat button sits on the console bar, not inside the settings menu');
  chatBtn.click();await flush();
  const chatDlg=d.querySelector('.ao-chat-dialog');
  assert(chatDlg&&chatDlg.hasAttribute('open'),'clicking the button opens the confirmation modal, it does not act');
  assert.equal(chatPosts,0,'nothing is sent before the user confirms');
  assert(chatDlg.textContent.includes('3 cửa sổ')&&chatDlg.textContent.includes('Lịch sử')&&chatDlg.textContent.includes('từ 1')&&chatDlg.textContent.includes('Agent 0'),'modal explains what will happen');
  assert(!chatDlg.querySelector('[data-chat-confirm]').disabled&&chatDlg.querySelector('[data-chat-block]').hidden,'confirm is available when nothing is running');
  chatDlg.querySelector('[data-chat-cancel]').click();await flush();
  assert(!chatDlg.hasAttribute('open')&&chatPosts===0,'cancel closes the modal and sends nothing');
  chatStatus={windows:2,tasks:1,workflows:0,can_start:false,reason:'Chưa thể bắt đầu cuộc trò chuyện mới: còn 1 nhiệm vụ đang chạy hoặc chờ chạy. Chờ xong hoặc hủy chúng trước.',agent0:true};
  chatBtn.click();await flush();
  assert(chatDlg.querySelector('[data-chat-confirm]').disabled&&!chatDlg.querySelector('[data-chat-block]').hidden&&chatDlg.querySelector('[data-chat-block]').textContent.includes('nhiệm vụ'),'confirm is disabled and the reason is shown while work runs');
  chatDlg.querySelector('[data-chat-confirm]').click();await flush();
  assert.equal(chatPosts,0,'a disabled confirm sends nothing');
  chatDlg.querySelector('[data-chat-cancel]').click();await flush();
  chatStatus={windows:3,tasks:0,workflows:0,can_start:true,reason:null,agent0:true};
  chatBtn.click();await flush();
  chatDlg.querySelector('[data-chat-confirm]').click();await flush();
  assert.deepEqual(posts.at(-1),{input:'/api/chat/new',body:{confirm:true,cols:100,rows:30}},'confirm sends the explicit confirmation');
  assert(!chatDlg.hasAttribute('open'),'modal closes after a successful reset');
  assert(d.querySelector('[data-toast]').textContent.includes('cuộc trò chuyện mới')&&d.querySelector('[data-toast]').textContent.includes('đóng 3 cửa sổ'),'toast reports what was closed');
  // The add-terminal dialog no longer asks for a working folder.
  assert(!d.querySelector('[data-add-folder]'),'no working-folder select in the add-terminal dialog');
  assert(!/Thư mục làm việc/.test(d.getElementById('ao-studio').textContent),'no "Thư mục làm việc" field anywhere');
  assert.deepEqual(errors,[]);
  console.log('PASS: fixed board CSS, 7 nodes/7 edges, endpoint math, horizontal scroller, real event mapping, running-task selection, selected vs running, stable SVG, stopped/review/unknown states, existing task handler, reduced-motion rules, live (non-sample) Agent 0/runner/terminal/event data.');
  dom.window.close();
})().catch(error=>{console.error(error.stack||error);process.exit(1);});
