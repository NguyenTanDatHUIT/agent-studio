if (!window.__aoGeminiBridgeLoaded) {
  window.__aoGeminiBridgeLoaded = true;

  const SELECTORS = {
    composer: [
      'rich-textarea div[contenteditable="true"]',
      'div.ql-editor[contenteditable="true"]',
      'div[role="textbox"][contenteditable="true"]',
      'textarea'
    ],
    sendButton: [
      'button.send-button:not([disabled]):not([aria-disabled="true"])',
      'button[aria-label*="Send" i]:not([disabled]):not([aria-disabled="true"])',
      'button[aria-label*="Gửi" i]:not([disabled]):not([aria-disabled="true"])'
    ],
    stopIndicator: [
      'button[aria-label*="Stop" i]',
      'button[aria-label*="Dừng" i]',
      '.stop-icon'
    ],
    modelResponses: [
      'message-content.model-response-text',
      'model-response message-content',
      '[data-message-author-role="model"]',
      '.model-response-text'
    ]
  };

  function queryFirst(list) {
    for (const sel of list) {
      const el = document.querySelector(sel);
      if (el && el.offsetParent !== null) return el;
    }
    return null;
  }

  function queryAllResponses() {
    for (const sel of SELECTORS.modelResponses) {
      const nodes = Array.from(document.querySelectorAll(sel));
      if (nodes.length > 0) return nodes;
    }
    return [];
  }

  // Văn bản hiển thị (innerText của phần tử đang hiển thị, nên giữ đúng xuống dòng).
  function extractCleanModelText(rootEl) {
    if (!rootEl) return '';
    return (rootEl.innerText || rootEl.textContent || '').trim();
  }

  // Văn bản gốc của từng khối mã: textContent của <pre>/<code>, không bị ảnh hưởng bởi giao diện (nút Sao chép, nhãn ngôn ngữ).
  function extractCodeBlocks(rootEl) {
    if (!rootEl) return [];
    const out = [];
    rootEl.querySelectorAll('pre').forEach(pre => {
      const code = pre.querySelector('code') || pre;
      const txt = (code.textContent || '').trim();
      if (txt) out.push(txt);
    });
    return out;
  }

  // Lấy aria-label của các nút hiển thị trên trang (để chẩn đoán khi không tìm được nút gửi).
  function getNearbyButtonLabels(composer) {
    try {
      // Thử tìm trong container gần nhất trước, nếu rỗng thì quét toàn trang.
      const containers = [];
      if (composer) {
        const f = composer.closest('form');
        const c = composer.closest('[class*="input"]') || composer.closest('[class*="toolbar"]') || composer.closest('[class*="bottom"]');
        if (f) containers.push(f);
        if (c && c !== f) containers.push(c);
        if (composer.parentElement) containers.push(composer.parentElement);
      }
      containers.push(document.body || document.documentElement);
      for (const root of containers) {
        const btns = Array.from(root.querySelectorAll('button'))
          .filter(b => b.offsetParent !== null);
        if (btns.length > 0) {
          return btns
            .map(b => b.getAttribute('aria-label') || b.getAttribute('title') || b.textContent.trim().slice(0, 30) || '(no label)')
            .filter(Boolean)
            .slice(0, 15);
        }
      }
      return [];
    } catch (_) { return []; }
  }

  // Trả về số lượt tin của người dùng hiện tại trên trang.
  function countUserTurns() {
    try {
      const nodes = document.querySelectorAll('[data-message-author-role="user"], user-query, .user-query');
      return nodes.length;
    } catch (_) { return 0; }
  }

  // Chờ Gemini rảnh (không còn stop indicator), tối đa waitMs.
  async function waitForIdle(waitMs = 15000) {
    const start = Date.now();
    while (Date.now() - start < waitMs) {
      if (!queryFirst(SELECTORS.stopIndicator)) return true;
      await new Promise(r => setTimeout(r, 300));
    }
    return false;
  }

  // Nhãn của một nút: aria-label, title, tooltip, và tên biểu tượng mat-icon bên trong.
  function buttonLabel(btn) {
    const parts = [btn.getAttribute('aria-label'), btn.getAttribute('title'), btn.getAttribute('mattooltip')];
    const icon = btn.querySelector('mat-icon');
    if (icon) parts.push(icon.getAttribute('fonticon'), icon.getAttribute('data-mat-icon-name'));
    return parts.filter(Boolean).join(' ').trim();
  }

  const SEND_LABEL_RE = /send|gửi/i;
  const SEND_EXCLUDE_RE = /stop|dừng|mic|voice|giọng|upload|tải|attach|đính|add|thêm|tool|công cụ|menu|copy|sao chép/i;

  // Nút chỉ được coi là "gửi" khi có lớp send-button hoặc nhãn có chữ gửi/send; luôn loại nút dừng, micro, tải lên, thêm, công cụ...
  function isSendCandidate(btn) {
    const cls = String(btn.className || '');
    const label = buttonLabel(btn);
    if (/stop/i.test(cls) || SEND_EXCLUDE_RE.test(label)) return false;
    return /send-button/.test(cls) || SEND_LABEL_RE.test(label);
  }

  // Tìm nút gửi quanh ô soạn tin (đi dần lên các phần tử cha, tối đa 8 cấp);
  // không có thì tìm theo SELECTORS.sendButton; vẫn không có thì quét toàn document.
  // Trả {btn: nút còn bật | null, locked: có nút gửi nhưng đang bị khóa}.
  function findSendButton(composer) {
    const seen = new Set();
    const found = [];

    // Vòng 1: leo lên tối đa 8 cấp cha từ ô soạn tin.
    let scope = composer;
    for (let level = 0; level < 8 && scope && scope.querySelectorAll; level++, scope = scope.parentElement) {
      for (const b of scope.querySelectorAll('button')) {
        if (seen.has(b)) continue;
        seen.add(b);
        if (b.offsetParent !== null && isSendCandidate(b)) found.push(b);
      }
      if (found.length) break;
    }

    // Vòng 2: thử SELECTORS cổ điển.
    if (!found.length) {
      const b = queryFirst(SELECTORS.sendButton);
      if (b && !seen.has(b) && isSendCandidate(b)) found.push(b);
    }

    // Vòng 3 (fallback toàn trang): quét document khi cả hai vòng trên thất bại.
    // Chỉ dùng khi thực sự cần; ghi log để chẩn đoán.
    if (!found.length) {
      try {
        for (const b of document.querySelectorAll('button')) {
          if (seen.has(b) || b.offsetParent === null) continue;
          if (isSendCandidate(b)) found.push(b);
        }
        if (found.length) {
          console.warn('[AO Gemini] findSendButton: dùng fallback toàn trang, tìm thấy', found.length, 'nút:', found.map(b => buttonLabel(b) || '(no label)'));
        }
      } catch (_) {}
    }

    const enabled = found.find(b => !b.disabled && b.getAttribute('aria-disabled') !== 'true');
    return { btn: enabled || null, locked: !enabled && found.length > 0 };
  }

  // Trạng thái của lần tìm nút gửi gần nhất: có thấy nút gửi nhưng bị khóa không (để báo lỗi đúng nhánh).
  const sendState = { locked: false };

  // Tìm nút gửi (còn bật, không phải nút Stop), tối đa waitMs.
  async function waitForSendButton(waitMs = 12000, composer = null) {
    const start = Date.now();
    sendState.locked = false;
    for (;;) {
      const r = composer ? findSendButton(composer) : { btn: queryFirst(SELECTORS.sendButton), locked: false };
      if (r.locked) sendState.locked = true;
      if (r.btn) return r.btn;
      if (Date.now() - start >= waitMs) return null;
      await new Promise(r2 => setTimeout(r2, 200));
    }
  }

  async function fillComposerAndSend(promptText) {
    // --- Bước 0: Tìm ô soạn tin ---
    let composer = null;
    for (let i = 0; i < 25; i++) {
      composer = queryFirst(SELECTORS.composer);
      if (composer) break;
      await new Promise(r => setTimeout(r, 300));
    }
    if (!composer) {
      throw new Error('Không tìm thấy ô nhập chat trên trang Gemini (hãy kiểm tra đã đăng nhập chưa).');
    }

    // --- Bước 1: Chờ Gemini rảnh trước khi gửi ---
    const idle = await waitForIdle(15000);
    if (!idle) {
      throw new Error('Gemini đang trả lời — vui lòng chờ Gemini xong rồi thử lại.');
    }

    // --- Bước 2: Điền chữ vào ô soạn tin ---
    composer.focus();
    if (composer.tagName === 'TEXTAREA') {
      composer.value = promptText;
      composer.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      const sel = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(composer);
      sel.removeAllRanges();
      sel.addRange(range);
      document.execCommand('insertText', false, promptText);
      if ((composer.innerText || '').trim().length === 0) {
        composer.textContent = promptText;
      }
      composer.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: promptText }));
    }

    // Cho React/Angular cập nhật trạng thái nút gửi.
    await new Promise(r => setTimeout(r, 350));

    // --- Bước 3: Tìm nút gửi (tối đa 12 giây) ---
    const sendBtn = await waitForSendButton(12000, composer);
    const lockedFirst = sendState.locked;

    // --- Bước 4: Ghi nhận trạng thái trước khi bấm ---
    const userTurnsBefore = countUserTurns();
    const repliesBefore = queryAllResponses().length;

    // Thấy nút gửi nhưng bị khóa suốt 12 giây: Enter cũng sẽ bị từ chối, báo ngay (không phát Enter).
    if (!sendBtn && lockedFirst) {
      throw new Error(
        'Nút gửi của Gemini đang bị khóa (disabled) sau 12 giây, chưa gửi. ' +
        'Có thể nội dung quá dài hoặc trang đang bận; hãy kiểm tra tab Gemini.'
      );
    }

    // --- Bước 5: Bấm hoặc dùng Enter dự phòng ---
    if (sendBtn) {
      sendBtn.click();
    } else {
      // Nhánh Enter dự phòng: phát đủ keydown/keypress/keyup. Có thể bị Gemini bỏ qua.
      const kOpts = { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true };
      composer.dispatchEvent(new KeyboardEvent('keydown', kOpts));
      composer.dispatchEvent(new KeyboardEvent('keypress', kOpts));
      composer.dispatchEvent(new KeyboardEvent('keyup', kOpts));
      // Ghi vào console để chẩn đoán.
      console.warn('[AO Gemini] Không tìm thấy nút gửi sau 12 giây — đã phát Enter giả (có thể bị bỏ qua). Nhãn nút gần ô chat:', getNearbyButtonLabels(composer));
    }

    // --- Bước 6: Kiểm tra ô chat có được làm trống / Gemini bắt đầu trả lời ---
    const getComposerText = () =>
      (composer.tagName === 'TEXTAREA' ? composer.value : composer.innerText || '').trim();

    const sentAt = Date.now();
    while (Date.now() - sentAt < 6000) {
      await new Promise(r => setTimeout(r, 300));
      if (getComposerText().length === 0 || queryFirst(SELECTORS.stopIndicator)) return;
    }

    // --- Bước 7: Thử lại một lần nếu ô chat vẫn còn chữ ---
    // Chỉ thử lại khi Gemini chưa bắt đầu trả lời VÀ số lượt tin chưa tăng.
    const userTurnsAfter = countUserTurns();
    const stillGenerating = Boolean(queryFirst(SELECTORS.stopIndicator));
    if (!stillGenerating && userTurnsAfter <= userTurnsBefore && queryAllResponses().length <= repliesBefore && getComposerText().length > 0) {
      // Thử lại: tìm nút gửi và bấm thêm một lần.
      const retryBtn = await waitForSendButton(5000, composer);
      if (retryBtn) {
        retryBtn.click();
      } else {
        const kOpts = { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true };
        composer.dispatchEvent(new KeyboardEvent('keydown', kOpts));
        composer.dispatchEvent(new KeyboardEvent('keypress', kOpts));
        composer.dispatchEvent(new KeyboardEvent('keyup', kOpts));
        console.warn('[AO Gemini] Thử lại: vẫn không tìm thấy nút gửi — phát Enter giả lần 2.');
      }
      // Chờ thêm 4 giây sau thử lại.
      const retryAt = Date.now();
      while (Date.now() - retryAt < 4000) {
        await new Promise(r => setTimeout(r, 300));
        if (getComposerText().length === 0 || queryFirst(SELECTORS.stopIndicator)) return;
      }
    }

    // --- Bước 8: Báo lỗi chi tiết ---
    const composerTextNow = getComposerText();
    const nowGenerating = Boolean(queryFirst(SELECTORS.stopIndicator));
    if (nowGenerating || countUserTurns() > userTurnsBefore || queryAllResponses().length > repliesBefore) {
      // Gemini đã nhận (ô chat chưa trống nhưng đang xử lý) — coi là thành công.
      return;
    }
    if (!sendBtn) {
      const labels = getNearbyButtonLabels(composer);
      throw new Error(
        'Không tìm thấy nút gửi sau 12 giây — không gửi được lệnh. ' +
        'Nhãn các nút gần ô chat: [' + labels.join(', ') + ']. ' +
        'Hãy kiểm tra xem trang Gemini có thay đổi giao diện không.'
      );
    }
    if (composerTextNow.length > 0) {
      throw new Error(
        'Đã bấm nút gửi (và thử lại một lần) nhưng ô chat vẫn còn nội dung — ' +
        'Gemini có thể đang bận hoặc nút gửi bị khoá ngay sau khi bấm. ' +
        'Hãy kiểm tra tab Gemini và thử lại.'
      );
    }
    // Trường hợp hiếm: ô chat đã trống nhưng không có stop indicator trong 10 giây — coi là thành công.
  }

  async function waitForModelReply(prevCount, prevLastText, timeoutMs = 240000) {
    const start = Date.now();
    let stableSince = 0;
    let lastObserved = '';

    while (Date.now() - start < timeoutMs) {
      await new Promise(r => setTimeout(r, 350));
      const nodes = queryAllResponses();
      const currentLast = nodes.length > 0 ? extractCleanModelText(nodes[nodes.length - 1]) : '';
      const hasNewOutput = nodes.length > prevCount || (currentLast && currentLast !== prevLastText);
      const isGenerating = Boolean(queryFirst(SELECTORS.stopIndicator));

      if (!hasNewOutput) continue;

      if (currentLast !== lastObserved || isGenerating || currentLast.length === 0) {
        lastObserved = currentLast;
        stableSince = Date.now();
        continue;
      }

      if (Date.now() - stableSince >= 1200) {
        return currentLast;
      }
    }
    throw new Error('Quá thời gian chờ phản hồi từ trang Gemini.');
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || msg.type !== 'AO_RUN_PROMPT') return false;
    (async () => {
      try {
        const beforeNodes = queryAllResponses();
        const prevCount = beforeNodes.length;
        const prevLastText = prevCount > 0 ? extractCleanModelText(beforeNodes[prevCount - 1]) : '';
        await fillComposerAndSend(msg.prompt);
        const reply = await waitForModelReply(prevCount, prevLastText);
        const nodes = queryAllResponses();
        const last = nodes.length > 0 ? nodes[nodes.length - 1] : null;
        const blocks = extractCodeBlocks(last);
        // Chỉ giữ HTML thô khi câu trả lời có vẻ chứa lệnh công cụ, để chẩn đoán khi trích sai.
        const debugHtml = last && /AO_TOOL|"action"/.test(reply) ? last.innerHTML.slice(0, 8000) : '';
        sendResponse({ ok: true, text: reply, blocks, debug_html: debugHtml });
      } catch (err) {
        sendResponse({ ok: false, error: String(err.message || err) });
      }
    })();
    return true;
  });

  setInterval(() => {
    try { chrome.runtime.sendMessage({ type: 'GEMINI_TAB_HEARTBEAT' }); } catch (_) {}
  }, 15000);
}
