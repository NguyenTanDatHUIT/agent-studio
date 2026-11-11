// Luồng giao diện "Quy tắc điều phối agent" trong DOM giả (NODE_PATH=<thư mục có jsdom> node tests/rules_ui.cjs):
// mở, sửa, kiểm giá trị, lưu, xem trước, khôi phục lịch sử, khôi phục mặc định, nhập tệp .md. Bố cục thật xem bằng tools/ui_shots.cjs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const assets = path.join(__dirname, '..', 'agent_orchestrator', 'web_assets');

const params = () => ({default_provider: 'agy', provider_models: {agy: {model: 'Gemini 4 Argon', effort: 'medium'}, claude: {model: '', effort: ''}, codex: {model: '', effort: ''}},
  max_fix_rounds: 2, max_agents_per_task: 2, max_concurrent_agents: 3, concurrency_enforced: true, single_builder: true, close_on_success: true,
  hang_minutes: 15, prompt_in_file: true, max_line_chars: 500, report_in_file: true, prompts_dir: '', subagent_policy: 'allowed', ram_free_warn_mb: 2000, roles_enabled: true});
const texts = () => ({rules: 'Quy tắc mặc định {MAX_FIX_ROUNDS}', constraints: 'Ràng buộc mặc định', checklist: 'Checklist mặc định'});
const sampleRoles = () => ([
  {slug: 'index', category: 'index', label: 'Bảng điều hướng (INDEX.md)', summary: 'Hướng dẫn nhanh', relpath: 'INDEX.md', path: 'C:/state/prompts/roles/INDEX.md', content: '# Bảng điều hướng'},
  {slug: 'minimal-change', category: 'coding', label: 'Sửa tối giản (Minimal Change)', summary: 'Diff nhỏ nhất', relpath: 'coding/minimal-change.md', path: 'C:/state/prompts/roles/coding/minimal-change.md', content: '# Vai trò: Sửa tối giản'}
]);

(async () => {
  const dom = new JSDOM(fs.readFileSync(path.join(assets, 'index.html'), 'utf8'), {url: 'http://127.0.0.1:8765/#token=t', runScripts: 'outside-only', pretendToBeVisual: true});
  const w = dom.window, errors = [], calls = [], notices = [];
  w.addEventListener('error', e => errors.push(e.error || e.message));
  w.ResizeObserver = class { observe() {} disconnect() {} };
  w.HTMLElement.prototype.scrollIntoView = () => {};
  w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  w.HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
  w.setTimeout = () => 1;
  w.requestAnimationFrame = fn => { fn(); return 1; };
  w.confirm = () => true;

  let state = {params: params(), texts: texts(), history: [{time: '2026-11-09T10:00:00+00:00'}], applied: 'old', digest: 'new'};
  const view = () => ({params: state.params, texts: state.texts, default: {params: params(), texts: texts()}, preview: 'XEM TRƯỚC ' + state.params.max_fix_rounds, unknown_variables: [],
    digest: state.digest, applied_digest: state.applied, agent0_running: true, text_limit: 15000, variables: ['REPO', 'ROLES_DIR', 'MAX_FIX_ROUNDS'],
    roles_dir: 'C:/state/prompts/roles', roles: sampleRoles(), history: state.history});
  w.fetch = async (url, opts = {}) => {
    const u = String(url).replace(/^.*\/api/, '');
    const body = opts.body ? JSON.parse(opts.body) : null;
    if (!u.startsWith('/orchestration-rules')) return {ok: true, json: async () => []};
    calls.push([opts.method || 'GET', u, body]);
    if (u === '/orchestration-rules' && body) {
      state = {...state, params: {...state.params, ...body.params}, texts: {...state.texts, ...body.texts}, history: [{time: '2026-11-09T11:00:00+00:00'}, ...state.history]};
    } else if (u.endsWith('/reset')) state = {...state, params: params(), texts: texts()};
    else if (u.endsWith('/restore')) state = {...state, params: {...params(), max_fix_rounds: 9}};
    else if (u.endsWith('/restart-agent0')) { state.applied = state.digest; return {ok: true, json: async () => ({restarted: true})}; }
    return {ok: true, json: async () => (u.endsWith('/preview') ? {preview: 'XEM TRƯỚC ' + body.params.max_fix_rounds, unknown_variables: ['BIEN_LA']} : view())};
  };
  w.eval(fs.readFileSync(path.join(assets, 'app.js'), 'utf8'));
  const tick = async () => { for (let i = 0; i < 6; i++) await new Promise(r => setImmediate(r)); };
  await tick();
  const d = w.document, dlg = () => d.querySelector('.ao-rules-dialog');
  const last = () => calls[calls.length - 1];
  const input = (sel, value) => { const el = dlg().querySelector(sel); el.value = value; el.dispatchEvent(new w.Event('input', {bubbles: true})); };
  const click = async sel => { dlg().querySelector(sel).click(); await tick(); };

  assert.equal(dlg().hasAttribute('open'), false, 'hộp thoại chưa mở thì chưa hiện');
  d.querySelector('[data-action="open-orch-rules"]').click();
  await tick();
  assert.equal(dlg().hasAttribute('open'), true, 'mở được từ nút trong Cài đặt');
  assert.equal(dlg().querySelector('[data-rp="max_fix_rounds"]').value, '2');
  assert.equal(dlg().querySelector('[data-rt="constraints"]').value, 'Ràng buộc mặc định');
  assert.match(dlg().textContent, /chưa nhận bản mới/, 'cảnh báo Agent 0 đang chạy chưa nhận bản mới');
  assert.match(dlg().textContent, /Mặc định: 2/, 'hiện giá trị mặc định');
  assert.equal(dlg().querySelector('[data-rt-count="constraints"]').textContent, '18/15000');
  assert.equal(dlg().querySelector('[data-rp="roles_enabled"]').checked, true);
  assert.match(dlg().querySelector('[data-role-inspect-body]').textContent, /Bảng điều hướng/);
  const roleSel = dlg().querySelector('[data-role-inspect]');
  roleSel.value = '1';
  roleSel.dispatchEvent(new w.Event('change', {bubbles: true}));
  assert.match(dlg().querySelector('[data-role-inspect-body]').textContent, /Sửa tối giản/);

  // Giá trị sai: không gửi lên, ô được đánh dấu lỗi.
  const before = calls.length;
  input('[data-rp="max_fix_rounds"]', '99');
  await click('[data-rules-save]');
  assert.equal(calls.length, before, 'giá trị ngoài miền không được gửi');
  assert.equal(dlg().querySelector('[data-rp="max_fix_rounds"]').getAttribute('aria-invalid'), 'true');

  // Sửa một tham số, một ô văn bản, một công tắc, một model rồi lưu.
  input('[data-rp="max_fix_rounds"]', '4');
  input('[data-rt="constraints"]', 'Chỉ sửa thư mục src.');
  assert.equal(dlg().querySelector('[data-rt-count="constraints"]').textContent, '20/15000');
  const box = dlg().querySelector('[data-rp="single_builder"]'); box.checked = false;
  input('[data-rp-model="claude"]', 'Opus');
  await click('[data-rules-save]');
  assert.deepEqual(last().slice(0, 2), ['POST', '/orchestration-rules']);
  assert.equal(last()[2].params.max_fix_rounds, 4);
  assert.equal(last()[2].params.single_builder, false);
  assert.deepEqual(last()[2].params.provider_models.claude, {model: 'Opus', effort: ''});
  assert.equal(last()[2].texts.constraints, 'Chỉ sửa thư mục src.');
  assert.equal(dlg().querySelector('[data-rp="max_fix_rounds"]').value, '4', 'hiện lại giá trị đã lưu');
  assert.equal(dlg().querySelectorAll('.ao-rules-history li').length, 2, 'lịch sử có thêm một bản');

  // Xem trước không ghi.
  await click('[data-rules-preview]');
  assert.equal(last()[1], '/orchestration-rules/preview');
  assert.equal(dlg().querySelector('[data-rules-preview-box]').hidden, false);
  assert.equal(dlg().querySelector('[data-rules-preview-text]').textContent, 'XEM TRƯỚC 4');

  // Khôi phục lịch sử và khôi phục mặc định.
  await click('[data-rules-restore="1"]');
  assert.deepEqual(last(), ['POST', '/orchestration-rules/restore', {index: 1}]);
  assert.equal(dlg().querySelector('[data-rp="max_fix_rounds"]').value, '9');
  await click('[data-rules-reset]');
  assert.equal(last()[1], '/orchestration-rules/reset');
  assert.equal(dlg().querySelector('[data-rp="max_fix_rounds"]').value, '2');
  assert.equal(dlg().querySelector('[data-rt="rules"]').value, 'Quy tắc mặc định {MAX_FIX_ROUNDS}');

  // Nhập .md: tệp hợp lệ điền vào ô (chưa lưu), tệp lạ bị từ chối và không đổi gì.
  const FENCE = '`'.repeat(3);
  const md = `# Quy tắc điều phối agent\n\n<!-- agent-studio-rules v1 -->\n\n## Tham số\n\n${FENCE}json\n{"max_fix_rounds": 6, "provider_models": {"codex": {"model": "gpt", "effort": "high"}}}\n${FENCE}\n\n## Quy tắc điều phối\n\nQuy tắc nhập vào\n\n## Ràng buộc chung\n\nRB nhập vào\n\n## Checklist nghiệm thu\n\nCL nhập vào\n`;
  const fileInput = () => dlg().querySelector('[data-rules-file]');
  const feed = async text => {
    Object.defineProperty(fileInput(), 'files', {configurable: true, value: [{size: text.length, text: async () => text}]});
    fileInput().dispatchEvent(new w.Event('change', {bubbles: true}));
    await tick();
  };
  const posts = calls.filter(c => c[0] === 'POST').length;
  await feed(md);
  assert.equal(dlg().querySelector('[data-rp="max_fix_rounds"]').value, '6');
  assert.equal(dlg().querySelector('[data-rt="rules"]').value, 'Quy tắc nhập vào');
  assert.equal(dlg().querySelector('[data-rp-model="codex"]').value, 'gpt');
  assert.equal(dlg().querySelector('[data-rp-effort="codex"]').value, 'high');
  assert.equal(calls.filter(c => c[0] === 'POST').length, posts, 'nhập tệp chưa ghi gì lên máy chủ');
  await feed('# không phải tệp của công cụ');
  assert.equal(dlg().querySelector('[data-rt="rules"]').value, 'Quy tắc nhập vào', 'tệp lạ không đổi nội dung');
  await feed(md.replace('## Checklist nghiệm thu', '## Mục khác'));
  assert.equal(dlg().querySelector('[data-rt="checklist"]').value, 'CL nhập vào', 'thiếu mục thì từ chối');

  // Không có kiểu gắn trực tiếp trên ô nhập (docs/UI-RULES.md).
  assert.equal(dlg().querySelectorAll('input[style],select[style],textarea[style]').length, 0);
  assert.equal(errors.length, 0, 'không có lỗi script: ' + errors.map(String).join('; '));
  w.close();
  console.log('PASS: rules dialog opens, validates, saves, previews, restores history/defaults, imports .md safely');
})().catch(e => { console.error(e); process.exit(1); });
