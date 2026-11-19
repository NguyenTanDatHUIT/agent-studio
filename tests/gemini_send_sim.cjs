/**
 * gemini_send_sim.cjs – Mô phỏng DOM tối thiểu cho fillComposerAndSend
 * Chạy: node tests\gemini_send_sim.cjs   (từ thư mục repo)
 *
 * LƯU Ý: mô phỏng KHÔNG thay thế thử trên Gemini thật.
 * Chủ máy cần nạp lại extension và thử trực tiếp.
 */
'use strict';

const vm   = require('vm');
const fs   = require('fs');
const path = require('path');

// ─── Nạp source và inject export hook ────────────────────────────────────────
const SRC_PATH = path.join(__dirname, '..', 'browser_extension', 'content_gemini.js');
let srcTemplate = fs.readFileSync(SRC_PATH, 'utf8');

// Thêm dòng export ngay trước dấu } cuối của if-block.
srcTemplate = srcTemplate.replace(
  /(setInterval\(\(\) => \{[\s\S]*?\}, 15000\);)([\r\n\s]*\}[\r\n\s]*)$/,
  '$1\n  __aoExports__.fillComposerAndSend = fillComposerAndSend;\n$2'
);

// ─── Phần tử DOM giả đầy đủ ──────────────────────────────────────────────────
function makeBtn(ariaLabel, opts = {}) {
  /* Tạo button giả với querySelectorAll/querySelector để tương thích
     với findSendButton (duyệt scope.querySelectorAll('button')) */
  const btn = {
    tagName: 'BUTTON',
    className: opts.className || '',
    textContent: opts.textContent || '',
    disabled: !!opts.disabled,
    offsetParent: opts.hidden ? null : {},
    _clicked: 0,
    _attrs: {
      'aria-label':      ariaLabel || '',
      'aria-disabled':   opts.ariaDisabled ? 'true' : 'false',
      title:             opts.title || '',
      mattooltip:        opts.mattooltip || '',
    },
    getAttribute(n) { return this._attrs[n] ?? null; },
    setAttribute(n, v) { this._attrs[n] = v; },
    dispatchEvent() {},
    // querySelector cho mat-icon: trả null (không có biểu tượng trong test)
    querySelector() { return null; },
    querySelectorAll() { return []; },
    parentElement: null,
    _onClick: opts.onClick || null,
    click() {
      this._clicked++;
      if (this._onClick) this._onClick();
    },
  };
  return btn;
}

function makeComposer() {
  const el = {
    tagName: 'DIV',
    innerText: '',
    textContent: '',
    className: '',
    offsetParent: {},
    _attrs: { contenteditable: 'true', role: 'textbox' },
    getAttribute(n) { return this._attrs[n] ?? null; },
    setAttribute(n, v) { this._attrs[n] = v; },
    focus() {},
    dispatchEvent() {},
    // closest: trả null → findSendButton sẽ dùng parentElement
    closest() { return null; },
    // querySelectorAll('button') trên composer: trả rỗng (các nút ở cấp trên)
    querySelectorAll() { return []; },
    querySelector()    { return null; },
    // parentElement được set từ ngoài khi tổ hợp DOM
    parentElement: null,
  };
  return el;
}

function makeContainer(composer, ...btns) {
  /* Container (cha trực tiếp của composer) chứa các nút để findSendButton tìm được */
  const el = {
    tagName: 'DIV',
    className: 'ao-test-container',
    offsetParent: {},
    _attrs: {},
    getAttribute(n) { return this._attrs[n] ?? null; },
    querySelectorAll(sel) {
      if (sel === 'button') return btns;
      return [];
    },
    querySelector(sel) {
      if (sel === 'button') return btns[0] || null;
      return null;
    },
    parentElement: null,  // dừng leo cây ở đây
  };
  composer.parentElement = el;
  for (const b of btns) b.parentElement = el;
  return el;
}

// ─── Sandbox cho từng ca ──────────────────────────────────────────────────────
function makeSandbox(opts = {}) {
  /*
   * opts.sendButtonDelay  – ms trễ trước khi nút Send xuất hiện (rời khỏi hidden)
   * opts.stopUntil        – ms giữ stop indicator
   * opts.clearAfterClick  – ms sau click thì xóa ô chat; -1 = không bao giờ
   * opts.neverSend        – không bao giờ có nút gửi
   */
  const composer = makeComposer();

  // --- Nút gửi ---
  let sendBtnVisible = !opts.neverSend && !opts.sendButtonDelay;
  const sendBtn = makeBtn('Send message', {
    onClick: () => {
      if (opts.clearAfterClick === -1) return;
      const delay = (opts.clearAfterClick != null) ? opts.clearAfterClick : 100;
      setTimeout(() => { composer.innerText = ''; composer.textContent = ''; }, delay);
    },
  });
  // Ẩn/hiện nút gửi theo sendBtnVisible
  Object.defineProperty(sendBtn, 'offsetParent', {
    get: () => sendBtnVisible ? {} : null,
    configurable: true,
  });

  if (opts.sendButtonDelay) {
    setTimeout(() => { sendBtnVisible = true; }, opts.sendButtonDelay);
  }

  // --- Stop indicator ---
  let stopActive = !!opts.stopUntil;
  const stopBtn = makeBtn('Stop generating');
  Object.defineProperty(stopBtn, 'offsetParent', {
    get: () => stopActive ? {} : null,
    configurable: true,
  });

  if (opts.stopUntil) {
    setTimeout(() => {
      stopActive = false;
      if (!opts.neverSend) sendBtnVisible = true;
    }, opts.stopUntil);
  }

  // --- Container (cha của composer, chứa cả nút gửi và nút stop) ---
  const btnsInContainer = opts.neverSend ? [stopBtn] : [sendBtn, stopBtn];
  makeContainer(composer, ...btnsInContainer);

  // --- document giả ---
  const document = {
    // querySelector cho SELECTORS — dùng bởi queryFirst và queryAllResponses
    querySelector(sel) {
      // Ô soạn tin
      if (
        sel.includes('contenteditable') || sel.includes('textbox') ||
        sel.includes('ql-editor')       || sel.includes('rich-textarea') ||
        sel.includes('textarea')
      ) return composer;
      // Stop indicator
      if (sel.includes('Stop') || sel.includes('Dừng') || sel.includes('stop-icon'))
        return stopActive ? stopBtn : null;
      // Nút gửi fallback (SELECTORS.sendButton) — chỉ trả khi visible
      if (sel.includes('send-button') || (sel.includes('Send') && !sel.includes('Stop')) || sel.includes('Gửi'))
        return sendBtnVisible ? sendBtn : null;
      return null;
    },
    querySelectorAll(sel) {
      // Lượt tin model/user: rỗng (không test waitForModelReply ở đây)
      return [];
    },
    createRange() {
      return { selectNodeContents() {}, setStart() {}, setEnd() {} };
    },
    execCommand(cmd, _ui, val) {
      if (cmd === 'insertText') { composer.innerText = val; composer.textContent = val; }
    },
    body: {
      querySelectorAll() { return []; },
      querySelector()    { return null; },
    },
  };

  class FakeEvent    { constructor(t, o) { this.type = t; Object.assign(this, o || {}); } }
  class FakeIE       extends FakeEvent {}
  class FakeKE       extends FakeEvent { constructor(t, o) { super(t, o); this.key = o?.key; } }

  const aoExports = {};

  const sandbox = {
    window: {
      __aoGeminiBridgeLoaded: false,
      getSelection() { return { removeAllRanges() {}, addRange() {} }; },
    },
    document,
    __aoExports__: aoExports,
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
    Date,
    Promise,
    Array,
    Boolean,
    String,
    Set,
    console,
    Event:         FakeEvent,
    InputEvent:    FakeIE,
    KeyboardEvent: FakeKE,
    chrome: {
      runtime: {
        onMessage: { addListener() {} },
        sendMessage() {},
      },
    },
  };

  sandbox._sendBtn  = sendBtn;
  sandbox._stopBtn  = stopBtn;
  sandbox._composer = composer;

  return sandbox;
}

function loadFn(sandbox) {
  sandbox.window.__aoGeminiBridgeLoaded = false;
  vm.runInNewContext(srcTemplate, sandbox);
  return sandbox.__aoExports__.fillComposerAndSend;
}

// ─── HELPERS TEST ─────────────────────────────────────────────────────────────
let passed = 0, failed = 0;

async function test(name, fn) {
  try {
    await fn();
    console.log('  ✓', name);
    passed++;
  } catch (e) {
    console.error('  ✗', name);
    console.error('    ', e.message);
    failed++;
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error('Assertion: ' + msg);
}

// ─── CA KIỂM THỬ ─────────────────────────────────────────────────────────────
(async () => {
  console.log('\n=== gemini_send_sim.cjs – Mô phỏng DOM giả tối thiểu ===\n');
  console.log('LƯU Ý: mô phỏng KHÔNG thay thế thử trên Gemini thật.\n');

  // CA1: Nút gửi xuất hiện trễ 5 giây → vẫn gửi đúng 1 lần
  await test('CA1: Nút gửi xuất hiện trễ 5s → gửi đúng 1 lần', async () => {
    const sb = makeSandbox({ sendButtonDelay: 5000, clearAfterClick: 100 });
    const fn = loadFn(sb);
    await fn('test prompt CA1');
    assert(sb._sendBtn._clicked === 1, `Expected 1 click, got ${sb._sendBtn._clicked}`);
  });

  // CA2: Stop indicator còn 3 giây → chờ rảnh rồi gửi
  await test('CA2: Stop indicator còn 3s → chờ rồi gửi', async () => {
    const sb = makeSandbox({ stopUntil: 3000, clearAfterClick: 100 });
    const fn = loadFn(sb);
    await fn('test after stop CA2');
    assert(sb._sendBtn._clicked >= 1, `Expected ≥1 click, got ${sb._sendBtn._clicked}`);
  });

  // CA3: Không bao giờ có nút gửi → báo lỗi "Không tìm thấy nút gửi"
  await test('CA3: Không có nút gửi → báo lỗi đúng', async () => {
    const sb = makeSandbox({ neverSend: true });
    // Giả lập Enter bị bỏ qua: ô chat không tự xóa sau dispatchEvent
    const fn = loadFn(sb);
    let threw = false;
    try {
      await fn('test no button CA3');
    } catch (e) {
      threw = true;
      assert(
        /Không tìm thấy nút gửi/i.test(e.message),
        `Lỗi không khớp: ${e.message}`
      );
    }
    assert(threw, 'Phải throw lỗi khi không có nút gửi');
  });

  // CA4: Bấm xong ô chat vẫn đầy → thử lại 1 lần rồi báo lỗi; click ≥ 2
  await test('CA4: Bấm xong ô chat vẫn đầy → thử lại 1 lần rồi báo lỗi', async () => {
    const sb = makeSandbox({ clearAfterClick: -1 });
    const fn = loadFn(sb);
    let threw = false;
    try {
      await fn('test retry CA4');
    } catch (e) {
      threw = true;
      assert(
        /ô chat vẫn còn|Đã bấm/i.test(e.message),
        `Lỗi không khớp: ${e.message}`
      );
    }
    assert(threw, 'Phải throw lỗi sau thử lại');
    assert(
      sb._sendBtn._clicked >= 2,
      `Expected ≥2 clicks (thử lại), got ${sb._sendBtn._clicked}`
    );
  });

  // ─── Kết quả ─────────────────────────────────────────────────────────────
  console.log(`\nKết quả: ${passed} đạt / ${passed + failed} ca`);
  if (failed > 0) {
    console.error(`${failed} ca THẤT BẠI`);
    process.exit(1);
  } else {
    console.log('Tất cả ca mô phỏng đạt.');
    process.exit(0);
  }
})();
