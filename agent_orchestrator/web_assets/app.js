'use strict';
(() => {
  const root = document.getElementById('ao-studio');
  const $ = s => root.querySelector(s), $$ = s => [...root.querySelectorAll(s)];
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = {queued:'Trong hàng đợi',running:'Đang thực hiện',awaiting_review:'Chờ review',approved:'Đã duyệt',changes_requested:'Cần chỉnh sửa',failed:'Thất bại',cancelled:'Đã hủy'};
  const pages = {terminals:['Cửa sổ CMD','Không gian dòng lệnh','Log worker, test và sự kiện được cập nhật từ queue.'],overview:['Tổng quan','Trung tâm điều phối','Giao việc rõ ràng. Theo dõi xuyên suốt. Duyệt từng thay đổi.'],flow:['Luồng tự động','Nhìn rõ từng bước chạy','Luồng động kích hoạt khi Agent 0 gọi agent hoặc giao việc.'],tasks:['Nhiệm vụ','Mỗi nhiệm vụ, một worktree','Phân công, xem bằng chứng test và duyệt thay đổi.'],history:['Lịch sử','Lịch sử trò chuyện','Xem lại, mở lại hoặc xóa các phiên của Agent 0 và terminal agent.'],reports:['Báo cáo','Hiệu quả vận hành','Tổng hợp tối đa 200 nhiệm vụ gần nhất; usage thiếu được giữ nguyên.'],permissions:['Quyền & bảo vệ','Tự động hóa có giới hạn','Chính sách hiện tại và quyền thực thi local.']};
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
  function notify(text,error=false,title='Agent Studio'){
    const e=$('[data-toast]');
    if(e){
      e.hidden=false;
      e.textContent=text;
      e.classList.toggle('error',error);
      if(e._toastTimer)clearTimeout(e._toastTimer);
      e._toastTimer=setTimeout(()=>{e.hidden=true;},6000);
    }
    if(state.sound!==false&&'Notification' in window&&Notification.permission==='granted'){
      try{
        const n=new Notification(title,{
          body:text,
          tag:'ao-alert-'+(Date.now()%100000),
          renotify:true
        });
        n.onclick=()=>{try{window.focus();}catch(_){}n.close();};
      }catch(_){}
    }
  }
  let audioCtx=null;
  function getAudioContext(){
    if(!audioCtx&&(window.AudioContext||window.webkitAudioContext)){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)();}catch(_){}}
    if(audioCtx&&audioCtx.state==='suspended'){audioCtx.resume().catch(()=>{});}
    return audioCtx;
  }
  function requestNotificationPermission(){
    if('Notification' in window&&Notification.permission==='default'){
      try{Notification.requestPermission().then(p=>{if(p==='granted')notify('Đã cấp quyền thông báo màn hình.');}).catch(()=>{});}catch(_){}
    }
  }
  const unlockAudio=()=>{getAudioContext();if(state.sound!==false)requestNotificationPermission();};
  window.addEventListener('click',unlockAudio,{once:true});
  window.addEventListener('keydown',unlockAudio,{once:true});
  async function playChime(kind='success'){
    if(state.sound===false)return;
    try{
      const ctx=getAudioContext();if(!ctx)return;
      if(ctx.state==='suspended')await ctx.resume().catch(()=>{});
      const now=ctx.currentTime,osc=ctx.createOscillator(),gain=ctx.createGain();
      osc.type='sine';
      if(kind==='error'){osc.frequency.setValueAtTime(440,now);osc.frequency.setValueAtTime(311.13,now+0.12);}
      else{osc.frequency.setValueAtTime(587.33,now);osc.frequency.setValueAtTime(880,now+0.12);}
      gain.gain.setValueAtTime(0.24,now);gain.gain.exponentialRampToValueAtTime(0.001,now+0.45);
      osc.connect(gain);gain.connect(ctx.destination);osc.start(now);osc.stop(now+0.45);
    }catch(_){}
  }
  let cachedVoices=[];
  function loadVoices(){if('speechSynthesis' in window){try{cachedVoices=window.speechSynthesis.getVoices()||[];}catch(_){}}}
  loadVoices();
  if('speechSynthesis' in window){window.speechSynthesis.onvoiceschanged=loadVoices;}
  function getVietnameseVoice(){
    if(!cachedVoices.length)loadVoices();
    return cachedVoices.find(v=>v.lang&&(v.lang.toLowerCase().startsWith('vi')||v.lang.toLowerCase().includes('vietnam')))
        ||cachedVoices.find(v=>v.name&&(v.name.toLowerCase().includes('vietnam')||v.name.toLowerCase().includes('tiếng việt')));
  }
  let lastSpokenAt=0;
  let activeAudio=null;
  async function speakText(text){
    if(state.sound===false)return;
    const now=Date.now();
    if(now-lastSpokenAt<3500)return; // Cooldown 3.5s tránh nói đè hoặc lặp
    lastSpokenAt=now;

    // 1. Nếu có voice tiếng Việt trên hệ điều hành thì dùng voice nội bộ
    const viVoice=getVietnameseVoice();
    if(viVoice){
      try{
        window.speechSynthesis.cancel();
        const u=new SpeechSynthesisUtterance(text);
        u.voice=viVoice;
        u.lang=viVoice.lang||'vi-VN';
        u.rate=1.0;
        u.volume=1.0;
        window.speechSynthesis.speak(u);
        return;
      }catch(_){}
    }

    // 2. Tải file âm thanh tiếng Việt chuẩn từ endpoint nội bộ /api/tts
    try{
      if(activeAudio){try{activeAudio.pause();}catch(_){}activeAudio=null;}
      const resp=await api('/tts?q='+encodeURIComponent(text),undefined,true);
      if(resp.ok){
        const blob=await resp.blob();
        const blobUrl=URL.createObjectURL(blob);
        const audio=new Audio(blobUrl);
        activeAudio=audio;
        audio.onended=()=>{URL.revokeObjectURL(blobUrl);if(activeAudio===audio)activeAudio=null;};
        audio.onerror=()=>{URL.revokeObjectURL(blobUrl);if(activeAudio===audio)activeAudio=null;};
        await audio.play();
        return;
      }
    }catch(_){}

    // 3. Fallback cuối cùng nếu không có mạng / lỗi
    if(window.speechSynthesis){
      try{
        window.speechSynthesis.cancel();
        const u=new SpeechSynthesisUtterance(text);
        u.lang='vi-VN';
        u.rate=1.0;
        window.speechSynthesis.speak(u);
      }catch(_){}
    }
  }
  function formatAgentSpeech(item){
    if(!item)return 'Agent đã hoàn thành công việc.';
    let agentNum=null, provider='';
    if(typeof item==='object'){
      agentNum=item.agent??item.agent_n??null;
      provider=item.provider||'';
      if(!agentNum&&item.id){
        if(item.id==='agent0')return 'Agent 0 đã hoàn thành công việc.';
        const m=String(item.id).match(/^([a-z0-9]+)[-_ ](\d+)$/i);
        if(m){provider=provider||m[1];agentNum=m[2];}
      }
      if(!agentNum&&item.title){
        const m=String(item.title).match(/Agent\s*(\d+)/i);
        if(m)agentNum=m[1];
        const p=String(item.title).match(/(claude|codex|agy|antigravity)/i);
        if(p)provider=provider||p[1];
      }
    }else if(typeof item==='string'){
      if(item==='agent0'||item.includes('Agent 0'))return 'Agent 0 đã hoàn thành công việc.';
      const m=item.match(/Agent\s*(\d+)/i)||item.match(/^([a-z0-9]+)[-_ ](\d+)$/i);
      if(m)agentNum=m[2]||m[1];
      const p=item.match(/(claude|codex|agy|antigravity)/i);
      if(p)provider=p[1];
    }
    const provNames={claude:'Claude',codex:'Codex',agy:'Antigravity',antigravity:'Antigravity'};
    const pName=provNames[String(provider).toLowerCase()]||provider||'';
    if(agentNum!=null){
      return pName?`Agent ${agentNum} ${pName} đã hoàn thành công việc.`:`Agent ${agentNum} đã hoàn thành công việc.`;
    }
    if(pName){
      return `Agent ${pName} đã hoàn thành công việc.`;
    }
    return 'Agent đã hoàn thành công việc.';
  }
  function agentDisplayName(task){
    const provider=task.provider||'worker';
    return task.agent?`Agent ${task.agent} (${provider})`:provider;
  }
  const seenTaskStatuses=new Map();
  const notifiedTaskIds=new Set();
  function checkTaskSoundAlerts(newTasks){
    if(!seenTaskStatuses.size){
      for(const t of newTasks){
        seenTaskStatuses.set(t.id,t.status);
        if(t.status==='awaiting_review'||t.status==='approved'||t.status==='failed')notifiedTaskIds.add(t.id);
      }
      return;
    }
    for(const t of newTasks){
      const prev=seenTaskStatuses.get(t.id);
      if(prev&&prev!==t.status){
        seenTaskStatuses.set(t.id,t.status);
        const name=agentDisplayName(t);
        if(t.status==='awaiting_review'&&!notifiedTaskIds.has(t.id)){
          notifiedTaskIds.add(t.id);
          const speechMsg=formatAgentSpeech(t);
          playChime('success');
          setTimeout(()=>speakText(speechMsg),250);
          notify(`${name} đã làm xong công việc, chờ review!`,false,'Nhiệm vụ hoàn tất');
        }else if(t.status==='failed'&&!notifiedTaskIds.has(t.id)){
          notifiedTaskIds.add(t.id);
          const failSpeech=formatAgentSpeech(t).replace('đã hoàn thành công việc.','gặp sự cố khi làm việc.');
          playChime('error');
          setTimeout(()=>speakText(failSpeech),250);
          notify(`${name} gặp sự cố khi làm nhiệm vụ!`,true,'Nhiệm vụ thất bại');
        }else if(t.status==='approved'){
          // Agent 0 check và duyệt task: KHÔNG PHÁT GIỌNG NÓI để tránh lặp lại thông báo!
          notify(`Nhiệm vụ của ${name} đã được phê duyệt!`,false,'Nhiệm vụ được duyệt');
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
  function navigate(page){state.page=page;$$('[data-view]').forEach(e=>e.hidden=e.dataset.view!==page);$$('[data-page]').forEach(e=>e.setAttribute('aria-current',e.dataset.page===page?'page':'false'));$('[data-title]').textContent=pages[page][1];$('[data-sub]').textContent=pages[page][2];$('[data-crumb]').textContent=pages[page][0];root.classList.toggle('ao-console-compact',page==='terminals');if(page==='history')loadHistory();save();requestAnimationFrame(drawEdges);}
  // Preserve the supplied compact toolbar, sidebar and scoped visual styles.
  const view=$('[data-view="terminals"]'),toolbar=view.querySelector('.ao-console-toolbar'),inventory=view.querySelector('.ao-console-inventory');
  const bar=$('[data-compact-console-bar]').content.cloneNode(true).firstElementChild;
  bar.querySelector('.ao-console-bar-info').append(inventory.querySelector('.ao-window-range'));
  bar.querySelector('[data-compact-layout-mount]').append(toolbar.querySelector('.ao-layout-group'));
  bar.querySelector('[data-compact-mode-mount]').append(toolbar.querySelector('.ao-console-mode'));
  const add=inventory.querySelector('[data-console-action="add"]');add.innerHTML='<i data-lucide="plus"></i>CMD';add.setAttribute('aria-label','Thêm cửa sổ theo dõi');bar.querySelector('.ao-console-bar-actions').prepend(add);
  const reload=inventory.querySelector('[data-console-action="feed"]');reload.textContent='Làm mới log';bar.querySelector('[data-compact-extra-mount]').append(reload);
  const newChat=inventory.querySelector('[data-console-action="newchat"]');if(newChat)bar.querySelector('.ao-console-bar-actions').prepend(newChat);
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
  function roleLabel(slug){return (state.config?.roles||[]).find(r=>r.slug===slug)?.label||slug;}
  function configure(config){
    state.config=config;const repoName=config.repo.split(/[\\/]/).pop();$('.ao-project').innerHTML=`<strong>${esc(repoName)}</strong><small>Nhánh cơ sở · ${esc(config.base_ref)}</small><small title="${esc(config.repo)}">${esc(config.repo)}</small><button type="button" class="ao-btn ao-repo-switch-btn cursor-interaction" data-action="open-repo-dialog"><i data-lucide="folder-search" aria-hidden="true"></i> Chọn thư mục...</button>`;
    $('.ao-crumb').innerHTML=`<i data-lucide="folder-git-2" style="cursor:pointer" data-action="open-repo-dialog" title="Chọn thư mục..."></i>${esc(repoName)}<span>/</span><strong data-crumb>${pages[state.page][0]}</strong>`;$('.ao-kicker').textContent='WORKSPACE / '+repoName.toUpperCase();
    $('[data-test-options]').innerHTML=config.tests.map((name,i)=>`<label><input type="checkbox" name="tests" value="${esc(name)}" ${i===0?'checked':''}> ${esc(name)}</label>`).join('')||'<span>Chưa cấu hình test profile. Thêm profile trong file cấu hình.</span>';
    [...form.elements.provider.options].forEach(o=>o.disabled=!config.providers[o.value]);const enabled=[...form.elements.provider.options].find(o=>!o.disabled);if(enabled)form.elements.provider.value=enabled.value;
    if(form.elements.role){
      const prevRole=form.elements.role.value,roles=Array.isArray(config.roles)?config.roles:[];
      form.elements.role.innerHTML='<option value="">Mặc định (không gắn vai trò)</option>'+roles.map(r=>`<option value="${esc(r.slug)}">${esc(r.label)}</option>`).join('');
      if(prevRole&&roles.some(r=>r.slug===prevRole))form.elements.role.value=prevRole;
    }
    $('[data-execution]').textContent=config.execution_enabled?'Đã cho phép chạy local':'Đang khóa thực thi';
    const policies=[['shield-check','Claude Worker','Restricted, chỉ đọc/sửa file; không cấp shell.'],['box','Codex Worker','Workspace-write; tắt mạng cho lệnh model theo adapter.'],['file-lock-2','Phạm vi chỉnh sửa','Kiểm tra sau khi chạy; sửa ngoài phạm vi sẽ chặn review/export.'],['terminal','Test profile',config.tests.length?config.tests.join(', ')+' · chạy bằng quyền tài khoản local.':'Chưa cấu hình.'],['fingerprint','Review và digest','Test, snapshot và SHA-256 được kiểm tra lại trước khi duyệt/xuất.'],['git-pull-request','Tích hợp','Người dùng áp dụng patch và kiểm thử lại; không tự commit/merge/push.'],['info','Runner','Launcher dự án mở runner cùng web; Ctrl+C dừng cả hai. Runner mở riêng không được web giám sát.']];
    $('[data-policy]').innerHTML=policies.map(([icon,name,description])=>`<div class="ao-permission"><i data-lucide="${icon}"></i><div>${esc(name)}<p>${esc(description)}</p></div></div>`).join('');icons();
  }
  function testSummary(t){const tests=t.result?.tests||[];return tests.length?`${tests.filter(x=>x.exit_code===0&&!x.reason).length}/${tests.length} profile đạt`:'Chưa có kết quả';}
  function renderTasks(){
    const filter=$('[data-task-filter]').value,term=search.value.toLowerCase(),tasks=state.tasks.filter(t=>(filter==='all'||t.status===filter)&&(!term||(title(t)+' '+t.id+' '+(t.role||'')).toLowerCase().includes(term)));
    $('[data-task-rows]').innerHTML=tasks.length?tasks.map(t=>`<tr ${t.id===state.selected?'aria-selected="true"':''}><td><strong>${esc(title(t))}</strong><small>${short(t.id)} · ${esc(t.allow_paths.join(', '))}</small></td><td>${esc(t.agent?`${t.provider} ${t.agent}`:t.provider)}${t.round>1?`<small>vòng ${t.round}</small>`:''}${t.role?`<small>${esc(t.role)}</small>`:''}</td><td>${chip(t.status)}${t.cancel_requested?'<small>Đã yêu cầu hủy</small>':''}</td><td>${esc(testSummary(t))}</td><td><button class="ao-link" type="button" data-task="${t.id}">Chi tiết →</button></td></tr>`).join(''):'<tr><td colspan="5" class="ao-empty">Không có nhiệm vụ phù hợp. Tạo nhiệm vụ để bắt đầu.</td></tr>';
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

    const liveAgents=(state.sessions||[]).filter(s=>s.kind==='agent'&&s.alive);
    if(!relevantTasks.length){
      if(liveAgents.length){
        for(const s of liveAgents){
          const p=s.provider;
          const provLabel={claude:'Claude',codex:'Codex',agy:'Antigravity'}[p]||p;
          const agentName=s.title||(`Agent ${s.agent||''} · ${provLabel}`);
          const isBusy=!s.idle;
          const cwdName=s.cwd?s.cwd.split(/[\\/]/).pop():'';
          lanes.push({
            key:s.id,
            provider:p,
            agent:s.agent,
            session:s,
            task:null,
            worker:{
              name:agentName,
              desc:'Cửa sổ CMD · '+(cwdName||s.id),
              text:isBusy?'Đang chạy / xử lý':'Sẵn sàng · Chờ lệnh',
              running:isBusy,
              success:!isBusy
            },
            test:{
              name:'Theo dõi · '+agentName,
              desc:s.id+(s.readonly?' · Chỉ đọc':' · Tương tác'),
              text:isBusy?'Đang hoạt động':'Chờ Agent 0 giao việc',
              running:isBusy,
              success:!isBusy
            }
          });
        }
      }else if(state.runners?.managed){
        const provs=Object.keys(state.runners?.providers||{}).filter(p=>['claude','codex','agy'].includes(p));
        for(const p of provs){
          const runner=state.runners.providers[p];
          if(!runner||runner.status==='stopped')continue;
          const provLabel={claude:'Claude',codex:'Codex',agy:'Antigravity'}[p]||p;
          const runnerText=({starting:'Runner đang khởi động',polling:'Runner đang nhận việc',idle:'Runner sẵn sàng',busy:'Runner đang xử lý',stopped:'Runner đã dừng',error:'Runner lỗi'}[runner.status]||runner.status);
          const agentName=provLabel+' Worker';
          lanes.push({
            key:p,
            provider:p,
            agent:null,
            task:null,
            worker:{name:agentName,desc:'Runner '+p,text:runnerText,running:runner.status==='busy',success:runner.status==='idle'},
            test:{name:'Test · '+agentName,desc:'Test runner',text:'Chờ worker',running:false,success:false}
          });
        }
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
      const isTerminalFlow=!relevantTasks.length&&liveAgents.length>0;
      data.review={
        name:isTerminalFlow?'Nghiệm thu':'Review',
        desc:isTerminalFlow?'Agent 0 theo dõi và đánh giá':(rv?short(rv.id)+' · '+(rv.result?.changed_files?.length||0)+' file đổi':'Chưa có diff chờ duyệt'),
        text:isTerminalFlow?'Nghiệm thu qua Cửa sổ CMD':(rv?'Task chờ duyệt':reviewCount?`${reviewCount} task chờ duyệt`:'Chờ kiểm tra'),
        task:rv
      };
      data.export={
        name:isTerminalFlow?'Tích hợp':'Xuất patch',
        desc:isTerminalFlow?'Commit & tích hợp vào repo':(ap?short(ap.id)+' · sẵn sàng xuất':'Chưa có patch được duyệt'),
        text:isTerminalFlow?'Theo chỉ đạo của Agent 0':(ap?'Đã duyệt · có thể xuất':approvedCount?`${approvedCount} đã duyệt · có thể xuất`:'Chờ được duyệt'),
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
          if(l.session)wNode.dataset.termId=l.session.id;
          wNode.style.top=l.top+'px';wNode.style.left='264px';wNode.style.width='218px';wNode.style.height='136px';
          wNode.innerHTML=`<div class="ao-node-top flow-node__top"><span class="flow-node__type">${l.session?'Agent':'Worker'}</span><span class="flow-node__id">${short(l.task?.id||l.session?.id||'')}</span></div><div class="ao-node-name">${esc(l.worker.name)}</div><div class="ao-node-desc flow-node__desc" title="${esc(l.task?.id||l.session?.id||'')} · ${esc(title(l.task||{}))}">${esc(l.worker.desc)}</div><div class="ao-node-foot flow-node__status ${l.worker.running?'status-running':l.worker.success?'status-success':''}" title="${esc(l.worker.text)}">${esc(l.worker.text)}</div>`;
          board.append(wNode);

          const tNode=document.createElement('button');
          tNode.type='button';
          tNode.className='ao-node flow-node flow-node--test-1 cursor-interaction';
          tNode.dataset.node='test'+l.key;tNode.dataset.taskId=l.task?.id||'';tNode.dataset.flowRunning=String(!!l.test.running);
          if(l.session)tNode.dataset.termId=l.session.id;
          tNode.style.top=l.top+'px';tNode.style.left='534px';tNode.style.width='194px';tNode.style.height='136px';
          tNode.innerHTML=`<div class="ao-node-top flow-node__top"><span class="flow-node__type">${l.session?'Theo dõi':'Test'}</span><span class="flow-node__id">${short(l.task?.id||l.session?.id||'')}</span></div><div class="ao-node-name">${esc(l.test.name)}</div><div class="ao-node-desc flow-node__desc" title="${esc(l.test.desc)}">${esc(l.test.desc)}</div><div class="ao-node-foot flow-node__status ${l.test.running?'status-running':l.test.success?'status-success':''}" title="${esc(l.test.text)}">${esc(l.test.text)}</div>`;
          board.append(tNode);
        }

        const rNode=document.createElement('button');
        rNode.type='button';
        rNode.className='ao-node flow-node flow-node--review cursor-interaction';
        rNode.dataset.node='review';rNode.dataset.taskId=rv?.id||'';
        rNode.style.top=centerY+'px';rNode.style.left='800px';rNode.style.width='198px';rNode.style.height='132px';
        rNode.innerHTML=`<div class="ao-node-top flow-node__top"><span class="flow-node__type">Kiểm soát</span><span class="flow-node__id">${rv?short(rv.id):''}</span></div><div class="ao-node-name">${esc(data.review.name)}</div><div class="ao-node-desc flow-node__desc" title="${esc(data.review.desc)}">${esc(data.review.desc)}</div><div class="ao-node-foot flow-node__status" title="${esc(data.review.text)}">${esc(data.review.text)}</div>`;
        board.append(rNode);

        const eNode=document.createElement('button');
        eNode.type='button';
        eNode.className='ao-node flow-node flow-node--patch cursor-interaction';
        eNode.dataset.node='export';eNode.dataset.taskId=ap?.id||'';
        eNode.style.top=centerY+'px';eNode.style.left='1074px';eNode.style.width='172px';eNode.style.height='132px';
        eNode.innerHTML=`<div class="ao-node-top flow-node__top"><span class="flow-node__type">Tích hợp</span><span class="flow-node__id">${ap?short(ap.id):''}</span></div><div class="ao-node-name">${esc(data.export.name)}</div><div class="ao-node-desc flow-node__desc" title="${esc(data.export.desc)}">${esc(data.export.desc)}</div><div class="ao-node-foot flow-node__status" title="${esc(data.export.text)}">${esc(data.export.text)}</div>`;
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
    const isTerminalFlow=!relevantTasks.length&&liveAgents.length>0;
    $$('[data-flow-summary]').forEach(e=>{
      if(!lanes.length){
        e.textContent='Chưa có hoạt động';
        e.classList.remove('has-activity');
      }else if(isViewingTask&&selectedTask){
        e.textContent=`Xem lại task ${short(selectedTask.id)}`;
        e.classList.remove('has-activity');
      }else if(isTerminalFlow){
        const activeCount=liveAgents.filter(s=>!s.idle).length;
        e.textContent=activeCount?`${activeCount} agent đang thực hiện lệnh · ${liveAgents.length} agent mở`:`${liveAgents.length} agent tương tác sẵn sàng`;
        e.classList.add('has-activity');
      }else{
        e.textContent=running?`${running} task đang thực hiện`:reviewCount?`${reviewCount} task chờ review`:'Sẵn sàng';
        e.classList.toggle('has-activity',running>0);
      }
    });

    const selected=state.flowNode&&data[state.flowNode],task=selected?.task;
    $$('[data-node-title]').forEach(e=>e.textContent=task?selected.name+' · '+short(task.id):(lanes.length?(isViewingTask?`Nhiệm vụ ${short(selectedTask.id)}`:(isTerminalFlow?'Điều phối Agent tương tác':'Quy trình điều phối')):'Agent 0 · Sẵn sàng điều phối'));
    $$('[data-node-description]').forEach(e=>e.textContent=task?title(task)+' · '+selected.text:(lanes.length?(isViewingTask?'Sơ đồ quy trình thực hiện của nhiệm vụ đã chọn. Bấm các bước để xem chi tiết.':(isTerminalFlow?'Agent 0 đang điều phối các cửa sổ terminal tương tác. Bấm vào từng bước để chuyển sang Cửa sổ CMD.':'Chọn một bước để xem nhiệm vụ liên quan. Review và xuất patch không tự tích hợp vào main.')):'Agent 0 đang chờ lệnh.'));
    $$('[data-node-badge]').forEach(e=>e.textContent=task?labels[task.status]:(lanes.length?(isViewingTask?'Lịch sử':(isTerminalFlow?'Terminal trực tiếp':'Đang thực thi')):(a0.connected?'MCP Sẵn sàng':'Chờ kết nối')));
    $$('[data-action="open-task"]').forEach(btn=>{btn.textContent=isTerminalFlow?'Mở cửa sổ CMD →':'Xem nhiệm vụ →';});

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
  // ===== Quy tắc điều phối agent (docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md): cấu hình Agent 0 điều phối các CMD agent =====
  const RULE_NUMBERS=[
    {key:'max_fix_rounds',label:'Số lần sửa trước khi thay cửa sổ',hint:'Agent chưa đạt thì Agent 0 yêu cầu sửa tối đa chừng này lần, sau đó đóng cửa sổ và mở cửa sổ mới.',min:0,max:10},
    {key:'max_agents_per_task',label:'Số cửa sổ tối đa cho một việc',hint:'Quá số này Agent 0 dừng lại và báo bạn kèm bằng chứng.',min:1,max:10},
    {key:'max_concurrent_agents',label:'Số agent chạy cùng lúc',hint:'Giới hạn agent tương tác đang sống (không tính Agent 0).',min:1,max:12},
    {key:'hang_minutes',label:'Phút im lặng coi là treo',hint:'Agent không tạo tệp mới và terminal im quá số phút này thì bị coi là treo.',min:1,max:240},
    {key:'max_line_chars',label:'Độ dài tối đa một dòng gõ vào terminal',hint:'Dòng dài bị terminal thu gọn thành văn bản dán và mất phần đầu.',min:80,max:4000},
    {key:'ram_free_warn_mb',label:'Ngưỡng cảnh báo RAM trống (MB)',hint:'Dưới ngưỡng này nên cân nhắc trước khi mở thêm agent.',min:0,max:1000000}];
  const RULE_BOOLS=[
    {key:'concurrency_enforced',label:'Chặn mở agent khi đã đủ số chạy cùng lúc',hint:'Tắt: chỉ ghi vào quy tắc, công cụ không chặn (cho vượt tạm thời).'},
    {key:'single_builder',label:'Chỉ một agent build/chạy test nặng tại một thời điểm',hint:'Các agent khác chỉ viết mã và chờ lệnh.'},
    {key:'close_on_success',label:'Đóng cửa sổ khi việc đã nghiệm thu đạt',hint:'Trừ khi còn việc kế tiếp cho chính agent đó.'},
    {key:'prompt_in_file',label:'Prompt giao việc phải ghi thành tệp',hint:'Dòng gõ vào terminal chỉ trỏ tới tệp.'},
    {key:'report_in_file',label:'Báo cáo cuối ghi ra tệp',hint:'Trong terminal chỉ trả đường dẫn và tối đa 3 dòng tóm tắt.'},
    {key:'roles_enabled',label:'Bật thư viện vai trò & mẫu chuẩn (roles)',hint:'Đồng bộ bộ vai trò chuyên môn và khung mẫu bàn giao ra {ROLES_DIR}, kèm chỉ dẫn cho Agent 0.'}];
  const RULE_TEXTS=[
    {key:'rules',label:'Quy tắc điều phối',hint:'Nội dung chính Agent 0 phải tuân thủ. Biến dùng được: '},
    {key:'constraints',label:'Ràng buộc chung dán vào mọi prompt giao agent code',hint:'Điều cấm/bắt buộc Agent 0 phải chép vào mọi tệp prompt. Thêm ràng buộc riêng của dự án ở đây.'},
    {key:'checklist',label:'Checklist nghiệm thu',hint:'Các phép kiểm Agent 0 phải làm trước khi tuyên bố đạt.'}];
  const RULE_PROVIDERS={agy:'agy',claude:'claude',codex:'codex'},RULE_EFFORTS={'':'Không chỉ định',low:'low',medium:'medium',high:'high'};
  const RULES_MARK='<!-- agent-studio-rules v1 -->';
  const rulesModal=document.createElement('dialog');rulesModal.className='ao-window-dialog ao-rules-dialog';root.append(rulesModal);
  let rulesView=null;
  const rulesSel=(opts,value,attr)=>`<select ${attr}>${Object.entries(opts).map(([v,l])=>`<option value="${esc(v)}" ${String(value)===v?'selected':''}>${esc(l)}</option>`).join('')}</select>`;
  const ruleDefault=def=>`<em class="ao-rule-default">Mặc định: ${esc(def===''||def==null?'trống':def===true?'bật':def===false?'tắt':def)}</em>`;
  function renderRules(view){
    rulesView=view;const p=view.params,d=view.default.params,t=view.texts;
    const running=view.agent0_running,applied=view.applied_digest===view.digest;
    const status=running?(applied?'Agent 0 đang chạy đã nhận bản quy tắc này.':'Agent 0 đang chạy chưa nhận bản mới. Khởi động lại Agent 0 để áp dụng.'):'Agent 0 chưa chạy: bản này sẽ được dùng khi mở Agent 0.';
    const nums=RULE_NUMBERS.map(f=>`<label class="ao-rule-field"><strong>${esc(f.label)}</strong><input type="number" inputmode="numeric" min="${f.min}" max="${f.max}" value="${esc(p[f.key])}" data-rp="${f.key}">${ruleDefault(d[f.key])}<small>${esc(f.hint)}</small></label>`).join('');
    const providers=`<label class="ao-rule-field"><strong>CLI mặc định</strong>${rulesSel(RULE_PROVIDERS,p.default_provider,'data-rp="default_provider"')}${ruleDefault(d.default_provider)}<small>Dùng khi bạn không nói rõ.</small></label>
      <label class="ao-rule-field"><strong>Chính sách subagent</strong>${rulesSel({allowed:'Cho phép (subagent mặc định của CLI)',off:'Tắt'},p.subagent_policy,'data-rp="subagent_policy"')}${ruleDefault(d.subagent_policy==='allowed'?'Cho phép':'Tắt')}<small>Subagent chạy trong cùng cửa sổ, không mở thêm cửa sổ.</small></label>`;
    const models=Object.keys(RULE_PROVIDERS).map(k=>`<div class="ao-rule-field ao-rule-model"><strong>Model mong đợi · ${esc(k)}</strong><div class="ao-rule-pair"><input type="text" maxlength="80" value="${esc(p.provider_models[k].model)}" placeholder="Ví dụ ${esc(d.provider_models[k].model||'tên model')}" data-rp-model="${k}" aria-label="Model ${esc(k)}">${rulesSel(RULE_EFFORTS,p.provider_models[k].effort,`data-rp-effort="${k}" aria-label="Mức suy luận ${k}"`)}</div>${ruleDefault(d.provider_models[k].model?d.provider_models[k].model+' · '+d.provider_models[k].effort:'trống')}<small>Agent 0 đọc terminal để xác nhận trước khi giao việc; để trống nếu không cần.</small></div>`).join('');
    const bools=RULE_BOOLS.map(f=>`<label class="ao-setting"><input type="checkbox" data-rp="${f.key}" ${(p[f.key]??d[f.key])?'checked':''}><span><strong>${esc(f.label)}</strong><small>${esc(f.hint)}</small></span></label>`).join('');
    const texts=RULE_TEXTS.map(f=>`<div class="ao-rule-text"><div class="ao-rule-text-head"><strong>${esc(f.label)}</strong><small data-rt-count="${f.key}">${t[f.key].length}/${view.text_limit}</small></div><small>${esc(f.hint)}${f.key==='rules'?esc(view.variables.map(v=>'{'+v+'}').join(' ')):''}</small><textarea class="ao-rules-text" rows="${f.key==='rules'?14:7}" maxlength="${view.text_limit}" data-rt="${f.key}" spellcheck="false">${esc(t[f.key])}</textarea></div>`).join('');
    const rolesCatalog=Array.isArray(view.roles)&&view.roles.length?(()=>{
      const first=view.roles[0],opts=view.roles.map((r,i)=>`<option value="${i}">${esc(r.label)} (${esc(r.relpath)})</option>`).join('');
      return `<h3>Thư viện vai trò &amp; mẫu chuẩn</h3><div class="ao-rule-field"><small>Thư mục đồng bộ tự động ngoài repo: <code>${esc(view.roles_dir||'')}</code></small><select data-role-inspect aria-label="Chọn vai trò hoặc mẫu chuẩn để xem nội dung">${opts}</select><small data-role-inspect-meta>${esc(first.summary)} · <code>${esc(first.path)}</code></small><pre class="ao-code ao-rules-preview" data-role-inspect-body>${esc(first.content)}</pre></div>`;
    })():'';
    const hist=view.history.length?view.history.map((h,i)=>`<li><span>${esc(String(h.time||'').replace('T',' ').slice(0,19))}</span><button type="button" class="ao-link cursor-interaction" data-rules-restore="${i}">Khôi phục</button></li>`).join(''):'<li class="ao-empty">Chưa có bản cũ nào.</li>';
    rulesModal.innerHTML=`<div class="ao-rules-body"><div class="ao-rules-head"><h2>Quy tắc điều phối agent</h2><button type="button" class="ao-settings-close cursor-interaction" data-rules-close aria-label="Đóng"><i data-lucide="x" aria-hidden="true"></i></button></div>
      <p class="ao-sub">Cách Agent 0 giao việc cho các cửa sổ CMD, nghiệm thu, sửa và thay cửa sổ. Lưu xong có hiệu lực cho phiên Agent 0 kế tiếp (mở mới, khởi động lại hoặc mở lại phiên).</p>
      <div class="ao-notice ao-rules-status" data-rules-status><span>${esc(status)}</span>${running&&!applied?'<button type="button" class="ao-btn cursor-interaction" data-rules-restart>Khởi động lại Agent 0 để áp dụng</button>':''}</div>
      <h3>Tham số</h3><div class="ao-rules-grid">${nums}${providers}${models}
      <label class="ao-rule-field ao-rule-wide"><strong>Thư mục lưu tệp prompt và báo cáo</strong><input type="text" maxlength="260" value="${esc(p.prompts_dir)}" placeholder="Để trống: thư mục riêng của công cụ, nằm ngoài repo" data-rp="prompts_dir"><small>Phải là đường dẫn tuyệt đối nằm ngoài repo (để không bị commit). Agent phải đọc và ghi được thư mục này.</small></label></div>
      <div class="ao-rules-checks">${bools}</div>
      <h3>Nội dung</h3>${texts}
      <div class="ao-actions ao-rules-actions"><button type="button" class="ao-btn ao-primary cursor-interaction" data-rules-save>Lưu</button><button type="button" class="ao-btn cursor-interaction" data-rules-preview>Xem trước</button><button type="button" class="ao-btn cursor-interaction" data-rules-reset>Khôi phục mặc định</button><button type="button" class="ao-btn cursor-interaction" data-rules-export>Xuất .md</button><button type="button" class="ao-btn cursor-interaction" data-rules-import>Nhập .md</button><input type="file" accept=".md,text/markdown,text/plain" data-rules-file hidden></div>
      <div data-rules-preview-box hidden><h3>Xem trước: nội dung Agent 0 sẽ nhận</h3><pre class="ao-code ao-rules-preview" data-rules-preview-text></pre></div>
      ${rolesCatalog}
      <h3>Lịch sử (20 bản gần nhất)</h3><ul class="ao-rules-history">${hist}</ul></div>`;
    icons();
  }
  function collectRules(){
    const params={provider_models:{}},texts={};let bad=null;
    rulesModal.querySelectorAll('[data-rp]').forEach(el=>{
      const k=el.dataset.rp;el.removeAttribute('aria-invalid');
      if(el.type==='checkbox')params[k]=el.checked;
      else if(el.type==='number'){const v=el.value.trim(),n=Number(v);if(v===''||!Number.isInteger(n)||n<Number(el.min)||n>Number(el.max)){el.setAttribute('aria-invalid','true');bad=bad||`${k}: nhập số nguyên từ ${el.min} đến ${el.max}.`;}else params[k]=n;}
      else params[k]=el.value;
    });
    rulesModal.querySelectorAll('[data-rp-model]').forEach(el=>{params.provider_models[el.dataset.rpModel]={model:el.value,effort:rulesModal.querySelector(`[data-rp-effort="${el.dataset.rpModel}"]`).value};});
    rulesModal.querySelectorAll('[data-rt]').forEach(el=>{texts[el.dataset.rt]=el.value;});
    if(bad)throw new Error('Giá trị chưa hợp lệ. '+bad);
    return {params,texts};
  }
  const FENCE='`'.repeat(3);
  function rulesToMarkdown(view){
    let body;try{body=collectRules();}catch(_){body={params:view.params,texts:view.texts};}
    return `# Quy tắc điều phối agent\n\n${RULES_MARK}\n\n## Tham số\n\n${FENCE}json\n${JSON.stringify(body.params,null,2)}\n${FENCE}\n\n## Quy tắc điều phối\n\n${body.texts.rules}\n\n## Ràng buộc chung\n\n${body.texts.constraints}\n\n## Checklist nghiệm thu\n\n${body.texts.checklist}\n`;
  }
  function parseRulesMarkdown(text){
    text=text.replace(/\r\n/g,'\n');
    if(!text.includes(RULES_MARK))throw new Error('Tệp không phải bản xuất của Quy tắc điều phối agent (thiếu dấu nhận diện).');
    const parts=text.split(/\n## /).slice(1),map={};
    for(const part of parts){const nl=part.indexOf('\n');map[part.slice(0,nl).trim()]=part.slice(nl+1).replace(/^\n+/,'').replace(/\s+$/,'');}
    for(const n of ['Tham số','Quy tắc điều phối','Ràng buộc chung','Checklist nghiệm thu'])if(!(n in map))throw new Error('Thiếu mục "'+n+'".');
    const m=map['Tham số'].match(new RegExp(FENCE+'json\\n([\\s\\S]*?)\\n'+FENCE));if(!m)throw new Error('Mục "Tham số" thiếu khối JSON.');
    let params;try{params=JSON.parse(m[1]);}catch(_){throw new Error('Khối JSON ở mục "Tham số" không đọc được.');}
    if(!params||typeof params!=='object'||Array.isArray(params))throw new Error('Khối JSON ở mục "Tham số" không hợp lệ.');
    return {params,texts:{rules:map['Quy tắc điều phối'],constraints:map['Ràng buộc chung'],checklist:map['Checklist nghiệm thu']}};
  }
  async function openRules(){renderRules(await api('/orchestration-rules'));if(!rulesModal.open)rulesModal.showModal();}
  rulesModal.addEventListener('input',e=>{const t=e.target.closest('[data-rt]');if(!t)return;const c=rulesModal.querySelector(`[data-rt-count="${t.dataset.rt}"]`);if(c)c.textContent=t.value.length+'/'+rulesView.text_limit;});
  rulesModal.addEventListener('change',e=>{
    const ri=e.target.closest('[data-role-inspect]');
    if(ri&&rulesView&&Array.isArray(rulesView.roles)){
      const item=rulesView.roles[Number(ri.value)];
      if(item){
        const meta=rulesModal.querySelector('[data-role-inspect-meta]'),body=rulesModal.querySelector('[data-role-inspect-body]');
        if(meta)meta.innerHTML=`${esc(item.summary)} · <code>${esc(item.path)}</code>`;
        if(body)body.textContent=item.content;
      }
      return;
    }
    const f=e.target.closest('[data-rules-file]');if(!f||!f.files[0])return;const file=f.files[0];f.value='';
    runAction(async()=>{
      if(file.size>200000)throw new Error('Tệp quá lớn (tối đa 200 KB).');
      const data=parseRulesMarkdown(await file.text());
      renderRules({...rulesView,params:{...rulesView.params,...data.params,provider_models:{...rulesView.params.provider_models,...(data.params.provider_models||{})}},texts:data.texts});
      notify('Đã nạp nội dung từ tệp. Kiểm tra rồi bấm Lưu để áp dụng.');
    });
  });
  rulesModal.addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b)return;
    if('rulesClose' in b.dataset){rulesModal.close();return;}
    if('rulesSave' in b.dataset)runAction(async()=>{const v=await api('/orchestration-rules',collectRules());renderRules(v);notify('Đã lưu quy tắc. Có hiệu lực cho phiên Agent 0 kế tiếp.');});
    else if('rulesPreview' in b.dataset)runAction(async()=>{const r=await api('/orchestration-rules/preview',collectRules());const box=rulesModal.querySelector('[data-rules-preview-box]');box.hidden=false;rulesModal.querySelector('[data-rules-preview-text]').textContent=r.preview;if(r.unknown_variables.length)notify('Có biến không nhận ra, sẽ giữ nguyên chữ: '+r.unknown_variables.map(v=>'{'+v+'}').join(', '),true);box.scrollIntoView({block:'nearest'});});
    else if('rulesReset' in b.dataset){if(!confirm('Khôi phục toàn bộ tham số và nội dung về mặc định? Bản hiện tại được giữ trong Lịch sử.'))return;runAction(async()=>{renderRules(await api('/orchestration-rules/reset',{}));notify('Đã khôi phục mặc định.');});}
    else if('rulesRestore' in b.dataset)runAction(async()=>{renderRules(await api('/orchestration-rules/restore',{index:Number(b.dataset.rulesRestore)}));notify('Đã khôi phục bản lịch sử. Bản trước đó được giữ trong Lịch sử.');});
    else if('rulesRestart' in b.dataset){if(!confirm('Khởi động lại Agent 0? Cuộc trò chuyện hiện tại vẫn nằm trong Lịch sử.'))return;runAction(async()=>{await api('/orchestration-rules/restart-agent0',{});await syncTerms();renderRules(await api('/orchestration-rules'));notify('Đã khởi động lại Agent 0 với quy tắc mới.');});}
    else if('rulesExport' in b.dataset){const blob=new Blob([rulesToMarkdown(rulesView)],{type:'text/markdown'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='quy-tac-dieu-phoi-agent.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    else if('rulesImport' in b.dataset)rulesModal.querySelector('[data-rules-file]').click();
  });
  root.addEventListener('click',e=>{if(e.target.closest('[data-action="open-orch-rules"]'))runAction(openRules);});
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
    detail.innerHTML=`<div class="ao-actions ao-spread"><h3>${short(id)} · ${esc(title(t))}</h3>${chip(t.status)}</div><p class="ao-sub ao-wrap">${esc(t.prompt)}</p><div class="ao-detail-grid"><div><label>Base / worktree</label><p class="ao-wrap">${esc(t.base)}<br>orch/${esc(t.id)}</p></div><div><label>Phạm vi</label><p>${esc(t.allow_paths.join(', '))}</p></div><div><label>Test</label><p>${esc(testSummary(t))}</p></div>${t.role?`<div><label>Vai trò chuyên môn</label><p>${esc(roleLabel(t.role))} (<code>${esc(t.role)}</code>)</p></div>`:''}</div>${t.result?.error?`<div class="ao-notice error">${esc(t.result.error)}</div>`:''}<div class="ao-actions"><button class="ao-btn" data-detail="log">Log worker</button><button class="ao-btn" data-detail="events">Sự kiện</button>${['awaiting_review','approved','changes_requested'].includes(t.status)?'<button class="ao-btn" data-detail="diff">Xem diff & test</button>':''}${['queued','running'].includes(t.status)&&!t.cancel_requested?'<button class="ao-btn ao-danger" data-detail="cancel">Hủy nhiệm vụ</button>':''}<button class="ao-btn" data-detail="retry">${t.agent?`Giao việc tiếp cho ${esc(t.provider)} ${t.agent}`:'Giao việc tiếp'}</button></div><div class="ao-detail-content" data-detail-content></div><div data-review-controls></div>`;
    detail.scrollIntoView({block:'nearest',behavior:'smooth'});icons();
  }
  async function detailAction(action){
    const id=state.selected,t=state.tasks.find(t=>t.id===id);if(!t)return;const content=$('[data-detail-content]');
    if(action==='retry'){openForm(t.provider,t.agent?'':t.prompt,t.allow_paths.join(', '),t.agent,t.role||'');return;}
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
    if(state.sound){
      getAudioContext();
      requestNotificationPermission();
      playChime('success');
      setTimeout(()=>speakText('Đã bật âm thanh thông báo.'),250);
      notify('Đã bật âm thanh và thông báo');
    }else{
      notify('Đã tắt âm thanh và thông báo');
    }
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
  function placeTerm(w){const e=terms.get(w.id),card=$(`[data-window="${w.id}"]`);if(!e||!card)return;const host=card.querySelector('[data-term-host]');host.hidden=false;card.querySelector('[data-window-output]').hidden=true;const hist=card.querySelector('.ao-terminal-history');if(hist)hist.hidden=true;if(e.el.parentNode!==host)host.appendChild(e.el);if(!e.opened){e.opened=true;try{e.term.open(e.el);}catch(error){e.opened=false;}if(e.opened&&typeof WebglAddon!=='undefined'){try{const gl=new WebglAddon.WebglAddon();gl.onContextLoss(()=>{try{gl.dispose();}catch(_){}});e.term.loadAddon(gl);}catch(_){}}}if(e.observer)e.observer.disconnect();e.observer=new ResizeObserver(()=>{try{e.fit.fit();}catch(_){}});e.observer.observe(host);requestAnimationFrame(()=>{try{e.fit.fit();}catch(_){}});}
  function attachTerm(info){
    if(typeof Terminal==='undefined')return;
    const term=new Terminal({
      cursorBlink:info.kind!=='worker',
      disableStdin:info.kind==='worker',
      fontSize:13,
      fontFamily:'Consolas,"Courier New",monospace',
      scrollback:2000,
      theme:termTheme(),
      windowsPty:{backend:'conpty'},
      allowProposedApi:true
    });
    const fit=new FitAddon.FitAddon();term.loadAddon(fit);
    // WebGL renderer: far faster than the DOM renderer when the screen holds a lot of text. Loaded after open() (see placeTerm).

    const el=document.createElement('div');el.className='ao-term-el';
    const e={term,fit,el,after:0,dead:false,id:info.id,readonly:info.kind==='worker',queue:Promise.resolve(),agent:info.agent,provider:info.provider,title:info.title,kind:info.kind,gen:info.gen};terms.set(info.id,e);

    // Mọi đường dán (Ctrl+V, chuột phải, nút Dán) đi qua đây; cùng một nội dung đến lần hai trong 500ms là sự kiện trùng nên bỏ qua.
    e.pasteOnce=text=>{
      if(!text||e.readonly)return;
      const now=Date.now();
      if(e.lastPaste&&e.lastPaste.text===text&&now-e.lastPaste.t<500)return;
      e.lastPaste={text,t:now};
      term.paste(text);
    };

    // Bắt phím tắt Paste / Copy và xử lý bộ gõ tiếng Việt (IME/Unikey) trên terminal
    term.attachCustomKeyEventHandler(ev=>{
      if((ev.ctrlKey&&(ev.key==='v'||ev.key==='V'))||(ev.shiftKey&&ev.key==='Insert')){
        if(e.readonly){
          ev.preventDefault?.();
          return false;
        }
        // Trả false để xterm không gửi mã điều khiển ASCII \x16 vào ConPTY;
        // trình duyệt sẽ tự phát sự kiện 'paste' native vào textarea helper của xterm
        // và capture listener bên dưới sẽ gọi pasteOnce đúng 1 lần duy nhất.
        return false;
      }
      if(ev.ctrlKey&&(ev.key==='c'||ev.key==='C')&&term.hasSelection()){
        if(ev.type==='keydown'){
          navigator.clipboard.writeText(term.getSelection()).catch(()=>{});
        }
        return false;
      }
      return true;
    });

    // Đồng bộ với Windows Vietnamese IME / TSF composition:
    // xterm.js giữ chuỗi đã gõ trước đó trong textarea.value sau khi kết thúc composition (_finalizeComposition),
    // khiến lần gõ dấu tiếp theo (keyCode 229) so sánh độ dài sai và tự phát DEL (\x7f) làm mất chữ hoặc lặp chữ.
    // Xóa sạch textarea.value ngay sau mỗi nhịp compositionend giúp từng ký tự tiếng Việt độc lập.
    el.addEventListener('compositionend',()=>{
      setTimeout(()=>{
        if(term.textarea&&!e.readonly){term.textarea.value='';}
      },0);
    },true);

    // Sự kiện Paste: capture-phase để chặn xterm internal handler (handlePasteEvent) khỏi gửi trùng vào ConPTY.
    // xterm đăng ký bubble-phase paste trên textarea VÀ element → nếu để bubble thì cả pasteOnce lẫn xterm đều gửi → dán 2 lần.
    el.addEventListener('paste',ev=>{
      if(e.readonly)return;
      ev.preventDefault();
      ev.stopPropagation();
      ev.stopImmediatePropagation();
      const text=(ev.clipboardData||window.clipboardData)?.getData('text');
      e.pasteOnce(text);
    },true);

    // Chuột phải: capture-phase chặn xterm rightClickHandler (di chuyển textarea dưới chuột gây paste thêm).
    // Bôi đen thì copy, không bôi đen thì paste.
    el.addEventListener('contextmenu',async ev=>{
      ev.preventDefault();
      ev.stopPropagation();
      ev.stopImmediatePropagation();
      if(e.pasteReading)return;
      if(term.hasSelection()){
        try{await navigator.clipboard.writeText(term.getSelection());}catch(_){}
        term.clearSelection();
      }else if(!e.readonly){
        e.pasteReading=true;
        try{
          e.pasteOnce(await navigator.clipboard.readText());
        }catch(_){}finally{e.pasteReading=false;}
      }
    },true);

    term.attachCustomWheelEventHandler(ev=>{
      if(term.buffer.active.type!=='alternate')return true; // normal buffer: xterm scrolls its own scrollback
      if(state.wheel==='arrows')return true;                // xterm default
      ev.preventDefault();
      if(state.wheel==='none'||e.readonly)return false;
      e.wheelAcc=(e.wheelAcc||0)+(ev.deltaMode===1?ev.deltaY*33:ev.deltaMode===2?ev.deltaY*400:ev.deltaY);
      let keys=0;while(Math.abs(e.wheelAcc)>=90&&keys<4){term.input(e.wheelAcc<0?'\x1b[5~':'\x1b[6~',true);e.wheelAcc-=Math.sign(e.wheelAcc)*90;keys++;}
      return false;
    });

    // Gửi từng sự kiện onData theo đúng thứ tự hàng đợi, KHÔNG gộp các lần onData trên client
    // (gộp Backspace + ký tự thay thế của Unikey/EVKey trong cùng 1 request sẽ làm TUI hiểu nhầm hoặc mất chữ).
    // Loại bỏ chuỗi báo focus (\x1b[I / \x1b[O) do trình duyệt tự phát khi cửa sổ IME / chuột đổi focus.
    // Bật log byte thô: localStorage.setItem('ao-term-debug','1') rồi tải lại trang.
    let debugIn=false;try{debugIn=localStorage.getItem('ao-term-debug')==='1';}catch(_){}
    const sendInput=chunk=>{
      const data=String(chunk||'').replace(/\x1b\[[IO]/g,'');
      if(!data)return;
      if(debugIn)console.log('[term in]',e.id,[...data].map(c=>c.codePointAt(0).toString(16)).join(' '));
      e.queue=e.queue.then(()=>api(`/terminals/${e.id}/input`,{data})).catch(()=>{});
    };
    e.flush=()=>{};

    term.onData(d=>{
      if(e.readonly)return;
      // Lệnh gạch chéo (/clear, /model...) do CLI tự xử lý: không coi là giao việc nên không báo "đã xong".
      let submitsWork=false;
      for(const ch of d.replace(/\x1b\[[0-?]*[ -\/]*[@-~]/g,'')){
        if(ch==='\x7f'||ch==='\b'){e.line=(e.line||'').slice(0,-1);}
        else if(ch==='\r'||ch==='\n'){const t=(e.line||'').trim();e.line='';if(!/^\/[^\s\/]*(\s|$)/.test(t))submitsWork=true;}
        else if(ch>=' ')e.line=((e.line||'')+ch).slice(-500);
      }
      if(e.id!=='agent0'&&submitsWork){
        e.awaitingResponse=true;
        e.notified=false;
        e.streamBytes=0;
        e.sentAt=Date.now();
        if(e.quietTimer){clearTimeout(e.quietTimer);e.quietTimer=null;}
      }
      if(d.includes('\x03')){
        e.awaitingResponse=false;
        e.notified=true;
        if(e.quietTimer){clearTimeout(e.quietTimer);e.quietTimer=null;}
      }
      sendInput(d);
    });

    term.onResize(({cols,rows})=>{api(`/terminals/${e.id}/resize`,{cols,rows}).catch(()=>{});});
    streamLoop();return e;
  }
  // Gom output của nhiều lần poll thành một lần write mỗi khung hình để xterm không bị nghẽn khi agy vẽ lại cả màn hình.
  function flushWrite(e){
    e.rafId=0;const parts=e.pending;if(!parts||!parts.length)return;e.pending=[];
    let n=0;for(const b of parts)n+=b.length;
    const all=parts.length===1?parts[0]:new Uint8Array(n);
    if(parts.length>1){let o=0;for(const b of parts){all.set(b,o);o+=b.length;}}
    try{e.term.write(all);}catch(_){}
  }
  let streaming=false;
  async function streamLoop(){
    if(streaming)return;streaming=true;
    try{while(terms.size){
      const live=[...terms.values()].filter(e=>!e.dead&&!e.ended);
      if(!live.length){await new Promise(r=>setTimeout(r,1000));continue;}
      const reqMap=new Map(live.map(e=>[e.id,e]));
      try{
        const r=await api('/terminals/stream?c='+encodeURIComponent(live.map(e=>e.id+':'+e.after).join(','))+'&wait=6');
        for(const [id,x] of Object.entries(r)){
          const e=reqMap.get(id);if(!e||e.dead||terms.get(id)!==e||(x.gen!=null&&e.gen!=null&&x.gen!==e.gen))continue;
          if(x.gone){e.dead=true;continue;}
          if(x.data){
            const bin=atob(x.data),bytes=new Uint8Array(bin.length);
            for(let k=0;k<bin.length;k++)bytes[k]=bin.charCodeAt(k);
            (e.pending||(e.pending=[])).push(bytes);
            if(!e.rafId)e.rafId=requestAnimationFrame(()=>flushWrite(e));
            if(!e.readonly&&e.id!=='agent0'&&e.awaitingResponse&&!e.notified){
              e.streamBytes=(e.streamBytes||0)+bytes.length;
              if(e.quietTimer)clearTimeout(e.quietTimer);
              const hasPromptMarker=bin.includes('? for shortcuts')||/(\r?\n|^)[>›]\s*$/.test(bin);
              const quietDelay=hasPromptMarker?800:2200;
              e.quietTimer=setTimeout(()=>{
                if(!e.awaitingResponse||e.notified)return;
                const elapsed=Date.now()-(e.sentAt||0);
                if(e.streamBytes>30&&elapsed>800){
                  e.notified=true;
                  e.awaitingResponse=false;
                  const speechMsg=formatAgentSpeech(e);
                  playChime('success');
                  setTimeout(()=>speakText(speechMsg),250);
                  notify(speechMsg,false,e.title||e.id);
                }else{
                  e.awaitingResponse=false;
                  e.notified=true;
                }
              },quietDelay);
            }
          }
          e.after=x.next;
          if(!x.alive){
            e.ended=true;
            if(!e.readonly&&e.id!=='agent0'&&e.awaitingResponse&&!e.notified){
              e.awaitingResponse=false;
              e.notified=true;
              if(e.quietTimer)clearTimeout(e.quietTimer);
              const speechMsg=formatAgentSpeech(e);
              playChime('success');
              setTimeout(()=>speakText(speechMsg),250);
              notify(speechMsg,false,e.title||e.id);
            }
            flushWrite(e);
            e.term.write(e.readonly?'\r\n\x1b[33m[Task đã kết thúc. Có thể đóng cửa sổ theo dõi này.]\x1b[0m\r\n':'\r\n\x1b[33m[Terminal đã kết thúc (mã '+x.exit_code+'). Bấm "Đóng terminal" để xóa cửa sổ này.]\x1b[0m\r\n');
          }
        }
      }catch(error){await new Promise(r=>setTimeout(r,1500));}
    }}finally{streaming=false;}
  }
  function dropTerm(id){const e=terms.get(id);if(!e)return;if(e.quietTimer)clearTimeout(e.quietTimer);if(e.flush)e.flush();e.dead=true;if(e.observer)e.observer.disconnect();e.term.dispose();terms.delete(id);}
  async function syncTerms(){
        
    const list=await api('/terminals');const ids=new Set(list.map(s=>s.id));let changed=list.length!==state.sessions.length||list.some((s,i)=>state.sessions[i]?.id!==s.id);
    const fresh=state.known?list.filter(x=>x.kind==='worker'&&!state.known.has(x.id)):[];state.known=new Set(ids);
    state.sessions=list;
    // A resumed conversation reuses the terminal id (agent0, claude-1) for a brand-new process whose output starts at 0.
    // Keeping the old xterm and read cursor mixes the two sessions, so a changed generation means: drop and rebuild.
    for(const s of list){const old=terms.get(s.id);if(old&&s.gen!=null&&old.gen!==s.gen){dropTerm(s.id);changed=true;}}
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
  function updateWindow(w,text){const card=$(`[data-window="${w.id}"]`);if(!card)return;const task=windowTask(w);const sess=w.session;card.querySelector('[data-window-path]').textContent=w.id==='agent0'?'Claude Code · MCP':sess?sess.id+' · '+(sess.kind==='worker'?(sess.remember===false?'không nhớ ngữ cảnh':'nhớ ngữ cảnh'):({claude:'Claude Code',codex:'Codex CLI',agy:'Antigravity CLI'}[sess.provider]||sess.provider)):'';const statusEl=card.querySelector('[data-window-status]');const statusLabel=w.id==='agent0'?(state.agent0.connected?'Đã kết nối':'Chưa kết nối'):sess?sessionState(sess):'';const isRunning=w.id==='agent0'?Boolean(state.agent0.connected||sess?.alive):Boolean(sess&&sess.alive);const wantCls='st-radar '+(isRunning?'running':'stopped');if(statusEl.className!==wantCls)statusEl.className=wantCls;if(statusEl.textContent!=='')statusEl.textContent='';const ariaVal=statusLabel||(isRunning?'Đang chạy':'Đã dừng');if(statusEl.getAttribute('aria-label')!==ariaVal)statusEl.setAttribute('aria-label',ariaVal);if(statusEl.title!==ariaVal)statusEl.title=ariaVal;const output=card.querySelector('[data-window-output]');if(output.textContent!==text){const atBottom=output.scrollTop+output.clientHeight>=output.scrollHeight-30;output.textContent=text;if(atBottom)output.scrollTop=output.scrollHeight;}}
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
  function renderWorkflows(){const box=$('[data-workflows]');if(!box)return;const list=state.workflows||[];box.innerHTML=`<div class="ao-panel-head"><div><h2>Workflow</h2><p>Kế hoạch nhiều bước do Agent 0 tạo bằng enqueue_plan: bước sau tự chạy khi các bước nó chờ đã xong.</p></div></div>`+(list.length?list.map(w=>`<article class="ao-wf"><header><strong>${esc(w.title)}</strong><span class="ao-wf-state ${esc(w.state)}">${esc(wfStates[w.state]||w.state)}</span><code>${esc(w.id)}</code>${w.state==='running'||w.state==='blocked'?`<button type="button" class="ao-btn cursor-interaction" data-wf-cancel="${esc(w.id)}">Hủy</button>`:''}</header><ol>${w.steps.map(s=>`<li class="ao-wf-step ${esc(s.status)}"><b>${esc(s.id)}</b><span>Agent ${s.agent} (${esc(s.provider)})${s.role?' · '+esc(s.role):''}</span><span>${esc(wfLabels[s.status]||s.status)}${s.task_status?' · '+esc(s.task_status):''}</span><small>${s.after.length?'sau '+s.after.map(esc).join(', '):'bắt đầu ngay'}${s.note?' · '+esc(s.note):''}</small></li>`).join('')}</ol></article>`).join(''):'<p class="ao-muted" style="padding:0 16px 16px">Chưa có workflow. Nhờ Agent 0 lập kế hoạch nhiều bước.</p>');}
  // Work from earlier chats is hidden by default (a new chat starts clean); this keeps it one click away.
  function renderScopeNote(){
    const box=$('[data-scope-note]');if(!box)return;
    const hidden=state.chat&&state.chat.hidden?state.chat.hidden:{tasks:0,review:0};
    box.hidden=!state.allChats&&!hidden.tasks;
    $('[data-scope-text]').textContent=state.allChats
      ?'Đang hiện cả nhiệm vụ của các cuộc trò chuyện trước.'
      :`Đang ẩn ${hidden.tasks} nhiệm vụ của các cuộc trò chuyện trước${hidden.review?` (${hidden.review} đang chờ review)`:''}.`;
    $('[data-scope-toggle]').textContent=state.allChats?'Chỉ cuộc trò chuyện hiện tại':'Hiện tất cả';
  }
  async function refreshData(){const q=state.allChats?'?scope=all':'';const prior=state.tasks.find(t=>t.id===state.selected)?.status;const [tasks,events,runners,agent0]=await Promise.all([api('/tasks'+q),api('/activity'+q),api('/runners'),api('/agent0').catch(()=>({connected:false}))]);checkTaskSoundAlerts(tasks);state.agent0=agent0;state.chat=await api('/chat').catch(()=>null);renderScopeNote();state.workflows=await api('/workflows'+q).then(r=>Array.isArray(r)?r:[]).catch(()=>[]);renderWorkflows();state.tasks=tasks;state.events=events;state.runners=runners;$('.ao-demo').textContent=runnerLabel();$('.ao-demo').classList.toggle('error',Object.values(runners.providers).some(r=>r.status==='error'));renderTasks();await syncTerms().catch(e=>{notify('Terminal: '+e.message,true);});buildWindows();$('[data-console-active]').textContent=tasks.filter(t=>t.status==='running').length+' task đang chạy';await refreshWindows();if(!state.busy&&state.page==='tasks'&&state.selected&&prior!==tasks.find(t=>t.id===state.selected)?.status)await selectTask(state.selected);}
  async function runAction(fn){if(state.busy)return;state.busy=true;root.setAttribute('aria-busy','true');$$('[data-review],[data-detail="export"],[data-action="create-task"]').forEach(b=>b.disabled=true);try{await fn();}catch(error){notify(error.message,true);}finally{state.busy=false;root.removeAttribute('aria-busy');$$('[data-review],[data-detail="export"],[data-action="create-task"]').forEach(b=>b.disabled=false);}}
  function openForm(provider,prompt='',scope='src, tests',agent=null,role=''){state.formAgent=agent||null;form.elements.provider.disabled=!!agent;form.querySelector('.ao-actions .ao-muted').textContent=agent?`Giao việc tiếp cho ${provider} ${agent}: theo cài đặt nhớ ngữ cảnh của agent.`:'Worker nhận việc khi runner đang hoạt động.';navigate('tasks');form.hidden=false;form.elements.prompt.value=prompt;form.elements.scope.value=scope;if(form.elements.role)form.elements.role.value=role||'';if(provider&&state.config?.providers[provider])form.elements.provider.value=provider;form.elements.prompt.focus();}
  form.addEventListener('submit',event=>{event.preventDefault();runAction(async()=>{if(!form.reportValidity())return;const data=new FormData(form),tests=data.getAll('tests'),role=String(data.get('role')||'').trim();if(!tests.length)throw Error('Chọn ít nhất một test profile.');const result=await api('/tasks',{...(state.formAgent?{agent:state.formAgent}:{provider:data.get('provider')}),...(role?{role}:{}),prompt:String(data.get('prompt')).trim(),allow_paths:String(data.get('scope')).split(/[,\n]/).map(x=>x.trim()).filter(Boolean),tests});form.hidden=true;form.elements.prompt.value='';if(form.elements.role)form.elements.role.value='';state.formAgent=null;form.elements.provider.disabled=false;notify(result.round>1?`${result.provider} ${result.agent} làm tiếp task ${short(result.id)} (vòng ${result.round}).`:`Đã thêm task ${short(result.id)} (${result.provider} ${result.agent}) vào hàng đợi.`);await refreshData();await selectTask(result.id);});});
  const modal=document.createElement('dialog');modal.className='ao-window-dialog';modal.innerHTML='<form method="dialog"><h2>Thêm terminal agent</h2><label>Agent<select data-add-agent required></select></label><label data-add-repo-wrap hidden>Repo (mã nguồn)<select data-add-repo></select></label><p>Mở một phiên tương tác thật. Agent 0 theo dõi được (chỉ đọc) qua list_terminals / read_terminal.</p><div class="ao-actions"><button value="cancel">Đóng</button><button value="add">Mở terminal</button></div></form>';root.append(modal);
  modal.addEventListener('close',()=>{if(modal.returnValue!=='add')return;const provider=modal.querySelector('[data-add-agent]').value,repo=modal.querySelector('[data-add-repo]').value;if(state.sessions.length>=12){notify('Tối đa 12 terminal.',true);return;}runAction(async()=>{const info=await api('/terminals/open',{kind:'agent',provider,...(repo&&repo!=='default'?{repo}:{}),cols:100,rows:30});state.focus=null;await syncTerms();const idx=state.windows.findIndex(w=>w.id===info.id);if(idx>=0)state.windowPage=Math.floor(idx/(layouts[state.layout][0]*layouts[state.layout][1]))+1;renderWindows();});});

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
          notify(`Đã chọn thư mục: ${applied.name||applied.repo}${applied.agent0_restarted?'. Agent 0 được mở lại để làm việc trên repo này.':''}`);
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
      notify(`Đã chọn thư mục: ${applied.name||applied.repo}${applied.agent0_restarted?'. Agent 0 được mở lại để làm việc trên repo này.':''}`);
      const cfg=await api('/config');
      configure(cfg);
      await refreshData();
    });
  });

  function openRepoDialog(){
    pickFolderNative();
  }

  const historyView=$('[data-view="history"]');
  historyView.innerHTML=`<div class="ao-panel ao-history-page"><div class="ao-history-toolbar"><input type="search" class="ao-history-search" data-history-search placeholder="Tìm theo tiêu đề, task hoặc ID..." aria-label="Tìm kiếm lịch sử"><select class="ao-history-select" data-history-provider aria-label="Lọc theo provider"><option value="">Tất cả agent</option><option value="agent0">Agent 0</option><option value="claude">Claude</option><option value="codex">Codex</option><option value="agy">Antigravity (agy)</option></select><button type="button" class="ao-btn cursor-interaction" data-history-refresh><i data-lucide="rotate-cw"></i>Làm mới</button><button type="button" class="ao-btn cursor-interaction" data-history-clear title="Xóa toàn bộ lịch sử không đang mở">Xóa tất cả</button></div><div class="ao-history-list" data-history-list role="feed" aria-label="Danh sách phiên làm việc"></div></div>`;

  const transcriptModal=document.createElement('dialog');
  transcriptModal.className='ao-window-dialog ao-transcript-dialog';
  transcriptModal.innerHTML=`<div class="ao-transcript-header"><div><h2 data-transcript-title>Xem lại transcript</h2><p class="ao-muted" style="margin:2px 0 0;font-size:12px" data-transcript-meta>Nội dung bản ghi màn hình (chỉ đọc)</p></div><div class="ao-actions"><button type="button" class="ao-btn cursor-interaction" data-transcript-copy><i data-lucide="copy"></i>Sao chép</button><button type="button" class="ao-winbtn ao-winbtn-close cursor-interaction" data-transcript-close aria-label="Đóng transcript"><i data-lucide="x"></i></button></div></div><div class="ao-transcript-body"><pre class="ao-transcript-content" data-transcript-content role="log" tabindex="0"></pre></div><div class="ao-transcript-footer"><span class="ao-muted" data-transcript-count>0 dòng</span><button type="button" class="ao-btn cursor-interaction" data-transcript-more hidden>Tải thêm dòng cũ hơn</button></div>`;
  root.append(transcriptModal);

  function formatConvDate(isoStr){
    if(!isoStr)return 'Khác';
    try{
      const d=new Date(isoStr);
      if(isNaN(d.getTime()))return 'Khác';
      const now=new Date(),today=new Date(now.getFullYear(),now.getMonth(),now.getDate()),target=new Date(d.getFullYear(),d.getMonth(),d.getDate()),diffDays=Math.round((today-target)/(1000*60*60*24));
      if(diffDays===0)return 'Hôm nay';
      if(diffDays===1)return 'Hôm qua';
      return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}`;
    }catch(_){return 'Khác';}
  }
  function convAgentBadge(c){
    if(c.kind==='agent0'||c.provider==='agent0')return 'Agent 0';
    const p=c.provider||'agent',names={claude:'Claude',codex:'Codex',agy:'Antigravity'},pName=names[p]||p;
    const n=c.agent_n??c.agent_number;return n?`${pName} ${n}`:pName;
  }
  const convStatusLabels={active:'Đang mở',closed:'Đã đóng',exited:'Đã đóng',failed:'Lỗi',awaiting_review:'Chờ review'};
  const convStart=c=>c.started||c.created_at;
  let convCache=[];
  async function loadHistory(){
    const listEl=historyView.querySelector('[data-history-list]');
    listEl.innerHTML='<p class="ao-muted" style="padding:24px;text-align:center">Đang tải lịch sử…</p>';
    const q=historyView.querySelector('[data-history-search]').value.trim();
    const prov=historyView.querySelector('[data-history-provider]').value;
    const params=new URLSearchParams({limit:'100'});
    if(q)params.set('q',q);
    if(prov)params.set('provider',prov);
    try{
      const convs=await api('/conversations?'+params.toString());
      convCache=convs;
      renderHistoryList(convs);
    }catch(err){
      listEl.innerHTML=`<p class="ao-notice error" style="margin:16px">${esc(err.message)}</p>`;
    }
  }
  function renderHistoryList(convs){
    const listEl=historyView.querySelector('[data-history-list]');
    if(!convs||!convs.length){
      listEl.innerHTML='<p class="ao-empty" style="padding:24px;text-align:center">Không tìm thấy phiên hội thoại nào.</p>';
      return;
    }
    const groups=new Map();
    for(const c of convs){
      const dt=formatConvDate(convStart(c));
      if(!groups.has(dt))groups.set(dt,[]);
      groups.get(dt).push(c);
    }
    let html='';
    for(const [dateLabel,items] of groups){
      html+=`<div class="ao-history-group-title">${esc(dateLabel)}</div>`;
      for(const c of items){
        const startedAt=convStart(c)?new Date(convStart(c)):null,timeStr=startedAt&&!isNaN(startedAt.getTime())?startedAt.toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'}):'—';
        const badgeText=convAgentBadge(c);
        const provClass=c.kind==='agent0'?'agy':(c.provider||'codex');
        const st=c.status||'exited';
        const stLabel=convStatusLabels[st]||st;
        const sub=[c.task_id?`task ${short(c.task_id)}`:'',c.cwd?c.cwd:''].filter(Boolean).join(' · ');
        const isLive=c.live===true;
        html+=`<div class="ao-history-row" data-conv-id="${esc(c.id)}"><time class="ao-history-time">${esc(timeStr)}</time><span class="ao-history-badge ${esc(provClass)}">${esc(badgeText)}</span><div class="ao-history-info"><strong class="ao-history-title" title="${esc(c.title||c.id)}">${esc(c.title||'Phiên làm việc '+short(c.id))}</strong><span class="ao-history-context" title="${esc(sub)}">${esc(sub||short(c.id))}</span></div><span class="ao-conv-status ${esc(st)}">${esc(stLabel)}</span><div class="ao-history-actions"><button type="button" class="ao-btn cursor-interaction" data-conv-resume="${esc(c.id)}" ${isLive?'disabled title="Phiên đang mở trong terminal"':''}>Mở lại</button><button type="button" class="ao-btn cursor-interaction" data-conv-view="${esc(c.id)}" title="Xem lại toàn bộ nội dung transcript">Xem lại</button><button type="button" class="ao-btn cursor-interaction" data-conv-delete="${esc(c.id)}" ${isLive?'disabled title="Đóng terminal trước khi xóa"':'title="Xóa phiên và bản ghi này khỏi máy"'}>Xóa</button></div></div>`;
      }
    }
    listEl.innerHTML=html;
    icons();
  }
  let historySearchTimer=null;
  historyView.querySelector('[data-history-search]').addEventListener('input',()=>{clearTimeout(historySearchTimer);historySearchTimer=setTimeout(loadHistory,200);});
  historyView.querySelector('[data-history-provider]').addEventListener('change',loadHistory);
  historyView.querySelector('[data-history-refresh]').addEventListener('click',loadHistory);
  historyView.querySelector('[data-history-clear]').addEventListener('click',()=>{
    if(!confirm('Xóa TOÀN BỘ lịch sử chat và bản ghi transcript (trừ các phiên đang mở)? Không thể hoàn tác.'))return;
    runAction(async()=>{const r=await api('/conversations/delete-all',{confirm:true});notify(`Đã xóa ${r.deleted} phiên${r.kept_open?` (giữ ${r.kept_open} phiên đang mở)`:''}.`);await loadHistory();});
  });
  historyView.addEventListener('click',event=>{
    const del=event.target.closest('[data-conv-delete]');if(!del||del.disabled)return;
    const id=del.dataset.convDelete,conv=convCache.find(c=>c.id===id)||{};
    if(!confirm(`Xóa phiên "${conv.title||short(id)}" và bản ghi của nó? Không thể hoàn tác.`))return;
    runAction(async()=>{await api(`/conversations/${id}/delete`,{});notify('Đã xóa phiên và bản ghi.');await loadHistory();});
  });

  let activeTranscriptConv=null,transcriptLines=[],transcriptHasMore=false,nextTranscriptAfter=0;
  async function openTranscript(convId){
    const conv=convCache.find(c=>c.id===convId)||{id:convId};
    activeTranscriptConv=conv;
    transcriptLines=[];
    nextTranscriptAfter=0;
    transcriptModal.querySelector('[data-transcript-title]').textContent=conv.title?`Xem lại: ${conv.title}`:`Xem lại transcript (${short(convId)})`;
    transcriptModal.querySelector('[data-transcript-meta]').textContent=`${convAgentBadge(conv)}${conv.cwd?' · '+conv.cwd:''}${conv.task_id?' · Task '+short(conv.task_id):''}`;
    const bodyEl=transcriptModal.querySelector('[data-transcript-content]');
    bodyEl.textContent='Đang tải bản ghi…';
    transcriptModal.querySelector('[data-transcript-count]').textContent='0 dòng';
    transcriptModal.querySelector('[data-transcript-more]').hidden=true;
    if(typeof transcriptModal.showModal==='function')transcriptModal.showModal();
    else transcriptModal.setAttribute('open','');
    icons();
    await loadTranscriptChunk(convId,0);
  }
  async function loadTranscriptChunk(convId,afterSeq){
    try{
      const res=await api(`/conversations/${convId}/transcript?after=${afterSeq}&limit=500`);
      const lines=res.lines||[];
      transcriptLines=transcriptLines.concat(lines);
      nextTranscriptAfter=res.next_after??(afterSeq+lines.length);
      transcriptHasMore=!!res.has_more;
      const bodyEl=transcriptModal.querySelector('[data-transcript-content]');
      if(!transcriptLines.length){
        bodyEl.textContent='Chưa có nội dung bản ghi màn hình cho phiên này.';
      }else{
        bodyEl.textContent=transcriptLines.map(l=>{
          let prefix='';
          if(l.timestamp){try{prefix=`[${new Date(l.timestamp).toLocaleTimeString('vi-VN')}] `;}catch(_){}}
          return `${prefix}${l.text}`;
        }).join('\n');
      }
      transcriptModal.querySelector('[data-transcript-count]').textContent=`${transcriptLines.length} dòng`;
      transcriptModal.querySelector('[data-transcript-more]').hidden=!transcriptHasMore;
    }catch(err){
      transcriptModal.querySelector('[data-transcript-content]').textContent=`Lỗi đọc transcript: ${err.message}`;
    }
  }
  transcriptModal.querySelector('[data-transcript-close]').addEventListener('click',()=>{
    if(typeof transcriptModal.close==='function')transcriptModal.close();
    else transcriptModal.removeAttribute('open');
  });
  transcriptModal.querySelector('[data-transcript-copy]').addEventListener('click',()=>{
    const text=transcriptModal.querySelector('[data-transcript-content]').textContent||'';
    if(!text)return;
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(()=>notify('Đã sao chép transcript.')).catch(()=>notify('Không thể sao chép.',true));
    }else{
      notify('Clipboard không khả dụng.',true);
    }
  });
  transcriptModal.querySelector('[data-transcript-more]').addEventListener('click',()=>{
    if(activeTranscriptConv)loadTranscriptChunk(activeTranscriptConv.id,nextTranscriptAfter);
  });
  async function resumeConversation(convId){
    const row=historyView.querySelector(`[data-conv-id="${convId}"]`);
    const btn=row?.querySelector('[data-conv-resume]');
    if(btn){btn.disabled=true;btn.textContent='Đang mở…';}
    try{
      const res=await api(`/conversations/${convId}/resume`,{});
      notify(`Đã khôi phục phiên: ${res.title||convId}`);
      navigate('terminals');
      await refreshData();
      const winId=res.id||res.terminal_id;
      if(winId){
        const idx=state.windows.findIndex(w=>w.id===winId);
        if(idx>=0){
          state.windowPage=Math.floor(idx/(layouts[state.layout][0]*layouts[state.layout][1]))+1;
          renderWindows();
        }
      }
    }catch(err){
      notify(`Không thể resume: ${err.message}`,true);
      if(btn){btn.disabled=false;btn.textContent='Mở lại';}
    }
  }
  // ===== Danh sách thả xuống theo template (docs/UI-RULES.md, mục 1) =====
  // Giữ nguyên <select> thật (giá trị, nhãn, kiểm tra hợp lệ, bố cục, đọc/ghi từ mã khác); chỉ thay danh sách bật ra
  // của hệ điều hành bằng menu dùng token --ao-*. Bàn phím: Enter/Space/Alt+↓ mở; ↑ ↓ Home End chọn; Enter chọn; Esc/Tab đóng.
  const selectMenu={el:null,sel:null,items:[],active:-1};
  function selectIsMenuable(sel){return sel&&sel.tagName==='SELECT'&&root.contains(sel)&&!sel.multiple&&!(sel.size>1)&&!sel.disabled;}
  function closeSelectMenu(refocus){
    const m=selectMenu;if(!m.el)return;
    const sel=m.sel;m.el.remove();sel.setAttribute('aria-expanded','false');
    m.el=null;m.sel=null;m.items=[];m.active=-1;
    if(refocus&&sel.isConnected)sel.focus();
  }
  function markSelectActive(index,scroll){
    const m=selectMenu;if(!m.el)return;
    m.active=index;
    m.items.forEach((item,i)=>{if(i===index)item.setAttribute('data-active','true');else item.removeAttribute('data-active');});
    if(scroll&&m.items[index]&&m.items[index].scrollIntoView)m.items[index].scrollIntoView({block:'nearest'});
  }
  function moveSelectActive(step,from){
    const m=selectMenu,n=m.items.length;let i=from;
    for(let tries=0;tries<n;tries++){i=(i+step+n)%n;if(!m.items[i].hasAttribute('aria-disabled'))return markSelectActive(i,true);}
  }
  function pickSelectOption(index){
    const m=selectMenu,sel=m.sel;if(!sel||!m.items[index]||m.items[index].hasAttribute('aria-disabled'))return;
    closeSelectMenu(true);
    if(sel.selectedIndex!==index){
      sel.selectedIndex=index;
      sel.dispatchEvent(new Event('input',{bubbles:true}));
      sel.dispatchEvent(new Event('change',{bubbles:true}));
    }
  }
  function openSelectMenu(sel){
    if(selectMenu.sel===sel){closeSelectMenu(true);return;}
    closeSelectMenu(false);
    const menu=document.createElement('div');
    menu.className='ao-select-menu';menu.setAttribute('role','listbox');menu.setAttribute('data-select-menu','');
    menu.innerHTML=[...sel.options].map((o,i)=>`<div class="ao-select-option" role="option" data-i="${i}" aria-selected="${o.selected}"${o.disabled?' aria-disabled="true"':''}>${esc(o.textContent)}</div>`).join('');
    (sel.closest('dialog')||root).append(menu);
    const r=sel.getBoundingClientRect(),vh=window.innerHeight||800,vw=window.innerWidth||1200;
    menu.style.minWidth=Math.max(r.width,140)+'px';
    menu.style.left=Math.max(8,Math.min(r.left,vw-(menu.offsetWidth||r.width)-8))+'px';
    const below=vh-r.bottom-8,above=r.top-8,want=Math.min(menu.scrollHeight||280,280);
    if(below<want&&above>below){menu.style.bottom=(vh-r.top+4)+'px';menu.style.maxHeight=Math.max(120,Math.min(280,above))+'px';}
    else{menu.style.top=(r.bottom+4)+'px';menu.style.maxHeight=Math.max(120,Math.min(280,below))+'px';}
    selectMenu.el=menu;selectMenu.sel=sel;selectMenu.items=[...menu.children];
    sel.setAttribute('aria-expanded','true');sel.setAttribute('aria-haspopup','listbox');
    markSelectActive(Math.max(0,sel.selectedIndex),true);
  }
  root.addEventListener('mousedown',event=>{
    const target=event.target;if(!target||!target.closest)return;
    const option=target.closest('.ao-select-option');
    if(option&&selectMenu.el&&selectMenu.el.contains(option)){event.preventDefault();pickSelectOption(Number(option.dataset.i));return;}
    const sel=target.closest('select');
    if(selectIsMenuable(sel)&&event.button===0){event.preventDefault();sel.focus();openSelectMenu(sel);return;}
    if(selectMenu.el&&!target.closest('[data-select-menu]'))closeSelectMenu(false);
  },true);
  root.addEventListener('mouseover',event=>{
    const option=event.target&&event.target.closest&&event.target.closest('.ao-select-option');
    if(option&&selectMenu.el&&selectMenu.el.contains(option)&&!option.hasAttribute('aria-disabled'))markSelectActive(Number(option.dataset.i),false);
  });
  root.addEventListener('keydown',event=>{
    const sel=event.target;
    if(selectMenu.el){
      const k=event.key;
      if(k==='ArrowDown'){event.preventDefault();moveSelectActive(1,selectMenu.active);}
      else if(k==='ArrowUp'){event.preventDefault();moveSelectActive(-1,selectMenu.active);}
      else if(k==='Home'){event.preventDefault();moveSelectActive(1,-1);}
      else if(k==='End'){event.preventDefault();moveSelectActive(-1,0);}
      else if(k==='Enter'||k===' '){event.preventDefault();pickSelectOption(selectMenu.active);}
      else if(k==='Escape'){event.preventDefault();event.stopPropagation();closeSelectMenu(true);}
      else if(k==='Tab')closeSelectMenu(false);
      return;
    }
    if(selectIsMenuable(sel)&&(event.key==='Enter'||event.key===' '||(event.altKey&&event.key==='ArrowDown'))){event.preventDefault();openSelectMenu(sel);}
  },true);
  window.addEventListener('resize',()=>closeSelectMenu(false));
  document.addEventListener('scroll',event=>{const t=event.target;if(selectMenu.el&&!(t&&t.nodeType===1&&t.closest('[data-select-menu]')))closeSelectMenu(false);},true);

  // ===== Cuộc trò chuyện mới: đóng mọi CMD (lưu vào Lịch sử), đánh số agent lại từ 1, mở lại Agent 0 =====
  const chatModal=document.createElement('dialog');chatModal.className='ao-window-dialog ao-chat-dialog';
  chatModal.innerHTML='<form method="dialog"><h2>Bắt đầu cuộc trò chuyện mới?</h2><p data-chat-intro></p><ul class="ao-chat-effects" data-chat-effects></ul><p class="ao-notice error" data-chat-block hidden></p><div class="ao-actions"><button type="button" class="ao-btn cursor-interaction" data-chat-cancel>Hủy</button><button type="button" class="ao-btn ao-btn-primary cursor-interaction" data-chat-confirm>Đóng và mở cuộc trò chuyện mới</button></div></form>';
  root.append(chatModal);
  async function openChatModal(){
    closeSettings();
    const st=await api('/chat');
    const confirmBtn=chatModal.querySelector('[data-chat-confirm]');
    chatModal.querySelector('[data-chat-intro]').textContent=st.windows
      ?`Cuộc trò chuyện hiện tại (${st.windows} cửa sổ CMD) sẽ kết thúc.`
      :'Chưa có cửa sổ CMD nào đang mở.';
    chatModal.querySelector('[data-chat-effects]').innerHTML=[
      st.windows?`Đóng ${st.windows} cửa sổ CMD; tất cả được giữ trong <strong>Lịch sử</strong> để xem lại hoặc mở lại.`:'',
      'Đánh số agent bắt đầu lại từ 1.',
      st.agent0?'Mở lại Agent 0 với một cuộc trò chuyện trống.':'Agent 0 sẽ không tự mở vì cấu hình chưa bật chạy cục bộ.'
    ].filter(Boolean).map(x=>`<li>${x}</li>`).join('');
    const block=chatModal.querySelector('[data-chat-block]');
    block.hidden=st.can_start;block.textContent=st.reason||'';
    confirmBtn.disabled=!st.can_start;confirmBtn.textContent='Đóng và mở cuộc trò chuyện mới';
    if(typeof chatModal.showModal==='function')chatModal.showModal();else chatModal.setAttribute('open','');
    icons();
  }
  chatModal.querySelector('[data-chat-confirm]').addEventListener('click',event=>{
    const btn=event.currentTarget;if(btn.disabled)return;
    btn.disabled=true;btn.textContent='Đang đóng…';
    runAction(async()=>{
      try{
        const r=await api('/chat/new',{confirm:true,cols:100,rows:30});
        if(typeof chatModal.close==='function')chatModal.close();else chatModal.removeAttribute('open');
        state.focus=null;state.windowPage=1;
        notify(`Đã bắt đầu cuộc trò chuyện mới: đóng ${r.closed} cửa sổ (đã lưu vào Lịch sử)${r.agent0?', mở lại Agent 0':''}.`);
        await refreshData();
      }catch(error){
        btn.disabled=false;btn.textContent='Đóng và mở cuộc trò chuyện mới';
        throw error;
      }
    });
  });
  chatModal.querySelector('[data-chat-cancel]').addEventListener('click',()=>{if(typeof chatModal.close==='function')chatModal.close();else chatModal.removeAttribute('open');});

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
            e.pasteOnce(text);
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
    const node=target.closest('[data-node]');if(node){
      const termId=node.dataset.termId;
      if(termId){state.focus=termId;navigate('terminals');renderWindows();refreshWindows();return;}
      const kind=node.dataset.node;state.flowNode=kind;
      const t=state.tasks.find(t=>t.id===node.dataset.taskId);
      if(t)runAction(()=>selectTask(t.id));
      else if(kind==='agent0'){state.focus='agent0';navigate('terminals');renderWindows();refreshWindows();}
      else notify('Chưa có nhiệm vụ tại bước này.');
      return;
    }
    if(action==='open-task'){
      const t=state.tasks.find(t=>t.status==='awaiting_review')||state.tasks[0];
      if(t)runAction(()=>selectTask(t.id));
      else if(state.flowNode&&$(`[data-node="${state.flowNode}"]`)?.dataset.termId){
        state.focus=$(`[data-node="${state.flowNode}"]`).dataset.termId;navigate('terminals');renderWindows();refreshWindows();
      }else if(state.sessions?.some(s=>s.kind==='agent'&&s.alive)){
        navigate('terminals');
      }else navigate('tasks');
    }
    const layout=target.closest('[data-console-layout]');if(layout){state.layout=layout.dataset.consoleLayout;state.focus=null;state.windowPage=1;renderWindows();refreshWindows();closeSettings();}
    const mode=target.closest('[data-console-mode]');if(mode){state.mode=mode.dataset.consoleMode;state.focus=null;renderWindows();refreshWindows();closeSettings();}
    const wp=target.closest('[data-window-page]');if(wp){state.windowPage=Number(wp.dataset.windowPage);renderWindows();refreshWindows();}
    const focus=target.closest('[data-focus]');if(focus){state.focus=state.focus?null:focus.dataset.focus;renderWindows();refreshWindows();}
    const historyButton=target.closest('[data-history]');if(historyButton){const card=historyButton.closest('[data-window]');card.classList.toggle('ao-expanded');historyButton.textContent=card.classList.contains('ao-expanded')?'Thu gọn log':'Xem log mở rộng';}
    const scopeToggle=target.closest('[data-scope-toggle]');if(scopeToggle){state.allChats=!state.allChats;runAction(refreshData);return;}
    const consoleAction=target.closest('[data-console-action]')?.dataset.consoleAction;
    if(consoleAction==='unfocus'){state.focus=null;renderWindows();refreshWindows();}
    if(consoleAction==='feed')runAction(refreshData);
    if(consoleAction==='newchat'){runAction(openChatModal);return;}
    const convResume=target.closest('[data-conv-resume]');
    if(convResume){resumeConversation(convResume.dataset.convResume);return;}
    const convView=target.closest('[data-conv-view]');
    if(convView){openTranscript(convView.dataset.convView);return;}
    if(consoleAction==='add'){closeSettings();const names={claude:'Claude',codex:'Codex',agy:'Antigravity (agy)'},agents=state.config?.terminal_agents||[];if(!agents.length){notify('Chưa cấu hình agent nào trong config.',true);return;}modal.querySelector('[data-add-agent]').innerHTML=agents.map(a=>`<option value="${a}">${names[a]||a}</option>`).join('');const repos=state.config?.repos||['default'];modal.querySelector('[data-add-repo]').innerHTML=repos.map(r=>`<option value="${esc(r)}">${r==='default'?'Repo chính':esc(r)}</option>`).join('');modal.querySelector('[data-add-repo-wrap]').hidden=repos.length<2;modal.showModal();}
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
  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!state.busy){refreshData().catch(()=>{});}});
  async function start(){try{configure(await api('/config'));await refreshData();}catch(error){$('.ao-demo').textContent='CHƯA KẾT NỐI';$('.ao-demo').classList.add('error');notify(error.message,true);}finally{setTimeout(tick,3000);}}
  async function tick(){if(!state.busy){try{if(!state.config)configure(await api('/config'));await refreshData();}catch(error){$('.ao-demo').textContent='MẤT KẾT NỐI';$('.ao-demo').classList.add('error');}}setTimeout(tick,document.hidden?4000:3000);}
  start();
})();
