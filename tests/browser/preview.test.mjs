import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { chromium, webkit } from 'playwright';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, writeFile, mkdir, rename, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import http from 'node:http';
import crypto from 'node:crypto';
import { assertRenderedFace } from './font-evidence.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
let temp, site, server, browser, origin;
const results = { environment: {}, scenarios: [], fonts: {}, metrics: {} };
const failures = [];
const evidence = process.env.THEME_EVIDENCE_DIR;
const python = process.platform === 'win32' ? ['py', '-3.11', '-X', 'utf8'] : ['python3'];

function run(args) {
  const result = spawnSync(python[0], [...python.slice(1), ...args], {
    cwd: root, encoding: 'utf8', windowsHide: true, timeout: 30000, maxBuffer: 4 * 1024 * 1024,
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + result.stderr);
}

before(async () => {
  temp = await mkdtemp(path.join(tmpdir(), 'clair-obscur-browser-'));
  const artifacts = path.join(temp, 'artifacts');
  const generated = path.join(temp, 'generated', 'site');
  site = path.join(temp, 'relocated', 'preview');
  run(['build.py', '--output', artifacts]);
  run(['preview.py', '--artifacts', artifacts, '--output', generated]);
  await mkdir(path.dirname(site));
  await rename(generated, site);
  server = http.createServer(async (request, response) => {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const target = path.resolve(site, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!target.startsWith(site + path.sep)) { response.writeHead(403).end(); return; }
    try {
      const body = await readFile(target);
      const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.zip': 'application/zip', '.xpi': 'application/x-xpinstall' };
      response.writeHead(200, { 'Content-Type': types[path.extname(target)] || 'text/plain', 'Cache-Control': 'no-store' });
      response.end(body);
    } catch { response.writeHead(404).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
  // Uses a disposable profile and never falls back to a visible browser.
  // WebKit can run the portable layout and download checks by test name.
  // The exact glyph-face checks continue to require Chromium's CDP interface.
  const engine = process.env.THEME_BROWSER_ENGINE || 'chromium';
  assert.ok(['chromium', 'webkit'].includes(engine), 'Unknown specimen browser engine');
  const launchOptions = engine === 'webkit' ? { headless: true } : {
    channel: process.env.THEME_BROWSER_CHANNEL || 'chrome', headless: true,
    chromiumSandbox: true, args: ['--mute-audio', '--disable-gpu'],
  };
  browser = await (engine === 'webkit' ? webkit : chromium).launch(launchOptions);
  results.environment = { engine, browser: browser.version(), channel: launchOptions.channel, requestedLaunch: launchOptions, node: process.version, platform: process.platform, renderer: 'isolated headless page', relocatedPreview: true, nativeChromeFrameVerified: false, equibopVerified: false };
  let versionSession;
  try {
    versionSession = await browser.newBrowserCDPSession();
    const { product, revision, protocolVersion, jsVersion } = await versionSession.send('Browser.getVersion');
    results.environment.browserProcess = { status: 'observed', product, revision, protocolVersion, jsVersion };
  } catch (error) {
    results.environment.browserProcess = { status: 'unavailable', error: error.name };
  } finally { await versionSession?.detach(); }
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
  const { missingFont = false, setup, ...contextOptions } = options;
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
  if (setup) await setup(context, page);
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

test('narrow enlarged headings wrap without reducing text or hiding content', async () => {
  for (const { width, height, enlarged } of [
    { width: 390, height: 844, enlarged: false },
    { width: 844, height: 320, enlarged: false },
    { width: 320, height: 640, enlarged: true },
  ]) {
    const { context, page, consoleErrors } = await pageFor({
      viewport: { width, height }, isMobile: true, hasTouch: true, reducedMotion: 'reduce',
    });
    try {
      if (enlarged) await page.addStyleTag({ content: 'html { font-size: 200%; }' });
      for (const appearance of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name: appearance, exact: true }).tap();
        const layout = await page.evaluate(() => ({
          viewport: innerWidth, pageWidth: document.documentElement.scrollWidth,
          rootFontSize: getComputedStyle(document.documentElement).fontSize,
          headings: ['palettes-heading', 'downloads-heading'].map(id => {
            const node = document.getElementById(id), box = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return { id, text: node.textContent, fontSize: style.fontSize,
              width: box.width, height: box.height, left: box.left, right: box.right,
              clientWidth: node.clientWidth, scrollWidth: node.scrollWidth,
              overflowX: style.overflowX };
          }),
          controls: [...document.querySelectorAll('.switcher button,.download-card a.button')].map(node => {
            const box = node.getBoundingClientRect();
            return { label: node.textContent, left: box.left, right: box.right, height: box.height };
          }),
        }));
        results.scenarios.push({ name: 'narrow headings', appearance, width, height, enlarged, layout });
        assert.equal(layout.rootFontSize, enlarged ? '32px' : '16px');
        assert.ok(layout.pageWidth <= width + 1, JSON.stringify(layout));
        assert.deepEqual(layout.headings.map(h => h.text), [
          'One identity, two appearances.', 'Choose a platform candidate',
        ]);
        for (const heading of layout.headings) {
          assert.equal(heading.overflowX, 'visible', 'Do not hide the overflowing prose');
          assert.ok(heading.scrollWidth <= heading.clientWidth + 1, JSON.stringify(heading));
          if (enlarged) assert.ok(parseFloat(heading.fontSize) >= 48, 'Keep the enlarged heading size');
        }
        for (const control of layout.controls) {
          assert.ok(control.height >= 44, JSON.stringify(control));
          assert.ok(control.left >= -1 && control.right <= width + 1, JSON.stringify(control));
        }
        if (evidence && enlarged) {
          await page.locator('#palettes-heading').scrollIntoViewIfNeeded();
          await page.screenshot({ path: path.join(evidence, `${appearance.toLowerCase()}-320-enlarged-headings.png`) });
        }
      }
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
});

test('six genuine Inter glyph faces and native monospace are distinguishable', async t => {
  const { context, page } = await pageFor();
  try {
    const session = await context.newCDPSession(page);
    await session.send('DOM.enable'); await session.send('CSS.enable');
    const faceStates = await page.evaluate(async () => Promise.all(
      [...document.fonts].filter(face => face.family === 'Clair Obscur Inter').map(async face => {
        const record = { family: face.family, weight: face.weight, style: face.style, statusBeforeRequest: face.status };
        try { await face.load(); record.loadRequest = 'fulfilled'; }
        catch (error) { record.loadRequest = 'rejected'; record.error = error.name; }
        return { ...record, status: face.status };
      })));
    results.fonts.localFaces = { required: process.env.THEME_REQUIRE_INTER === '1', faces: faceStates };
    assert.deepEqual(faceStates.map(face => `${face.weight}:${face.style}`).sort(),
      ['400:normal', '400:italic', '600:normal', '600:italic', '700:normal', '700:italic'].sort(),
      'The fixture must declare each required face exactly once');
    const loadedFaces = faceStates.filter(face => face.status === 'loaded').length;
    if (loadedFaces !== 6 && process.env.THEME_REQUIRE_INTER !== '1') {
      t.skip('Six installed Inter faces are required for exact glyph-face verification');
      return;
    }
    assert.equal(loadedFaces, 6, JSON.stringify(results.fonts.localFaces));
    await page.evaluate(async () => {
      await document.fonts.ready;
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    });
    const { root: document } = await session.send('DOM.getDocument');
    const expected = {
      regular: 'Inter-Regular', semibold: 'Inter-SemiBold', bold: 'Inter-Bold', italic: 'Inter-Italic',
      'semibold-italic': 'Inter-SemiBoldItalic', 'bold-italic': 'Inter-BoldItalic',
    };
    for (const [kind, face] of Object.entries(expected)) {
      const { nodeId } = await session.send('DOM.querySelector', { nodeId: document.nodeId, selector: '#face-' + kind });
      const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
      results.fonts[kind] = fonts;
      assertRenderedFace(fonts, face);
    }
    const { nodeId } = await session.send('DOM.querySelector', { nodeId: document.nodeId, selector: '#face-code' });
    const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
    results.fonts.code = fonts;
    assert.ok(fonts.some(font => font.glyphCount > 0));
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
      for (const palette of await page.locator('[data-palette]').all()) {
        assert.equal(await palette.evaluate(node => getComputedStyle(node).getPropertyValue('--canvas').trim()), 'Canvas');
      }
      assert.equal(await page.locator('#sample-button').isEnabled(), true);
    }
    results.scenarios.push({ name: 'keyboard, 200% text, reduced motion, forced colors', status: 'passed' });
  } finally { await context.close(); }
});

test('download clicks save all platform choices without navigating away', async () => {
  // Separate palette chooser journeys keep the test about deliberate file
  // selection. One context per palette and one for the paired GX candidate
  // keep each journey below Chromium's ordinary ten-download burst threshold.
  // A single rapid seventeen-click burst measures Chromium's download
  // throttle instead. Browser limits and download permissions stay unchanged.
  for (const name of ['Clair', 'Obscur', 'Clair and Obscur']) {
    const { context, page, consoleErrors } = await pageFor({ viewport: { width: name === 'Clair and Obscur' ? 390 : 1280, height: 900 } });
    try {
    const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
    assert.equal(manifest.downloads.length, 17);
    const choices = manifest.downloads.filter(item => item.name === name);
    assert.equal(choices.length, name === 'Clair and Obscur' ? 1 : 8);
    for (const download of choices) {
      const group = page.locator(`#${download.platform}-downloads`);
      const link = group.locator(`a[download][href="downloads/${download.path}"]`);
      assert.equal(await link.count(), 1);
      let saved;
      try { [saved] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), link.click()]); }
      catch (error) {
        failures.push({ scenario:'download', platform:download.platform, path:download.path, pageUrl:page.url(), error:error.message });
        throw new Error(`${download.platform} ${download.name} download failed (${download.path}): ${error.message}`, { cause:error });
      }
      assert.equal(saved.suggestedFilename(), path.basename(download.path));
      assert.equal(await saved.failure(), null);
      const chunks = [];
      for await (const chunk of await saved.createReadStream()) chunks.push(chunk);
      const bytes = Buffer.concat(chunks);
      assert.equal(page.url(), origin + '/');
      const record = manifest.files.find(file => file.path === download.path);
      assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), record.sha256);
      results.scenarios.push({ name:`${download.name} ${download.platform} download`, status:'passed', path:download.path, sha256:record.sha256 });
      if (['equicord', 'vencord', 'betterdiscord'].includes(download.platform)) {
        const css = await page.evaluate(text => { const sheet = new CSSStyleSheet(); sheet.replaceSync(text); return { rules: sheet.cssRules.length, faces: [...sheet.cssRules].filter(rule => rule.type === CSSRule.FONT_FACE_RULE).length }; }, bytes.toString('utf8'));
        assert.ok(css.rules > 10);
        assert.equal(css.faces, 6);
      }
    }
    const navigation = await page.evaluate(() => {
      const n = performance.getEntriesByType('navigation')[0];
      return { domContentLoadedMs: n.domContentLoadedEventEnd, loadMs: n.loadEventEnd, requests: performance.getEntriesByType('resource').length };
    });
    results.metrics[`previewNavigation${name}`] = { ...navigation, scope: `one local headless ${choices.length}-choice journey, not application startup or comparative performance` };
    assert.deepEqual(consoleErrors, []);
    assert.deepEqual(failures, []);
    } finally { await context.close(); }
  }
});

test('released source stays separate from the current preview snapshot', async () => {
  const { context, page } = await pageFor();
  try {
    const manifest = await (await context.request.get(origin + '/site-manifest.json')).json();
    const releaseBase = `https://github.com/T92T1914/clair-obscur-themes/releases/download/v${manifest.release.version}`;
    assert.equal(await page.locator('#released-source').getAttribute('href'), releaseBase + '/source.zip');
    assert.equal(await page.locator('#released-checksums').getAttribute('href'), releaseBase + '/release-SHA256SUMS');
    assert.equal(await page.locator('#current-source').textContent(), 'Current source snapshot');
    const sourceText = await page.locator('#source-identity').textContent();
    if (manifest.source.revision) {
      assert.ok(sourceText.includes(manifest.source.revision));
      assert.equal(sourceText.includes('with local source changes'), manifest.source.state === 'modified');
    } else {
      assert.ok(sourceText.includes('Revision unavailable'));
      assert.equal(manifest.source.state, 'unavailable');
    }
    const [saved] = await Promise.all([page.waitForEvent('download'), page.locator('#current-source').click()]);
    assert.equal(saved.suggestedFilename(), 'source.zip');
    assert.equal(await saved.failure(), null);
    const chunks = [];
    for await (const chunk of await saved.createReadStream()) chunks.push(chunk);
    const digest = crypto.createHash('sha256').update(Buffer.concat(chunks)).digest('hex');
    assert.equal(digest, manifest.source.sha256);
    assert.equal(await (await context.request.get(origin + '/source-SHA256SUMS')).text(), `${digest}  source.zip\n`);
    results.scenarios.push({ name: 'separate release source links and revision-labeled current source download', status: 'passed', source: manifest.source });
  } finally { await context.close(); }
});

test('static delivery remains usable without JavaScript and internal links resolve', async () => {
  const { context, page, consoleErrors } = await pageFor({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  try {
    assert.equal(await page.locator('#downloads .download-card a[download]').count(), 17);
    assert.ok(await page.locator('#local-package-checker').isHidden());
    assert.match(await page.locator('#downloads .status').textContent(), /preview builds/);
    assert.match(await page.locator('.hero .status').textContent(), /Full native acceptance remains open/);
    const acceptance = page.getByRole('link', { name: 'dated acceptance record', exact: true });
    assert.ok(await acceptance.isVisible());
    assert.equal(await acceptance.getAttribute('href'), 'https://github.com/T92T1914/clair-obscur-themes/blob/main/docs/acceptance.md');
    assert.doesNotMatch(await page.content(), /\{\{[A-Z_]+\}\}/);
    for (const [name, background] of [['Obscur', 'rgb(9, 9, 9)'], ['Clair', 'rgb(248, 247, 243)']]) {
      const card = page.locator(`[data-palette="${name}"]`);
      assert.equal(await card.evaluate(node => getComputedStyle(node).backgroundColor), background);
    }
    const unresolved = await page.evaluate(() => [...document.querySelectorAll('a[href^="#"]')]
      .map(link => link.getAttribute('href').slice(1)).filter(id => !document.getElementById(id)));
    assert.deepEqual(unresolved, []);
    await page.getByRole('link', { name: 'Equibop with Equicord', exact: true }).click();
    assert.equal(new URL(page.url()).hash, '#equicord-downloads');
    assert.ok(await page.locator('#equicord-downloads').isVisible());
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'no-JavaScript palette comparison, grouped downloads and anchor navigation', status: 'passed' });
  } finally { await context.close(); }
});

async function waitForGuideDestination(page, anchor, timeout = 2000) {
  // Keyboard dispatch can finish before the fragment navigation is observed.
  // Neither a matching URL alone nor repaired focus proves the keyboard path.
  await page.waitForURL(url => url.hash === '#' + anchor, { timeout, waitUntil: 'commit' });
  const focused = await page.waitForFunction(id => document.activeElement?.id === id, anchor, { timeout });
  await focused.dispose();
}

async function packageCheckerState(page) {
  return page.evaluate(() => {
    function storageEntries(name) {
      try { return Object.entries(window[name]).sort(([a], [b]) => a.localeCompare(b)); }
      catch (error) { return { unavailable: error.name }; }
    }
    return { reading: document.documentElement.dataset.theme,
      target: document.querySelector('#package-target').value,
      appearance: document.querySelector('#package-appearance').value,
      local: storageEntries('localStorage'), session: storageEntries('sessionStorage'), cookie: document.cookie };
  });
}

async function waitForPackageState(page, state) {
  const done = await page.waitForFunction(expected => document.querySelector('#local-package-checker').dataset.state === expected,
    state, { timeout: 2000 });
  await done.dispose();
}

async function checkLocalPackageIdentification(page, manifest, payloads, { delivery, textScale = 100 }) {
  const requests = [], downloads = [], identified = [], guides = new Set();
  const onRequest = request => requests.push(request.url());
  const onDownload = download => downloads.push(download.suggestedFilename());
  page.on('request', onRequest);
  page.on('download', onDownload);
  try {
    assert.ok(await page.locator('#local-package-checker').isVisible());
    await waitForPackageState(page, 'idle');
    assert.equal(await page.locator('#local-package-status').getAttribute('role'), 'status');
    const bound = Math.max(...manifest.downloads.map(item => manifest.files.find(record => record.path === item.path).bytes));
    assert.match(await page.locator('#local-package-bound').textContent(), new RegExp(bound.toLocaleString('en-US')));
    await page.locator('#package-target').selectOption('brave');
    await page.locator('#package-appearance').selectOption('Clair');
    await page.getByRole('button', { name: 'Clair', exact: true }).click();
    const before = await packageCheckerState(page);
    const input = page.locator('#local-package-file');
    await input.focus();
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'local-package-clear');
    await page.keyboard.press('Shift+Tab');
    assert.equal(await input.evaluate(node => getComputedStyle(node).outlineWidth), '2px');
    for (const { item, file } of payloads) {
      const bytes = await readFile(file);
      const record = manifest.files.find(record => record.path === item.path);
      const expectedHash = crypto.createHash('sha256').update(bytes).digest('hex');
      assert.equal(expectedHash, record.sha256);
      const expected = manifest.downloads.filter(choice => manifest.files.find(record => record.path === choice.path).sha256 === expectedHash)
        .flatMap(choice => (choice.platform === 'opera-gx' ? ['Clair', 'Obscur'] : [choice.name])
          .map(appearance => ({ choice, anchor: `guide-${choice.platform}-${appearance.toLowerCase()}` })));
      await input.focus();
      const url = page.url();
      await input.setInputFiles(file);
      await waitForPackageState(page, 'matched');
      assert.equal(page.url(), url, 'Identification must not navigate');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'local-package-file');
      assert.equal(await page.locator('.local-file-hash code').textContent(), expectedHash);
      const matches = page.locator('#local-package-result .identified-package');
      assert.equal(await matches.count(), expected.length);
      assert.deepEqual((await matches.locator('.guide-link').evaluateAll(links => links.map(link => link.getAttribute('href')))).sort(),
        expected.map(reference => '#' + reference.anchor).sort());
      for (const { choice, anchor } of expected) {
        const match = matches.filter({ has: page.locator(`a.guide-link[href="#${anchor}"]`) });
        const identity = await match.textContent();
        assert.ok(identity.includes('Package ' + choice.version));
        assert.ok(identity.includes(record.sha256));
        assert.equal(await match.locator('.identified-package-path code').textContent(), 'downloads/' + choice.path);
        assert.match(identity, /Native acceptance pending/);
        assert.ok(identity.includes(await page.locator(`#${choice.platform}-downloads > p`).first().textContent()));
        if (['equicord', 'vencord', 'betterdiscord'].includes(choice.platform)) assert.match(identity, /not Discord-endorsed/);
        const link = match.locator('.guide-link');
        await link.focus();
        await page.keyboard.press('Enter');
        await waitForGuideDestination(page, anchor);
        assert.ok(await page.locator('#' + anchor).isVisible());
        guides.add(anchor);
      }
      const geometry = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
      assert.ok(geometry.document <= geometry.width + 1, JSON.stringify({ textScale, ...geometry }));
      assert.deepEqual(await packageCheckerState(page), before);
      identified.push({ path: item.path, sha256: expectedHash, guides: expected.map(reference => reference.anchor) });
    }
    assert.equal(identified.length, 13);
    assert.equal(guides.size, 18);
    const chrome = payloads.find(payload => payload.item.platform === 'chrome' && payload.item.name === 'Clair');
    const renamed = path.join(temp, `identification-${delivery}-renamed.bin`);
    await writeFile(renamed, await readFile(chrome.file));
    await input.focus();
    const url = page.url();
    await input.setInputFiles(renamed);
    await waitForPackageState(page, 'matched');
    assert.equal(await page.locator('#local-package-result .identified-package').count(), 3);
    const exact = await readFile(chrome.file);
    await input.setInputFiles({ name: '<img src=x onerror="throw 1">.bin', mimeType: 'application/octet-stream', buffer: exact });
    await waitForPackageState(page, 'matched');
    assert.match(await page.locator('#local-package-selection').textContent(), /<img src=x/);
    assert.equal(await page.locator('#local-package-selection img').count(), 0);
    const changed = Buffer.from(exact);
    changed[0] ^= 1;
    for (const bytes of [changed, Buffer.from('an unrelated local file'), Buffer.alloc(0), Buffer.alloc(bound, 19)]) {
      await input.setInputFiles({ name: 'unknown-package.zip', mimeType: 'application/octet-stream', buffer: bytes });
      await waitForPackageState(page, 'no-match');
      assert.equal(await page.locator('.local-file-hash code').textContent(), crypto.createHash('sha256').update(bytes).digest('hex'));
      assert.equal(await page.locator('#local-package-result .identified-package').count(), 0);
      assert.match(await page.locator('#local-package-status').textContent(), /computed SHA-256 matches no package referenced/);
    }
    assert.equal(page.url(), url);
    assert.deepEqual(await packageCheckerState(page), before);
    await page.locator('#local-package-clear').focus();
    await page.keyboard.press('Enter');
    await waitForPackageState(page, 'idle');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'local-package-clear');
    assert.equal(await input.evaluate(node => node.files.length), 0);
    assert.ok(await page.locator('#local-package-result').isHidden());
    assert.equal(await page.locator('#local-package-result').textContent(), '');
    assert.equal(await page.locator('#local-package-selection').textContent(), '');
    assert.equal(await page.locator('#downloads .download-card').count(), 17);
    assert.deepEqual(await packageCheckerState(page), before);
    assert.deepEqual(requests, [], 'Reading, hashing, rendering and guide routing must not request resources');
    assert.deepEqual(downloads, [], 'Identification must not start downloads');
    return { delivery, textScale, identified, routes: guides.size, renamed: 'same bytes matched all Chrome aliases',
      changed: 'same size with a changed byte computed no match', unknown: 'small, empty and bound-sized computed no match',
      filename: 'plain text', storage: 'unchanged', requests, downloads, focus: 'preserved', clear: 'passed' };
  } finally {
    page.off('request', onRequest);
    page.off('download', onDownload);
  }
}

test('actual public package downloads identify all captured guides locally without filename inference', async () => {
  const payloads = [];
  let manifest;
  for (const name of ['Clair', 'Obscur', 'Clair and Obscur']) {
    const { context, page, consoleErrors } = await pageFor();
    try {
      manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
      const distinct = manifest.downloads.filter((item, index, items) => items.findIndex(choice => choice.path === item.path) === index);
      for (const item of distinct.filter(item => item.name === name)) {
        const file = path.join(temp, 'identified-public', ...item.path.split('/'));
        await mkdir(path.dirname(file), { recursive: true });
        const link = page.locator(`#${item.platform}-downloads a.button[download][href="downloads/${item.path}"]`);
        const [download] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), link.click()]);
        assert.equal(await download.failure(), null);
        await download.saveAs(file);
        assert.equal(page.url(), origin + '/');
        payloads.push({ item, file });
      }
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
  assert.equal(payloads.length, 13);
  for (const width of [320, 390]) {
    for (const textScale of [100, 200]) {
      const { context, page, consoleErrors } = await pageFor({ viewport: { width, height: 844 } });
      try {
        await page.evaluate(scale => document.documentElement.style.fontSize = scale + '%', textScale);
        const identified = await checkLocalPackageIdentification(page, manifest, payloads, { delivery: 'public', textScale });
        assert.deepEqual(consoleErrors, []);
        results.scenarios.push({ name: 'actual public package identification', status: 'passed', width, ...identified });
      } finally { await context.close(); }
    }
  }
});

test('local package failures remain uncomputed and late work cannot replace a new selection or Clear', async () => {
  const { context, page, consoleErrors } = await pageFor({ viewport: { width: 320, height: 844 } });
  const requests = [], downloads = [];
  try {
    const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
    const item = manifest.downloads.find(item => item.platform === 'chrome' && item.name === 'Clair');
    const exact = await readFile(path.join(site, 'downloads', ...item.path.split('/')));
    const record = manifest.files.find(record => record.path === item.path);
    const bound = Math.max(...manifest.downloads.map(item => manifest.files.find(record => record.path === item.path).bytes));
    page.on('request', request => requests.push(request.url()));
    page.on('download', download => downloads.push(download.suggestedFilename()));
    await page.evaluate(() => {
      const originalRead = File.prototype.arrayBuffer;
      const subtle = crypto.subtle;
      const originalHash = subtle.digest.bind(subtle);
      const controls = { reads: 0, hashes: 0, holdRead: false, holdHash: false, rejectRead: false, rejectHash: false,
        pendingReads: [], pendingHashes: [] };
      window.packageFixture = controls;
      File.prototype.arrayBuffer = function () {
        controls.reads++;
        if (controls.rejectRead) return Promise.reject(new Error('Controlled read rejection'));
        if (controls.holdRead) {
          controls.holdRead = false;
          return new Promise((resolve, reject) => controls.pendingReads.push({
            resolve: () => originalRead.call(this).then(resolve, reject), reject: () => reject(new Error('Controlled stale read rejection')) }));
        }
        return originalRead.call(this);
      };
      subtle.digest = function (algorithm, bytes) {
        controls.hashes++;
        if (controls.rejectHash) return Promise.reject(new Error('Controlled hash rejection'));
        if (controls.holdHash) {
          controls.holdHash = false;
          return new Promise((resolve, reject) => controls.pendingHashes.push({
            resolve: () => originalHash(algorithm, bytes).then(resolve, reject), reject: () => reject(new Error('Controlled stale hash rejection')) }));
        }
        return originalHash(algorithm, bytes);
      };
    });
    const input = page.locator('#local-package-file');
    await input.focus();
    const before = await packageCheckerState(page), url = page.url();
    const matched = () => input.setInputFiles({ name: 'current-package.bin', mimeType: 'application/octet-stream', buffer: exact });
    const snapshot = () => page.locator('#local-package-checker').evaluate(node => ({
      state: node.dataset.state, status: node.querySelector('#local-package-status').textContent,
      result: node.querySelector('#local-package-result').textContent, hidden: node.querySelector('#local-package-result').hidden,
      selection: node.querySelector('#local-package-selection').textContent }));
    const settle = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    async function waitPending(kind) {
      const waiting = await page.waitForFunction(name => window.packageFixture[name].length === 1, kind, { timeout: 2000 });
      await waiting.dispose();
    }
    async function startPending(kind) {
      await page.evaluate(name => window.packageFixture[name] = true, kind === 'pendingReads' ? 'holdRead' : 'holdHash');
      await input.setInputFiles({ name: 'older-package.bin', mimeType: 'application/octet-stream', buffer: Buffer.from('older bytes') });
      await waitPending(kind);
      await waitForPackageState(page, 'checking');
      assert.ok(await page.locator('#local-package-result').isHidden());
      assert.equal(await page.locator('#local-package-result').textContent(), '');
      assert.ok(await input.isEnabled());
      assert.ok(await page.locator('#local-package-clear').isEnabled());
    }
    async function release(kind, method) {
      await page.evaluate(async ({ kind, method }) => {
        await window.packageFixture[kind].shift()[method]();
      }, { kind, method });
      await settle();
    }
    const checks = [];
    // Superseded success and rejection in both await phases must stay silent.
    for (const kind of ['pendingReads', 'pendingHashes']) {
      for (const method of ['resolve', 'reject']) {
        await startPending(kind);
        await matched();
        await waitForPackageState(page, 'matched');
        assert.equal(await page.locator('.local-file-hash code').textContent(), record.sha256);
        const current = await snapshot();
        const hashes = await page.evaluate(() => window.packageFixture.hashes);
        await release(kind, method);
        assert.deepEqual(await snapshot(), current);
        assert.equal(await page.evaluate(() => window.packageFixture.hashes), hashes,
          'An obsolete read must not start another hash');
        checks.push({ kind, method, replacement: 'matched selection', status: 'passed' });
      }
    }
    for (const replacement of ['oversize', 'clear', 'empty-selection']) {
      await startPending('pendingReads');
      const reads = await page.evaluate(() => window.packageFixture.reads);
      if (replacement === 'oversize') {
        await input.setInputFiles({ name: 'complete-kit.zip', mimeType: 'application/zip', buffer: Buffer.alloc(bound + 1) });
        await waitForPackageState(page, 'size-rejected');
        assert.equal(await page.evaluate(() => window.packageFixture.reads), reads);
        assert.match(await page.locator('#local-package-status').textContent(), /not read and no digest was computed/);
      } else if (replacement === 'clear') {
        await page.locator('#local-package-clear').focus();
        await page.keyboard.press('Enter');
        await waitForPackageState(page, 'idle');
        assert.equal(await page.evaluate(() => document.activeElement.id), 'local-package-clear');
      } else {
        await input.setInputFiles([]);
        await waitForPackageState(page, 'idle');
      }
      const current = await snapshot();
      const hashes = await page.evaluate(() => window.packageFixture.hashes);
      await release('pendingReads', 'resolve');
      assert.deepEqual(await snapshot(), current);
      assert.equal(await page.evaluate(() => window.packageFixture.hashes), hashes);
      checks.push({ kind: 'pendingReads', method: 'resolve', replacement, status: 'passed' });
    }
    // The Clear generation also owns a pending hash and its later rejection.
    for (const method of ['resolve', 'reject']) {
      await startPending('pendingHashes');
      await page.locator('#local-package-clear').click();
      await waitForPackageState(page, 'idle');
      const current = await snapshot();
      await release('pendingHashes', method);
      assert.deepEqual(await snapshot(), current);
      checks.push({ kind: 'pendingHashes', method, replacement: 'Clear', status: 'passed' });
    }
    for (const [fixture, state, message] of [['rejectRead', 'read-failed', /No digest was computed/],
      ['rejectHash', 'hash-failed', /No digest comparison was made/]]) {
      await matched();
      await waitForPackageState(page, 'matched');
      await page.evaluate(name => window.packageFixture[name] = true, fixture);
      await input.setInputFiles({ name: 'failure.bin', mimeType: 'application/octet-stream', buffer: exact });
      await waitForPackageState(page, state);
      assert.match(await page.locator('#local-package-status').textContent(), message);
      assert.ok(await page.locator('#local-package-result').isHidden());
      assert.equal(await page.locator('#local-package-result').textContent(), '');
      await page.evaluate(name => window.packageFixture[name] = false, fixture);
      await matched();
      await waitForPackageState(page, 'matched');
      checks.push({ failure: state, recovery: 'matched', status: 'passed' });
    }
    await page.evaluate(() => {
      window.savedCrypto = Object.getOwnPropertyDescriptor(window, 'crypto');
      Object.defineProperty(window, 'crypto', { configurable: true, value: undefined });
    });
    const reads = await page.evaluate(() => window.packageFixture.reads);
    await matched();
    await waitForPackageState(page, 'unavailable');
    assert.match(await page.locator('#local-package-status').textContent(), /No digest was computed/);
    assert.equal(await page.evaluate(() => window.packageFixture.reads), reads);
    assert.ok(await page.locator('#local-package-result').isHidden());
    await page.evaluate(() => {
      if (window.savedCrypto) Object.defineProperty(window, 'crypto', window.savedCrypto);
      else delete window.crypto;
    });
    await matched();
    await waitForPackageState(page, 'matched');
    await input.focus();
    assert.equal(await page.evaluate(() => document.activeElement.id), 'local-package-file');
    assert.equal(page.url(), url);
    assert.deepEqual(await packageCheckerState(page), before);
    assert.deepEqual(requests, []);
    assert.deepEqual(downloads, []);
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'local package controlled failures and stale async ownership', status: 'passed',
      checks, oversize: 'rejected before read', cryptoUnavailable: 'no read, recovered', requests, downloads });
  } finally { await context.close(); }
});

test('incomplete captured package metadata is unavailable rather than a computed no match', async () => {
  for (const defect of ['size', 'hash', 'route']) {
    const { context, page, consoleErrors } = await pageFor({ setup: async (_context, fixturePage) => {
      await fixturePage.route('**/preview.js', async route => {
        const script = await readFile(path.join(site, 'preview.js'), 'utf8');
        const change = defect === 'size' ? 'document.querySelector("#chrome-clair").dataset.packageBytes = "-1";'
          : defect === 'hash' ? 'document.querySelector("#guide-chrome-clair .package-hash code").textContent = "not a digest";'
            : 'document.querySelector("#chrome-clair .guide-link").remove();';
        await route.fulfill({ contentType: 'text/javascript', body: change + '\n' + script });
      });
    } });
    try {
      await waitForPackageState(page, 'unavailable');
      assert.ok(await page.locator('#local-package-file').isDisabled());
      assert.match(await page.locator('#local-package-status').textContent(), /references are incomplete. No digest was computed/);
      assert.equal(await page.locator('#local-package-result').textContent(), '');
      assert.ok(await page.locator('#local-package-result').isHidden());
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'invalid local package reference fixture', status: 'passed', defect, result: 'unavailable, uncomputed' });
    } finally { await context.close(); }
  }
});

async function checkPackageChooser(page, manifest, { delivery, textScale = 100 }) {
  const requests = [], downloads = [], routes = [];
  const onRequest = request => requests.push(request.url());
  const onDownload = download => downloads.push(download.suggestedFilename());
  page.on('request', onRequest);
  page.on('download', onDownload);
  try {
    assert.ok(await page.locator('#package-chooser').isVisible());
    assert.equal(await page.locator('#package-target').inputValue(), '');
    assert.equal(await page.locator('#package-appearance').inputValue(), 'Obscur');
    assert.ok(await page.locator('#package-choice-result').isHidden());
    // Exercise native selects with actual keyboard input before the matrix.
    await page.locator('#package-target').focus();
    await page.keyboard.press('Tab');
    await page.keyboard.press('Shift+Tab');
    assert.equal(await page.locator('#package-target').evaluate(node => getComputedStyle(node).outlineWidth), '2px');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('#package-target').inputValue(), 'chrome');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('#package-appearance').inputValue(), 'Clair');
    const selectedHref = await page.locator('#package-choice-file').getAttribute('href');
    for (const readingAppearance of ['Obscur', 'Clair']) {
      await page.getByRole('button', { name: readingAppearance, exact: true }).focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('#package-appearance').inputValue(), 'Clair');
      assert.equal(await page.locator('#package-target').inputValue(), 'chrome');
      assert.equal(await page.locator('#package-choice-file').getAttribute('href'), selectedHref);
    }
    const records = new Map(manifest.files.map(item => [item.path, item]));
    for (const target of [...new Set(manifest.downloads.map(item => item.platform))]) {
      for (const appearance of ['Clair', 'Obscur']) {
        const item = manifest.downloads.find(item => item.platform === target && (target === 'opera-gx' || item.name === appearance));
        const record = records.get(item.path);
        const readingBefore = await page.locator('html').getAttribute('data-theme');
        await page.locator('#package-target').selectOption(target);
        await page.locator('#package-appearance').selectOption(appearance);
        assert.equal(await page.locator('html').getAttribute('data-theme'), readingBefore);
        const result = page.locator('#package-choice-result');
        assert.ok(await result.isVisible());
        assert.equal(await page.locator('#package-choice-file').getAttribute('href'), 'downloads/' + item.path);
        assert.match(await page.locator('#package-choice-file').textContent(), delivery === 'portable' ? /^Open included / : /^Download /);
        assert.equal(await result.locator('.package-choice-path code').textContent(), 'downloads/' + item.path);
        const identity = await result.textContent();
        assert.ok(identity.includes('Package ' + item.version));
        assert.ok(identity.includes(record.sha256));
        assert.ok(identity.includes('Native acceptance pending'));
        assert.ok(identity.includes(await page.locator(`#${target}-downloads > p`).first().textContent()));
        if (target === 'opera-gx') assert.match(identity, /pairs Clair Light with Obscur Dark/);
        if (['equicord', 'vencord', 'betterdiscord'].includes(target)) assert.match(identity, /not Discord-endorsed/);
        assert.match(await page.locator('#package-choice-status').textContent(), new RegExp('Selected ' + appearance));
        const anchor = `guide-${target}-${appearance.toLowerCase()}`;
        assert.equal(await page.locator('#package-choice-guide').getAttribute('href'), '#' + anchor);
        await page.locator('#package-choice-guide').focus();
        await page.keyboard.press('Enter');
        await waitForGuideDestination(page, anchor);
        assert.ok(await page.locator('#' + anchor).isVisible());
        const geometry = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
        assert.ok(geometry.document <= geometry.width + 1, JSON.stringify({ textScale, ...geometry }));
        routes.push({ target, appearance, path: item.path, guide: anchor, sha256: record.sha256 });
      }
    }
    assert.equal(routes.length, 18);
    assert.equal(new Set(routes.map(route => route.path)).size, 13);
    assert.deepEqual(downloads, [], 'Selection and guide routing cannot start downloads');
    assert.deepEqual(requests, [], 'Selection and local guide routing cannot request resources');
    await page.locator('#package-target').selectOption('');
    assert.ok(await page.locator('#package-choice-result').isHidden());
    assert.equal(await page.locator('#package-choice-file, #package-choice-guide').count(), 0);
    assert.match(await page.locator('#package-choice-status').textContent(), /Choose a target/);
    assert.equal(await page.locator('#downloads .download-card').count(), 17);
    return { delivery, textScale, routes, nativeSelectKeyboard: 'passed', readingAppearanceIndependent: true,
      selectionRequests: requests, selectionDownloads: downloads, explicitTargetReset: 'passed' };
  } finally { page.off('request', onRequest); page.off('download', onDownload); }
}

test('explicit target and package appearance chooser preserves every route and static fallback', async () => {
  for (const width of [320, 390]) {
    for (const textScale of [100, 200]) {
      const { context, page, consoleErrors } = await pageFor({ viewport: { width, height: 844 } });
      try {
        if (textScale === 200) await page.evaluate(() => document.documentElement.style.fontSize = '200%');
        const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
        const routing = await checkPackageChooser(page, manifest, { delivery: 'public', textScale });
        assert.deepEqual(consoleErrors, []);
        results.scenarios.push({ name: 'explicit public target/package-appearance chooser', status: 'passed', width, ...routing });
      } finally { await context.close(); }
    }
  }
  const { context, page, consoleErrors } = await pageFor({ viewport: { width: 390, height: 844 } });
  try {
    const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
    for (const [target, appearance] of [['chrome', 'Clair'], ['equicord', 'Obscur']]) {
      await page.locator('#package-target').selectOption(target);
      await page.locator('#package-appearance').selectOption(appearance);
      const item = manifest.downloads.find(item => item.platform === target && item.name === appearance);
      await page.locator('#package-choice-file').focus();
      const [download] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
      assert.equal(await download.failure(), null);
      const chunks = [];
      for await (const chunk of await download.createReadStream()) chunks.push(chunk);
      const record = manifest.files.find(record => record.path === item.path);
      assert.equal(crypto.createHash('sha256').update(Buffer.concat(chunks)).digest('hex'), record.sha256);
      const anchor = `guide-${target}-${appearance.toLowerCase()}`;
      await page.locator('#package-choice-guide').focus();
      await page.keyboard.press('Enter');
      await waitForGuideDestination(page, anchor);
    }
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'chooser public archive and CSS downloads with keyboard guide return', status: 'passed', choices: 2 });
  } finally { await context.close(); }
  const fallback = await pageFor({ javaScriptEnabled: false, viewport: { width: 320, height: 844 } });
  try {
    assert.ok(await fallback.page.locator('#package-chooser').isHidden());
    assert.ok(await fallback.page.locator('#local-package-checker').isHidden());
    assert.equal(await fallback.page.locator('#downloads .download-card').count(), 17);
    assert.equal(await fallback.page.locator('#downloads .guide-link').count(), 18);
    await fallback.page.locator('#edge-clair .guide-link').focus();
    await fallback.page.keyboard.press('Enter');
    await waitForGuideDestination(fallback.page, 'guide-edge-clair');
    assert.deepEqual(fallback.consoleErrors, []);
    results.scenarios.push({ name: 'chooser progressive enhancement keeps no-script catalog', status: 'passed', width: 320 });
  } finally { await fallback.context.close(); }
});

test('guide destination wait admits delayed navigation and focus without an immediate-read assumption', async () => {
  const { context, page } = await pageFor();
  try {
    await page.setContent('<a id="trigger" href="#destination">Guide</a><section id="destination" tabindex="-1">Destination</section>');
    // Hold the fixture transition behind explicit releases, not a timer.
    await page.locator('#trigger').evaluate(node => node.addEventListener('click', event => event.preventDefault()));
    await page.locator('#trigger').focus();
    await page.keyboard.press('Enter');
    assert.throws(() => assert.equal(new URL(page.url()).hash, '#destination'), { code: 'ERR_ASSERTION' });
    let settled = false;
    const destination = waitForGuideDestination(page, 'destination').then(
      () => { settled = true; return { error: null }; },
      error => ({ error }),
    );
    await page.evaluate(() => history.pushState(null, '', '#destination'));
    await page.waitForURL(url => url.hash === '#destination', { timeout: 2000, waitUntil: 'commit' });
    assert.equal(await page.evaluate(() => document.activeElement.id), 'trigger');
    assert.equal(settled, false, 'Correct fragment without destination focus must remain pending');
    await page.locator('#destination').focus();
    const outcome = await destination;
    if (outcome.error) throw outcome.error;
    assert.equal(new URL(page.url()).hash, '#destination');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'destination');
  } finally { await context.close(); }
});

test('guide destination wait rejects absent navigation, a wrong fragment and wrong focus', async () => {
  for (const scenario of ['absent navigation', 'wrong fragment', 'wrong focus']) {
    const { context, page } = await pageFor();
    try {
      await page.setContent('<a id="trigger" href="#destination">Guide</a><section id="destination" tabindex="-1">Destination</section>');
      await page.locator('#trigger').focus();
      if (scenario === 'wrong fragment') {
        await page.evaluate(() => history.pushState(null, '', '#other'));
        await page.locator('#destination').focus();
      } else if (scenario === 'wrong focus') {
        await page.evaluate(() => history.pushState(null, '', '#destination'));
      }
      await assert.rejects(waitForGuideDestination(page, 'destination', 250), { name: 'TimeoutError' }, scenario);
      assert.equal(await page.evaluate(() => document.activeElement.id), scenario === 'wrong fragment' ? 'destination' : 'trigger');
    } finally { await context.close(); }
  }
});

test('relocated local guides cover every appearance by keyboard without external network or script', async () => {
  for (const javaScriptEnabled of [true, false]) {
    for (const width of [320, 390]) {
      const { context, page, network, consoleErrors } = await pageFor({ javaScriptEnabled, viewport: { width, height: 844 } });
      try {
        const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
        const records = new Map(manifest.files.map(item => [item.path, item]));
        const links = page.locator('#downloads .guide-link');
        assert.equal(await links.count(), 18, 'Two appearance links for the one paired Opera GX package');
        const appearances = javaScriptEnabled ? ['Obscur', 'Clair'] : ['Obscur'];
        for (const appearance of appearances) {
          if (javaScriptEnabled) {
            await page.getByRole('button', { name: appearance, exact: true }).focus();
            await page.keyboard.press('Enter');
            assert.equal(await page.locator('html').getAttribute('data-theme'), appearance);
          }
          for (const item of manifest.downloads) {
            const names = item.platform === 'opera-gx' ? ['Clair', 'Obscur'] : [item.name];
            const card = page.locator(`#${item.platform}-${item.platform === 'opera-gx' ? 'paired' : item.name.toLowerCase()}`);
            await card.locator('a[download]').focus();
            for (const name of names) {
              // Tab moves from the exact download to its locally bundled guide.
              await page.keyboard.press('Tab');
              const anchor = `guide-${item.platform}-${name.toLowerCase()}`;
              assert.equal(await page.evaluate(() => document.activeElement.getAttribute('href')), '#' + anchor);
              await page.keyboard.press('Enter');
              await waitForGuideDestination(page, anchor);
              assert.equal(new URL(page.url()).hash, '#' + anchor);
              const packageSection = page.locator('#' + anchor);
              assert.ok(await packageSection.isVisible());
              assert.equal(await page.evaluate(() => document.activeElement.id), anchor);
              assert.equal(await packageSection.locator('a[download]').getAttribute('href'), 'downloads/' + item.path);
              assert.ok((await packageSection.textContent()).includes('Package ' + item.version));
              assert.ok((await packageSection.textContent()).includes(records.get(item.path).sha256));
              const guide = page.locator('#guide-' + item.platform);
              for (const heading of ['Prerequisites and status', 'Install', 'Switch', 'Remove and restore', 'Fonts', 'Troubleshooting']) {
                assert.equal(await guide.getByRole('heading', { name: heading, exact: true }).count(), 1);
              }
              const bounds = await guide.evaluate(node => ({ left: node.getBoundingClientRect().left, right: node.getBoundingClientRect().right, width: innerWidth }));
              assert.ok(bounds.left >= -1 && bounds.right <= bounds.width + 1, JSON.stringify(bounds));
              // Resume from this card for the second appearance of the paired file.
              await card.locator(`a.guide-link[href="#${anchor}"]`).focus();
            }
          }
          const geometry = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
          assert.ok(geometry.document <= geometry.width + 1, JSON.stringify(geometry));
        }
        for (const client of ['vencord', 'betterdiscord']) {
          const fontLink = page.locator(`#guide-${client} a[href="#guide-client-fonts"]`);
          await fontLink.focus();
          await page.keyboard.press('Enter');
          await waitForGuideDestination(page, 'guide-client-fonts');
          assert.equal(new URL(page.url()).hash, '#guide-client-fonts');
          assert.equal(await page.evaluate(() => document.activeElement.id), 'guide-client-fonts');
          assert.match(await page.locator('#guide-client-fonts').textContent(), /system sans-serif fallbacks/);
        }
        assert.ok(network.every(url => url.startsWith(origin + '/')), 'Essential guidance cannot require external requests');
        assert.deepEqual(consoleErrors, []);
        assert.deepEqual(failures, []);
        results.scenarios.push({ name: 'relocated complete local target/appearance guides', status: 'passed', width, javaScriptEnabled, pageAppearances: appearances, guideAppearances: 18, externalNetwork: 'blocked', nativeAppsVerified: false });
      } finally { await context.close(); }
    }
  }
});

test('portable kit downloads, extracts and relocates into a complete offline file page', { timeout: 90000 }, async () => {
  const archiveName = 'Clair-Obscur-portable-preview.zip';
  const archivePath = path.join(temp, archiveName);
  const checksumPath = path.join(temp, 'portable-SHA256SUMS');
  const extracted = path.join(temp, 'downloaded-kit');
  const relocated = path.join(temp, 'moved-kit', 'preview');
  const { context, page } = await pageFor({ viewport: { width: 390, height: 844 } });
  let publicManifest;
  const downloadNames = {};
  try {
    publicManifest = await (await context.request.get(origin + '/site-manifest.json')).json();
    for (const [selector, destination] of [['#portable-preview', archivePath], ['#portable-checksums', checksumPath]]) {
      const [download] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.locator(selector).click()]);
      assert.equal(await download.failure(), null);
      const suggested = download.suggestedFilename();
      // Chrome may add .txt to an extensionless text/plain checksum response.
      const acceptedNames = selector === '#portable-checksums'
        ? ['portable-SHA256SUMS', 'portable-SHA256SUMS.txt'] : [archiveName];
      assert.ok(acceptedNames.includes(suggested), suggested);
      downloadNames[selector] = suggested;
      await download.saveAs(destination);
      assert.equal(page.url(), origin + '/');
    }
  } finally { await context.close(); }
  const archiveBytes = await readFile(archivePath);
  const checksum = await readFile(checksumPath, 'utf8');
  const digest = crypto.createHash('sha256').update(archiveBytes).digest('hex');
  assert.equal(checksum, `${digest}  ${archiveName}\n`);
  if (evidence) {
    await writeFile(path.join(evidence, archiveName), archiveBytes);
    await writeFile(path.join(evidence, 'portable-SHA256SUMS'), checksum);
  }
  assert.deepEqual(publicManifest.distribution.portable_kit, {
    archive: archiveName, checksums: 'portable-SHA256SUMS', sha256: digest, bytes: archiveBytes.length,
  });
  // Consume only the actual clicked download. Check ownership and hashes
  // before extracting, then move that complete directory before opening it.
  run(['-c', [
    'import hashlib,json,pathlib,stat,sys,zipfile',
    'archive_path,output=map(pathlib.Path,sys.argv[1:])',
    'with zipfile.ZipFile(archive_path) as archive:',
    ' names=archive.namelist()',
    ' assert names==sorted(set(names)) and archive.testzip() is None',
    ' for info in archive.infolist():',
    '  name=pathlib.PurePosixPath(info.filename)',
    '  assert not name.is_absolute() and ".." not in name.parts and "\\\\" not in info.filename',
    '  assert stat.S_ISREG(info.external_attr >> 16)',
    ' manifest=json.loads(archive.read("site-manifest.json"))',
    ' assert set(manifest["files"])==set(names)-{"site-manifest.json"}',
    ' assert "Clair-Obscur-portable-preview.zip" not in names and "portable-SHA256SUMS" not in names',
    ' for name,digest in manifest["files"].items():',
    '  assert hashlib.sha256(archive.read(name)).hexdigest()==digest',
    ' archive.extractall(output)',
  ].join('\n'), archivePath, extracted]);
  await mkdir(path.dirname(relocated));
  await rename(extracted, relocated);
  const inner = JSON.parse(await readFile(path.join(relocated, 'site-manifest.json'), 'utf8'));
  const packages = JSON.parse(await readFile(path.join(relocated, 'downloads', 'artifact-manifest.json'), 'utf8'));
  const records = new Map(packages.files.map(item => [item.path, item]));
  assert.deepEqual(inner.source, publicManifest.source);
  assert.deepEqual(inner.release, publicManifest.release);
  assert.deepEqual(inner.distribution, { kind: 'portable-kit' });
  assert.equal(packages.downloads.length, 17);
  assert.equal(new Set(packages.downloads.map(item => item.path)).size, 13);
  const requests = [], errors = [], journeys = [], packageJourneys = [], chooserJourneys = [], identificationJourneys = [];
  const includedPayloads = packages.downloads.filter((item, index, items) => items.findIndex(choice => choice.path === item.path) === index)
    .map(item => ({ item, file: path.join(relocated, 'downloads', ...item.path.split('/')) }));
  let closedContexts = 0;
  async function filePage(options) {
    const localContext = await browser.newContext({ serviceWorkers: 'block', ...options });
    try {
      const localPage = await localContext.newPage();
      localPage.on('request', request => requests.push(request.url()));
      localPage.on('pageerror', error => errors.push(String(error)));
      localPage.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      await localContext.route('**/*', route => {
        if (new URL(route.request().url()).protocol !== 'file:') return route.abort();
        return route.continue();
      });
      await localPage.goto(pathToFileURL(path.join(relocated, 'index.html')).href);
      await localPage.evaluate(() => document.fonts.ready);
      return { localContext, localPage };
    } catch (error) { await localContext.close(); closedContexts++; throw error; }
  }
  for (const javaScriptEnabled of [true, false]) {
    for (const width of [320, 390]) {
      const { localContext, localPage } = await filePage({ javaScriptEnabled, viewport: { width, height: 844 } });
      try {
        assert.match(await localPage.locator('#portable-delivery').textContent(), /extracted portable preview/);
        assert.equal(await localPage.locator('#portable-preview, #portable-checksums').count(), 0);
        assert.equal(await localPage.locator('#downloads .download-card').count(), 17);
        if (javaScriptEnabled) {
          chooserJourneys.push({ width, ...await checkPackageChooser(localPage, packages, { delivery: 'portable' }) });
          for (const textScale of [100, 200]) {
            await localPage.evaluate(scale => document.documentElement.style.fontSize = scale + '%', textScale);
            identificationJourneys.push({ width, ...await checkLocalPackageIdentification(localPage, packages, includedPayloads,
              { delivery: 'portable', textScale }) });
          }
          await localPage.evaluate(() => document.documentElement.style.fontSize = '100%');
        } else {
          assert.ok(await localPage.locator('#package-chooser').isHidden());
          assert.ok(await localPage.locator('#local-package-checker').isHidden());
        }
        for (const [appearance, background] of [['Obscur', 'rgb(9, 9, 9)'], ['Clair', 'rgb(248, 247, 243)']]) {
          assert.equal(await localPage.locator(`[data-palette="${appearance}"]`).evaluate(node => getComputedStyle(node).backgroundColor), background);
          if (javaScriptEnabled) {
            await localPage.getByRole('button', { name: appearance, exact: true }).focus();
            await localPage.keyboard.press('Enter');
            assert.equal(await localPage.locator('html').getAttribute('data-theme'), appearance);
          }
        }
        if (javaScriptEnabled) {
          await localPage.locator('#sample-button').focus();
          await localPage.keyboard.press('Enter');
          assert.match(await localPage.locator('#control-status').textContent(), /Control activated/);
        }
        let guideAppearances = 0;
        for (const item of packages.downloads) {
          const card = localPage.locator(`#${item.platform}-${item.platform === 'opera-gx' ? 'paired' : item.name.toLowerCase()}`);
          await card.locator('a[download]').focus();
          for (const name of item.platform === 'opera-gx' ? ['Clair', 'Obscur'] : [item.name]) {
            const anchor = `guide-${item.platform}-${name.toLowerCase()}`;
            await localPage.keyboard.press('Tab');
            assert.equal(await localPage.evaluate(() => document.activeElement.getAttribute('href')), '#' + anchor);
            await localPage.keyboard.press('Enter');
            await waitForGuideDestination(localPage, anchor);
            const section = localPage.locator('#' + anchor);
            assert.ok(await section.isVisible());
            assert.ok((await section.textContent()).includes(records.get(item.path).sha256));
            assert.equal(await section.locator('.local-package-path code').textContent(), 'downloads/' + item.path);
            const guide = localPage.locator('#guide-' + item.platform);
            for (const heading of ['Prerequisites and status', 'Install', 'Switch', 'Remove and restore', 'Fonts', 'Troubleshooting']) {
              assert.equal(await guide.getByRole('heading', { name: heading, exact: true }).count(), 1);
            }
            await card.locator(`a.guide-link[href="#${anchor}"]`).focus();
            guideAppearances++;
          }
        }
        assert.equal(guideAppearances, 18);
        const geometry = await localPage.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
        assert.ok(geometry.document <= geometry.width + 1, JSON.stringify(geometry));
        journeys.push({ javaScriptEnabled, width, guideAppearances, scriptControls: javaScriptEnabled ? 'passed' : 'not applicable' });
      } finally { await localContext.close(); closedContexts++; }
    }
    // Preserve deliberate palette journeys below Chromium's download burst
    // threshold. Use every included choice in both modes. CSS opens as local
    // text in Chrome, while these archive types produce actual downloads.
    for (const name of ['Clair', 'Obscur', 'Clair and Obscur']) {
      const { localContext, localPage } = await filePage({ javaScriptEnabled, viewport: { width: 390, height: 844 } });
      try {
        for (const item of packages.downloads.filter(item => item.name === name)) {
          const link = localPage.locator(`#${item.platform}-downloads a[download][href="downloads/${item.path}"]`);
          assert.match(await link.textContent(), /^Open included /);
          const included = await readFile(path.join(relocated, 'downloads', ...item.path.split('/')));
          const expected = records.get(item.path);
          assert.equal(included.length, expected.bytes);
          assert.equal(crypto.createHash('sha256').update(included).digest('hex'), expected.sha256);
          await link.focus();
          let method, matchingGuide = null;
          try {
            if (item.path.endsWith('.css')) {
              const localUrl = pathToFileURL(path.join(relocated, 'downloads', ...item.path.split('/'))).href;
              await Promise.all([localPage.waitForURL(localUrl, { timeout: 5000 }), localPage.keyboard.press('Enter')]);
              assert.equal(await localPage.locator('pre').textContent(), included.toString('utf8'));
              await localPage.goBack();
              assert.equal(await localPage.locator('#portable-delivery').count(), 1);
              matchingGuide = `guide-${item.platform}-${item.name.toLowerCase()}`;
              await localPage.locator(`#${item.platform}-${item.name.toLowerCase()} a.guide-link[href="#${matchingGuide}"]`).focus();
              await localPage.keyboard.press('Enter');
              await waitForGuideDestination(localPage, matchingGuide);
              assert.ok(await localPage.locator('#' + matchingGuide).isVisible());
              await localPage.goBack();
              await localPage.waitForURL(pathToFileURL(path.join(relocated, 'index.html')).href, { timeout: 2000, waitUntil: 'commit' });
              method = 'opened included CSS as exact text, returned and reached matching guide';
            } else {
              const [download] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
              assert.equal(await download.failure(), null);
              assert.equal(download.suggestedFilename(), path.basename(item.path));
              const chunks = [];
              for await (const chunk of await download.createReadStream()) chunks.push(chunk);
              assert.equal(crypto.createHash('sha256').update(Buffer.concat(chunks)).digest('hex'), expected.sha256);
              method = 'saved included archive';
            }
          }
          catch (error) {
            failures.push({ scenario: 'portable included package', javaScriptEnabled, platform: item.platform,
              path: item.path, pageUrl: localPage.url(), requests, errors, error: error.message });
            throw new Error(`Portable ${item.platform} ${item.name} journey failed (${item.path}): ${error.message}`, { cause: error });
          }
          assert.equal(localPage.url(), pathToFileURL(path.join(relocated, 'index.html')).href);
          packageJourneys.push({ javaScriptEnabled, platform: item.platform, path: item.path, sha256: expected.sha256, method, matchingGuide });
        }
      } finally { await localContext.close(); closedContexts++; }
    }
  }
  assert.equal(packageJourneys.length, 34);
  assert.equal(packageJourneys.filter(item => item.method === 'saved included archive').length, 22);
  assert.equal(packageJourneys.filter(item => item.method === 'opened included CSS as exact text, returned and reached matching guide').length, 12);
  const chosen = await filePage({ javaScriptEnabled: true, viewport: { width: 390, height: 844 } });
  try {
    for (const [target, appearance] of [['chrome', 'Obscur'], ['equicord', 'Clair']]) {
      await chosen.localPage.locator('#package-target').selectOption(target);
      await chosen.localPage.locator('#package-appearance').selectOption(appearance);
      const item = packages.downloads.find(item => item.platform === target && item.name === appearance);
      const included = await readFile(path.join(relocated, 'downloads', ...item.path.split('/')));
      await chosen.localPage.locator('#package-choice-file').focus();
      if (item.path.endsWith('.css')) {
        const fileUrl = pathToFileURL(path.join(relocated, 'downloads', ...item.path.split('/'))).href;
        await Promise.all([chosen.localPage.waitForURL(fileUrl, { timeout: 5000 }), chosen.localPage.keyboard.press('Enter')]);
        assert.equal(await chosen.localPage.locator('pre').textContent(), included.toString('utf8'));
        await chosen.localPage.goBack();
        await chosen.localPage.locator('#package-target').selectOption(target);
        await chosen.localPage.locator('#package-appearance').selectOption(appearance);
      } else {
        const [download] = await Promise.all([chosen.localPage.waitForEvent('download', { timeout: 5000 }), chosen.localPage.keyboard.press('Enter')]);
        assert.equal(await download.failure(), null);
        const chunks = [];
        for await (const chunk of await download.createReadStream()) chunks.push(chunk);
        assert.deepEqual(Buffer.concat(chunks), included);
      }
      const anchor = `guide-${target}-${appearance.toLowerCase()}`;
      await chosen.localPage.locator('#package-choice-guide').focus();
      await chosen.localPage.keyboard.press('Enter');
      await waitForGuideDestination(chosen.localPage, anchor);
      chooserJourneys.push({ target, appearance, path: item.path, method: item.path.endsWith('.css') ? 'opened included CSS and returned to matching guide' : 'saved included archive and reached matching guide' });
    }
  } finally { await chosen.localContext.close(); closedContexts++; }
  assert.ok(requests.every(url => new URL(url).protocol === 'file:'), 'The extracted consumer must not request network resources');
  assert.deepEqual(errors, []);
  if (evidence) {
    await writeFile(path.join(evidence, 'portable-site-manifest.json'), JSON.stringify(inner, null, 2) + '\n');
  }
  results.scenarios.push({ name: 'actual downloaded and relocated offline portable kit', status: 'passed',
    archive: archiveName, sha256: digest, bytes: archiveBytes.length, downloadNames, source: inner.source,
    protocol: 'file:', network: 'all external requests blocked', requests, errors, journeys, packageJourneys, chooserJourneys, identificationJourneys,
    closedContexts, nativeAppsVerified: false });
});

test('new desktop browser choices remain distinct and readable on a phone', async () => {
  const { context, page, consoleErrors } = await pageFor({ viewport: { width: 390, height: 844 }, hasTouch: true });
  try {
    for (const [platform, label, count] of [['brave', 'Brave', 2], ['vivaldi', 'Vivaldi', 2], ['opera-gx', 'Opera GX', 1]]) {
      await page.getByRole('link', { name: label, exact: true }).click();
      assert.equal(new URL(page.url()).hash, `#${platform}-downloads`);
      const group = page.locator(`#${platform}-downloads`);
      assert.ok(await group.isVisible());
      assert.equal(await group.locator('.download-card').count(), count);
      assert.equal(await group.locator('a[download]').count(), count);
      assert.match(await group.textContent(), /unverified|No Brave installation/);
    }
    assert.match(await page.locator('#opera-gx-downloads').textContent(), /One package pairs Clair Light with Obscur Dark/);
    assert.match(await page.locator('#vivaldi-downloads').textContent(), /5\.0 or later/);
    const geometry = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
    assert.ok(geometry.document <= geometry.width + 1, JSON.stringify(geometry));
    const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
    for (const name of ['Clair', 'Obscur']) {
      const chrome = manifest.downloads.find(item => item.name === name && item.platform === 'chrome');
      const brave = manifest.downloads.find(item => item.name === name && item.platform === 'brave');
      assert.equal(brave.path, chrome.path);
      assert.equal(brave.native_acceptance, 'unverified');
    }
    assert.deepEqual(consoleErrors, []);
    assert.deepEqual(failures, []);
    results.scenarios.push({ name: 'phone navigation to Brave, Vivaldi and paired Opera GX desktop candidates', status: 'passed', nativeAppsVerified: false });
  } finally { await context.close(); }
});

test('Equicord CSS consumes host variables only on its matching native base', async () => {
  const { context, page } = await pageFor();
  try {
    const palettes = JSON.parse(await readFile(path.join(root, 'tokens.json'), 'utf8')).themes;
    const color = hex => `rgb(${[1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16)).join(', ')})`;
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
        #primary:hover { background:var(--control-primary-background-hover); color:var(--control-primary-text-hover); }
        #secondary { background:var(--control-secondary-background-default); color:var(--control-secondary-text-default); }
        #secondary:hover { background:var(--control-secondary-background-hover); color:var(--control-secondary-text-hover); }
        #mention { display:block; background:var(--mention-background); color:var(--mention-foreground); }
        #mention:hover { background:var(--background-mentioned-hover); }
      </style></head><body><p id="message-content-fixture">Regular <strong>bold</strong> <em>italic</em> <code>code</code></p>
      <button id="primary" class="vc-btn-base vc-btn-medium">Host control</button><button id="secondary">Secondary control</button>
      <a id="mention" href="#fixture">Mention</a>
      <span class="switch">Off</span><span class="switch checked">On<span class="vc-switch-indicator">Indicator</span></span></body></html>`);
      await page.addStyleTag({ content: css });
      await page.evaluate(() => document.fonts.ready);
      await page.mouse.move(1270, 890);
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
      const colors = async selector => page.locator(selector).evaluate(node => ({
        background: getComputedStyle(node).backgroundColor, text: getComputedStyle(node).color,
      }));
      const expected = palettes[name];
      assert.deepEqual(await colors('#primary'), { background: color(expected.accent), text: color(expected.on_accent) });
      assert.deepEqual(await colors('#secondary'), { background: color(expected.control), text: color(expected.text) });
      assert.deepEqual(await colors('#mention'), { background: color(expected.selected), text: color(expected.accent) });
      await page.locator('#primary').hover();
      assert.deepEqual(await colors('#primary'), { background: color(expected.accent), text: color(expected.on_accent) });
      await page.locator('#secondary').hover();
      assert.deepEqual(await colors('#secondary'), { background: color(expected.hover), text: color(expected.text) });
      await page.locator('#mention').hover();
      assert.deepEqual(await colors('#mention'), { background: color(expected.hover), text: color(expected.accent) });
      await page.locator('#primary').focus();
      await page.keyboard.press('Tab');
      assert.equal(await page.locator('#secondary').evaluate(node => node.matches(':focus-visible')), true);
      const focus = await page.locator('#secondary').evaluate(node => ({
        width: getComputedStyle(node).outlineWidth, style: getComputedStyle(node).outlineStyle,
        offset: getComputedStyle(node).outlineOffset, color: getComputedStyle(node).outlineColor,
      }));
      assert.deepEqual(focus, { width: '2px', style: 'solid', offset: '2px', color: color(expected.focus) });
      await page.locator('.checked').evaluate(node => node.classList.add('vc-switch-focusVisible'));
      assert.equal(await page.locator('.vc-switch-indicator').evaluate(node => getComputedStyle(node).outlineColor), color(expected.focus));
      assert.equal(await page.locator('.vc-switch-indicator').evaluate(node => getComputedStyle(node).outlineWidth), '2px');
      await page.evaluate(value => document.documentElement.className = `theme-${value}`, mode === 'dark' ? 'light' : 'dark');
      assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(171, 205, 239)');
      results.scenarios.push({ name: `${name} Equicord host-contract fixture`, status: 'passed', rendered, focus,
        pairedStates: 'primary, secondary and mention default/hover; separate keyboard and switch-class focus',
        oppositeBase: 'retains fixture native baseline', nativeAppVerified: false });
    }
  } finally { await context.close(); }
});

test('client adapters preserve switch geometry and pair their real selector contracts', async () => {
  const { context, page } = await pageFor({ reducedMotion: 'reduce' });
  try {
    const palettes = JSON.parse(await readFile(path.join(root, 'tokens.json'), 'utf8')).themes;
    const color = hex => `rgb(${[1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16)).join(', ')})`;
    for (const [client, label] of [['vencord', 'Vencord'], ['betterdiscord', 'BetterDiscord']]) {
      for (const [name, mode] of [['Clair', 'light'], ['Obscur', 'dark']]) {
        const css = await (await context.request.get(`${origin}/downloads/${client}/${name}-${label}.theme.css`)).text();
        // Original synthetic model of the inspected client selectors. It does
        // not contain Discord content or establish a loaded client result.
        const vc = client === 'vencord';
        const markup = vc ? `
          <button id="brand" class="vc-btn-base vc-btn-primary">Brand</button>
          <div id="off" class="vc-switch-container"><svg class="vc-switch-slider" style="transform:translateX(-2px)"><rect fill="white"/><path/></svg></div>
          <div id="on" class="vc-switch-container vc-switch-checked"><svg class="vc-switch-slider" style="transform:translateX(18px)"><rect fill="white"/><path/></svg></div>
          <div id="disabled" class="vc-switch-container vc-switch-disabled">Disabled</div>` : `
          <button id="brand" class="bd-button bd-button-filled bd-button-color-brand">Brand</button>
          <label class="bd-switch"><input id="off-input" type="checkbox"><span id="off" class="bd-switch-body"><svg><rect class="bd-switch-handle" fill="white"/><path/></svg></span></label>
          <label class="bd-switch"><input id="on-input" type="checkbox" checked><span id="on" class="bd-switch-body"><svg style="transform:translateX(18px)"><rect class="bd-switch-handle" fill="white"/><path/></svg></span></label>
          <label id="disabled" class="bd-switch bd-switch-disabled"><input type="checkbox" disabled><span class="bd-switch-body">Disabled</span></label>`;
        await page.setContent(`<html class="theme-${mode}"><head><style>
          body { background:var(--background-primary,#abcdef); color:var(--text-normal,#123456); }
          #brand { width:80px; height:28px; }
          .vc-btn-primary { background:var(--control-primary-background-default,#445566); color:var(--control-primary-text-default,white); }
          .vc-switch-container { width:44px; height:28px; border:1px solid transparent; background:#72767d; transition:background-color 120ms; }
          .vc-switch-checked { background:#445566; }
          .vc-switch-disabled { opacity:.3; }
          .vc-switch-slider { width:28px; height:28px; transition:transform 120ms; }
          .vc-switch-slider path { fill:#72767d; }
          .bd-button-color-brand { background:var(--bd-brand,#445566); color:white; transition:background-color 120ms; }
          .bd-switch { display:block; position:relative; width:40px; height:24px; }
          .bd-switch input { opacity:0; position:absolute; width:100%; height:100%; margin:0; }
          .bd-switch-body { --switch-color:#72767d; display:block; width:40px; height:24px; background:var(--switch-color); transition:background-color 120ms; }
          .bd-switch input:checked + .bd-switch-body { --switch-color:var(--bd-brand,#445566); }
          .bd-switch-body svg { width:24px; height:24px; }
          .bd-switch-body path { fill:var(--switch-color); }
          .bd-switch-disabled { opacity:.5; filter:grayscale(100%); }
          #critical { background:#be1f1f; color:white; }
        </style></head><body>${markup}<button id="critical" class="bd-button bd-button-filled bd-button-color-red">Critical</button></body></html>`);
        const geometry = () => page.evaluate(() => Object.fromEntries(['brand', 'off', 'on', 'disabled'].map(id => {
          const node = document.getElementById(id), style = getComputedStyle(node), svg = node.querySelector('svg');
          return [id, { width:style.width, height:style.height, position:style.position,
            display:style.display, opacity:style.opacity, filter:style.filter,
            transform:svg && getComputedStyle(svg).transform }];
        })));
        const beforeGeometry = await geometry();
        const beforeCritical = await page.locator('#critical').evaluate(node => ({ background:getComputedStyle(node).backgroundColor, text:getComputedStyle(node).color }));
        await page.addStyleTag({ content: css });
        await page.mouse.move(1270, 890);
        const expected = palettes[name];
        const state = await page.evaluate(vcModel => {
          const pair = id => ({ background:getComputedStyle(document.getElementById(id)).backgroundColor, text:getComputedStyle(document.getElementById(id)).color });
          return { brand:pair('brand'), critical:pair('critical'), off:pair('off').background,
            on:pair('on').background,
            offHandle:getComputedStyle(document.querySelector(vcModel ? '#off rect' : '#off .bd-switch-handle')).fill,
            onHandle:getComputedStyle(document.querySelector(vcModel ? '#on rect' : '#on .bd-switch-handle')).fill,
            offMark:getComputedStyle(document.querySelector('#off path')).fill,
            onMark:getComputedStyle(document.querySelector('#on path')).fill,
            reducedTransition:getComputedStyle(document.getElementById('on')).transitionDuration };
        }, vc);
        assert.deepEqual(await geometry(), beforeGeometry);
        assert.deepEqual(state.critical, beforeCritical);
        assert.deepEqual(state.brand, { background:color(expected.accent), text:color(expected.on_accent) });
        assert.equal(state.off, color(expected.control)); assert.equal(state.on, color(expected.accent));
        assert.equal(state.offHandle, color(expected.text)); assert.equal(state.onHandle, color(expected.on_accent));
        assert.equal(state.offMark, color(expected.control)); assert.equal(state.onMark, color(expected.accent));
        assert.equal(state.reducedTransition, '0s');
        await page.locator('#brand').hover();
        assert.deepEqual(await page.locator('#brand').evaluate(node => ({ background:getComputedStyle(node).backgroundColor, text:getComputedStyle(node).color })), state.brand);
        if (vc) await page.locator('#on').evaluate(node => node.classList.add('vc-switch-focusVisible'));
        else { await page.locator('#brand').focus(); await page.keyboard.press('Tab'); await page.keyboard.press('Tab'); }
        const focus = await page.locator('#on').evaluate(node => ({ width:getComputedStyle(node).outlineWidth, color:getComputedStyle(node).outlineColor }));
        assert.deepEqual(focus, { width:'2px', color:color(expected.focus) });
        await page.evaluate(value => document.documentElement.className = `theme-${value}`, mode === 'dark' ? 'light' : 'dark');
        assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(171, 205, 239)');
        results.scenarios.push({ name:`${name} ${label} component-contract fixture`, status:'passed', state, focus,
          geometry:'unchanged width, height, display, position, transform and disabled behavior', nativeAppVerified:false });
      }
    }
  } finally { await context.close(); }
});
