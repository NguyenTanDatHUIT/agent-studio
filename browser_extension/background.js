const CLIENT_ID = 'ext-' + Math.random().toString(36).slice(2, 10);
let polling = false;
let lastStatus = { connected: false, error: 'Chưa cấu hình khóa ghép đôi' };

chrome.alarms.create('ao-bridge-keepalive', { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener(() => { ensurePollLoop(); });
chrome.runtime.onStartup.addListener(() => { ensurePollLoop(); });
chrome.runtime.onInstalled.addListener(() => { ensurePollLoop(); });

async function getConfig() {
  const data = await chrome.storage.local.get(['bridgeUrl', 'bridgeKey', 'enabled']);
  return {
    bridgeUrl: (data.bridgeUrl || '').replace(/\/+$/, ''),
    bridgeKey: data.bridgeKey || '',
    enabled: data.enabled !== false
  };
}

async function findOrOpenGeminiTab(targetConv, newChat) {
  const tabs = await chrome.tabs.query({ url: 'https://gemini.google.com/*' });
  let tab = tabs[0] || null;
  const desiredUrl = targetConv
    ? `https://gemini.google.com/app/${encodeURIComponent(targetConv)}`
    : 'https://gemini.google.com/app';

  if (!tab) {
    tab = await chrome.tabs.create({ url: desiredUrl, active: true });
    await waitForTabComplete(tab.id);
    return tab;
  }

  if (targetConv && (!tab.url || !tab.url.includes(`/app/${targetConv}`))) {
    await chrome.tabs.update(tab.id, { url: desiredUrl });
    await waitForTabComplete(tab.id);
  } else if (newChat && tab.url && /\/app\/[A-Za-z0-9_-]+/.test(tab.url)) {
    await chrome.tabs.update(tab.id, { url: 'https://gemini.google.com/app' });
    await waitForTabComplete(tab.id);
  }
  return await chrome.tabs.get(tab.id);
}

function waitForTabComplete(tabId, timeoutMs = 20000) {
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      resolve();
    }, timeoutMs);
    function listener(updatedId, info) {
      if (updatedId === tabId && info.status === 'complete') {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        setTimeout(resolve, 900);
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });
}

async function callBridge(cfg, path, method = 'GET', body = null) {
  const res = await fetch(`${cfg.bridgeUrl}/api/gemini-bridge${path}`, {
    method,
    headers: {
      'X-Gemini-Bridge-Key': cfg.bridgeKey,
      ...(body ? { 'Content-Type': 'application/json' } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return await res.json();
}

async function ensurePollLoop() {
  if (polling) return;
  polling = true;
  try {
    while (true) {
      const cfg = await getConfig();
      if (!cfg.enabled || !cfg.bridgeUrl || !cfg.bridgeKey) {
        lastStatus = { connected: false, error: 'Chưa cấu hình hoặc đang tạm dừng' };
        break;
      }
      const tabs = await chrome.tabs.query({ url: 'https://gemini.google.com/*' });
      const activeTab = tabs[0] || null;

      try {
        const job = await callBridge(
          cfg,
          `/poll?client_id=${encodeURIComponent(CLIENT_ID)}&tab_id=${activeTab ? activeTab.id : 'none'}&url=${encodeURIComponent(activeTab ? activeTab.url || '' : '')}&wait=${lastStatus.connected ? 8 : 0}`
        );
        lastStatus = { connected: true, error: null, tabUrl: activeTab ? activeTab.url : null };

        if (job && job.prompt_id) {
          const targetTab = await findOrOpenGeminiTab(job.target_conv, job.new_chat);
          let response;
          try {
            response = await chrome.tabs.sendMessage(targetTab.id, {
              type: 'AO_RUN_PROMPT',
              promptId: job.prompt_id,
              prompt: job.prompt
            });
          } catch (err) {
            await chrome.scripting.executeScript({ target: { tabId: targetTab.id }, files: ['content_gemini.js'] });
            response = await chrome.tabs.sendMessage(targetTab.id, {
              type: 'AO_RUN_PROMPT',
              promptId: job.prompt_id,
              prompt: job.prompt
            });
          }
          const refreshedTab = await chrome.tabs.get(targetTab.id);
          await callBridge(cfg, '/reply', 'POST', {
            prompt_id: job.prompt_id,
            text: response && response.ok ? response.text : '',
            blocks: response && response.ok ? (response.blocks || []) : [],
            debug_html: response && response.ok ? (response.debug_html || '') : '',
            url: refreshedTab ? refreshedTab.url : '',
            error: response && !response.ok ? (response.error || 'Content script error') : null
          });
        }
      } catch (err) {
        lastStatus = { connected: false, error: String(err.message || err) };
        await new Promise(r => setTimeout(r, 3000));
      }
    }
  } finally {
    polling = false;
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === 'AO_SAVE_PAIRING') {
    chrome.storage.local.set({
      bridgeUrl: msg.bridgeUrl,
      bridgeKey: msg.bridgeKey,
      enabled: msg.enabled !== false
    }).then(() => {
      ensurePollLoop();
      sendResponse({ ok: true });
    });
    return true;
  }
  if (msg && msg.type === 'AO_GET_STATUS') {
    ensurePollLoop();
    sendResponse(lastStatus);
    return false;
  }
  if (msg && msg.type === 'GEMINI_TAB_HEARTBEAT') {
    ensurePollLoop();
    sendResponse({ ok: true });
    return false;
  }
});
