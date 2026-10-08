import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { chromium, webkit } from 'playwright';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, writeFile, mkdir, rename, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
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
  const result = spawnSync(python[0], [...python.slice(1), ...args], { cwd: root, encoding: 'utf8', windowsHide: true });
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
          assert.equal(new URL(page.url()).hash, '#guide-client-fonts');
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
