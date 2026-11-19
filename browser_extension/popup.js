const pairInput = document.getElementById('pair');
const enabledInput = document.getElementById('enabled');
const statusBox = document.getElementById('status');

async function refresh() {
  const cfg = await chrome.storage.local.get(['bridgeUrl', 'bridgeKey', 'enabled']);
  if (cfg.bridgeUrl && cfg.bridgeKey && !pairInput.value) {
    pairInput.value = `${cfg.bridgeUrl}|${cfg.bridgeKey}`;
  }
  enabledInput.checked = cfg.enabled !== false;
  chrome.runtime.sendMessage({ type: 'AO_GET_STATUS' }, (st) => {
    if (st && st.connected) {
      statusBox.className = 'status ok';
      statusBox.textContent = 'Đã kết nối Agent Studio. Tab: ' + (st.tabUrl || 'Sẵn sàng mở tự động');
    } else {
      statusBox.className = 'status warn';
      statusBox.textContent = 'Chưa kết nối: ' + ((st && st.error) || 'Kiểm tra Agent Studio đang chạy');
    }
  });
}

document.getElementById('save').addEventListener('click', () => {
  const raw = pairInput.value.trim();
  const parts = raw.split('|');
  if (parts.length !== 2 || !parts[0].startsWith('http://127.0.0.1:')) {
    statusBox.className = 'status warn';
    statusBox.textContent = 'Định dạng hợp lệ: http://127.0.0.1:<port>|<key>';
    return;
  }
  chrome.runtime.sendMessage({
    type: 'AO_SAVE_PAIRING',
    bridgeUrl: parts[0].trim(),
    bridgeKey: parts[1].trim(),
    enabled: enabledInput.checked
  }, () => {
    statusBox.textContent = 'Đã lưu! Đang kết nối...';
    setTimeout(refresh, 800);
  });
});

refresh();
