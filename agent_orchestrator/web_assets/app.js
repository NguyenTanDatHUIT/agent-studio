'use strict';
(() => {
  const root = document.getElementById('ao-studio');
  const $ = s => root.querySelector(s), $$ = s => [...root.querySelectorAll(s)];
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = {queued:'Trong hàng đợi',running:'Đang thực hiện',awaiting_review:'Chờ review',approved:'Đã duyệt',changes_requested:'Cần chỉnh sửa',failed:'Thất bại',cancelled:'Đã hủy'};
  const pages = {terminals:['Cửa sổ CMD','Không gian dòng lệnh','Log worker, test và sự kiện được cập nhật từ queue.'],overview:['Tổng quan','Trung tâm điều phối','Giao việc rõ ràng. Theo dõi xuyên suốt. Duyệt từng thay đổi.'],flow:['Luồng tự động','Nhìn rõ từng bước chạy','Luồng động kích hoạt khi Agent 0 gọi agent hoặc giao việc.'],tasks:['Nhiệm vụ','Mỗi nhiệm vụ, một worktree','Phân công, xem bằng chứng test và duyệt thay đổi.'],reports:['Báo cáo','Hiệu quả vận hành','Tổng hợp tối đa 200 nhiệm vụ gần nhất; usage thiếu được giữ nguyên.'],permissions:['Quyền & bảo vệ','Tự động hóa có giới hạn','Chính sách hiện tại và quyền thực thi local.']};
  let pref={};try {pref=JSON.parse(localStorage.getItem('agent-studio-ui')||'{}')||{};}catch {}
  const layouts = {'1x2':[1,2], '2x2':[2,2], '2x3':[2,3], '3x3':[3,3]};
  const parseLayout=text=>{const m=/^\s*(\d{1,2})\s*[x×X]\s*(\d{1,2})\s*$/.exec(String(text));if(!m)return null;const r=+m[1],c=+m[2];return r>=1&&c>=1&&r<=6&&c<=6?{key:`${r}x${c}`,dims:[r,c]}:null;};
  {const d=typeof pref.layout==='string'&&!Object.hasOwn(layouts,pref.layout)?parseLayout(pref.layout):null;if(d)layouts[d.key]=d.dims;}
  const state={page:Object.hasOwn(pages,pref.page)?pref.page:'terminals',layout:Object.hasOwn(layouts,pref.layout)?pref.layout:'2x2',mode:pref.mode==='all'?'all':'paged',windowPage:1,focus:null,order:Array.isArray(pref.order)?pref.order:[],extra:Array.isArray(pref.extra)?pref.extra.filter(x=>/^w[a-f0-9]+$/.test(x.id||'')&&/^[0-9a-f]{24}$/.test(x.taskId||'')).slice(0,30):[],tasks:[],events:[],sessions:[],agent0:{connected:false},runners:{managed:false,providers:{}},selected:null,config:null,bundle:null,busy:false,windows:[],outputs:new Map(),drafts:new Map(),streams:new Map(),sound:pref.sound!==false};
  const hash=new URLSearchParams(location.hash.slice(1));
  const token=hash.get('token')||sessionStorage.getItem('agent-studio-token')||'';
  if(hash.has('token')){sessionStorage.setItem('agent-studio-token',token);history.replaceState(null,'',location.pathname);}
  function save(){try {localStorage.setItem('agent-studio-ui',JSON.stringify({page:state.page,layout:state.layout,mode:state.mode,order:state.order,extra:state.extra,side:state.side,theme:state.theme,palette:state.palette,wheel:state.wheel,sound:state.sound}));}catch {}}
  const icons=()=>globalThis.lucide?.createIcons({attrs:{width:16,height:16}});
  const title=t=>(t.prompt||'').split('\n')[0],short=id=>id?.slice(0,8)||'—';
  const time=value=>value?new Date(value).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'—';
  const number=value=>typeof value==='number'?value.toLocaleString('vi-VN'):'Chưa có';
  const chip=status=>`<span class="ao-chip ${status==='failed'?'bad':['awaiting_review','changes_requested'].includes(status)?'review':['approved','running'].includes(status)?'good':''}"><span class="ao-dot"></span>${esc(labels[status]||status)}</span>`;
  const agentLogos={
    claude:'<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.3916z"/></svg>',
    agent0:'<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.3916z"/></svg>',
    codex:'<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="M9.205 8.658v-2.26c0-.19.072-.333.238-.428l4.543-2.616c.619-.357 1.356-.523 2.117-.523 2.854 0 4.662 2.212 4.662 4.566 0 .167 0 .357-.024.547l-4.71-2.759a.797.797 0 00-.856 0l-5.97 3.473zm10.609 8.8V12.06c0-.333-.143-.57-.429-.737l-5.97-3.473 1.95-1.118a.433.433 0 01.476 0l4.543 2.617c1.309.76 2.189 2.378 2.189 3.948 0 1.808-1.07 3.473-2.76 4.163zM7.802 12.703l-1.95-1.142c-.167-.095-.239-.238-.239-.428V5.899c0-2.545 1.95-4.472 4.591-4.472 1 0 1.927.333 2.712.928L8.23 5.067c-.285.166-.428.404-.428.737v6.898zM12 15.128l-2.795-1.57v-3.33L12 8.658l2.795 1.57v3.33L12 15.128zm1.796 7.23c-1 0-1.927-.332-2.712-.927l4.686-2.712c.285-.166.428-.404.428-.737v-6.898l1.974 1.142c.167.095.238.238.238.428v5.233c0 2.545-1.974 4.472-4.614 4.472zm-5.637-5.303l-4.544-2.617c-1.308-.761-2.188-2.378-2.188-3.948A4.482 4.482 0 014.21 6.327v5.423c0 .333.143.571.428.738l5.947 3.449-1.95 1.118a.432.432 0 01-.476 0zm-.262 3.9c-2.688 0-4.662-2.021-4.662-4.519 0-.19.024-.38.047-.57l4.686 2.71c.286.167.571.167.856 0l5.97-3.448v2.26c0 .19-.07.333-.237.428l-4.543 2.616c-.619.357-1.356.523-2.117.523zm5.899 2.83a5.947 5.947 0 005.827-4.756C22.287 18.339 24 15.84 24 13.296c0-1.665-.713-3.282-1.998-4.448.119-.5.19-.999.19-1.498 0-3.401-2.759-5.947-5.946-5.947-.642 0-1.26.095-1.88.31A5.962 5.962 0 0010.205 0a5.947 5.947 0 00-5.827 4.757C1.713 5.447 0 7.945 0 10.49c0 1.666.713 3.283 1.998 4.448-.119.5-.19 1-.19 1.499 0 3.401 2.759 5.946 5.946 5.946.642 0 1.26-.095 1.88-.309a5.96 5.96 0 004.162 1.713z"/></svg>',
    agy:'<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="M12.24 10.285V14.4h6.806c-.275 1.765-2.056 5.174-6.806 5.174-4.095 0-7.439-3.389-7.439-7.574s3.345-7.574 7.439-7.574c2.33 0 3.891.989 4.785 1.849l3.254-3.138C18.189 1.186 15.479 0 12.24 0c-6.635 0-12 5.365-12 12s5.365 12 12 12c6.926 0 11.52-4.869 11.52-11.726 0-.788-.085-1.39-.189-1.989H12.24z"/></svg>'
  };
  const agentLogo=kind=>agentLogos[kind]||'<i data-lucide="square-terminal"></i>';
  function notify(text,error=false){const e=$('[data-toast]');e.hidden=false;e.textContent=text;e.classList.toggle('error',error);}
  let audioCtx=null;
  function getAudioContext(){
    if(!audioCtx&&(window.AudioContext||window.webkitAudioContext)){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)();}catch(_){}}
    if(audioCtx&&audioCtx.state==='suspended'){audioCtx.resume().catch(()=>{});}
    return audioCtx;
  }
  window.addEventListener('click',()=>getAudioContext(),{once:true});
  function playChime(kind='success'){
    if(state.sound===false)return;
    try{
      const ctx=getAudioContext();if(!ctx)return;
      const now=ctx.currentTime,osc=ctx.createOscillator(),gain=ctx.createGain();
      osc.type='sine';
      if(kind==='error'){osc.frequency.setValueAtTime(440,now);osc.frequency.setValueAtTime(311.13,now+0.12);}
      else{osc.frequency.setValueAtTime(587.33,now);osc.frequency.setValueAtTime(880,now+0.12);}
      gain.gain.setValueAtTime(0.18,now);gain.gain.exponentialRampToValueAtTime(0.001,now+0.45);
      osc.connect(gain);gain.connect(ctx.destination);osc.start(now);osc.stop(now+0.45);
    }catch(_){}
  }
  function speakText(text){
    if(state.sound===false||!window.speechSynthesis)return;
    try{window.speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.lang='vi-VN';u.rate=1.05;u.volume=1.0;window.speechSynthesis.speak(u);}catch(_){}
  }
  function agentDisplayName(task){
    const provider=task.provider||'worker';
    return task.agent?`Agent ${task.agent} (${provider})`:provider;
  }
  const seenTaskStatuses=new Map();
  function checkTaskSoundAlerts(newTasks){
    if(!seenTaskStatuses.size){for(const t of newTasks)seenTaskStatuses.set(t.id,t.status);return;}
    for(const t of newTasks){
      const prev=seenTaskStatuses.get(t.id);
      if(prev&&prev!==t.status){
        seenTaskStatuses.set(t.id,t.status);
        const name=agentDisplayName(t);
        if(t.status==='awaiting_review'){
          const msg=`${name} đã làm xong công việc, chờ review!`;
          playChime('success');speakText(msg);notify(msg);
        }else if(t.status==='failed'){
          const msg=`${name} gặp sự cố khi làm nhiệm vụ!`;
          playChime('error');speakText(msg);notify(msg,true);
        }else if(t.status==='approved'){
          const msg=`Nhiệm vụ của ${name} đã được phê duyệt!`;
          playChime('success');speakText(msg);
        }
      }else if(!prev){
        seenTaskStatuses.set(t.id,t.status);
      }
    }
  }
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
  const reload=inventory.querySelector('[data-console-action="feed"]');reload.textContent='Làm mới log';bar.querySelector('[data-compact-extra-mount]').append(reload);
  toolbar.replaceWith(bar);inventory.remove();
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
    state.config=config;const repoName=config.repo.split(/[\\/]/).pop();$('.ao-project').innerHTML=`<strong>${esc(repoName)}</strong><small>Nhánh cơ sở · ${esc(config.base_ref)}</small><small title="${esc(config.repo)}">${esc(config.repo)}</small><button type="button" class="ao-btn ao-repo-switch-btn cursor-interaction" data-action="open-repo-dialog"><i data-lucide="folder-search" aria-hidden="true"></i> Chọn thư mục...</button>`;
    $('.ao-crumb').innerHTML=`<i data-lucide="folder-git-2" style="cursor:pointer" data-action="open-repo-dialog" title="Chọn thư mục..."></i>${esc(repoName)}<span>/</span><strong data-crumb>${pages[state.page][0]}</strong>`;$('.ao-kicker').textContent='WORKSPACE / '+repoName.toUpperCase();
    $('[data-test-options]').innerHTML=config.tests.map((name,i)=>`<label><input type="checkbox" name="tests" value="${esc(name)}" ${i===0?'checked':''}> ${esc(name)}</label>`).join('')||'<span>Chưa cấu hình test profile. Thêm profile trong file cấu hình.</span>';
    [...form.elements.provider.options].forEach(o=>o.disabled=!config.providers[o.value]);const enabled=[...form.elements.provider.options].find(o=>!o.disabled);if(enabled)form.elements.provider.value=enabled.value;
    $('[data-execution]').textContent=config.execution_enabled?'Đã cho phép chạy local':'Đang khóa thực thi';
    const policies=[['shield-check','Claude Worker','Restricted, chỉ đọc/sửa file; không cấp shell.'],['box','Codex Worker','Workspace-write; tắt mạng cho lệnh model theo adapter.'],['file-lock-2','Phạm vi chỉnh sửa','Kiểm tra sau khi chạy; sửa ngoài phạm vi sẽ chặn review/export.'],['terminal','Test profile',config.tests.length?config.tests.join(', ')+' · chạy bằng quyền tài khoản local.':'Chưa cấu hình.'],['fingerprint','Review và digest','Test, snapshot và SHA-256 được kiểm tra lại trước khi duyệt/xuất.'],['git-pull-request','Tích hợp','Người dùng áp dụng patch và kiểm thử lại; không tự commit/merge/push.'],['info','Runner','Launcher dự án mở runner cùng web; Ctrl+C dừng cả hai. Runner mở riêng không được web giám sát.']];
    $('[data-policy]').innerHTML=policies.map(([icon,name,description])=>`<div class="ao-permission"><i data-lucide="${icon}"></i><div>${esc(name)}<p>${esc(description)}</p></div></div>`).join('');icons();
  }
  function testSummary(t){const tests=t.result?.tests||[];return tests.length?`${tests.filter(x=>x.exit_code===0&&!x.reason).length}/${tests.length} profile đạt`:'Chưa có kết quả';}
  function renderTasks(){
    const filter=$('[data-task-filter]').value,term=search.value.toLowerCase(),tasks=state.tasks.filter(t=>(filter==='all'||t.status===filter)&&(!term||(title(t)+' '+t.id).toLowerCase().includes(term)));
    $('[data-task-rows]').innerHTML=tasks.length?tasks.map(t=>`<tr ${t.id===state.selected?'aria-selected="true"':''}><td><strong>${esc(title(t))}</strong><small>${short(t.id)} · ${esc(t.allow_paths.join(', '))}</small></td><td>${esc(t.agent?`${t.provider} ${t.agent}`:t.provider)}${t.round>1?`<small>vòng ${t.round}</small>`:''}</td><td>${chip(t.status)}${t.cancel_requested?'<small>Đã yêu cầu hủy</small>':''}</td><td>${esc(testSummary(t))}</td><td><button class="ao-link" type="button" data-task="${t.id}">Chi tiết →</button></td></tr>`).join(''):'<tr><td colspan="5" class="ao-empty">Không có nhiệm vụ phù hợp. Tạo nhiệm vụ để bắt đầu.</td></tr>';
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
  const sessionState=sess=>sess.kind==='worker'?(!sess.alive?'Đã đóng':sess.idle?'Sẵn sàng':'Đang làm'):(sess.alive?'Đang chạy':'Đã kết thúc');
  const runnerText=p=>{const r=state.runners?.providers?.[p];return r?({starting:'Runner đang khởi động',polling:'Runner đang nhận việc',idle:'Runner sẵn sàng',busy:'Runner đang xử lý',stopped:'Runner đã dừng',error:'Runner lỗi'}[r.status]||r.status):(state.config?.providers?.[p]?'Chưa có runner giám sát':'Chưa cấu hình');};
  const liveCount=p=>state.sessions.filter(x=>x.provider===p&&x.kind==='agent'&&x.alive).length;
  function renderFlow(){
    const counts=s=>state.tasks.filter(t=>t.status===s).length;
    const a0=state.agent0||{},seen=a0.idle_seconds==null?'':a0.idle_seconds<60?a0.idle_seconds+' giây trước':Math.round(a0.idle_seconds/60)+' phút trước';
    const runningCount=counts('running'),reviewCount=counts('awaiting_review'),approvedCount=counts('approved');

    // Luồng làm việc CHỈ hiển thị khi Agent 0 đang điều phối / gọi agent làm việc:
    // 1. Có task đang chạy (running) hoặc trong hàng đợi (queued)
    const inFlightTasks=(state.tasks||[]).filter(t=>['running','queued','awaiting_review'].includes(t.status)).sort((t1,t2)=>(t1.status==='running'?0:1)-(t2.status==='running'?0:1));

    // 2. Hoặc có kế hoạch workflow nhiều bước đang chạy (enqueue_plan)
    const activeWf=(state.workflows||[]).find(w=>w.state==='running'||w.state==='blocked');
    const activeWfTaskIds=new Set(activeWf?(activeWf.steps||[]).map(s=>s.task_id).filter(Boolean):[]);
    const activeWfTasks=(state.tasks||[]).filter(t=>activeWfTaskIds.has(t.id));

    // 3. Hoặc người dùng chủ động chọn xem sơ đồ của một task cụ thể qua state.flowSelectedTask
    const selectedTask=state.flowSelectedTask?(state.tasks||[]).find(t=>t.id===state.flowSelectedTask):null;

    let relevantTasks=[];
    let isViewingTask=false;

    if(inFlightTasks.length>0){
      relevantTasks=inFlightTasks;
    }else if(activeWfTasks.length>0){
      relevantTasks=activeWfTasks;
    }else if(selectedTask){
      relevantTasks=[selectedTask];
      isViewingTask=true;
    }else if(state.tasks?.length>0){
      relevantTasks=state.tasks;
    }

    const rv=relevantTasks.find(t=>t.status==='awaiting_review')||(isViewingTask&&selectedTask?.status==='awaiting_review'?selectedTask:null);
    const ap=relevantTasks.find(t=>t.status==='approved')||(isViewingTask&&selectedTask?.status==='approved'?selectedTask:null);

    const lanes=[];
    const seenKeys=new Set();
    for(const t of relevantTasks){
      const p=t.provider;
      const key=t.agent?`${p}${t.agent}`:p;
      if(seenKeys.has(key))continue;
      seenKeys.add(key);

      const event=state.events.filter(e=>e.task_id===t.id).sort((a,b)=>b.seq-a.seq)[0];
      const workerRunning=t.status==='running'&&event?.kind==='worker_started';
      const testRunning=t.status==='running'&&event?.kind==='test_started';
      const workerDone=testRunning||['awaiting_review','approved','changes_requested'].includes(t.status);
      const tests=t.result?.tests||[],testPassed=tests.length>0&&tests.every(x=>x.exit_code===0&&!x.reason);

      const agentName=(p==='claude'?'Claude':'Codex')+(t.agent?` ${t.agent}`:' Worker');
      const workerDesc='worktree · orch/'+short(t.id);
      const workerText=workerRunning?'Đang xử lý code':workerDone?'✓ Code đã sẵn sàng':(labels[t.status]||'Chờ giao việc');

      const testName='Test · '+agentName;
      const testDesc='Profile · '+(t.tests?.join(', ')||(state.config?.tests||[]).join(', ')||'Chưa cấu hình test');
      const testText=testRunning?'Đang chạy test':testPassed?'✓ '+testSummary(t):tests.length?testSummary(t):t.status==='queued'||workerRunning?'Chờ worker':['failed','cancelled'].includes(t.status)?'Chưa có kết quả · task đã dừng':'Chưa có kết quả';

      lanes.push({
        key,
        provider:p,
        agent:t.agent,
        task:t,
        worker:{name:agentName,desc:workerDesc,text:workerText,running:workerRunning,success:workerDone},
        test:{name:testName,desc:testDesc,text:testText,running:testRunning,success:testPassed}
      });
    }

    if(!relevantTasks.length&&(a0.connected||state.runners?.managed)){
      const provs=['claude','codex'].filter(p=>state.config?.providers?.[p]||state.runners?.providers?.[p]);
      for(const p of (provs.length?provs:['claude','codex'])){
        const runner=state.runners?.providers?.[p];
        const runnerText=runner?({starting:'Runner đang khởi động',polling:'Runner đang nhận việc',idle:'Runner sẵn sàng',busy:'Runner đang xử lý',stopped:'Runner đã dừng',error:'Runner lỗi'}[runner.status]||runner.status):(state.config?.providers?.[p]?'Chưa có runner giám sát':'Chưa cấu hình');
        const agentName=(p==='claude'?'Claude':'Codex')+' Worker';
        lanes.push({
          key:p,
          provider:p,
          agent:null,
          task:null,
          worker:{name:agentName,desc:'Runner '+p,text:runnerText,running:runner?.status==='busy',success:runner?.status==='idle'},
          test:{name:'Test · '+agentName,desc:'Test runner',text:'Chờ worker',running:false,success:false}
        });
      }
    }

    const data={
      agent0:{
        name:'Agent 0',
        desc:a0.connected?'Đã nối MCP · '+(a0.client||'Claude Code'):'Chưa nối MCP',
        text:a0.connected?`● ${a0.last_tool||'đang chờ lệnh'}${seen?' · '+seen:''}`:`○ Chưa kết nối · ${counts('queued')} chờ`,
        task:state.tasks.find(t=>t.status==='queued'),
        success:!!a0.connected
      }
    };

    if(lanes.length){
      data.review={
        name:'Review',
        desc:rv?short(rv.id)+' · '+(rv.result?.changed_files?.length||0)+' file đổi':'Chưa có diff chờ duyệt',
        text:rv?'Task chờ duyệt':reviewCount?`${reviewCount} task chờ duyệt`:'Chờ kiểm tra',
        task:rv
      };
      data.export={
        name:'Xuất patch',
        desc:ap?short(ap.id)+' · sẵn sàng xuất':'Chưa có patch được duyệt',
        text:ap?'Đã duyệt · có thể xuất':approvedCount?`${approvedCount} đã duyệt · có thể xuất`:'Chờ được duyệt',
        task:ap
      };
      for(const l of lanes){
        data[l.key]={name:l.worker.name,desc:l.worker.desc,text:l.worker.text,task:l.task,running:l.worker.running,success:l.worker.success};
        data['test'+l.key]={name:l.test.name,desc:l.test.desc,text:l.test.text,task:l.task,running:l.test.running,success:l.test.success};
      }
    }

    $$('.agent-flow-section').forEach(sec=>{
      let banner=sec.querySelector('.flow-banner');
      if(isViewingTask&&selectedTask){
        if(!banner){
          banner=document.createElement('div');
          banner.className='flow-banner';
          sec.insertBefore(banner,sec.querySelector('.flow-scroller'));
        }
        banner.innerHTML=`<span>Đang xem lại sơ đồ nhiệm vụ: <strong>${short(selectedTask.id)}</strong> (${esc(selectedTask.agent?'Agent '+selectedTask.agent+' · '+selectedTask.provider:selectedTask.provider)}) · ${chip(selectedTask.status)}</span><button type="button" class="flow-banner-close cursor-interaction" data-flow-clear="true">✕ Về trạng thái chờ</button>`;
      }else if(banner){
        banner.remove();
      }
    });

    $$('.ao-flow').forEach(board=>{
      let a0Node=board.querySelector('[data-node="agent0"]');
      if(!a0Node){
        a0Node=document.createElement('button');
        a0Node.type='button';
        a0Node.className='ao-node flow-node flow-node--agent cursor-interaction';
        a0Node.dataset.node='agent0';
        a0Node.setAttribute('aria-pressed','false');
        a0Node.innerHTML='<div class="ao-node-top flow-node__top"><span class="flow-node__type">Điều phối</span><span class="flow-node__id">A0</span></div><div class="ao-node-name">Agent 0</div><div class="ao-node-desc flow-node__desc"></div><div class="ao-node-foot flow-node__status"></div>';
        board.append(a0Node);
      }
      a0Node.querySelector('.ao-node-desc').textContent=data.agent0.desc;
      a0Node.querySelector('.ao-node-desc').title=data.agent0.desc;
      const a0Foot=a0Node.querySelector('.ao-node-foot');
      a0Foot.textContent=data.agent0.text;
      a0Foot.title=data.agent0.text;
      a0Foot.classList.toggle('status-success',!!data.agent0.success);

      board.querySelectorAll('.flow-idle-placeholder,[data-node]:not([data-node="agent0"])').forEach(e=>e.remove());

      if(!lanes.length){
        a0Node.style.top='140px';a0Node.style.left='28px';a0Node.style.width='168px';a0Node.style.height='132px';
        board.style.height='428px';
        const placeholder=document.createElement('div');
        placeholder.className='flow-idle-placeholder';
        placeholder.innerHTML='<span class="flow-idle-title">Đang chờ Agent 0 điều phối</span>';
        board.append(placeholder);
      }else{
        const count=lanes.length;
        let boardH=428,centerY=140;
        if(count===1){
          boardH=428;centerY=140;lanes[0].top=140;
        }else if(count===2){
          boardH=428;centerY=140;lanes[0].top=68;lanes[1].top=250;
        }else{
          boardH=Math.max(428,40+count*160+40);
          centerY=Math.round(40+((count-1)*160)/2);
          lanes.forEach((l,i)=>{l.top=40+i*160;});
        }
        board.style.height=boardH+'px';
        a0Node.style.top=centerY+'px';a0Node.style.left='28px';a0Node.style.width='168px';a0Node.style.height='132px';

        for(const l of lanes){
          const wNode=document.createElement('button');
          wNode.type='button';
          wNode.className=`ao-node flow-node flow-node--${l.provider} cursor-interaction`;
          wNode.dataset.node=l.key;wNode.dataset.taskId=l.task?.id||'';wNode.dataset.flowRunning=String(!!l.worker.running);
          wNode.style.top=l.top+'px';wNode.style.left='264px';wNode.style.width='218px';wNode.style.height='136px';
          wNode.innerHTML=`<div class="ao-node-top flow-node__top"><span class="flow-node__type">Worker</span><span class="flow-node__id">${short(l.task?.id)}</span></div><div class="ao-node-name">${esc(l.worker.name)}</div><div class="ao-node-desc flow-node__desc" title="${esc(l.task?.id||'')} · ${esc(title(l.task||{}))}">${esc(l.worker.desc)}</div><div class="ao-node-foot flow-node__status ${l.worker.running?'status-running':l.worker.success?'status-success':''}" title="${esc(l.worker.text)}">${esc(l.worker.text)}</div>`;
          board.append(wNode);

          const tNode=document.createElement('button');
          tNode.type='button';
          tNode.className='ao-node flow-node flow-node--test-1 cursor-interaction';
          tNode.dataset.node='test'+l.key;tNode.dataset.taskId=l.task?.id||'';tNode.dataset.flowRunning=String(!!l.test.running);
          tNode.style.top=l.top+'px';tNode.style.left='534px';tNode.style.width='194px';tNode.style.height='136px';
          tNode.innerHTML=`<div class="ao-node-top flow-node__top"><span class="flow-node__type">Test</span><span class="flow-node__id">${short(l.task?.id)}</span></div><div class="ao-node-name">${esc(l.test.name)}</div><div class="ao-node-desc flow-node__desc" title="${esc(l.test.desc)}">${esc(l.test.desc)}</div><div class="ao-node-foot flow-node__status ${l.test.running?'status-running':l.test.success?'status-success':''}" title="${esc(l.test.text)}">${esc(l.test.text)}</div>`;
          board.append(tNode);
        }

        const rNode=document.createElement('button');
        rNode.type='button';
        rNode.className='ao-node flow-node flow-node--review cursor-interaction';
        rNode.dataset.node='review';rNode.dataset.taskId=rv?.id||'';
        rNode.style.top=centerY+'px';rNode.style.left='800px';rNode.style.width='198px';rNode.style.height='132px';
        rNode.innerHTML=`<div class="ao-node-top flow-node__top"><span class="flow-node__type">Kiểm soát</span><span class="flow-node__id">${rv?short(rv.id):''}</span></div><div class="ao-node-name">Review</div><div class="ao-node-desc flow-node__desc" title="${esc(data.review.desc)}">${esc(data.review.desc)}</div><div class="ao-node-foot flow-node__status" title="${esc(data.review.text)}">${esc(data.review.text)}</div>`;
        board.append(rNode);

        const eNode=document.createElement('button');
        eNode.type='button';
        eNode.className='ao-node flow-node flow-node--patch cursor-interaction';
        eNode.dataset.node='export';eNode.dataset.taskId=ap?.id||'';
        eNode.style.top=centerY+'px';eNode.style.left='1074px';eNode.style.width='172px';eNode.style.height='132px';
        eNode.innerHTML=`<div class="ao-node-top flow-node__top"><span class="flow-node__type">Tích hợp</span><span class="flow-node__id">${ap?short(ap.id):''}</span></div><div class="ao-node-name">Xuất patch</div><div class="ao-node-desc flow-node__desc" title="${esc(data.export.desc)}">${esc(data.export.desc)}</div><div class="ao-node-foot flow-node__status" title="${esc(data.export.text)}">${esc(data.export.text)}</div>`;
        board.append(eNode);
      }

      board.querySelectorAll('[data-node]').forEach(node=>{
        const key=node.dataset.node,d=data[key],task=d?.task;
        const selected=state.flowNode===key&&(task?.id===state.selected||key==='agent0');
        node.classList.toggle('is-selected',selected);node.setAttribute('aria-pressed',String(selected));
        node.classList.toggle('is-running',!!(d?.running));
      });
    });

    const flowEdges=[];
    if(lanes.length){
      for(const l of lanes){
        flowEdges.push(['agent0',l.key]);
        flowEdges.push([l.key,'test'+l.key]);
        flowEdges.push(['test'+l.key,'review']);
      }
      flowEdges.push(['review','export']);
    }
    state.flowEdges=flowEdges;

    const running=runningCount;
    $$('[data-flow-summary]').forEach(e=>{
      if(!lanes.length){
        e.textContent='Chưa có hoạt động';
        e.classList.remove('has-activity');
      }else if(isViewingTask&&selectedTask){
        e.textContent=`Xem lại task ${short(selectedTask.id)}`;
        e.classList.remove('has-activity');
      }else{
        e.textContent=running?`${running} task đang thực hiện`:reviewCount?`${reviewCount} task chờ review`:'Sẵn sàng';
        e.classList.toggle('has-activity',running>0);
      }
    });

    const selected=state.flowNode&&data[state.flowNode],task=selected?.task;
    $$('[data-node-title]').forEach(e=>e.textContent=task?selected.name+' · '+short(task.id):(lanes.length?(isViewingTask?`Nhiệm vụ ${short(selectedTask.id)}`:'Quy trình điều phối'):'Agent 0 · Sẵn sàng điều phối'));
    $$('[data-node-description]').forEach(e=>e.textContent=task?title(task)+' · '+selected.text:(lanes.length?(isViewingTask?'Sơ đồ quy trình thực hiện của nhiệm vụ đã chọn. Bấm các bước để xem chi tiết.':'Chọn một bước để xem nhiệm vụ liên quan. Review và xuất patch không tự tích hợp vào main.'):'Agent 0 đang chờ lệnh.'));
    $$('[data-node-badge]').forEach(e=>e.textContent=task?labels[task.status]:(lanes.length?(isViewingTask?'Lịch sử':'Đang thực thi'):(a0.connected?'MCP Sẵn sàng':'Chờ kết nối')));

    renderLive();icons();requestAnimationFrame(drawEdges);
  }

    // Sidebar: closes to an icon rail so the work area gets the full width; the choice is remembered.
  const topLeft=document.createElement('div'),sideToggle=document.createElement('button');
  topLeft.className='ao-top-left';sideToggle.type='button';sideToggle.className='ao-side-toggle cursor-interaction';sideToggle.dataset.sideToggle='';
  const crumb=$('.ao-crumb');crumb.replaceWith(topLeft);topLeft.append(sideToggle,crumb);
  function applySide(){const closed=state.side==='collapsed',label=closed?'Mở thanh bên':'Đóng thanh bên';root.classList.toggle('ao-side-collapsed',closed);sideToggle.setAttribute('aria-expanded',String(!closed));sideToggle.setAttribute('aria-label',label);sideToggle.title=label;sideToggle.innerHTML=`<i data-lucide="${closed?'panel-left-open':'panel-left-close'}" aria-hidden="true"></i>`;icons();}
  sideToggle.addEventListener('click',()=>{state.side=state.side==='collapsed'?'open':'collapsed';applySide();save();});
  $$('.ao-nav button').forEach(b=>{b.title=b.getAttribute('aria-label')||'';});
  state.side=pref.side==='collapsed'?'collapsed':'open';applySide();
  const layoutInput=$('[data-console-layout-input]');
  layoutInput.addEventListener('change',()=>{
    const d=parseLayout(layoutInput.value);
    if(!d){layoutInput.setAttribute('aria-invalid','true');notify('Nhập dạng số x số, ví dụ 1x2 hoặc 3 x 2 (mỗi số từ 1 đến 6).',true);return;}
    layouts[d.key]=d.dims;state.layout=d.key;state.focus=null;state.windowPage=1;layoutInput.removeAttribute('aria-invalid');
    renderWindows();refreshWindows();layoutInput.value=d.key.replace('x',' x ');
  });
  layoutInput.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();layoutInput.blur();}});
  const settingDefs=[
    {key:'remember_context',scope:'worker',label:'Nhớ ngữ cảnh sau mỗi task',hint:'Bật: task tiếp theo của agent này làm tiếp trong cùng worktree và nhớ hội thoại. Tắt: mỗi task bắt đầu mới từ commit gốc. Agent 0 có thể ghi đè từng lần giao việc.'},
    {key:'default_remember',scope:'agent0',label:'Agent mới mặc định nhớ ngữ cảnh',hint:'Áp dụng cho agent tạo sau này khi Agent 0 giao việc mà không nói gì về ngữ cảnh. Agent đã có giữ cài đặt riêng của nó.'}];
  const settingsModal=document.createElement('dialog');settingsModal.className='ao-window-dialog ao-settings-dialog';root.append(settingsModal);
  async function openSettings(id){
    const w=state.windows.find(x=>x.id===id);if(!w)return;let scope='terminal',values={};
    if(id==='agent0'){scope='agent0';values=await api('/settings');}
    else if(w.session?.kind==='worker'){scope='worker';values=(await api('/agents')).find(x=>x.agent===w.session.agent)||{};}
    const rows=settingDefs.filter(d=>d.scope===scope);
    const body=rows.length?rows.map(d=>`<label class="ao-setting"><input type="checkbox" data-setting="${d.key}" ${values[d.key]===false?'':'checked'}><span><strong>${esc(d.label)}</strong><small>${esc(d.hint)}</small></span></label>`).join(''):'<p class="ao-muted">Terminal tương tác là một tiến trình đang sống nên luôn giữ ngữ cảnh. Loại cửa sổ này chưa có tùy chọn nào.</p>';
    settingsModal.innerHTML=`<form method="dialog"><h2>Cài đặt · ${esc(w.name)}</h2>${body}${w.session&&w.session.kind!=='worker'?wheelGroup():''}<div class="ao-actions"><button value="close">Đóng</button></div></form>`;
    settingsModal.dataset.scope=scope;settingsModal.dataset.agent=w.session?.agent??'';settingsModal.showModal();
  }
  settingsModal.addEventListener('change',e=>{
    const wheel=e.target.closest('input[name="wheel"]');
    if(wheel){if(Object.hasOwn(wheelChoices,wheel.value)){state.wheel=wheel.value;save();notify('Đã lưu cách lăn chuột.');}return;}
    const box=e.target.closest('[data-setting]');if(!box)return;const scope=settingsModal.dataset.scope,key=box.dataset.setting;
    runAction(async()=>{try{
      if(scope==='agent0')await api('/settings',{[key]:box.checked});else await api(`/agents/${settingsModal.dataset.agent}/settings`,{[key]:box.checked});
      notify('Đã lưu cài đặt.');await refreshData();
    }catch(error){box.checked=!box.checked;throw error;}});
  });
  root.addEventListener('click',e=>{const b=e.target.closest('[data-settings]');if(b)runAction(()=>openSettings(b.dataset.settings));});
  const collapsed=new Set();
  root.addEventListener('click',e=>{const b=e.target.closest('[data-collapse]');if(!b)return;const id=b.dataset.collapse;collapsed.has(id)?collapsed.delete(id):collapsed.add(id);renderWindows();refreshWindows();});
  function renderLive(){
    const box=$('[data-live-activity]');if(!box)return;const a0=state.agent0||{};
    const row=(label,value,extra='')=>`<div class="ao-live-row"><span class="ao-dot"></span><strong>${esc(label)}</strong><span class="ao-live-value">${esc(value)}</span>${extra}</div>`;
    const terms=state.sessions.map(x=>row(x.title,sessionState(x),`<code>${esc(x.id)}</code><button type="button" class="ao-link cursor-interaction" data-open-term="${esc(x.id)}">Mở</button>`)).join('')||'<p class="ao-empty">Chưa có terminal nào đang mở.</p>';
    const events=state.events.slice(0,8).map(e=>`<div class="ao-event"><time>${esc(time(e.time).slice(0,5))}</time><span class="ao-dot"></span><span><strong>${short(e.task_id)}</strong> · ${esc(e.kind)}</span></div>`).join('')||'<p class="ao-empty">Chưa có sự kiện.</p>';
    box.innerHTML=`<div class="ao-panel-head"><h2>Hoạt động trực tiếp</h2><span class="ao-chip">Dữ liệu thật · cập nhật mỗi 3 giây</span></div><div class="ao-live"><div><h3>Điều phối</h3>${row('Agent 0',a0.connected?'Đã kết nối · '+(a0.last_tool||'chờ lệnh'):'Chưa kết nối')}${['claude','codex'].map(p=>row('Runner '+p,runnerText(p))).join('')}</div><div><h3>Terminal đang mở</h3>${terms}</div><div><h3>Sự kiện gần nhất</h3>${events}</div></div>`;
  }
  root.addEventListener('click',e=>{const b=e.target.closest('[data-open-term]');if(!b)return;state.focus=b.dataset.openTerm;navigate('terminals');renderWindows();refreshWindows();requestAnimationFrame(()=>terms.forEach(x=>{try{x.fit.fit();}catch(_){}}));});
  function drawEdges(){
    $$('.ao-flow').forEach(flow=>{
      const svg=flow.querySelector('svg'),box=flow.getBoundingClientRect();if(!box.width)return;
      svg.setAttribute('viewBox',`0 0 ${box.width} ${box.height}`);svg.setAttribute('width',box.width);svg.setAttribute('height',box.height);
      const edgeList=state.flowEdges||[];
      const edges=edgeList.map(([from,to])=>{
        const source=flow.querySelector(`[data-node="${from}"]`),target=flow.querySelector(`[data-node="${to}"]`);
        if(!source||!target)return null;
        const a=source.getBoundingClientRect(),b=target.getBoundingClientRect();
        const x1=a.right-box.left,y1=a.top+a.height/2-box.top,x2=b.left-box.left,y2=b.top+b.height/2-box.top,mx=(x1+x2)/2;
        const active=target.dataset.flowRunning==='true';
        return {key:from+'-'+to,d:`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`,active};
      }).filter(Boolean);
      if(!svg.querySelector('.flow-connections__base'))svg.innerHTML='<g class="flow-connections__base"></g><g class="flow-connections__motion"></g>';
      const currentKeys=new Set(edges.map(e=>e.key));
      for(const layer of ['base','motion']){
        const group=svg.querySelector('.flow-connections__'+layer);
        if(!group)continue;
        group.querySelectorAll('path').forEach(p=>{if(!currentKeys.has(p.dataset.edge))p.remove();});
        for(const edge of edges){
          let path=group.querySelector(`[data-edge="${edge.key}"]`);
          if(!path){path=document.createElementNS('http://www.w3.org/2000/svg','path');path.dataset.edge=edge.key;group.append(path);}
          path.setAttribute('d',edge.d);path.setAttribute('class',layer==='base'?'ao-edge':'flow-path'+(edge.active?' is-active':''));
        }
      }
    });
  }
  async function selectTask(id){
    state.selected=id;state.bundle=null;navigate('tasks');renderTasks();
    const t=state.tasks.find(t=>t.id===id);if(!t)return;
    const detail=$('[data-task-detail]');detail.hidden=false;
    detail.innerHTML=`<div class="ao-actions ao-spread"><h3>${short(id)} · ${esc(title(t))}</h3>${chip(t.status)}</div><p class="ao-sub ao-wrap">${esc(t.prompt)}</p><div class="ao-detail-grid"><div><label>Base / worktree</label><p class="ao-wrap">${esc(t.base)}<br>orch/${esc(t.id)}</p></div><div><label>Phạm vi</label><p>${esc(t.allow_paths.join(', '))}</p></div><div><label>Test</label><p>${esc(testSummary(t))}</p></div></div>${t.result?.error?`<div class="ao-notice error">${esc(t.result.error)}</div>`:''}<div class="ao-actions"><button class="ao-btn" data-detail="log">Log worker</button><button class="ao-btn" data-detail="events">Sự kiện</button>${['awaiting_review','approved','changes_requested'].includes(t.status)?'<button class="ao-btn" data-detail="diff">Xem diff & test</button>':''}${['queued','running'].includes(t.status)&&!t.cancel_requested?'<button class="ao-btn ao-danger" data-detail="cancel">Hủy nhiệm vụ</button>':''}<button class="ao-btn" data-detail="retry">${t.agent?`Giao việc tiếp cho ${esc(t.provider)} ${t.agent}`:'Giao việc tiếp'}</button></div><div class="ao-detail-content" data-detail-content></div><div data-review-controls></div>`;
    detail.scrollIntoView({block:'nearest',behavior:'smooth'});icons();
  }
  async function detailAction(action){
    const id=state.selected,t=state.tasks.find(t=>t.id===id);if(!t)return;const content=$('[data-detail-content]');
    if(action==='retry'){openForm(t.provider,t.agent?'':t.prompt,t.allow_paths.join(', '),t.agent);return;}
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
  // Appearance: light / dark / follow the system, and two palettes. Kept in this browser only.
  const THEME_MODES={system:'Theo hệ thống',light:'Sáng',dark:'Tối'},PALETTES={claude:'Claude · nền giấy ấm, chữ serif, màu đất nung',classic:'Cổ điển · nền xanh lạnh, màu teal (bản cũ)'};
  // Full-screen apps (Claude Code, Codex...) run in the alternate screen: ConPTY does not pass their mouse mode on,
  // so xterm.js turns every wheel notch into a burst of arrow keys, which those apps read as "previous prompt".
  const wheelChoices={page:'PageUp / PageDown, mỗi nấc lăn một trang',arrows:'Mũi tên ↑ ↓ (kiểu xterm; nhiều ứng dụng dùng để duyệt lịch sử gõ)',none:'Không gửi gì'};
  state.wheel=Object.hasOwn(wheelChoices,pref.wheel)?pref.wheel:'page';
  const wheelGroup=()=>`<fieldset class="ao-choice"><legend>Lăn chuột trong ứng dụng toàn màn hình (Claude Code, Codex…)</legend>${Object.entries(wheelChoices).map(([v,l])=>`<label><input type="radio" name="wheel" value="${v}" ${v===state.wheel?'checked':''}><span>${esc(l)}</span></label>`).join('')}<small class="ao-muted">Áp dụng cho mọi terminal. Ứng dụng chạy ở bộ đệm thường (có thanh cuộn) luôn cuộn bình thường.</small></fieldset>`;
  state.theme=Object.hasOwn(THEME_MODES,pref.theme)?pref.theme:'system';state.palette=Object.hasOwn(PALETTES,pref.palette)?pref.palette:'claude';
  function termTheme(){const probe=document.createElement('i');probe.style.cssText='position:absolute;visibility:hidden;background:var(--cmd-bg);color:var(--cmd-text)';($('.ao-console-view')||root).append(probe);const cs=getComputedStyle(probe),theme={background:cs.backgroundColor||'#1f1e1d',foreground:cs.color||'#e8e6dc'};probe.remove();return theme;}
  function applyTheme(){
    const scheme=state.theme==='system'?'light dark':state.theme;
    for(const el of [root,document.documentElement]){el.style.setProperty('color-scheme',scheme);el.dataset.theme=state.theme;el.dataset.palette=state.palette;}
    const theme=termTheme();terms.forEach(e=>{try{e.term.options.theme=theme;}catch(_){}});
  }
  const themeModal=document.createElement('dialog'),themeBtn=document.createElement('button'),demoBadge=$('.ao-demo'),topRight=document.createElement('div'),soundBtn=document.createElement('button');
  themeModal.className='ao-window-dialog ao-settings-dialog ao-theme-dialog';root.append(themeModal);
  themeBtn.type='button';themeBtn.className='ao-side-toggle cursor-interaction';themeBtn.dataset.themeOpen='';themeBtn.title='Giao diện';themeBtn.setAttribute('aria-label','Giao diện: sáng, tối, bảng màu');themeBtn.innerHTML='<i data-lucide="sun-moon" aria-hidden="true"></i>';
  soundBtn.type='button';soundBtn.className='ao-side-toggle cursor-interaction';soundBtn.dataset.soundToggle='';
  function updateSoundBtn(){
    const on=state.sound!==false;
    soundBtn.title=on?'Âm thanh thông báo: Đang bật (nhấp để tắt)':'Âm thanh thông báo: Đã tắt (nhấp để bật)';
    soundBtn.setAttribute('aria-label',soundBtn.title);
    soundBtn.innerHTML=`<i data-lucide="${on?'volume-2':'volume-x'}" aria-hidden="true"></i>`;
    icons();
  }
  soundBtn.addEventListener('click',()=>{
    state.sound=state.sound===false?true:false;
    updateSoundBtn();save();
    if(state.sound){playChime('success');notify('Đã bật âm thanh thông báo');}else{notify('Đã tắt âm thanh thông báo');}
  });
  updateSoundBtn();
  topRight.className='ao-top-right';demoBadge.replaceWith(topRight);topRight.append(soundBtn,themeBtn,demoBadge);
  themeBtn.addEventListener('click',()=>{
    const group=(name,title,options,current)=>`<fieldset class="ao-choice"><legend>${title}</legend>${Object.entries(options).map(([value,label])=>`<label><input type="radio" name="${name}" value="${value}" ${value===current?'checked':''}><span>${esc(label)}</span></label>`).join('')}</fieldset>`;
    themeModal.innerHTML=`<form method="dialog"><h2>Giao diện</h2>${group('theme-mode','Chế độ',THEME_MODES,state.theme)}${group('theme-palette','Bảng màu',PALETTES,state.palette)}<p class="ao-muted">Chỉ lưu trong trình duyệt này.</p><div class="ao-actions"><button value="close">Đóng</button></div></form>`;
    themeModal.showModal();
  });
  themeModal.addEventListener('change',e=>{
    const choice=e.target.closest('input[type=radio]');if(!choice)return;
    if(choice.name==='theme-mode'&&Object.hasOwn(THEME_MODES,choice.value))state.theme=choice.value;
    if(choice.name==='theme-palette'&&Object.hasOwn(PALETTES,choice.value))state.palette=choice.value;
    applyTheme();save();
  });
  applyTheme();icons();
  function liveTerm(id){const e=terms.get(id);return !!e&&!e.dead;}
  function placeTerm(w){const e=terms.get(w.id),card=$(`[data-window="${w.id}"]`);if(!e||!card)return;const host=card.querySelector('[data-term-host]');host.hidden=false;card.querySelector('[data-window-output]').hidden=true;const hist=card.querySelector('.ao-terminal-history');if(hist)hist.hidden=true;if(e.el.parentNode!==host)host.appendChild(e.el);if(!e.opened){e.opened=true;try{e.term.open(e.el);}catch(error){e.opened=false;}}if(e.observer)e.observer.disconnect();e.observer=new ResizeObserver(()=>{try{e.fit.fit();}catch(_){}});e.observer.observe(host);requestAnimationFrame(()=>{try{e.fit.fit();}catch(_){}});}
  function attachTerm(info){
    if(typeof Terminal==='undefined')return;
    const term=new Terminal({
      cursorBlink:info.kind!=='worker',
      disableStdin:info.kind==='worker',
      fontSize:13,
      fontFamily:'Consolas,"Courier New",monospace',
      scrollback:5000,
      theme:termTheme(),
      windowsPty:{backend:'conpty'},
      allowProposedApi:true
    });
    const fit=new FitAddon.FitAddon();term.loadAddon(fit);
    const el=document.createElement('div');el.className='ao-term-el';
    const e={term,fit,el,after:0,dead:false,id:info.id,readonly:info.kind==='worker',queue:Promise.resolve()};terms.set(info.id,e);

    // Bắt phím tắt Paste / Copy trên terminal
    term.attachCustomKeyEventHandler(ev=>{
      if((ev.ctrlKey&&(ev.key==='v'||ev.key==='V'))||(ev.shiftKey&&ev.key==='Insert')){
        if(ev.type==='keydown'&&!e.readonly){
          navigator.clipboard.readText().then(text=>{
            if(text)term.paste(text);
          }).catch(()=>{});
        }
        return false; // Ngăn xterm gửi ASCII \x16 vào ConPTY
      }
      if(ev.ctrlKey&&(ev.key==='c'||ev.key==='C')&&term.hasSelection()){
        if(ev.type==='keydown'){
          navigator.clipboard.writeText(term.getSelection()).catch(()=>{});
        }
        return false;
      }
      return true;
    });

    // Sự kiện Paste native trên thẻ container
    el.addEventListener('paste',ev=>{
      if(e.readonly)return;
      ev.preventDefault();
      const text=(ev.clipboardData||window.clipboardData)?.getData('text');
      if(text)term.paste(text);
    });

    // Chuột phải: bôi đen thì copy, không bôi đen thì paste
    el.addEventListener('contextmenu',async ev=>{
      if(term.hasSelection()){
        try{await navigator.clipboard.writeText(term.getSelection());}catch(_){}
      }else if(!e.readonly){
        ev.preventDefault();
        try{
          const text=await navigator.clipboard.readText();
          if(text)term.paste(text);
        }catch(_){}
      }
    });

    term.attachCustomWheelEventHandler(ev=>{
      if(term.buffer.active.type!=='alternate')return true; // normal buffer: xterm scrolls its own scrollback
      if(state.wheel==='arrows')return true;                // xterm default
      ev.preventDefault();
      if(state.wheel==='none'||e.readonly)return false;
      e.wheelAcc=(e.wheelAcc||0)+(ev.deltaMode===1?ev.deltaY*33:ev.deltaMode===2?ev.deltaY*400:ev.deltaY);
      let keys=0;while(Math.abs(e.wheelAcc)>=90&&keys<4){term.input(e.wheelAcc<0?'\x1b[5~':'\x1b[6~',true);e.wheelAcc-=Math.sign(e.wheelAcc)*90;keys++;}
      return false;
    });

    // Bộ đệm gom cụm gõ phím siêu tốc (10ms) & chuẩn hóa Unicode NFC:
    // Tránh việc gửi rời rạc từng Backspace / ký tự tiếng Việt từ Unikey/EVKey
    // làm ConPTY xử lý Backspace ngắt quãng gây nuốt chữ trước đó ("nhiêu" -> "nhêu", "bằng" -> "ằng").
    let inputBuf='',inputTimer=null;
    const flushInput=()=>{
      if(inputTimer){clearTimeout(inputTimer);inputTimer=null;}
      if(!inputBuf)return;
      const chunk=inputBuf;inputBuf='';
      e.queue=e.queue.then(()=>api(`/terminals/${e.id}/input`,{data:chunk})).catch(()=>{});
    };
    e.flush=flushInput;

    term.onData(d=>{
      if(e.readonly)return;
      const str=(typeof d==='string'?d.normalize('NFC'):d);
      inputBuf+=str;
      if(str.includes('\r')||str.includes('\n')||str.includes('\x1b')||str.includes('\x03')||inputBuf.length>=32){
        flushInput();
      }else{
        if(inputTimer)clearTimeout(inputTimer);
        inputTimer=setTimeout(flushInput,10);
      }
    });

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
          if(!x.alive){e.ended=true;e.term.write(e.readonly?'\r\n\x1b[33m[Task đã kết thúc. Có thể đóng cửa sổ theo dõi này.]\x1b[0m\r\n':'\r\n\x1b[33m[Terminal đã kết thúc (mã '+x.exit_code+'). Bấm "Đóng terminal" để xóa cửa sổ này.]\x1b[0m\r\n');}
        }
      }catch(error){await new Promise(r=>setTimeout(r,1500));}
    }}finally{streaming=false;}
  }
  function dropTerm(id){const e=terms.get(id);if(!e)return;if(e.flush)e.flush();e.dead=true;if(e.observer)e.observer.disconnect();e.term.dispose();terms.delete(id);}
  async function syncTerms(){
        
    const list=await api('/terminals');const ids=new Set(list.map(s=>s.id));let changed=list.length!==state.sessions.length||list.some((s,i)=>state.sessions[i]?.id!==s.id);
    const fresh=state.known?list.filter(x=>x.kind==='worker'&&!state.known.has(x.id)):[];state.known=new Set(ids);
    state.sessions=list;
    for(const s of list)if(!terms.has(s.id)){try{attachTerm(s);}catch(error){console.error(error);}changed=true;}
    for(const id of [...terms.keys()])if(!ids.has(id)){dropTerm(id);changed=true;}
    if(!state.agent0Tried&&state.config&&state.config.execution_enabled&&!state.config.demo&&!ids.has('agent0')){state.agent0Tried=true;try{await api('/terminals/open',{kind:'agent0',cols:100,rows:30});return syncTerms();}catch(error){notify('Agent 0: '+error.message,true);}}
    state.agent0Tried=true;
    renderFlow();
    if(changed)renderWindows();
    if(fresh.length){const last=fresh[fresh.length-1],idx=state.windows.findIndex(w=>w.id===last.id);if(idx>=0&&!state.focus){state.windowPage=Math.floor(idx/(layouts[state.layout][0]*layouts[state.layout][1]))+1;renderWindows();}notify('Terminal mới: '+fresh.map(x=>x.title).join(', ')+' — xem trực tiếp trong tab Cửa sổ CMD.');}
  }
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
    $$('[data-console-layout]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.consoleLayout===state.layout)));{const box=$('[data-console-layout-input]');if(box&&document.activeElement!==box){box.value=state.layout.replace('x',' x ');box.removeAttribute('aria-invalid');}}$$('[data-console-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.consoleMode===state.mode)));
    $('[data-console-grid]').style.setProperty('--console-cols',state.focus?1:layouts[state.layout][1]);$('[data-console-grid]').style.setProperty('--console-rows',state.focus?1:(state.mode==='all'?Math.max(1,Math.ceil(state.windows.length/layouts[state.layout][1])):layouts[state.layout][0]));root.style.setProperty('--console-rows',state.focus?1:layouts[state.layout][0]);
    $('[data-console-grid]').innerHTML=visibleWindows().map(w=>`<article class="ao-terminal${collapsed.has(w.id)?' is-collapsed':''}" data-window="${esc(w.id)}"><header class="ao-terminal-head"><div class="ao-terminal-title-row"><button type="button" class="ao-terminal-drag" draggable="true" data-drag="${esc(w.id)}" aria-label="Di chuyển ${esc(w.name)} bằng Alt và phím mũi tên">⠿</button><span class="ao-terminal-role ${w.kind}">${agentLogo(w.kind)}</span><span class="ao-terminal-name" title="${esc(w.session?w.session.cwd:w.name)}">${esc(w.name)}</span><span class="ao-terminal-meta"><code data-window-path>Queue local</code><span data-window-status></span></span><div class="ao-winctl" role="group" aria-label="Điều khiển cửa sổ ${esc(w.name)}"><button type="button" class="ao-winbtn cursor-interaction" data-settings="${esc(w.id)}" aria-label="Cài đặt ${esc(w.name)}" title="Cài đặt"><i data-lucide="settings"></i></button><button type="button" class="ao-winbtn cursor-interaction" data-collapse="${esc(w.id)}" aria-pressed="${collapsed.has(w.id)}" aria-label="${collapsed.has(w.id)?'Mở rộng':'Thu gọn'} ${esc(w.name)}" title="${collapsed.has(w.id)?'Mở rộng':'Thu gọn'}"><i data-lucide="minus"></i></button><button type="button" class="ao-winbtn cursor-interaction" data-focus="${esc(w.id)}" aria-label="${state.focus?'Khôi phục':'Phóng to'} ${esc(w.name)}" title="${state.focus?'Khôi phục':'Phóng to'}"><i data-lucide="${state.focus?'copy':'square'}"></i></button><button type="button" class="ao-winbtn ao-winbtn-close cursor-interaction" data-term-toggle="${esc(w.id)}" aria-label="${w.session?(w.session.kind==='worker'?'Đóng cửa sổ theo dõi':'Đóng terminal'):'Mở Agent 0'} ${esc(w.name)}" title="${w.session?(w.session.kind==='worker'?'Đóng cửa sổ theo dõi':'Đóng terminal'):'Mở Agent 0'}"><i data-lucide="${w.session?'x':'play'}"></i></button></div></div></header><pre class="ao-terminal-output" data-window-output role="log" aria-label="Log ${esc(w.name)}"></pre><div class="ao-term-host" data-term-host hidden></div><div class="ao-terminal-history"><button data-history="${esc(w.id)}">Xem log mở rộng</button><span>LOCAL · ${w.taskId?'TASK':'MONITOR'}</span></div></article>`).join('');
    $('[data-console-count]').textContent=state.windows.length+' cửa sổ';$('[data-console-active]').textContent=state.tasks.filter(t=>t.status==='running').length+' task đang chạy';$('[data-console-range]').textContent=state.focus?'Đang phóng to một cửa sổ':state.mode==='all'?'Tất cả cửa sổ':`Trang ${state.windowPage}/${count} · ${size} cửa sổ/trang`;
    $('[data-console-focusbar]').hidden=!state.focus;$('[data-console-focusname]').textContent='Đang phóng to · '+(state.windows.find(w=>w.id===state.focus)?.name||'');
    const pager=$('[data-console-pager]');pager.hidden=!!state.focus||state.mode==='all';pager.innerHTML=Array.from({length:count},(_,i)=>`<button data-window-page="${i+1}" aria-current="${state.windowPage===i+1?'page':'false'}">${i+1}</button>`).join('');
    for(const w of visibleWindows()){updateWindow(w,state.outputs.get(w.id)||'Chưa có log.');if(terms.has(w.id))placeTerm(w);}icons();save();
  }
  function updateWindow(w,text){const card=$(`[data-window="${w.id}"]`);if(!card)return;const task=windowTask(w);const sess=w.session;card.querySelector('[data-window-path]').textContent=w.id==='agent0'?'Claude Code · MCP':sess?sess.id+' · '+(sess.kind==='worker'?(sess.remember===false?'không nhớ ngữ cảnh':'nhớ ngữ cảnh'):({claude:'Claude Code',codex:'Codex CLI',agy:'Antigravity CLI'}[sess.provider]||sess.provider)):'';card.querySelector('[data-window-status]').textContent=w.id==='agent0'?(state.agent0.connected?'Đã kết nối':'Chưa kết nối'):sess?sessionState(sess):'';const output=card.querySelector('[data-window-output]');if(output.textContent!==text){const atBottom=output.scrollTop+output.clientHeight>=output.scrollHeight-30;output.textContent=text;if(atBottom)output.scrollTop=output.scrollHeight;}}
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
  const wfLabels={waiting:'Chờ',releasing:'Đang giao',released:'Đã giao',done:'Xong',blocked:'Bị chặn',cancelled:'Đã hủy'},wfStates={running:'Đang chạy',done:'Hoàn tất',blocked:'Bị chặn',cancelled:'Đã hủy'};
  function renderWorkflows(){const box=$('[data-workflows]');if(!box)return;const list=state.workflows||[];box.innerHTML=`<div class="ao-panel-head"><div><h2>Workflow</h2><p>Kế hoạch nhiều bước do Agent 0 tạo bằng enqueue_plan: bước sau tự chạy khi các bước nó chờ đã xong.</p></div></div>`+(list.length?list.map(w=>`<article class="ao-wf"><header><strong>${esc(w.title)}</strong><span class="ao-wf-state ${esc(w.state)}">${esc(wfStates[w.state]||w.state)}</span><code>${esc(w.id)}</code>${w.state==='running'||w.state==='blocked'?`<button type="button" class="ao-btn cursor-interaction" data-wf-cancel="${esc(w.id)}">Hủy</button>`:''}</header><ol>${w.steps.map(s=>`<li class="ao-wf-step ${esc(s.status)}"><b>${esc(s.id)}</b><span>Agent ${s.agent} (${esc(s.provider)})</span><span>${esc(wfLabels[s.status]||s.status)}${s.task_status?' · '+esc(s.task_status):''}</span><small>${s.after.length?'sau '+s.after.map(esc).join(', '):'bắt đầu ngay'}${s.note?' · '+esc(s.note):''}</small></li>`).join('')}</ol></article>`).join(''):'<p class="ao-muted" style="padding:0 16px 16px">Chưa có workflow. Nhờ Agent 0 lập kế hoạch nhiều bước.</p>');}
  async function refreshData(){const prior=state.tasks.find(t=>t.id===state.selected)?.status;const [tasks,events,runners,agent0]=await Promise.all([api('/tasks'),api('/activity'),api('/runners'),api('/agent0').catch(()=>({connected:false}))]);checkTaskSoundAlerts(tasks);state.agent0=agent0;state.workflows=await api('/workflows').then(r=>Array.isArray(r)?r:[]).catch(()=>[]);renderWorkflows();state.tasks=tasks;state.events=events;state.runners=runners;$('.ao-demo').textContent=runnerLabel();$('.ao-demo').classList.toggle('error',Object.values(runners.providers).some(r=>r.status==='error'));renderTasks();await syncTerms().catch(e=>{notify('Terminal: '+e.message,true);});buildWindows();$('[data-console-active]').textContent=tasks.filter(t=>t.status==='running').length+' task đang chạy';await refreshWindows();if(!state.busy&&state.page==='tasks'&&state.selected&&prior!==tasks.find(t=>t.id===state.selected)?.status)await selectTask(state.selected);}
  async function runAction(fn){if(state.busy)return;state.busy=true;root.setAttribute('aria-busy','true');$$('[data-review],[data-detail="export"],[data-action="create-task"]').forEach(b=>b.disabled=true);try{await fn();}catch(error){notify(error.message,true);}finally{state.busy=false;root.removeAttribute('aria-busy');$$('[data-review],[data-detail="export"],[data-action="create-task"]').forEach(b=>b.disabled=false);}}
  function openForm(provider,prompt='',scope='src, tests',agent=null){state.formAgent=agent||null;form.elements.provider.disabled=!!agent;form.querySelector('.ao-actions .ao-muted').textContent=agent?`Giao việc tiếp cho ${provider} ${agent}: theo cài đặt nhớ ngữ cảnh của agent.`:'Worker nhận việc khi runner đang hoạt động.';navigate('tasks');form.hidden=false;form.elements.prompt.value=prompt;form.elements.scope.value=scope;if(provider&&state.config?.providers[provider])form.elements.provider.value=provider;form.elements.prompt.focus();}
  form.addEventListener('submit',event=>{event.preventDefault();runAction(async()=>{if(!form.reportValidity())return;const data=new FormData(form),tests=data.getAll('tests');if(!tests.length)throw Error('Chọn ít nhất một test profile.');const result=await api('/tasks',{...(state.formAgent?{agent:state.formAgent}:{provider:data.get('provider')}),prompt:String(data.get('prompt')).trim(),allow_paths:String(data.get('scope')).split(/[,\n]/).map(x=>x.trim()).filter(Boolean),tests});form.hidden=true;form.elements.prompt.value='';state.formAgent=null;form.elements.provider.disabled=false;notify(result.round>1?`${result.provider} ${result.agent} làm tiếp task ${short(result.id)} (vòng ${result.round}).`:`Đã thêm task ${short(result.id)} (${result.provider} ${result.agent}) vào hàng đợi.`);await refreshData();await selectTask(result.id);});});
  const modal=document.createElement('dialog');modal.className='ao-window-dialog';modal.innerHTML='<form method="dialog"><h2>Thêm terminal agent</h2><label>Agent<select data-add-agent required></select></label><label data-add-repo-wrap hidden>Repo (mã nguồn)<select data-add-repo></select></label><label>Thư mục làm việc<select data-add-folder></select></label><p>Mở một phiên tương tác thật. Agent 0 theo dõi được (chỉ đọc) qua list_terminals / read_terminal.</p><div class="ao-actions"><button value="cancel">Đóng</button><button value="add">Mở terminal</button></div></form>';root.append(modal);
  modal.addEventListener('close',()=>{if(modal.returnValue!=='add')return;const provider=modal.querySelector('[data-add-agent]').value,task=modal.querySelector('[data-add-folder]').value,repo=modal.querySelector('[data-add-repo]').value;if(state.sessions.length>=12){notify('Tối đa 12 terminal.',true);return;}runAction(async()=>{const info=await api('/terminals/open',{kind:'agent',provider,...(task?{task_id:task}:repo&&repo!=='default'?{repo}:{}),cols:100,rows:30});state.focus=null;await syncTerms();const idx=state.windows.findIndex(w=>w.id===info.id);if(idx>=0)state.windowPage=Math.floor(idx/(layouts[state.layout][0]*layouts[state.layout][1]))+1;renderWindows();});});

  const repoModal=document.createElement('dialog');
  repoModal.className='ao-window-dialog ao-repo-dialog';
  repoModal.innerHTML='<form method="dialog"><h2>Chọn thư mục dự án</h2><label>Đường dẫn thư mục<div class="ao-scope-field-wrap"><input type="text" data-repo-path required placeholder="Chọn thư mục trên máy tính..."><button type="button" class="ao-btn ao-btn-primary cursor-interaction" data-browse-native title="Mở hộp thoại chọn thư mục của Windows"><i data-lucide="folder-search"></i> Chọn từ máy tính...</button></div></label><div class="ao-actions"><button value="cancel">Đóng</button><button value="apply" class="ao-btn ao-btn-primary">Áp dụng</button></div></form>';
  root.append(repoModal);

  async function pickFolderNative(){
    try{
      const cur=state.config?.repo||'';
      const res=await api('/browse/native',{initial:cur});
      if(res&&res.path&&!res.cancelled){
        const newPath=res.path.replace(/\//g,'\\');
        runAction(async()=>{
          const applied=await api('/repo',{path:newPath});
          notify(`Đã chọn thư mục: ${applied.name||applied.repo}`);
          const cfg=await api('/config');
          configure(cfg);
          await refreshData();
        });
      }
    }catch(err){notify(err.message,true);}
  }

  repoModal.querySelector('[data-browse-native]').addEventListener('click',async()=>{
    repoModal.close('cancel');
    await pickFolderNative();
  });

  repoModal.addEventListener('close',()=>{
    if(repoModal.returnValue!=='apply')return;
    const path=repoModal.querySelector('[data-repo-path]').value.trim();
    if(!path)return;
    runAction(async()=>{
      const applied=await api('/repo',{path});
      notify(`Đã chọn thư mục: ${applied.name||applied.repo}`);
      const cfg=await api('/config');
      configure(cfg);
      await refreshData();
    });
  });

  function openRepoDialog(){
    pickFolderNative();
  }
  root.addEventListener('input',e=>{if(e.target.dataset.command)state.drafts.set(e.target.dataset.command,e.target.value);});
  root.addEventListener('click',event=>{
    const target=event.target,wfCancel=target.closest('[data-wf-cancel]');if(wfCancel){runAction(async()=>{await api('/workflows/'+wfCancel.dataset.wfCancel+'/cancel',{});notify('Đã hủy workflow.');await refreshData();});return;}const flowSel=target.closest('[data-flow-select]');if(flowSel){state.flowSelectedTask=flowSel.dataset.flowSelect;renderFlow();return;}
    const flowClr=target.closest('[data-flow-clear]');if(flowClr){state.flowSelectedTask=null;renderFlow();return;}
    const page=target.closest('[data-page]');if(page){if(page.dataset.page==='flow')state.flowSelectedTask=null;navigate(page.dataset.page);requestAnimationFrame(()=>terms.forEach(e=>{try{e.fit.fit();}catch(_){}}));return;}
    const pasteBtn=target.closest('[data-paste]');
    if(pasteBtn){
      const wid=pasteBtn.dataset.paste;
      const e=terms.get(wid);
      if(e&&!e.readonly){
        navigator.clipboard.readText().then(text=>{
          if(text){
            e.term.paste(text);
            e.term.focus();
            notify('Đã dán vào terminal.');
          }
        }).catch(err=>{
          notify('Không đọc được clipboard: '+(err.message||err),true);
        });
      }
      return;
    }
    const toggle=target.closest('[data-term-toggle]');if(toggle){const w=state.windows.find(x=>x.id===toggle.dataset.termToggle);if(w)runAction(()=>toggleTerm(w));return;}
    const task=target.closest('[data-task]');if(task){runAction(()=>selectTask(task.dataset.task));return;}
    const action=target.closest('[data-action]')?.dataset.action;if(action==='new-task')openForm();if(action==='close-form')form.hidden=true;if(action==='open-repo-dialog')openRepoDialog();
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
    if(consoleAction==='history'){openHistoryModal();return;}
    const convResume=target.closest('[data-conv-resume]');
    if(convResume){resumeConversation(convResume.dataset.convResume);return;}
    const convView=target.closest('[data-conv-view]');
    if(convView){openTranscript(convView.dataset.convView);return;}
    if(consoleAction==='add'){closeSettings();const names={claude:'Claude',codex:'Codex',agy:'Antigravity (agy)'},agents=state.config?.terminal_agents||[];if(!agents.length){notify('Chưa cấu hình agent nào trong config.',true);return;}modal.querySelector('[data-add-agent]').innerHTML=agents.map(a=>`<option value="${a}">${names[a]||a}</option>`).join('');const repos=state.config?.repos||['default'];modal.querySelector('[data-add-repo]').innerHTML=repos.map(r=>`<option value="${esc(r)}">${r==='default'?'Repo chính':esc(r)}</option>`).join('');modal.querySelector('[data-add-repo-wrap]').hidden=repos.length<2;modal.querySelector('[data-add-folder]').innerHTML='<option value="">Theo repo đã chọn · '+esc((state.config.repo||'').split(/[\/]/).pop())+'</option>'+state.tasks.map(t=>`<option value="${t.id}">Worktree task ${short(t.id)} · ${esc(title(t))}</option>`).join('');modal.showModal();}
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
