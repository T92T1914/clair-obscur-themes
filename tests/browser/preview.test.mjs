import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { chromium } from 'playwright';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import http from 'node:http';
import crypto from 'node:crypto';

const root = fileURLToPath(new URL('../../', import.meta.url));
let temp, site, server, browser, origin;
const results = { environment: {}, scenarios: [], fonts: {}, metrics: {} };
const failures = [];
const evidence = process.env.THEME_EVIDENCE_DIR;
const python = process.platform === 'win32' ? ['py', '-3.11', '-X', 'utf8'] : ['python3'];

function run(args) {
  const result = spawnSync(python[0], [...python.slice(1), ...args], { cwd: root, encoding: 'utf8', windowsHide: true });
  assert.equal(result.status, 0, result.stdout + result.stderr);
}

before(async () => {
  temp = await mkdtemp(path.join(tmpdir(), 'clair-obscur-browser-'));
  const artifacts = path.join(temp, 'artifacts');
  site = path.join(temp, 'site');
  run(['build.py', '--output', artifacts]);
  run(['preview.py', '--artifacts', artifacts, '--output', site]);
  server = http.createServer(async (request, response) => {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const target = path.resolve(site, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!target.startsWith(site + path.sep)) { response.writeHead(403).end(); return; }
    try {
      const body = await readFile(target);
      const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.zip': 'application/zip' };
      response.writeHead(200, { 'Content-Type': types[path.extname(target)] || 'text/plain', 'Cache-Control': 'no-store' });
      response.end(body);
    } catch { response.writeHead(404).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
  // Uses a disposable profile and never falls back to a visible browser.
  browser = await chromium.launch({ channel: process.env.THEME_BROWSER_CHANNEL || 'chrome', headless: true });
  results.environment = { browser: browser.version(), channel: process.env.THEME_BROWSER_CHANNEL || 'chrome', node: process.version, platform: process.platform, renderer: 'isolated headless page', nativeChromeFrameVerified: false, equibopVerified: false };
  if (evidence) await mkdir(evidence, { recursive: true });
});

after(async () => {
  await browser?.close();
  if (server) await new Promise(resolve => server.close(resolve));
  if (evidence) await writeFile(path.join(evidence, 'browser-evidence.json'), JSON.stringify({ ...results, failures }, null, 2) + '\n');
  // This is the one newly created test directory, never a user profile.
  if (temp && path.basename(temp).startsWith('clair-obscur-browser-') && path.dirname(temp) === tmpdir()) await rm(temp, { recursive: true });
});

async function pageFor(options = {}) {
  const { missingFont = false, ...contextOptions } = options;
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, ...contextOptions });
  const page = await context.newPage();
  const network = [], consoleErrors = [];
  page.on('pageerror', error => consoleErrors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  await context.route('**/*', route => {
    network.push(route.request().url());
    if (!route.request().url().startsWith(origin + '/')) { failures.push('unexpected network origin'); return route.abort(); }
    return route.continue();
  });
  if (missingFont) {
    await page.route('**/tokens.css', async route => {
      const original = await readFile(path.join(site, 'tokens.css'), 'utf8');
      await route.fulfill({ contentType: 'text/css', body: original.replace(/src:local\([^;]+;/g, 'src:local("MissingClairObscurFixtureFont");') });
    });
    await page.route('**/preview.css', async route => {
      const original = await readFile(path.join(site, 'preview.css'), 'utf8');
      await route.fulfill({ contentType: 'text/css', body: original.replace('"Clair Obscur Inter", Inter,', '"Clair Obscur Inter",') });
    });
  }
  await page.goto(origin);
  await page.evaluate(() => document.fonts.ready);
  return { context, page, network, consoleErrors };
}

test('both appearances work at desktop and phone widths without horizontal overflow', async () => {
  for (const width of [390, 1280, 2560]) {
    const { context, page, network, consoleErrors } = await pageFor({ viewport: { width, height: 900 } });
    try {
      for (const name of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name, exact: true }).click();
        assert.equal(await page.locator('html').getAttribute('data-theme'), name);
        assert.equal(await page.getByRole('button', { name, exact: true }).getAttribute('aria-pressed'), 'true');
        const measurements = await page.evaluate(() => ({
          width: innerWidth, documentWidth: document.documentElement.scrollWidth,
          background: getComputedStyle(document.body).backgroundColor,
          color: getComputedStyle(document.body).color,
          font: getComputedStyle(document.body).fontFamily,
        }));
        assert.ok(measurements.documentWidth <= width + 1, JSON.stringify(measurements));
        assert.equal(measurements.background, name === 'Obscur' ? 'rgb(9, 9, 9)' : 'rgb(248, 247, 243)');
        results.scenarios.push({ name, viewport: width, measurements, status: 'passed' });
        if (evidence && width !== 2560) await page.screenshot({ path: path.join(evidence, `${name.toLowerCase()}-${width}-specimen.png`), fullPage: true });
      }
      assert.equal(new Set(network).size, 4, 'HTML, two CSS files and script only');
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
});

test('six genuine Inter glyph faces and native monospace are distinguishable', async t => {
  const { context, page } = await pageFor();
  try {
    const session = await context.newCDPSession(page);
    await session.send('DOM.enable'); await session.send('CSS.enable');
    const loadedFaces = await page.evaluate(() => [...document.fonts].filter(face => face.family === 'Clair Obscur Inter' && face.status === 'loaded').length);
    if (loadedFaces !== 6 && process.env.THEME_REQUIRE_INTER !== '1') {
      t.skip('Six installed Inter faces are required for exact glyph-face verification');
      return;
    }
    assert.equal(loadedFaces, 6);
    const { root: document } = await session.send('DOM.getDocument');
    const expected = {
      regular: 'Inter-Regular', semibold: 'Inter-SemiBold', bold: 'Inter-Bold', italic: 'Inter-Italic',
      'semibold-italic': 'Inter-SemiBoldItalic', 'bold-italic': 'Inter-BoldItalic',
    };
    for (const [kind, face] of Object.entries(expected)) {
      const { nodeId } = await session.send('DOM.querySelector', { nodeId: document.nodeId, selector: '#face-' + kind });
      const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
      results.fonts[kind] = fonts;
      assert.ok(fonts.some(font => font.glyphCount > 0));
      assert.ok(fonts.some(font => font.postScriptName === face), JSON.stringify(fonts));
    }
    const { nodeId } = await session.send('DOM.querySelector', { nodeId: document.nodeId, selector: '#face-code' });
    const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
    results.fonts.code = fonts;
    assert.ok(fonts.every(font => !font.postScriptName?.startsWith('Inter')));
    await session.detach();
  } finally { await context.close(); }
});

test('missing local Inter uses fallback without network font requests', async () => {
  const { context, page, network } = await pageFor({ missingFont: true });
  try {
    const session = await context.newCDPSession(page);
    await session.send('DOM.enable'); await session.send('CSS.enable');
    const { root: document } = await session.send('DOM.getDocument');
    const { nodeId } = await session.send('DOM.querySelector', { nodeId: document.nodeId, selector: '#face-regular' });
    const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
    assert.ok(fonts.some(font => font.glyphCount > 0));
    const fallbackState = await page.evaluate(() => ({
      body: getComputedStyle(document.body).fontFamily,
      faces: [...document.fonts].map(face => ({ family: face.family, status: face.status })),
    }));
    assert.ok(fallbackState.faces.every(face => face.status === 'error'), JSON.stringify(fallbackState));
    // A user's system sans can itself resolve to Inter. Compare with the real
    // fallback stack, instead of pretending its PostScript name is universal.
    await page.evaluate(() => {
      const reference = document.createElement('p'); reference.id = 'fallback-reference';
      reference.textContent = document.querySelector('#face-regular').textContent;
      reference.style.fontFamily = 'system-ui, "Segoe UI", sans-serif';
      document.body.append(reference);
    });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const { nodeId: referenceId } = await session.send('DOM.querySelector', { nodeId: document.nodeId, selector: '#fallback-reference' });
    const { fonts: referenceFonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId: referenceId });
    const identities = list => list.map(({ familyName, postScriptName, isCustomFont }) => ({ familyName, postScriptName, isCustomFont }));
    assert.deepEqual(identities(fonts), identities(referenceFonts));
    results.fonts.missingLocalFallback = { fonts, aliasStates: fallbackState.faces, comparedWithSystemFallback: true };
    assert.ok(network.every(url => url.startsWith(origin + '/')));
  } finally { await context.close(); }
});

test('keyboard, enlarged text, reduced motion and forced colors retain usable controls', async () => {
  const { context, page } = await pageFor({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  try {
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').textContent(), 'Skip to content');
    await page.getByRole('button', { name: 'Clair', exact: true }).focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'Clair');
    await page.locator('#sample-button').focus();
    await page.keyboard.press('Enter');
    assert.match(await page.locator('#control-status').textContent(), /Control activated/);
    const focus = await page.locator('#sample-button').evaluate(node => getComputedStyle(node).outlineWidth);
    assert.equal(focus, '2px');
    await page.addStyleTag({ content: 'html { font-size: 200%; }' });
    const overflowing = await page.evaluate(() => [...document.querySelectorAll('body *')].filter(n => n.getBoundingClientRect().right > innerWidth + 1).map(n => [n.tagName, n.className, n.getBoundingClientRect().right]));
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), JSON.stringify(overflowing));
    await page.emulateMedia({ forcedColors: 'active' });
    for (const name of ['Obscur', 'Clair']) {
      await page.getByRole('button', { name, exact: true }).click();
      assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--panel').trim()), 'Canvas');
      assert.equal(await page.locator('#sample-button').isEnabled(), true);
    }
    results.scenarios.push({ name: 'keyboard, 200% text, reduced motion, forced colors', status: 'passed' });
  } finally { await context.close(); }
});

test('downloads match the artifact hashes and parsed CSS has no rejected rules', async () => {
  const { context, page, consoleErrors } = await pageFor();
  try {
    const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
    assert.equal(manifest.downloads.length, 4);
    for (const download of manifest.downloads) {
      const response = await context.request.get(origin + '/downloads/' + download.path);
      assert.equal(response.status(), 200);
      const bytes = await response.body();
      const record = manifest.files.find(file => file.path === download.path);
      assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), record.sha256);
      if (download.platform === 'equicord') {
        const css = await page.evaluate(text => { const sheet = new CSSStyleSheet(); sheet.replaceSync(text); return { rules: sheet.cssRules.length, faces: [...sheet.cssRules].filter(rule => rule.type === CSSRule.FONT_FACE_RULE).length }; }, bytes.toString('utf8'));
        assert.ok(css.rules > 10);
        assert.equal(css.faces, 6);
      }
    }
    const navigation = await page.evaluate(() => {
      const n = performance.getEntriesByType('navigation')[0];
      return { domContentLoadedMs: n.domContentLoadedEventEnd, loadMs: n.loadEventEnd, requests: performance.getEntriesByType('resource').length };
    });
    results.metrics.previewNavigation = { ...navigation, scope: 'single local headless specimen navigation, not application startup or comparative performance' };
    assert.deepEqual(consoleErrors, []);
    assert.deepEqual(failures, []);
  } finally { await context.close(); }
});

test('Equicord CSS consumes host variables only on its matching native base', async () => {
  const { context, page } = await pageFor();
  try {
    for (const [name, mode, background, text] of [
      ['Obscur', 'dark', 'rgb(9, 9, 9)', 'rgb(244, 244, 244)'],
      ['Clair', 'light', 'rgb(248, 247, 243)', 'rgb(36, 36, 36)'],
    ]) {
      const css = await (await context.request.get(`${origin}/downloads/equicord/${name}.theme.css`)).text();
      // Deliberate host-contract fixture. It is not Discord markup or app acceptance.
      await page.setContent(`<html class="theme-${mode}"><head><style>
        body { background:var(--background-primary,#abcdef); color:var(--text-normal,#123456); font-family:var(--font-primary,Arial); }
        button { font-family:var(--font-primary,Arial); background:var(--control-primary-background-default); color:var(--control-primary-text-default); }
        .switch { background:var(--switch-background-default); border:1px solid var(--switch-border-default); }
        .switch.checked { background:var(--switch-background-selected-default); }
      </style></head><body><p id="message-content-fixture">Regular <strong>bold</strong> <em>italic</em> <code>code</code></p>
      <button class="vc-btn-base vc-btn-medium">Host control</button><span class="switch">Off</span><span class="switch checked">On</span></body></html>`);
      await page.addStyleTag({ content: css });
      await page.evaluate(() => document.fonts.ready);
      const rendered = await page.evaluate(() => ({
        background: getComputedStyle(document.body).backgroundColor,
        text: getComputedStyle(document.body).color,
        controlWeight: getComputedStyle(document.querySelector('button')).fontWeight,
        codeFont: getComputedStyle(document.querySelector('code')).fontFamily,
        off: getComputedStyle(document.querySelector('.switch')).backgroundColor,
        on: getComputedStyle(document.querySelector('.checked')).backgroundColor,
      }));
      assert.equal(rendered.background, background); assert.equal(rendered.text, text);
      assert.equal(rendered.controlWeight, '600'); assert.match(rendered.codeFont, /monospace|Consolas/);
      assert.notEqual(rendered.off, rendered.on);
      await page.evaluate(value => document.documentElement.className = `theme-${value}`, mode === 'dark' ? 'light' : 'dark');
      assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(171, 205, 239)');
      results.scenarios.push({ name: `${name} Equicord host-contract fixture`, status: 'passed', rendered, oppositeBase: 'retains fixture native baseline', nativeAppVerified: false });
    }
  } finally { await context.close(); }
});
