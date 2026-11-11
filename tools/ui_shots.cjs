// Chụp giao diện thật (Chromium) ở hai cỡ rộng/hẹp để nhìn bằng mắt; jsdom không dàn trang nên không thay thế được.
//   set PLAYWRIGHT_DIR=<thư mục node_modules có playwright>   (hoặc đặt NODE_PATH tới đó)
//   set CHROME_PATH=<đường dẫn chrome.exe>                    (bỏ trống nếu Playwright đã tải trình duyệt)
//   node tools/ui_shots.cjs <thư-mục-ra>
// API được giả lập bằng dữ liệu có đúng tên trường mà backend trả (xem docs/UI-RULES.md, mục 2). Không cần chạy server.
const fs = require('fs'), path = require('path');
const out = process.argv[2];
if (!out) { console.error('Usage: node tools/ui_shots.cjs <out-dir>'); process.exit(2); }
fs.mkdirSync(out, { recursive: true });
const { chromium } = require(process.env.PLAYWRIGHT_DIR ? path.join(process.env.PLAYWRIGHT_DIR, 'playwright') : 'playwright');
const assets = path.join(__dirname, '..', 'agent_orchestrator', 'web_assets');
const ORIGIN = 'http://127.0.0.1:8765';
const at = (day, h, m) => `2026-11-${String(day).padStart(2, '0')}T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00+00:00`;
const today = new Date(), d0 = `2026-11-${String(Math.min(today.getUTCDate(), 28)).padStart(2, '0')}`;
const convs = [
  { id: 'c1', terminal_key: 'agy-3', provider: 'agy', agent_n: 3, kind: 'agent', cwd: 'C:\\CongViec\\agent\\agent-orchestrator-selftest', task_id: null, session_id: 's1', title: 'Giải phương trình bậc 2 x^2 - 5x + 6 = 0: tính delta, hai nghiệm, và kiểm tra lại bằng cách thay vào', started: d0 + 'T01:31:00+00:00', last_active: d0 + 'T01:40:00+00:00', status: 'active', live: true },
  { id: 'c2', terminal_key: 'agent0', provider: 'claude', agent_n: null, kind: 'agent0', cwd: 'C:\\CongViec\\agent\\agent-orchestrator-selftest', task_id: null, session_id: 's2', title: 'giao cho agy một task bất kỳ', started: d0 + 'T00:05:00+00:00', last_active: d0 + 'T00:40:00+00:00', status: 'closed', live: false },
  { id: 'c3', terminal_key: 'codex-1', provider: 'codex', agent_n: 1, kind: 'agent', cwd: 'C:\\x', task_id: 'a'.repeat(24), session_id: 's3', title: null, started: at(1, 22, 10), last_active: at(1, 22, 20), status: 'failed', live: false },
];
const api = {
  '/api/config': { repo: 'C:/fixture', base_ref: 'HEAD', providers: { claude: true, codex: true }, tests: ['unit', 'functional'], execution_enabled: true,
    roles: [{ slug: 'minimal-change', category: 'coding', label: 'Sửa tối giản (Minimal Change)', summary: 'Diff nhỏ nhất' }, { slug: 'backend-architect', category: 'coding', label: 'Kiến trúc & Dịch vụ Backend', summary: 'API & Service' }] },
  '/api/tasks': [], '/api/activity': [], '/api/runners': { managed: false, providers: {} }, '/api/agent0': { connected: false },
  '/api/terminals': [], '/api/agents': [], '/api/settings': { default_remember: true }, '/api/workflows': [], '/api/conversations': convs,
  '/api/chat': { windows: 3, tasks: 0, workflows: 0, can_start: true, reason: null, agent0: true },
};
const rulesParams = { default_provider: 'agy', provider_models: { agy: { model: 'Gemini 4 Argon', effort: 'medium' }, claude: { model: '', effort: '' }, codex: { model: '', effort: '' } },
  max_fix_rounds: 2, max_agents_per_task: 2, max_concurrent_agents: 3, concurrency_enforced: true, single_builder: true, close_on_success: true,
  hang_minutes: 15, prompt_in_file: true, max_line_chars: 500, report_in_file: true, prompts_dir: '', subagent_policy: 'allowed', ram_free_warn_mb: 2000, roles_enabled: true };
const rulesTexts = { rules: '**1. Vai trò.** Bạn chỉ điều phối và nghiệm thu bằng bằng chứng thật. **4. Vòng lặp nghiệm thu.** Sau {MAX_FIX_ROUNDS} lần sửa vẫn chưa đạt thì thay cửa sổ.', constraints: '- Không push, không merge nếu chủ máy chưa yêu cầu.', checklist: '- Đọc git status và git diff của thay đổi thật.' };
api['/api/orchestration-rules'] = { params: rulesParams, texts: rulesTexts, default: { params: rulesParams, texts: rulesTexts }, preview: 'Xem trước nội dung đã thay biến.', unknown_variables: [],
  digest: 'a', applied_digest: 'b', agent0_running: true, text_limit: 15000, variables: ['REPO', 'PROMPTS_DIR', 'ROLES_DIR', 'PROVIDER', 'PROVIDER_MODEL', 'MAX_FIX_ROUNDS', 'MAX_AGENTS_PER_TASK', 'MAX_CONCURRENT', 'MAX_LINE', 'HANG_MINUTES', 'SUBAGENT_POLICY'],
  roles_dir: 'C:\\Users\\owner\\AppData\\Local\\agent-orchestrator\\prompts\\roles',
  roles: [{ slug: 'index', category: 'index', label: 'Bảng điều hướng', summary: 'Hướng dẫn chọn vai trò và mẫu theo tình huống.', relpath: 'INDEX.md', path: 'C:\\Users\\owner\\AppData\\Local\\agent-orchestrator\\prompts\\roles\\INDEX.md', content: '# Thư viện vai trò & mẫu chuẩn\n- coding/minimal-change.md\n- review/reality-checker.md' }],
  history: [{ time: '2026-11-09T10:15:00+00:00' }, { time: '2026-11-08T21:02:00+00:00' }] };
api['/api/orchestration-rules/preview'] = api['/api/orchestration-rules'];
const types = { '.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html' };

(async () => {
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  let bad = 0;
  for (const [name, w, h] of [['wide', 1280, 820], ['narrow', 460, 820]]) {
    for (const scheme of ['dark', 'light']) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme });
      const page = await ctx.newPage();
      page.on('pageerror', e => { bad++; console.log('PAGEERROR', e.message); });
      await page.route(ORIGIN + '/**', route => {
        const u = new URL(route.request().url());
        if (u.pathname.startsWith('/api/')) return route.fulfill({ json: api[u.pathname] ?? { lines: [], total: 0, next: 0, has_more: false } });
        const file = path.join(assets, u.pathname === '/' ? 'index.html' : u.pathname.slice(1));
        if (!fs.existsSync(file)) return route.fulfill({ status: 404, body: '' });
        return route.fulfill({ body: fs.readFileSync(file), contentType: types[path.extname(file)] || 'application/octet-stream' });
      });
      await page.goto(ORIGIN + '/#token=x');
      await page.waitForTimeout(1200);
      await page.locator('[data-page="terminals"]').first().click();
      await page.waitForTimeout(300);
      const tag = `${name}-${scheme}`;
      // Một hộp thoại chưa mở phải ẩn hẳn (từng có lỗi: hộp thoại transcript đóng vẫn hiện ở cuối trang).
      const shownClosed = await page.evaluate(() => [...document.querySelectorAll('dialog:not([open])')].filter(d => getComputedStyle(d).display !== 'none').map(d => d.className));
      if (shownClosed.length) { bad++; console.log(`CLOSED-DIALOG-VISIBLE ${tag}:`, shownClosed); }
      // Thanh công cụ CMD: nút "Cuộc trò chuyện mới" nằm ngay trên thanh (không nằm trong menu cài đặt) và nhìn thấy được.
      const barBtn = page.locator('.ao-console-bar-actions [data-console-action="newchat"]');
      const barState = await barBtn.evaluate(el => { const r = el.getBoundingClientRect(); return { visible: r.width > 0 && r.height > 0, inside: r.left >= 0 && r.right <= innerWidth }; }).catch(() => null);
      if (!barState || !barState.visible || !barState.inside) { bad++; console.log(`NEWCHAT-BUTTON ${tag}: not visible in the console bar`, JSON.stringify(barState)); }
      else console.log(`ok ${tag}: new-chat button is on the console bar`);
      await page.screenshot({ path: path.join(out, `${tag}-bar.png`), clip: { x: 0, y: 0, width: w, height: 330 } });
      const gear = page.locator('[data-console-settings-toggle]').first();
      if (await gear.count() && await gear.isVisible()) {
        await gear.click(); await page.waitForTimeout(250);
        await page.screenshot({ path: path.join(out, `${tag}-settings.png`) });
        const listed = await page.locator('.ao-console-settings-panel').innerText();
        if (/Lịch sử/.test(listed) || /Cuộc trò chuyện mới/.test(listed)) { bad++; console.log(`SETTINGS-MENU ${tag}: still lists history or new chat`); }
        await gear.click();
      }
      // Lịch sử là mục menu bên trái.
      await page.locator('.ao-nav [data-page="history"]').click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(out, `${tag}-history.png`) });
      const m = await page.evaluate(() => { const l = document.querySelector('[data-history-list]'); return { sw: l.scrollWidth, cw: l.clientWidth }; });
      if (m.sw > m.cw) { bad++; console.log(`OVERFLOW ${tag}: scrollWidth ${m.sw} > clientWidth ${m.cw}`); }
      else console.log(`ok ${tag}: no horizontal overflow (${m.sw}/${m.cw})`);
      // Danh sách thả xuống phải là menu theo template (không phải menu gốc của hệ điều hành), nằm trọn trong cửa sổ.
      await page.locator('[data-history-provider]').click();
      await page.waitForTimeout(200);
      await page.screenshot({ path: path.join(out, `${tag}-select-open.png`) });
      const menu = await page.evaluate(() => {
        const m = document.querySelector('[data-select-menu]');
        if (!m) return null;
        const r = m.getBoundingClientRect();
        return { options: m.querySelectorAll('[role=option]').length, inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight, w: Math.round(r.width) };
      });
      if (!menu || menu.options < 5 || !menu.inside) { bad++; console.log(`SELECT-MENU ${tag}:`, JSON.stringify(menu)); }
      else console.log(`ok ${tag}: custom select menu, ${menu.options} options, inside viewport`);
      await page.keyboard.press('Escape');
      // Hộp thoại xem lại transcript: hiện khi mở (nằm trong màn hình), ẩn hẳn khi đóng.
      await page.locator('[data-conv-view]').first().click();
      await page.waitForTimeout(300);
      const tr = await page.evaluate(() => { const d = document.querySelector('.ao-transcript-dialog'); const r = d.getBoundingClientRect(); return { open: d.open, display: getComputedStyle(d).display, inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight }; });
      await page.screenshot({ path: path.join(out, `${tag}-transcript.png`) });
      await page.locator('[data-transcript-close]').click();
      await page.waitForTimeout(200);
      const trClosed = await page.evaluate(() => getComputedStyle(document.querySelector('.ao-transcript-dialog')).display);
      if (!tr.open || tr.display === 'none' || !tr.inside || trClosed !== 'none') { bad++; console.log(`TRANSCRIPT-DIALOG ${tag}:`, JSON.stringify({ ...tr, trClosed })); }
      else console.log(`ok ${tag}: transcript dialog shows when opened and is hidden when closed`);
      await page.locator('.ao-nav [data-page="terminals"]').click();
      await page.waitForTimeout(250);
      await page.locator('.ao-console-bar-actions [data-console-action="newchat"]').click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(out, `${tag}-newchat.png`) });
      const dlg = await page.evaluate(() => {
        const d = document.querySelector('.ao-chat-dialog[open]');
        if (!d) return null;
        const r = d.getBoundingClientRect();
        return { inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight, hasConfirm: !!d.querySelector('[data-chat-confirm]:not([disabled])') };
      });
      if (!dlg || !dlg.inside || !dlg.hasConfirm) { bad++; console.log(`NEWCHAT-DIALOG ${tag}:`, JSON.stringify(dlg)); }
      else console.log(`ok ${tag}: new-chat dialog inside viewport with an enabled confirm`);
      await page.keyboard.press('Escape');
      await page.locator('[data-page="tasks"]').first().click();
      await page.waitForTimeout(250);
      await page.locator('[data-action="new-task"]:visible').first().click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(out, `${tag}-form.png`) });
      const native = await page.evaluate(() => [...document.querySelectorAll('#ao-studio input:not([type=checkbox]):not([type=radio]), #ao-studio select, #ao-studio textarea')]
        .filter(el => !el.matches('.ao-command-input') && getComputedStyle(el).appearance !== 'none').map(el => el.outerHTML.slice(0, 80)));
      if (native.length) { bad++; console.log(`NATIVE-LOOK ${tag}:`, native); }
      // Quy tắc điều phối agent: hộp thoại mở được từ menu cài đặt, nằm trong màn hình, không tràn ngang, ô nhập theo template.
      await page.locator('.ao-nav [data-page="terminals"]').click();
      await page.waitForTimeout(250);
      const gear2 = page.locator('[data-console-settings-toggle]').first();
      if (await gear2.count() && await gear2.isVisible()) {
        await gear2.click(); await page.waitForTimeout(200);
        await page.locator('[data-action="open-orch-rules"]').first().click();
        await page.waitForTimeout(500);
        const rules = await page.evaluate(() => {
          const d = document.querySelector('.ao-rules-dialog[open]');
          if (!d) return null;
          const r = d.getBoundingClientRect();
          const controls = [...d.querySelectorAll('input:not([type=checkbox]):not([type=file]), select, textarea')];
          return { inside: r.left >= 0 && r.right <= innerWidth && r.top >= 0, hscroll: d.scrollWidth > d.clientWidth, controls: controls.length,
            native: controls.filter(el => getComputedStyle(el).appearance !== 'none').length, styled: controls.filter(el => el.getAttribute('style')).length,
            restart: !!d.querySelector('[data-rules-restart]'), fields: d.querySelectorAll('[data-rp]').length, texts: d.querySelectorAll('[data-rt]').length };
        });
        await page.screenshot({ path: path.join(out, `${tag}-rules.png`) });
        if (!rules || !rules.inside || rules.hscroll || rules.native || rules.styled || !rules.restart || rules.fields < 12 || rules.texts !== 3) { bad++; console.log(`RULES-DIALOG ${tag}:`, JSON.stringify(rules)); }
        else console.log(`ok ${tag}: rules dialog inside viewport, no horizontal scroll, ${rules.controls} form controls follow the template`);
        await page.locator('.ao-rules-dialog [data-rules-preview]').scrollIntoViewIfNeeded();
        await page.locator('.ao-rules-dialog [data-rules-preview]').click(); await page.waitForTimeout(300);
        await page.screenshot({ path: path.join(out, `${tag}-rules-bottom.png`) });
        await page.locator('.ao-rules-dialog [data-rules-close]').click();
      }
      await ctx.close();
    }
  }
  await browser.close();
  console.log(bad ? `FAIL: ${bad} problem(s)` : `OK: screenshots in ${out}`);
  process.exit(bad ? 1 : 0);
})();
