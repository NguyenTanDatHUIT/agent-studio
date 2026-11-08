// In-memory DOM check (NODE_PATH=<directory containing jsdom> node tests/layout_ui.cjs): custom rows x columns survive a reload; corrupt stored values fall back safely.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const assets = path.join(__dirname, '..', 'agent_orchestrator', 'web_assets');

async function load(stored) {
  const dom = new JSDOM(fs.readFileSync(path.join(assets, 'index.html'), 'utf8'), {url: 'http://127.0.0.1:8765/#token=t', runScripts: 'outside-only', pretendToBeVisual: true});
  const w = dom.window, errors = [];
  w.addEventListener('error', e => errors.push(e.error || e.message));
  w.ResizeObserver = class { observe() {} };
  w.HTMLElement.prototype.scrollIntoView = () => {};
  w.setTimeout = () => 1;
  w.requestAnimationFrame = fn => { fn(); return 1; };
  if (stored !== undefined) w.localStorage.setItem('agent-studio-ui', stored);
  w.fetch = async () => ({ok: true, json: async () => []});
  w.eval(fs.readFileSync(path.join(assets, 'app.js'), 'utf8'));
  await new Promise(r => setImmediate(r));
  const d = w.document;
  const out = {rows: d.getElementById('ao-studio').style.getPropertyValue('--console-rows'), cols: d.querySelector('[data-console-grid]').style.getPropertyValue('--console-cols'),
    input: d.querySelector('[data-console-layout-input]').value, errors: errors.length,
    collapsed: d.getElementById('ao-studio').classList.contains('ao-side-collapsed'), toggle: d.querySelector('[data-side-toggle]').getAttribute('aria-label'),
    theme: d.getElementById('ao-studio').dataset.theme, palette: d.getElementById('ao-studio').dataset.palette, htmlPalette: d.documentElement.dataset.palette};
  w.close();
  return out;
}

(async () => {
  assert.deepEqual(await load(JSON.stringify({layout: '3x4'})), {rows: '3', cols: '4', input: '3 x 4', errors: 0, collapsed: false, toggle: 'Đóng thanh bên', theme: 'system', palette: 'claude', htmlPalette: 'claude'});
  assert.deepEqual(await load(JSON.stringify({layout: '1x2'})), {rows: '1', cols: '2', input: '1 x 2', errors: 0, collapsed: false, toggle: 'Đóng thanh bên', theme: 'system', palette: 'claude', htmlPalette: 'claude'});
  for (const junk of [JSON.stringify({layout: '9x9'}), JSON.stringify({layout: 'evil'}), JSON.stringify({layout: {a: 1}}), 'not json', JSON.stringify({layout: '__proto__'}), undefined]) {
    assert.deepEqual(await load(junk), {rows: '2', cols: '2', input: '2 x 2', errors: 0, collapsed: false, toggle: 'Đóng thanh bên', theme: 'system', palette: 'claude', htmlPalette: 'claude'}, 'falls back to 2x2 for ' + junk);
  }
  assert.deepEqual(await load(JSON.stringify({side: 'collapsed'})), {rows: '2', cols: '2', input: '2 x 2', errors: 0, collapsed: true, toggle: 'Mở thanh bên', theme: 'system', palette: 'claude', htmlPalette: 'claude'}, 'sidebar stays closed after reload');
  for (const junk of [JSON.stringify({side: 'sideways'}), JSON.stringify({side: {a: 1}}), JSON.stringify({side: '__proto__'})]) {
    assert.equal((await load(junk)).collapsed, false, 'unknown sidebar value means open: ' + junk);
  }
  const themed = await load(JSON.stringify({theme: 'dark', palette: 'classic'}));
  assert.equal(themed.theme + '/' + themed.palette + '/' + themed.htmlPalette, 'dark/classic/classic', 'appearance survives reload');
  for (const junk of [JSON.stringify({theme: 'neon', palette: 'rainbow'}), JSON.stringify({theme: {a: 1}, palette: ['x']}), JSON.stringify({theme: '__proto__', palette: 'constructor'})]) {
    const r = await load(junk);
    assert.equal(r.theme + '/' + r.palette, 'system/claude', 'unknown appearance values fall back: ' + junk);
  }
  console.log('PASS: custom layout, sidebar and appearance survive reload; invalid stored values fall back safely');
})().catch(e => { console.error(e); process.exit(1); });
