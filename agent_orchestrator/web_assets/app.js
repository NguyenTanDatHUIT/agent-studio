'use strict';
(() => {
  const root = document.getElementById('ao-studio');
  const $ = s => root.querySelector(s), $$ = s => [...root.querySelectorAll(s)];
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = {queued:'Trong hàng đợi',running:'Đang thực hiện',awaiting_review:'Chờ review',approved:'Đã duyệt',changes_requested:'Cần chỉnh sửa',failed:'Thất bại',cancelled:'Đã hủy'};
  const pages = {terminals:['Cửa sổ CMD','Không gian dòng lệnh','Log worker, test và sự kiện được cập nhật từ queue.'],overview:['Tổng quan','Trung tâm điều phối','Giao việc rõ ràng. Theo dõi xuyên suốt. Duyệt từng thay đổi.'],flow:['Luồng tự động','Nhìn rõ từng bước chạy','Worker → test → review đúng digest → xuất patch.'],tasks:['Nhiệm vụ','Mỗi nhiệm vụ, một worktree','Phân công, xem bằng chứng test và duyệt thay đổi.'],reports:['Báo cáo','Hiệu quả vận hành','Tổng hợp tối đa 200 nhiệm vụ gần nhất; usage thiếu được giữ nguyên.'],permissions:['Quyền & bảo vệ','Tự động hóa có giới hạn','Chính sách hiện tại và quyền thực thi local.']};
  let pref={};try {pref=JSON.parse(localStorage.getItem('agent-studio-ui')||'{}')||{};}catch {}
  const layouts = {'1x2':[1,2], '2x2':[2,2], '2x3':[2,3], '3x3':[3,3]};
  const state={page:pages[pref.page]?pref.page:'terminals',layout:layouts[pref.layout]?pref.layout:'2x2',mode:pref.mode==='all'?'all':'paged',windowPage:1,focus:null,order:Array.isArray(pref.order)?pref.order:[],extra:Array.isArray(pref.extra)?pref.extra.filter(x=>/^w[a-f0-9]+$/.test(x.id||'')&&/^[0-9a-f]{24}$/.test(x.taskId||'')).slice(0,30):[],tasks:[],events:[],sessions:[],agent0:{connected:false},runners:{managed:false,providers:{}},selected:null,config:null,bundle:null,busy:false,windows:[],outputs:new Map(),drafts:new Map(),streams:new Map()};
  const hash=new URLSearchParams(location.hash.slice(1));
  const token=hash.get('token')||sessionStorage.getItem('agent-studio-token')||'';
  if(hash.has('token')){sessionStorage.setItem('agent-studio-token',token);history.replaceState(null,'',location.pathname);}
  function save(){try {localStorage.setItem('agent-studio-ui',JSON.stringify({page:state.page,layout:state.layout,mode:state.mode,order:state.order,extra:state.extra}));}catch {}}
  const icons=()=>globalThis.lucide?.createIcons({attrs:{width:16,height:16}});
  const title=t=>(t.prompt||'').split('\n')[0],short=id=>id?.slice(0,8)||'—';
  const time=value=>value?new Date(value).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'—';
  const number=value=>typeof value==='number'?value.toLocaleString('vi-VN'):'Chưa có';
  const chip=status=>`<span class="ao-chip ${status==='failed'?'bad':['awaiting_review','changes_requested'].includes(status)?'review':['approved','running'].includes(status)?'good':''}"><span class="ao-dot"></span>${esc(labels[status]||status)}</span>`;
  function notify(text,error=false){const e=$('[data-toast]');e.hidden=false;e.textContent=text;e.classList.toggle('error',error);}
  async function api(path,body,raw=false){
    const response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});
    if(!response.ok){const data=await response.json().catch(()=>({error:'HTTP '+response.status}));throw new Error(data.error||'Không thể hoàn tất yêu cầu');}
    return raw?response:response.json();
  }
  async function download(path,name){const response=await api(path,undefined,true),blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function navigate(page){state.page=page;$$('[data-view]').forEach(e=>e.hidden=e.dataset.view!==page);$$('[data-page]').forEach(e=>e.setAttribute('aria-current',e.dataset.page===page?'page':'false'));$('[data-title]').textContent=pages[page][1];$('[data-sub]').textContent=pages[page][2];$('[data-crumb]').textContent=pages[page][0];root.classList.toggle('ao-console-compact',page==='terminals');save();requestAnimationFrame(drawEdges);}
  // Preserve the supplied compact toolbar, sidebar and scoped visual styles.
  const view=$('[data-view="terminals"]'),toolbar=view.querySelector('.ao-console-toolbar'),inventory=view.querySelector('.ao-console-inventory');
  const bar=$('[data-compact-console-bar]').content.cloneNode(true).firstElementChild;
  bar.querySelector('.ao-console-bar-info').append(inventory.querySelector('.ao-window-range'));
  bar.querySelector('[data-compact-layout-mount]').append(toolbar.querySelector('.ao-layout-group'));
  bar.querySelector('[data-compact-mode-mount]').append(toolbar.querySelector('.ao-console-mode'));
  const add=inventory.querySelector('[data-console-action="add"]');add.innerHTML='<i data-lucide="plus"></i>CMD';add.setAttribute('aria-label','Thêm cửa sổ theo dõi');bar.querySelector('.ao-console-bar-actions').prepend(add);
  const reload=inventory.querySelector('[data-console-action="feed"]');reload.textContent='Làm mới log';bar.querySelector('[data-compact-extra-mount]').append(reload);toolbar.replaceWith(bar);inventory.remove();
  $('.ao-console-hint').innerHTML='<span>Kéo tay nắm để sắp xếp · Alt + ← / → để di chuyển cửa sổ</span><span>Log local · Giao việc qua hàng đợi có phạm vi</span>';
  $('[data-console-announce]').textContent='';
  $('.ao-footer').innerHTML='<span>Agent Studio · Local orchestrator</span><span>Workers chạy bằng terminal riêng</span>';
  root.setAttribute('aria-label','Agent Studio — Điều phối nhiệm vụ');
  $('.ao-demo').textContent='ĐANG KẾT NỐI';$('.ao-counter').textContent='0';$('.ao-kicker').textContent='LOCAL WORKSPACE';$('.ao-project').textContent='Đang đọc cấu hình…';
  $$('.ao-metric-value').forEach(e=>e.textContent='0');$('[data-events]').textContent='Chưa có sự kiện.';
  $('[data-view="overview"] .ao-bottomgrid .ao-panel').innerHTML='<div class="ao-panel-head"><h2>Trạng thái nhiệm vụ theo worker</h2></div><div data-workers></div>';
  $('[data-view="overview"] .ao-events').previousElementSibling.querySelector('span').textContent='Sự kiện từ queue';
  $('[data-view="reports"]').innerHTML='<div class="ao-reports" data-reports></div>';
  $('[data-view="permissions"]').innerHTML='<section class="ao-panel"><div class="ao-panel-head"><h2>Chính sách thực thi hiện tại</h2><span class="ao-chip" data-execution>Đang đọc</span></div><div data-policy></div></section>';
  $('[data-view="flow"] .ao-chip').textContent='Quy trình orchestrator';
  for(const mount of ['[data-flow-mount]','[data-full-flow-mount]']){$(mount).append($('[data-flow-template]').content.cloneNode(true));$(mount+' [data-action="next-step"]').remove();}
  const form=$('[data-create-form]');form.querySelector('h3').textContent='Tạo nhiệm vụ';form.elements.prompt.maxLength=40000;
  form.elements.provider.innerHTML='<option value="codex">Codex</option><option value="claude">Claude</option>';
  form.querySelector('[data-action="create-task"]').textContent='Thêm vào hàng đợi';form.querySelector('[data-action="create-task"]').type='submit';form.querySelector('.ao-actions .ao-muted').textContent='Worker nhận việc khi runner đang hoạt động.';
  const testsField=document.createElement('div');testsField.className='ao-field full';testsField.innerHTML='<span>Test profile bắt buộc</span><div data-test-options class="ao-test-options"></div>';form.querySelector('.ao-fields').append(testsField);
  for(const [value,label] of [['changes_requested','Cần chỉnh sửa'],['cancelled','Đã hủy']])$('[data-task-filter]').add(new Option(label,value));
  const search=document.createElement('input');search.type='search';search.className='ao-filter';search.placeholder='Tìm tên hoặc ID…';search.setAttribute('aria-label','Tìm nhiệm vụ');$('[data-task-filter]').parentElement.before(search);
  function configure(config){
    state.config=config;const repoName=config.repo.split(/[\\/]/).pop();$('.ao-project').innerHTML=`<strong>${esc(repoName)}</strong><small>Nhánh cơ sở · ${esc(config.base_ref)}</small><small title="${esc(config.repo)}">${esc(config.repo)}</small>`;
    $('.ao-crumb').innerHTML=`<i data-lucide="folder-git-2"></i>${esc(repoName)}<span>/</span><strong data-crumb>${pages[state.page][0]}</strong>`;$('.ao-kicker').textContent='WORKSPACE / '+repoName.toUpperCase();
    $('[data-test-options]').innerHTML=config.tests.map((name,i)=>`<label><input type="checkbox" name="tests" value="${esc(name)}" ${i===0?'checked':''}> ${esc(name)}</label>`).join('')||'<span>Chưa cấu hình test profile. Thêm profile trong file cấu hình.</span>';
    [...form.elements.provider.options].forEach(o=>o.disabled=!config.providers[o.value]);const enabled=[...form.elements.provider.options].find(o=>!o.disabled);if(enabled)form.elements.provider.value=enabled.value;
    $('[data-execution]').textContent=config.execution_enabled?'Đã cho phép chạy local':'Đang khóa thực thi';
    const policies=[['shield-check','Claude Worker','Restricted, chỉ đọc/sửa file; không cấp shell.'],['box','Codex Worker','Workspace-write; tắt mạng cho lệnh model theo adapter.'],['file-lock-2','Phạm vi chỉnh sửa','Kiểm tra sau khi chạy; sửa ngoài phạm vi sẽ chặn review/export.'],['terminal','Test profile',config.tests.length?config.tests.join(', ')+' · chạy bằng quyền tài khoản local.':'Chưa cấu hình.'],['fingerprint','Review và digest','Test, snapshot và SHA-256 được kiểm tra lại trước khi duyệt/xuất.'],['git-pull-request','Tích hợp','Người dùng áp dụng patch và kiểm thử lại; không tự commit/merge/push.'],['info','Runner','Launcher dự án mở runner cùng web; Ctrl+C dừng cả hai. Runner mở riêng không được web giám sát.']];
    $('[data-policy]').innerHTML=policies.map(([icon,name,description])=>`<div class="ao-permission"><i data-lucide="${icon}"></i><div>${esc(name)}<p>${esc(description)}</p></div></div>`).join('');icons();
  }
  function testSummary(t){const tests=t.result?.tests||[];return tests.length?`${tests.filter(x=>x.exit_code===0&&!x.reason).length}/${tests.length} profile đạt`:'Chưa có kết quả';}
  function renderTasks(){
    const filter=$('[data-task-filter]').value,term=search.value.toLowerCase(),tasks=state.tasks.filter(t=>(filter==='all'||t.status===filter)&&(!term||(title(t)+' '+t.id).toLowerCase().includes(term)));
    $('[data-task-rows]').innerHTML=tasks.length?tasks.map(t=>`<tr ${t.id===state.selected?'aria-selected="true"':''}><td><strong>${esc(title(t))}</strong><small>${short(t.id)} · ${esc(t.allow_paths.join(', '))}</small></td><td>${esc(t.provider)}</td><td>${chip(t.status)}${t.cancel_requested?'<small>Đã yêu cầu hủy</small>':''}</td><td>${esc(testSummary(t))}</td><td><button class="ao-link" type="button" data-task="${t.id}">Chi tiết →</button></td></tr>`).join(''):'<tr><td colspan="5" class="ao-empty">Không có nhiệm vụ phù hợp. Tạo nhiệm vụ để bắt đầu.</td></tr>';
    $('.ao-counter').textContent=state.tasks.length;$$('[data-metric]').forEach(e=>e.textContent=state.tasks.filter(t=>t.status===(e.dataset.metric==='review'?'awaiting_review':e.dataset.metric)).length);
    $('[data-workers]').innerHTML=['claude','codex'].map(p=>{const running=state.tasks.filter(t=>t.provider===p&&t.status==='running'),runner=state.runners.providers[p],runnerText=runner?({starting:'Runner đang khởi động',polling:'Runner đang nhận việc',idle:'Runner sẵn sàng',busy:'Runner đang xử lý',stopped:'Runner đã dừng',error:'Runner lỗi: '+(runner.error||'Kiểm tra terminal')}[runner.status]||runner.status):'Chưa có runner do web quản lý';return `<div class="ao-worker"><span class="ao-worker-icon ${p}"><i data-lucide="${p==='claude'?'sparkles':'terminal'}"></i></span><div class="ao-worker-body"><strong>${p==='claude'?'Claude':'Codex'} Worker</strong><p>${esc(runnerText)} · ${running.length?running.map(t=>short(t.id)).join(', ')+' · task đang chạy':state.config?.providers[p]?'Đã cấu hình · chưa có task running':'Chưa cấu hình provider'}</p></div><span class="ao-chip ${running.length?'good':''}">${running.length} running</span></div>`;}).join('');
    $('[data-events]').innerHTML=state.events.slice(0,6).map(e=>`<div class="ao-event"><time>${esc(time(e.time).slice(0,5))}</time><span class="ao-dot"></span><span><strong>${short(e.task_id)}</strong> · ${esc(e.kind)}</span></div>`).join('')||'<p class="ao-empty">Chưa có sự kiện.</p>';
    renderFlow();renderReports();icons();
  }
  function renderReports(){
    const tasks=state.tasks,finished=tasks.filter(t=>t.result?.worker),passed=tasks.filter(t=>t.result?.tests?.length&&t.result.tests.every(x=>x.exit_code===0&&!x.reason));
    const rows=tasks.filter(t=>t.result?.usage).map(t=>{const u=t.result.usage;return `<div class="ao-usage-row"><div><strong>${esc(t.provider)} · ${short(t.id)}</strong><small>${esc(u.source)}</small></div><div>${number(u.input_tokens)} vào / ${number(u.output_tokens)} ra<small>${u.cost_usd==null?'Chi phí chưa có':esc('$'+u.cost_usd)}</small></div></div>`;}).join('');
    const durations=finished.map(t=>t.result.worker.elapsed_seconds).filter(x=>typeof x==='number').sort((a,b)=>a-b),middle=Math.floor(durations.length/2),median=durations.length?(durations.length%2?durations[middle]:(durations[middle-1]+durations[middle])/2):null;
    $('[data-reports]').innerHTML=`<section class="ao-panel"><div class="ao-panel-head"><h2>Kết quả nhiệm vụ</h2><span class="ao-chip">${tasks.length} gần nhất</span></div><div class="ao-report-body"><div class="ao-report-num">${tasks.filter(t=>t.status==='approved').length}</div><p class="ao-muted">nhiệm vụ đã duyệt</p>${Object.entries(labels).map(([s,l])=>`<div class="ao-usage-row"><span>${l}</span><strong>${tasks.filter(t=>t.status===s).length}</strong></div>`).join('')}</div></section><section class="ao-panel"><div class="ao-panel-head"><h2>Test & thời gian</h2></div><div class="ao-report-body"><div class="ao-usage-row"><span>Task có test đạt</span><strong>${passed.length}/${tasks.length}</strong></div><div class="ao-usage-row"><span>Trung vị thời gian worker</span><strong>${median==null?'Chưa có':median.toFixed(1)+' giây'}</strong></div><div class="ao-notice">Thời gian lấy từ process worker đã kết thúc. Không ước lượng phần trăm tiến độ.</div></div></section><section class="ao-panel ao-wide"><div class="ao-panel-head"><h2>Token & usage do CLI trả về</h2></div><div class="ao-report-body">${rows||'<p class="ao-muted">Chưa có số liệu usage.</p>'}<div class="ao-notice">Thiếu số liệu được hiển thị “Chưa có”. Không suy đoán token hay tổng chi phí.</div></div></section>`;
  }
  function renderFlow(){
    const latest=p=>state.tasks.find(t=>t.provider===p&&t.status==='running')||state.tasks.find(t=>t.provider===p),counts=s=>state.tasks.filter(t=>t.status===s).length;
    const data={agent0:{name:'Agent 0',desc:'Giao việc qua MCP / web',text:`Hàng đợi · ${counts('queued')} task`,task:state.tasks.find(t=>t.status==='queued')},review:{name:'Review',desc:'Agent 0 kiểm tra diff',text:`${counts('awaiting_review')} task chờ duyệt`,task:state.tasks.find(t=>t.status==='awaiting_review')},export:{name:'Xuất patch',desc:'Người dùng tích hợp',text:counts('approved')?`${counts('approved')} đã duyệt · có thể xuất`:'Chờ được duyệt',task:state.tasks.find(t=>t.status==='approved')}};
    for(const p of ['claude','codex']){
      const t=latest(p),event=state.events.filter(e=>e.task_id===t?.id).sort((a,b)=>b.seq-a.seq)[0];
      // A running task alone does not identify its phase. Animate only known event evidence.
      const workerRunning=t?.status==='running'&&event?.kind==='worker_started';
      const testRunning=t?.status==='running'&&event?.kind==='test_started';
      const workerDone=testRunning||['awaiting_review','approved','changes_requested'].includes(t?.status)||!!t?.result?.worker&&t.result.worker.exit_code===0&&!t.result.worker.reason;
      const tests=t?.result?.tests||[],testPassed=tests.length>0&&tests.every(x=>x.exit_code===0&&!x.reason);
      data[p]={name:p==='claude'?'Claude Worker':'Codex Worker',desc:t?'worktree · orch/'+short(t.id):'Chưa có nhiệm vụ',text:workerRunning?'Đang xử lý code':workerDone?'✓ Code đã sẵn sàng':t?labels[t.status]:'Chờ giao việc',task:t,running:workerRunning,success:workerDone};
      data['test'+p]={name:t?'Test '+short(t.id):'Test · '+(p==='claude'?'Claude':'Codex'),desc:t?'Profile · '+t.tests.join(', '):'Profile trong cấu hình',text:testRunning?'Đang chạy test':testPassed?'✓ '+testSummary(t):tests.length?testSummary(t):t?.status==='queued'||workerRunning?'Chờ worker':t?.status==='failed'||t?.status==='cancelled'?'Chưa có kết quả · task đã dừng':'Chưa có kết quả',task:t,running:testRunning,success:testPassed};
    }
    $$('[data-node]').forEach(node=>{
      const key=node.dataset.node,d=data[key],task=d.task;
      node.querySelector('.ao-node-name').textContent=d.name;
      node.querySelector('.ao-node-desc').textContent=d.desc;node.querySelector('.ao-node-desc').title=task?task.id+' · '+title(task):d.desc;
      const foot=node.querySelector('.ao-node-foot');foot.textContent=d.text;foot.title=d.text;foot.classList.toggle('status-running',!!d.running);foot.classList.toggle('status-success',!!d.success);
      node.querySelector('.flow-node__id').textContent=key==='agent0'?'A0':task?short(task.id):'—';
      node.dataset.taskId=task?.id||'';node.dataset.flowRunning=String(!!d.running);
      node.classList.toggle('is-running',!!d.running);
      const selected=state.flowNode===key&&task?.id===state.selected;node.classList.toggle('is-selected',selected);node.setAttribute('aria-pressed',String(selected));
    });
    const running=counts('running');$$('[data-flow-summary]').forEach(e=>{e.textContent=running?`${running} task đang thực hiện`:counts('awaiting_review')?`${counts('awaiting_review')} task chờ review`:'Chưa có task đang chạy';e.classList.toggle('has-activity',running>0);});
    const selected=state.flowNode&&data[state.flowNode],task=selected?.task;
    $$('[data-node-title]').forEach(e=>e.textContent=task?selected.name+' · '+short(task.id):'Quy trình điều phối');
    $$('[data-node-description]').forEach(e=>e.textContent=task?title(task)+' · '+selected.text:'Chọn một bước để xem nhiệm vụ liên quan. Review và xuất patch không tự tích hợp vào main.');
    $$('[data-node-badge]').forEach(e=>e.textContent=task?labels[task.status]:'Queue local');requestAnimationFrame(drawEdges);
  }
  function drawEdges(){
    $$('.ao-flow').forEach(flow=>{
      const svg=flow.querySelector('svg'),box=flow.getBoundingClientRect();if(!box.width)return;
      svg.setAttribute('viewBox',`0 0 ${box.width} ${box.height}`);svg.setAttribute('width',box.width);svg.setAttribute('height',box.height);
      const edges=[['agent0','claude'],['agent0','codex'],['claude','testclaude'],['codex','testcodex'],['testclaude','review'],['testcodex','review'],['review','export']].map(([from,to])=>{
        const source=flow.querySelector(`[data-node="${from}"]`),target=flow.querySelector(`[data-node="${to}"]`),a=source.getBoundingClientRect(),b=target.getBoundingClientRect();
        const x1=a.right-box.left,y1=a.top+a.height/2-box.top,x2=b.left-box.left,y2=b.top+b.height/2-box.top,mx=(x1+x2)/2;
        const active=['claude','codex','testclaude','testcodex'].includes(to)&&target.dataset.flowRunning==='true';
        return {key:from+'-'+to,d:`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`,active};
      });
      // Keep SVG elements stable during polling so animation does not restart every 3 seconds.
      if(!svg.querySelector('.flow-connections__base'))svg.innerHTML='<g class="flow-connections__base"></g><g class="flow-connections__motion"></g>';
      for(const edge of edges){for(const layer of ['base','motion']){
        const group=svg.querySelector('.flow-connections__'+layer);let path=group.querySelector(`[data-edge="${edge.key}"]`);
        if(!path){path=document.createElementNS('http://www.w3.org/2000/svg','path');path.dataset.edge=edge.key;group.append(path);}
        path.setAttribute('d',edge.d);path.setAttribute('class',layer==='base'?'ao-edge':'flow-path'+(edge.active?' is-active':''));
      }}
    });
  }
  async function selectTask(id){
    state.selected=id;state.bundle=null;navigate('tasks');renderTasks();
    const t=state.tasks.find(t=>t.id===id);if(!t)return;
    const detail=$('[data-task-detail]');detail.hidden=false;
    detail.innerHTML=`<div class="ao-actions ao-spread"><h3>${short(id)} · ${esc(title(t))}</h3>${chip(t.status)}</div><p class="ao-sub ao-wrap">${esc(t.prompt)}</p><div class="ao-detail-grid"><div><label>Base / worktree</label><p class="ao-wrap">${esc(t.base)}<br>orch/${esc(t.id)}</p></div><div><label>Phạm vi</label><p>${esc(t.allow_paths.join(', '))}</p></div><div><label>Test</label><p>${esc(testSummary(t))}</p></div></div>${t.result?.error?`<div class="ao-notice error">${esc(t.result.error)}</div>`:''}<div class="ao-actions"><button class="ao-btn" data-detail="log">Log worker</button><button class="ao-btn" data-detail="events">Sự kiện</button>${['awaiting_review','approved','changes_requested'].includes(t.status)?'<button class="ao-btn" data-detail="diff">Xem diff & test</button>':''}${['queued','running'].includes(t.status)&&!t.cancel_requested?'<button class="ao-btn ao-danger" data-detail="cancel">Hủy nhiệm vụ</button>':''}<button class="ao-btn" data-detail="retry">Giao việc tiếp</button></div><div class="ao-detail-content" data-detail-content></div><div data-review-controls></div>`;
    detail.scrollIntoView({block:'nearest',behavior:'smooth'});icons();
  }
  async function detailAction(action){
    const id=state.selected,t=state.tasks.find(t=>t.id===id);if(!t)return;const content=$('[data-detail-content]');
    if(action==='retry'){openForm(t.provider,t.prompt,t.allow_paths.join(', '));return;}
    if(action==='cancel'){await api(`/tasks/${id}/cancel`,{});notify('Đã yêu cầu hủy. Worktree và log được giữ lại.');await refreshData();await selectTask(id);return;}
    if(action==='events'){const events=await api(`/tasks/${id}/events`);if(id!==state.selected)return;content.innerHTML='<pre class="ao-code"></pre>';content.firstChild.textContent=events.map(e=>`${e.time} ${e.kind}\n${JSON.stringify(e.data,null,2)}`).join('\n\n')||'Chưa có sự kiện.';return;}
    if(action==='log'){content.innerHTML=`<div class="ao-actions"><label>Giai đoạn <select class="ao-filter" data-log-stage><option value="worker">worker</option>${t.tests.map(n=>`<option value="test-${esc(n)}">test-${esc(n)}</option>`).join('')}</select></label><select class="ao-filter" data-log-stream aria-label="Luồng log"><option>stdout</option><option>stderr</option></select><button class="ao-btn" data-detail="refresh-log">Làm mới</button></div><pre class="ao-code" data-detail-log>Đang đọc…</pre>`;return detailAction('refresh-log');}
    if(action==='refresh-log'){const stage=$('[data-log-stage]').value,stream=$('[data-log-stream]').value,log=await api(`/tasks/${id}/logs?stage=${encodeURIComponent(stage)}&stream=${stream}`);if(id!==state.selected||!$('[data-detail-log]'))return;$('[data-detail-log]').textContent=(log.truncated?'[64 KB cuối log]\n':'')+(log.available?log.text||'(log trống)':'Chưa có file log.');return;}
    if(action==='diff'){
      state.bundle=null;$('[data-review-controls]').replaceChildren();content.textContent='Đang kiểm tra snapshot và patch…';const bundle=await api(`/tasks/${id}/review`);if(id!==state.selected)return;state.bundle=bundle;
      content.innerHTML=`<h3>Bằng chứng test</h3><pre class="ao-code" data-evidence></pre><p class="ao-sub ao-wrap">SHA-256: ${esc(bundle.patch_sha256)}</p><p class="ao-sub">${esc(bundle.changed_files.join(', '))}</p><pre class="ao-code ao-diff" data-diff></pre>${bundle.diff_truncated?'<div class="ao-notice">Diff hiển thị bị rút gọn. Tải và đọc toàn bộ patch trước khi duyệt.</div>':''}<button class="ao-btn" data-detail="full-diff">Tải toàn bộ diff</button>`;$('[data-evidence]').textContent=JSON.stringify(bundle.tests,null,2);$('[data-diff]').textContent=bundle.diff;
      $('[data-review-controls]').innerHTML=t.status==='awaiting_review'?`<label class="ao-field">Nhận xét review<textarea data-review-notes maxlength="12000" placeholder="Ghi nội dung đã kiểm tra và kết luận…"></textarea></label><label class="ao-check"><input type="checkbox" data-review-ack> Tôi đã đọc diff, yêu cầu và bằng chứng test${bundle.diff_truncated?' (bao gồm file patch đầy đủ)':''}.</label><div class="ao-actions"><button class="ao-btn ao-btn-primary" data-review="approve">Duyệt patch</button><button class="ao-btn" data-review="request_changes">Yêu cầu chỉnh sửa</button></div>`:t.status==='approved'?'<button class="ao-btn ao-btn-primary" data-detail="export">Xuất patch & manifest</button>':`<div class="ao-notice">${esc(t.result?.review?.notes||'Đã yêu cầu chỉnh sửa.')}</div>`;return;
    }
    if(action==='full-diff')return download(`/tasks/${id}/diff`,'changes.patch');
    if(action==='export'){const result=await api(`/tasks/${id}/export`,{});if(id!==state.selected)return;notify('Đã xuất patch và manifest. Mã chưa được tích hợp.');$('[data-review-controls]').innerHTML=`<div class="ao-notice ao-wrap">${esc(result.patch)}<br>${esc(result.manifest)}</div><div class="ao-actions"><button class="ao-btn" data-detail="download-patch">Tải changes.patch</button><button class="ao-btn" data-detail="download-manifest">Tải manifest.json</button></div>`;return;}
    if(action.startsWith('download-')){const key=action.slice(9);return download(`/tasks/${id}/download/${key}`,key==='patch'?'changes.patch':'manifest.json');}
  }
  const terms=new Map();
  function liveTerm(id){const e=terms.get(id);return !!e&&!e.dead;}
  function placeTerm(w){const e=terms.get(w.id),card=$(`[data-window="${w.id}"]`);if(!e||!card)return;const host=card.querySelector('[data-term-host]');host.hidden=false;card.querySelector('[data-window-output]').hidden=true;const hist=card.querySelector('.ao-terminal-history');if(hist)hist.hidden=true;if(e.el.parentNode!==host)host.appendChild(e.el);if(!e.opened){e.opened=true;try{e.term.open(e.el);}catch(error){e.opened=false;}}if(e.observer)e.observer.disconnect();e.observer=new ResizeObserver(()=>{try{e.fit.fit();}catch(_){}});e.observer.observe(host);requestAnimationFrame(()=>{try{e.fit.fit();}catch(_){}});}
  function attachTerm(info){
    const term=new Terminal({cursorBlink:true,fontSize:13,fontFamily:'Consolas,"Courier New",monospace',scrollback:5000,theme:{background:'#0b1017'}});
    const fit=new FitAddon.FitAddon();term.loadAddon(fit);
    const el=document.createElement('div');el.className='ao-term-el';
    const e={term,fit,el,after:0,dead:false,id:info.id,queue:Promise.resolve()};terms.set(info.id,e);
    term.onData(d=>{e.queue=e.queue.then(()=>api(`/terminals/${e.id}/input`,{data:d})).catch(()=>{});});
    term.onResize(({cols,rows})=>{api(`/terminals/${e.id}/resize`,{cols,rows}).catch(()=>{});});
    streamLoop();return e;
  }
  let streaming=false;
  async function streamLoop(){
    if(streaming)return;streaming=true;
    try{while(terms.size){
      const live=[...terms.values()].filter(e=>!e.dead&&!e.ended);
      if(!live.length){await new Promise(r=>setTimeout(r,1000));continue;}
      try{
        const r=await api('/terminals/stream?c='+encodeURIComponent(live.map(e=>e.id+':'+e.after).join(','))+'&wait=6');
        for(const [id,x] of Object.entries(r)){
          const e=terms.get(id);if(!e)continue;
          if(x.gone){e.dead=true;continue;}
          if(x.data){const bin=atob(x.data),bytes=new Uint8Array(bin.length);for(let k=0;k<bin.length;k++)bytes[k]=bin.charCodeAt(k);e.term.write(bytes);}
          e.after=x.next;
          if(!x.alive){e.ended=true;e.term.write('\r\n\x1b[33m[Terminal đã kết thúc (mã '+x.exit_code+'). Bấm "Đóng terminal" để xóa cửa sổ này.]\x1b[0m\r\n');}
        }
      }catch(error){await new Promise(r=>setTimeout(r,1500));}
    }}finally{streaming=false;}
  }
  function dropTerm(id){const e=terms.get(id);if(!e)return;e.dead=true;if(e.observer)e.observer.disconnect();e.term.dispose();terms.delete(id);}
  async function syncTerms(){
        
    const list=await api('/terminals');const ids=new Set(list.map(s=>s.id));let changed=list.length!==state.sessions.length||list.some((s,i)=>state.sessions[i]?.id!==s.id);
    state.sessions=list;
    for(const s of list)if(!terms.has(s.id)){try{attachTerm(s);}catch(error){console.error(error);}changed=true;}
    for(const id of [...terms.keys()])if(!ids.has(id)){dropTerm(id);changed=true;}
    if(!state.agent0Tried&&state.config&&state.config.execution_enabled&&!state.config.demo&&!ids.has('agent0')){state.agent0Tried=true;try{await api('/terminals/open',{kind:'agent0',cols:100,rows:30});return syncTerms();}catch(error){notify('Agent 0: '+error.message,true);}}
    state.agent0Tried=true;
    if(changed)renderWindows();  }
  async function toggleTerm(w){
    if(!w.session){await api('/terminals/open',{kind:'agent0',cols:100,rows:30});}
    else{const id=w.session.id;await api(`/terminals/${id}/close`,{}).catch(()=>{});dropTerm(id);}
    await syncTerms();renderWindows();
  }
  window.addEventListener('resize',()=>terms.forEach(e=>{try{e.fit.fit();}catch(_){}}));
  function buildWindows(){
    const windows=state.sessions.map(s=>({id:s.id,name:s.title,kind:s.kind==='agent0'?'agent0':(s.provider||'system'),session:s}));
    if(!windows.some(w=>w.id==='agent0'))windows.unshift({id:'agent0',name:'Agent 0 · Điều phối',kind:'agent0',session:null});
    const existing=new Map(windows.map(w=>[w.id,w]));if(!state.order.includes('agent0'))state.order.unshift('agent0');
    state.windows=[...state.order.filter(id=>existing.has(id)).map(id=>existing.get(id)),...windows.filter(w=>!state.order.includes(w.id))];state.order=state.windows.map(w=>w.id);
  }
  function windowTask(){return null;}
  function visibleWindows(){if(state.focus)return state.windows.filter(w=>w.id===state.focus);const size=layouts[state.layout][0]*layouts[state.layout][1];return state.mode==='all'?state.windows:state.windows.slice((state.windowPage-1)*size,state.windowPage*size);}
  function renderWindows(){
    buildWindows();const size=layouts[state.layout][0]*layouts[state.layout][1],count=Math.max(1,Math.ceil(state.windows.length/size));state.windowPage=Math.min(count,state.windowPage);
    $$('[data-console-layout]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.consoleLayout===state.layout)));$$('[data-console-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.consoleMode===state.mode)));
    $('[data-console-grid]').style.setProperty('--console-cols',state.focus?1:layouts[state.layout][1]);$('[data-console-grid]').style.setProperty('--console-rows',state.focus?1:(state.mode==='all'?Math.max(1,Math.ceil(state.windows.length/layouts[state.layout][1])):layouts[state.layout][0]));root.style.setProperty('--console-rows',state.focus?1:layouts[state.layout][0]);
    $('[data-console-grid]').innerHTML=visibleWindows().map(w=>`<article class="ao-terminal" data-window="${esc(w.id)}"><header class="ao-terminal-head"><div class="ao-terminal-title-row"><button type="button" class="ao-terminal-drag" draggable="true" data-drag="${esc(w.id)}" aria-label="Di chuyển ${esc(w.name)} bằng Alt và phím mũi tên">⠿</button><span class="ao-terminal-role ${w.kind}"><i data-lucide="${w.kind==='claude'?'sparkles':w.kind==='codex'?'terminal':'square-terminal'}"></i></span><span class="ao-terminal-name">${esc(w.name)}</span><button class="ao-terminal-tool" data-focus="${esc(w.id)}" aria-label="${state.focus?'Thu nhỏ':'Phóng to'} ${esc(w.name)}"><i data-lucide="${state.focus?'minimize-2':'maximize-2'}"></i></button></div><div class="ao-terminal-meta"><code data-window-path>Queue local</code><span data-window-status></span></div></header><pre class="ao-terminal-output" data-window-output role="log" aria-label="Log ${esc(w.name)}"></pre><div class="ao-term-host" data-term-host hidden></div><div class="ao-terminal-history"><button data-history="${esc(w.id)}">Xem log mở rộng</button><span>LOCAL · ${w.taskId?'TASK':'MONITOR'}</span></div><div class="ao-term-actions"><button type="button" class="ao-btn" data-term-toggle="${esc(w.id)}">${w.session?'Đóng terminal':'Mở Agent 0'}</button><span class="ao-term-hint">${w.id==='agent0'?'Gõ yêu cầu giao việc tại đây':esc(w.session?w.session.cwd:'')}</span></div></article>`).join('');
    $('[data-console-count]').textContent=state.windows.length+' cửa sổ';$('[data-console-active]').textContent=state.tasks.filter(t=>t.status==='running').length+' task đang chạy';$('[data-console-range]').textContent=state.focus?'Đang phóng to một cửa sổ':state.mode==='all'?'Tất cả cửa sổ':`Trang ${state.windowPage}/${count} · ${size} cửa sổ/trang`;
    $('[data-console-focusbar]').hidden=!state.focus;$('[data-console-focusname]').textContent='Đang phóng to · '+(state.windows.find(w=>w.id===state.focus)?.name||'');
    const pager=$('[data-console-pager]');pager.hidden=!!state.focus||state.mode==='all';pager.innerHTML=Array.from({length:count},(_,i)=>`<button data-window-page="${i+1}" aria-current="${state.windowPage===i+1?'page':'false'}">${i+1}</button>`).join('');
    for(const w of visibleWindows()){updateWindow(w,state.outputs.get(w.id)||'Chưa có log.');if(terms.has(w.id))placeTerm(w);}icons();save();
  }
  function updateWindow(w,text){const card=$(`[data-window="${w.id}"]`);if(!card)return;const task=windowTask(w);const sess=w.session;card.querySelector('[data-window-path]').textContent=w.id==='agent0'?'Claude Code · MCP':sess?({claude:'Claude Code',codex:'Codex CLI',agy:'Antigravity CLI'}[sess.provider]||sess.provider):'';card.querySelector('[data-window-status]').textContent=w.id==='agent0'?(state.agent0.connected?'Đã kết nối':'Chưa kết nối'):sess?(sess.alive?'Đang chạy':'Đã kết thúc'):'';const output=card.querySelector('[data-window-output]');if(output.textContent!==text){const atBottom=output.scrollTop+output.clientHeight>=output.scrollHeight-30;output.textContent=text;if(atBottom)output.scrollTop=output.scrollHeight;}}
  async function refreshWindows(){await Promise.all(visibleWindows().map(async w=>{let text;try{
    if(w.id==='agent0'){const a=state.agent0,seen=a.idle_seconds==null?'':a.idle_seconds<60?a.idle_seconds+' giây trước':Math.round(a.idle_seconds/60)+' phút trước';
      const head=a.connected?'● ĐÃ KẾT NỐI · '+(a.client||'Claude Code')+'\nHoạt động MCP gần nhất: '+(a.last_tool||'(chưa gọi tool)')+(seen?' · '+seen:'')+'\n\nGõ yêu cầu trực tiếp trong cửa sổ terminal "Agent 0" (Claude Code).':'○ CHƯA KẾT NỐI\nChưa thấy phiên Claude Code nào gắn MCP orchestrator.\nMở lại bằng lối tắt Agent Studio, hoặc chạy Start-Agent0.cmd CONFIG.';
      text=head+'\n\n— Việc Agent 0 giao / review gần đây —\n'+(state.events.slice(0,12).map(e=>`${time(e.time)} ${short(e.task_id)} ${e.kind}`).join('\n')||'Chưa có sự kiện.');}
    else text='';
    state.outputs.set(w.id,text);updateWindow(w,text);
    }catch(error){updateWindow(w,'Không đọc được log: '+error.message);}}));}
  function runnerLabel(){
    if(state.config?.demo)return 'OFFLINE DEMO · KHÔNG GỌI MODEL';
    if(!state.config?.execution_enabled)return 'LOCAL · KHÓA THỰC THI';
    const runners=Object.values(state.runners.providers);
    if(runners.some(r=>r.status==='error'))return 'LOCAL · RUNNER LỖI';
    return runners.some(r=>['idle','polling','busy','starting'].includes(r.status))?'LOCAL · RUNNER ĐANG MỞ':'LOCAL · CHƯA CÓ RUNNER GIÁM SÁT';
  }
  async function refreshData(){const prior=state.tasks.find(t=>t.id===state.selected)?.status;const [tasks,events,runners,agent0]=await Promise.all([api('/tasks'),api('/activity'),api('/runners'),api('/agent0').catch(()=>({connected:false}))]);state.agent0=agent0;state.tasks=tasks;state.events=events;state.runners=runners;$('.ao-demo').textContent=runnerLabel();$('.ao-demo').classList.toggle('error',Object.values(runners.providers).some(r=>r.status==='error'));renderTasks();await syncTerms().catch(e=>{notify('Terminal: '+e.message,true);});buildWindows();$('[data-console-active]').textContent=tasks.filter(t=>t.status==='running').length+' task đang chạy';await refreshWindows();if(!state.busy&&state.page==='tasks'&&state.selected&&prior!==tasks.find(t=>t.id===state.selected)?.status)await selectTask(state.selected);}
  async function runAction(fn){if(state.busy)return;state.busy=true;root.setAttribute('aria-busy','true');$$('[data-review],[data-detail="export"],[data-action="create-task"]').forEach(b=>b.disabled=true);try{await fn();}catch(error){notify(error.message,true);}finally{state.busy=false;root.removeAttribute('aria-busy');$$('[data-review],[data-detail="export"],[data-action="create-task"]').forEach(b=>b.disabled=false);}}
  function openForm(provider,prompt='',scope='src, tests'){navigate('tasks');form.hidden=false;form.elements.prompt.value=prompt;form.elements.scope.value=scope;if(provider&&state.config?.providers[provider])form.elements.provider.value=provider;form.elements.prompt.focus();}
  form.addEventListener('submit',event=>{event.preventDefault();runAction(async()=>{if(!form.reportValidity())return;const data=new FormData(form),tests=data.getAll('tests');if(!tests.length)throw Error('Chọn ít nhất một test profile.');const result=await api('/tasks',{provider:data.get('provider'),prompt:String(data.get('prompt')).trim(),allow_paths:String(data.get('scope')).split(/[,\n]/).map(x=>x.trim()).filter(Boolean),tests});form.hidden=true;form.elements.prompt.value='';notify('Đã thêm task '+short(result.id)+' vào hàng đợi.');await refreshData();await selectTask(result.id);});});
  const modal=document.createElement('dialog');modal.className='ao-window-dialog';modal.innerHTML='<form method="dialog"><h2>Thêm terminal agent</h2><label>Agent<select data-add-agent required></select></label><label>Thư mục làm việc<select data-add-folder></select></label><p>Mở một phiên tương tác thật. Agent 0 theo dõi được (chỉ đọc) qua list_terminals / read_terminal.</p><div class="ao-actions"><button value="cancel">Đóng</button><button value="add">Mở terminal</button></div></form>';root.append(modal);
  modal.addEventListener('close',()=>{if(modal.returnValue!=='add')return;const provider=modal.querySelector('[data-add-agent]').value,task=modal.querySelector('[data-add-folder]').value;if(state.sessions.length>=12){notify('Tối đa 12 terminal.',true);return;}runAction(async()=>{const info=await api('/terminals/open',{kind:'agent',provider,...(task?{task_id:task}:{}),cols:100,rows:30});state.focus=null;await syncTerms();const idx=state.windows.findIndex(w=>w.id===info.id);if(idx>=0)state.windowPage=Math.floor(idx/(layouts[state.layout][0]*layouts[state.layout][1]))+1;renderWindows();});});
  root.addEventListener('input',e=>{if(e.target.dataset.command)state.drafts.set(e.target.dataset.command,e.target.value);});
  root.addEventListener('click',event=>{
    const target=event.target,page=target.closest('[data-page]');if(page){navigate(page.dataset.page);requestAnimationFrame(()=>terms.forEach(e=>{try{e.fit.fit();}catch(_){}}));return;}
    const toggle=target.closest('[data-term-toggle]');if(toggle){const w=state.windows.find(x=>x.id===toggle.dataset.termToggle);if(w)runAction(()=>toggleTerm(w));return;}
    const task=target.closest('[data-task]');if(task){runAction(()=>selectTask(task.dataset.task));return;}
    const action=target.closest('[data-action]')?.dataset.action;if(action==='new-task')openForm();if(action==='close-form')form.hidden=true;
    const detail=target.closest('[data-detail]');if(detail){runAction(()=>detailAction(detail.dataset.detail));return;}
    const review=target.closest('[data-review]');if(review){runAction(async()=>{if(!state.bundle||state.bundle.id!==state.selected)throw Error('Mở lại diff để lấy digest hiện tại.');if(!$('[data-review-ack]').checked)throw Error('Xác nhận đã đọc diff và bằng chứng test.');const notes=$('[data-review-notes]').value.trim();if(!notes)throw Error('Nhập nhận xét review.');const id=state.selected;await api(`/tasks/${id}/review`,{verdict:review.dataset.review,patch_sha256:state.bundle.patch_sha256,notes});notify('Đã ghi nhận review cho đúng digest.');await refreshData();await selectTask(id);await detailAction('diff');});return;}
    const node=target.closest('[data-node]');if(node){const kind=node.dataset.node;state.flowNode=kind;const t=state.tasks.find(t=>t.id===node.dataset.taskId);if(t)runAction(()=>selectTask(t.id));else notify('Chưa có nhiệm vụ tại bước này.');return;}
    if(action==='open-task'){const t=state.tasks.find(t=>t.status==='awaiting_review')||state.tasks[0];if(t)runAction(()=>selectTask(t.id));else navigate('tasks');}
    const layout=target.closest('[data-console-layout]');if(layout){state.layout=layout.dataset.consoleLayout;state.focus=null;state.windowPage=1;renderWindows();refreshWindows();closeSettings();}
    const mode=target.closest('[data-console-mode]');if(mode){state.mode=mode.dataset.consoleMode;state.focus=null;renderWindows();refreshWindows();closeSettings();}
    const wp=target.closest('[data-window-page]');if(wp){state.windowPage=Number(wp.dataset.windowPage);renderWindows();refreshWindows();}
    const focus=target.closest('[data-focus]');if(focus){state.focus=state.focus?null:focus.dataset.focus;renderWindows();refreshWindows();}
    const historyButton=target.closest('[data-history]');if(historyButton){const card=historyButton.closest('[data-window]');card.classList.toggle('ao-expanded');historyButton.textContent=card.classList.contains('ao-expanded')?'Thu gọn log':'Xem log mở rộng';}
    const consoleAction=target.closest('[data-console-action]')?.dataset.consoleAction;
    if(consoleAction==='unfocus'){state.focus=null;renderWindows();refreshWindows();}
    if(consoleAction==='feed')runAction(refreshData);
    if(consoleAction==='add'){closeSettings();const names={claude:'Claude',codex:'Codex',agy:'Antigravity (agy)'},agents=state.config?.terminal_agents||[];if(!agents.length){notify('Chưa cấu hình agent nào trong config.',true);return;}modal.querySelector('[data-add-agent]').innerHTML=agents.map(a=>`<option value="${a}">${names[a]||a}</option>`).join('');modal.querySelector('[data-add-folder]').innerHTML='<option value="">Repo chính · '+esc((state.config.repo||'').split(/[\/]/).pop())+'</option>'+state.tasks.map(t=>`<option value="${t.id}">Worktree task ${short(t.id)} · ${esc(title(t))}</option>`).join('');modal.showModal();}
    if(target.closest('[data-console-settings-toggle]')){const panel=$('.ao-console-settings-panel');panel.hidden=!panel.hidden;$('[data-console-settings-toggle]').setAttribute('aria-expanded',String(!panel.hidden));}
    if(target.closest('[data-console-settings-close]'))closeSettings(true);
  });
  function closeSettings(focus=false){$('.ao-console-settings-panel').hidden=true;$('[data-console-settings-toggle]').setAttribute('aria-expanded','false');if(focus)$('[data-console-settings-toggle]').focus();}
  document.addEventListener('click',e=>{if(!bar.contains(e.target))closeSettings();});
  function reorder(from,to){const ids=state.windows.map(w=>w.id),a=ids.indexOf(from),b=ids.indexOf(to);if(a<0||b<0||a===b)return;ids.splice(a,1);ids.splice(b,0,from);state.order=ids;renderWindows();refreshWindows();$('[data-console-announce]').textContent='Đã sắp xếp cửa sổ.';}
  let dragged=null;
  root.addEventListener('dragstart',e=>{const handle=e.target.closest('[data-drag]');if(!handle)return;dragged=handle.dataset.drag;e.dataTransfer.setData('text/plain',dragged);});
  root.addEventListener('dragover',e=>{if(dragged&&e.target.closest('[data-window]'))e.preventDefault();});
  root.addEventListener('drop',e=>{const card=e.target.closest('[data-window]');if(dragged&&card){e.preventDefault();reorder(dragged,card.dataset.window);}dragged=null;});root.addEventListener('dragend',()=>dragged=null);
  root.addEventListener('keydown',e=>{if(e.key==='Escape')closeSettings(true);const handle=e.target.closest('[data-drag]');if(handle&&e.altKey&&['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();const i=state.windows.findIndex(w=>w.id===handle.dataset.drag),other=state.windows[i+(e.key==='ArrowLeft'?-1:1)];if(other){const id=handle.dataset.drag;reorder(id,other.id);$(`[data-drag="${id}"]`)?.focus();}}});
  search.addEventListener('input',renderTasks);$('[data-task-filter]').addEventListener('change',renderTasks);
  new ResizeObserver(drawEdges).observe(root);navigate(state.page);renderTasks();renderWindows();icons();
  async function start(){try{configure(await api('/config'));await refreshData();}catch(error){$('.ao-demo').textContent='CHƯA KẾT NỐI';$('.ao-demo').classList.add('error');notify(error.message,true);}finally{setTimeout(tick,3000);}}
  async function tick(){if(!document.hidden&&!state.busy){try{if(!state.config)configure(await api('/config'));await refreshData();}catch(error){$('.ao-demo').textContent='MẤT KẾT NỐI';$('.ao-demo').classList.add('error');}}setTimeout(tick,3000);}
  start();
})();
