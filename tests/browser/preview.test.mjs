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
const generalIconFunctions = [
  'phone', 'messages', 'contacts', 'camera', 'gallery', 'settings', 'calendar', 'clock',
  'files', 'notes', 'mail', 'browser', 'maps', 'music', 'video', 'store', 'wallet',
  'calculator', 'weather', 'health', 'fitness', 'voice-recorder', 'home', 'search',
];
const namedIconApps = [
  ['google-chrome', 'Google Chrome', 'com.android.chrome'], ['youtube', 'YouTube', 'com.google.android.youtube'],
  ['google-maps', 'Google Maps', 'com.google.android.apps.maps'], ['gmail', 'Gmail', 'com.google.android.gm'],
  ['google-photos', 'Google Photos', 'com.google.android.apps.photos'], ['google-messages', 'Google Messages', 'com.google.android.apps.messaging'],
  ['google-calendar', 'Google Calendar', 'com.google.android.calendar'], ['google-drive', 'Google Drive', 'com.google.android.apps.docs'],
  ['samsung-browser', 'Samsung Browser', 'com.sec.android.app.sbrowser'], ['samsung-notes', 'Samsung Notes', 'com.samsung.android.app.notes'],
  ['samsung-health', 'Samsung Health', 'com.sec.android.app.shealth'], ['garmin-connect', 'Garmin Connect', 'com.garmin.android.apps.connectmobile'],
  ['whatsapp', 'WhatsApp', 'com.whatsapp'], ['messenger', 'Messenger', 'com.facebook.orca'],
  ['instagram', 'Instagram', 'com.instagram.android'], ['facebook', 'Facebook', 'com.facebook.katana'],
  ['snapchat', 'Snapchat', 'com.snapchat.android'], ['tiktok', 'TikTok', 'com.zhiliaoapp.musically'],
  ['discord', 'Discord', 'com.discord'], ['reddit', 'Reddit', 'com.reddit.frontpage'],
  ['pinterest', 'Pinterest', 'com.pinterest'], ['telegram', 'Telegram', 'org.telegram.messenger'],
  ['spotify', 'Spotify', 'com.spotify.music'], ['netflix', 'Netflix', 'com.netflix.mediaclient'],
  ['amazon-shopping', 'Amazon Shopping', 'com.amazon.mShop.android.shopping'], ['walmart', 'Walmart', 'com.walmart.android'],
  ['temu', 'Temu', 'com.einnovation.temu'], ['uber', 'Uber', 'com.ubercab'], ['doordash', 'DoorDash', 'com.dd.doordash'],
  ['paypal', 'PayPal', 'com.paypal.android.p2pmobile'], ['outlook', 'Microsoft Outlook', 'com.microsoft.office.outlook'],
  ['chatgpt', 'ChatGPT', 'com.openai.chatgpt'], ['firefox', 'Firefox', 'org.mozilla.firefox'],
];
const iconFunctions = [...namedIconApps.map(row => row[0]), ...generalIconFunctions];
const iconManifestFunctions = [...generalIconFunctions, ...namedIconApps.map(row => row[0])];
const iconLabels = new Map([...generalIconFunctions.map(name => [name, name.replaceAll('-', ' ').replace(/\b[a-z]/g, letter => letter.toUpperCase())]),
  ...namedIconApps.map(([id, label]) => [id, label])]);
const iconArchive = 'icons/Clair-Obscur-SVG-Icons-0.3.0.zip';
const previousIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.2.0.zip';
const previousIconDigest = '6ae67a5aab7f4e0a50537bb6dcf3b383c5fc6e9e001d68db12a7413aaa376312';
const legacyIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.1.0.zip';
const legacyIconDigest = '040d7f472ca12d6cf115daaf2631b83477183dee42f0b91c6133e62322014e34';
const iconChecksums = digest => `${digest}  ${path.basename(iconArchive)}\n${previousIconDigest}  ${path.basename(previousIconArchive)}\n${legacyIconDigest}  ${path.basename(legacyIconArchive)}\n`;
const iconPaths = iconFunctions.flatMap(functionName => ['Clair', 'Obscur'].map(appearance => `icons/${appearance}/${functionName}.svg`));
const terminalFragment = 'Clair-Obscur-Windows-Terminal-0.1.0.json';
const terminalArchive = 'Clair-Obscur-Windows-Terminal-0.1.0.zip';
const terminalAnsi = [
  ['black', 'Black'], ['red', 'Red'], ['green', 'Green'], ['yellow', 'Yellow'],
  ['blue', 'Blue'], ['purple', 'Purple'], ['cyan', 'Cyan'], ['white', 'White'],
  ['brightBlack', 'Bright black'], ['brightRed', 'Bright red'], ['brightGreen', 'Bright green'], ['brightYellow', 'Bright yellow'],
  ['brightBlue', 'Bright blue'], ['brightPurple', 'Bright purple'], ['brightCyan', 'Bright cyan'], ['brightWhite', 'Bright white'],
];

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
      const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.zip': 'application/zip', '.xpi': 'application/x-xpinstall' };
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
      assert.deepEqual([...new Set(network)].sort(), [origin + '/', ...['tokens.css', 'preview.css', 'preview.js', ...iconPaths].map(file => origin + '/' + file)].sort(),
        'The page requests only its four original local assets and the 114 declared local SVGs');
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
      const card = page.locator(`.palette[data-palette="${name}"]`);
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

async function checkIconGallery(page) {
  assert.equal(await page.locator('#icons').getAttribute('aria-labelledby'), 'icons-heading');
  assert.equal(await page.locator('#icons-heading').textContent(), 'Matching app icons');
  assert.equal(await page.locator('#icons-app-heading').textContent(), 'Named apps');
  assert.equal(await page.locator('#icons-function-heading').textContent(), 'General functions');
  assert.equal(await page.locator('#icons [data-icon-kind="app"]').count(), 33);
  assert.equal(await page.locator('#icons [data-icon-kind="function"]').count(), 24);
  assert.equal(await page.locator('#icon-artwork-download').getAttribute('href'), iconArchive);
  assert.equal(await page.locator('#icon-artwork-previous-download').getAttribute('href'), previousIconArchive);
  assert.equal(await page.locator('#icon-artwork-legacy-download').getAttribute('href'), legacyIconArchive);
  assert.match(await page.locator('#icon-artwork-download').textContent(), /0\.3\.0/);
  assert.match(await page.locator('#icon-artwork-previous-download').textContent(), /preserved 0\.2\.0/);
  assert.match(await page.locator('#icon-artwork-legacy-download').textContent(), /original 0\.1\.0/);
  assert.equal(await page.locator('#icon-artwork-checksums').getAttribute('href'), 'icons/SVG-SHA256SUMS');
  const cards = await page.locator('#icons article.icon-card').evaluateAll(nodes => Promise.all(nodes.map(async card => {
    const box = card.getBoundingClientRect(), textErrors = [];
    const textNodes = [...card.querySelectorAll('h4, figcaption, p a, p code')];
    for (const node of textNodes) {
      const range = document.createRange(); range.selectNodeContents(node);
      const rects = [...range.getClientRects()].filter(rect => rect.width > 0 && rect.height > 0);
      if (!node.textContent.trim() || !rects.length) textErrors.push('text unavailable: ' + node.tagName);
      for (const rect of rects) {
        if (rect.left < box.left - 1 || rect.right > box.right + 1 || rect.left < -1 || rect.right > innerWidth + 1)
          textErrors.push('text outside card or viewport: ' + node.textContent);
      }
      for (let ancestor = node; ancestor; ancestor = ancestor.parentElement) {
        const style = getComputedStyle(ancestor), bounds = ancestor.getBoundingClientRect();
        if (style.display === 'none' || style.visibility !== 'visible' || Number(style.opacity) === 0)
          textErrors.push('text unavailable: ' + node.textContent);
        for (const rect of rects) {
          if (['hidden', 'clip'].includes(style.overflowX) && (rect.left < bounds.left - 1 || rect.right > bounds.right + 1))
            textErrors.push('text clipped horizontally: ' + node.textContent);
          if (['hidden', 'clip'].includes(style.overflowY) && (rect.top < bounds.top - 1 || rect.bottom > bounds.bottom + 1))
            textErrors.push('text clipped vertically: ' + node.textContent);
        }
      }
    }
    return {
    functionName: card.dataset.iconFunction, label: card.querySelector('h4')?.textContent, kind: card.dataset.iconKind,
    mapping: card.querySelector('p a')?.getAttribute('href'), packageId: card.querySelector('p code')?.textContent,
    textErrors, textNodes: textNodes.length, box: { left: box.left, right: box.right, width: box.width, height: box.height, viewport: innerWidth },
    pairs: card.querySelectorAll('.icon-pair').length,
    figures: await Promise.all([...card.querySelectorAll('.icon-pair figure')].map(async figure => {
      const node = figure.querySelector('img');
      if (!node) return { missingImage: true };
      let decode = true;
      try { await node.decode(); } catch { decode = false; }
      const box = node.getBoundingClientRect(), style = getComputedStyle(node);
      return { path: node.getAttribute('src'), alt: node.getAttribute('alt'), caption: figure.querySelector('figcaption')?.textContent,
        declaredWidth: node.getAttribute('width'), declaredHeight: node.getAttribute('height'),
        decode, naturalWidth: node.naturalWidth, naturalHeight: node.naturalHeight,
        width: box.width, height: box.height, left: box.left, right: box.right, viewport: innerWidth,
        display: style.display, visibility: style.visibility };
    })),
  }; })));
  assert.deepEqual(cards.map(card => card.functionName), iconFunctions);
  const decoded = [];
  for (const card of cards) {
    const functionName = card.functionName;
    const words = iconLabels.get(functionName);
    assert.equal(card.label, words);
    assert.ok(card.box.width > 0 && card.box.height > 0 && card.box.left >= -1 && card.box.right <= card.box.viewport + 1,
      JSON.stringify({ functionName, box: card.box }));
    assert.deepEqual(card.textErrors, [], functionName);
    const app = namedIconApps.find(row => row[0] === functionName);
    assert.equal(card.kind, app ? 'app' : 'function');
    if (app) {
      assert.equal(card.textNodes, 5, 'Named cards expose a heading, two captions, mapping link and package ID');
      assert.equal(card.mapping, `https://play.google.com/store/apps/details?id=${app[2]}`);
      assert.equal(card.packageId, app[2]);
    } else {
      assert.equal(card.textNodes, 3);
      assert.equal(card.mapping, undefined); assert.equal(card.packageId, undefined);
    }
    assert.equal(card.pairs, 1);
    assert.equal(card.figures.length, 2);
    for (const [index, appearance] of ['Clair', 'Obscur'].entries()) {
      const observation = card.figures[index];
      assert.equal(observation.caption, appearance);
      assert.equal(observation.path, `icons/${appearance}/${functionName}.svg`);
      assert.equal(observation.alt, `${appearance} ${words} icon`);
      assert.equal(observation.declaredWidth, '512');
      assert.equal(observation.declaredHeight, '512');
      assert.ok(observation.decode, `Icon not decoded: ${observation.path}`);
      assert.equal(observation.naturalWidth, 512); assert.equal(observation.naturalHeight, 512);
      assert.ok(observation.width > 0 && observation.height > 0, JSON.stringify(observation));
      assert.equal(observation.visibility, 'visible'); assert.notEqual(observation.display, 'none');
      assert.ok(observation.left >= -1 && observation.right <= observation.viewport + 1, JSON.stringify(observation));
      decoded.push(observation.path);
    }
  }
  assert.equal(await page.locator('#downloads .download-card').count(), 17);
  assert.equal(await page.locator('#downloads .guide-link').count(), 18);
  return decoded;
}

async function checkIconMappingKeyboard(page) {
  // Start at the last artwork download, then follow the real next Tab order
  // through every store link. No store request or phone installation is made.
  await page.locator('#icon-artwork-legacy-download').focus();
  for (const [id, , packageId] of namedIconApps) {
    await page.keyboard.press('Tab');
    const active = await page.evaluate(() => {
      const node = document.activeElement, box = node.getBoundingClientRect();
      return { id: node.closest('[data-icon-function]')?.dataset.iconFunction, href: node.getAttribute('href'),
        text: node.textContent, focused: node.matches(':focus'),
        left: box.left, right: box.right, top: box.top, bottom: box.bottom, width: innerWidth, height: innerHeight };
    });
    assert.equal(active.id, id); assert.equal(active.href, `https://play.google.com/store/apps/details?id=${packageId}`);
    assert.equal(active.text, 'Google Play listing'); assert.equal(active.focused, true);
    assert.ok(active.left >= -1 && active.right <= active.width + 1 && active.bottom > 0 && active.top < active.height,
      JSON.stringify(active));
  }
  return { keyboardReachable: namedIconApps.length, scope: 'Exact official href and actual Tab focus; store page and installation unexecuted' };
}

test('icon gallery decodes every current appearance at phone widths and enlarged fallback text', async () => {
  for (const scenario of [{ width: 390, enlarged: false }, { width: 320, enlarged: true }]) {
    const { context, page, consoleErrors } = await pageFor({ viewport: { width: scenario.width, height: 844 }, missingFont: scenario.enlarged });
    try {
      if (scenario.enlarged) await page.addStyleTag({ content: 'html { font-size: 200%; }' });
      for (const appearance of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name: appearance, exact: true }).click();
        assert.equal(await page.locator('html').getAttribute('data-theme'), appearance);
        const decoded = await checkIconGallery(page);
        assert.deepEqual(decoded, iconPaths);
        await checkIconMappingKeyboard(page);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        results.scenarios.push({ name: 'complete paired icon gallery', ...scenario, appearance,
          decoded, nativePhoneVerified: false, status: 'passed' });
      }
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
});

test('no-script keyboard navigation acquires current and both preserved icon ZIPs with exact checksums', async () => {
  const { context, page, consoleErrors } = await pageFor({ javaScriptEnabled: false, viewport: { width: 320, height: 844 },
    setup: async (context, page) => page.route('**/preview.css', async route => route.fulfill({ contentType: 'text/css',
      body: await readFile(path.join(site, 'preview.css'), 'utf8') + '\nhtml { font-size: 200%; }\n' + textSpacingOverride })) });
  try {
    await checkIconGallery(page);
    const spacingBaseline = await spacingContentBaseline(page);
    assert.equal(spacingBaseline.width, 320); assert.equal(spacingBaseline.rootFontSize, '32px');
    const spacingAdmission = await assertTextSpacing(page, spacingBaseline);
    let tabs = 0;
    while (await page.evaluate(() => document.activeElement?.id) !== 'icon-gallery-link' && tabs < 40) {
      await page.keyboard.press('Tab'); tabs++;
    }
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-gallery-link');
    await page.keyboard.press('Enter');
    await page.waitForURL(url => url.hash === '#icons');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-download');
    const [download] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await download.failure(), null);
    assert.equal(download.suggestedFilename(), path.basename(iconArchive));
    const archivePath = path.join(temp, 'keyboard-icons.zip');
    await download.saveAs(archivePath);
    const bytes = await readFile(archivePath);
    assert.deepEqual(bytes, await readFile(path.join(site, ...iconArchive.split('/'))));
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-checksums');
    const [checksumDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await checksumDownload.failure(), null);
    const chunks = []; for await (const chunk of await checksumDownload.createReadStream()) chunks.push(chunk);
    const digest = crypto.createHash('sha256').update(bytes).digest('hex');
    assert.equal(Buffer.concat(chunks).toString('utf8'), iconChecksums(digest));
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-previous-download');
    const [previousDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await previousDownload.failure(), null);
    assert.equal(previousDownload.suggestedFilename(), path.basename(previousIconArchive));
    const previousArchivePath = path.join(temp, 'keyboard-icons-previous.zip');
    await previousDownload.saveAs(previousArchivePath);
    const previousBytes = await readFile(previousArchivePath);
    assert.deepEqual(previousBytes, await readFile(path.join(site, ...previousIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(previousBytes).digest('hex'), previousIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-legacy-download');
    const [legacyDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await legacyDownload.failure(), null);
    assert.equal(legacyDownload.suggestedFilename(), path.basename(legacyIconArchive));
    const legacyArchivePath = path.join(temp, 'keyboard-icons-original.zip');
    await legacyDownload.saveAs(legacyArchivePath);
    const legacyBytes = await readFile(legacyArchivePath);
    assert.deepEqual(legacyBytes, await readFile(path.join(site, ...legacyIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(legacyBytes).digest('hex'), legacyIconDigest);
    run(['-c', [
      'import hashlib,json,pathlib,sys,zipfile',
      'archive_path,site=map(pathlib.Path,sys.argv[1:])',
      `functions=${JSON.stringify(iconManifestFunctions)}`,
      'expected={f"{appearance}/{function}.svg" for appearance in ("Clair","Obscur") for function in functions}',
      'with zipfile.ZipFile(archive_path) as archive:',
      ' assert len(archive.namelist())==116 and set(archive.namelist())==expected|{"manifest.json","LICENSE.txt"}',
      ' assert archive.testzip() is None',
      ' for name in expected|{"manifest.json","LICENSE.txt"}:',
      '  assert archive.read(name)==(site/"icons"/name).read_bytes()',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.3.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==114',
      ' assert [entry["id"] for entry in manifest["catalog"]]==functions',
      ' for record in manifest["files"]:',
      '  assert hashlib.sha256(archive.read(record["path"])).hexdigest()==record["sha256"]',
    ].join('\n'), archivePath, site]);
    run(['-c', [
      'import json,pathlib,sys,zipfile',
      `functions=${JSON.stringify(generalIconFunctions)}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==50',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.1.0" and manifest["stroke_width"]==12',
      ' assert manifest["functions"]==functions and len(manifest["files"])==48',
    ].join('\n'), legacyArchivePath]);
    run(['-c', [
      'import json,sys,zipfile',
      `functions=${JSON.stringify(generalIconFunctions)}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==50',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.2.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==48',
    ].join('\n'), previousArchivePath]);
    const mappingKeyboard = await checkIconMappingKeyboard(page);
    assert.equal(new URL(page.url()).hash, '#icons');
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'no-script icon artwork keyboard acquisition', status: 'passed', tabs,
      sha256: digest, previousSha256: previousIconDigest, legacySha256: legacyIconDigest,
      currentArchiveFiles: 116, preservedArchiveFiles: 50, nativePhoneVerified: false,
      width: 320, rootFontSize: '32px', spacingAdmission, mappingKeyboard,
      scope: 'Combined no-script, narrow, enlarged and spacing stress; separate from spacing-only acceptance' });
  } finally { await context.close(); }
});

test('icon gallery qualification rejects one missing image and recovers without hiding its label', async () => {
  const { context, page } = await pageFor({ setup: async pageContext => {
    await pageContext.route('**/icons/Clair/phone.svg', route => route.fulfill({ status: 404, contentType: 'image/svg+xml', body: '' }));
  } });
  try {
    await assert.rejects(checkIconGallery(page), /Icon not decoded: icons\/Clair\/phone\.svg/);
    const failed = page.locator('#icons [data-icon-function="phone"] img').first();
    assert.equal(await failed.getAttribute('alt'), 'Clair Phone icon');
    assert.equal(await page.locator('#icons [data-icon-function="phone"] h4').textContent(), 'Phone');
    await context.unroute('**/icons/Clair/phone.svg');
    await page.reload();
    assert.deepEqual(await checkIconGallery(page), iconPaths);
    const packageText = page.locator('#icons [data-icon-function="youtube"] p code');
    await packageText.evaluate(node => { node.style.visibility = 'hidden'; });
    await assert.rejects(checkIconGallery(page), /youtube/);
    await packageText.evaluate(node => { node.style.visibility = ''; });
    assert.deepEqual(await checkIconGallery(page), iconPaths);
    results.scenarios.push({ name: 'controlled missing gallery image', status: 'rejected and recovered',
      scope: 'disposable missing-resource fault, not a product defect' });
  } finally { await context.close(); }
});


function assertTerminalFragment(document) {
  assert.deepEqual(Object.keys(document), ['schemes']);
  assert.ok(Array.isArray(document.schemes));
  assert.equal(document.schemes.length, 2);
  const fields = ['name', 'background', 'foreground', 'cursorColor', 'selectionBackground', ...terminalAnsi.map(([field]) => field)];
  for (const [index, appearance] of ['Clair', 'Obscur'].entries()) {
    const scheme = document.schemes[index];
    assert.deepEqual(Object.keys(scheme).sort(), [...fields].sort());
    assert.equal(scheme.name, `Clair Obscur - ${appearance}`);
    for (const field of fields.filter(field => field !== 'name')) assert.match(scheme[field], /^#[a-f0-9]{6}$/i);
  }
}

function terminalRgb(hex) {
  return `rgb(${[1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16)).join(', ')})`;
}

async function checkTerminalSpecimens(page, document) {
  assertTerminalFragment(document);
  assert.equal(await page.locator('#terminal').getAttribute('aria-labelledby'), 'terminal-heading');
  assert.equal(await page.locator('#terminal-heading').textContent(), 'Windows Terminal colors');
  assert.equal(await page.locator('#terminal-download').getAttribute('href'), 'terminal/' + terminalArchive);
  assert.equal(await page.locator('#terminal-checksums').getAttribute('href'), 'terminal/SHA256SUMS');
  assert.equal(await page.locator('#terminal-guide').getAttribute('href'), 'terminal/installation.md');
  const observed = await page.locator('#terminal article.terminal-palette').evaluateAll(cards => {
    function textLayout(node) {
      if (!node) return { missing: true };
      const box = node.getBoundingClientRect(), style = getComputedStyle(node);
      const range = document.createRange(); range.selectNodeContents(node);
      const rects = [...range.getClientRects()].filter(rect => rect.width > 0 && rect.height > 0);
      const clippedBy = [];
      for (let ancestor = node.parentElement; ancestor; ancestor = ancestor.parentElement) {
        const parentStyle = getComputedStyle(ancestor), parent = ancestor.getBoundingClientRect();
        if (parentStyle.visibility !== 'visible' || parentStyle.display === 'none' || Number(parentStyle.opacity) === 0) clippedBy.push('hidden ancestor');
        if (['hidden', 'clip', 'scroll', 'auto'].includes(parentStyle.overflowY)
            && rects.some(rect => rect.top < parent.top - 1 || rect.bottom > parent.bottom + 1)) clippedBy.push('vertical clipping');
        if (['hidden', 'clip', 'scroll', 'auto'].includes(parentStyle.overflowX)
            && rects.some(rect => rect.left < parent.left - 1 || rect.right > parent.right + 1)) clippedBy.push('horizontal clipping');
      }
      return { text: node.textContent, width: box.width, height: box.height, left: box.left, right: box.right,
        clientWidth: node.clientWidth, scrollWidth: node.scrollWidth, display: style.display, visibility: style.visibility,
        opacity: style.opacity, fontSize: style.fontSize, color: style.color, background: style.backgroundColor,
        rects: rects.map(rect => ({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom })),
        clippedBy, viewport: innerWidth };
    }
    return cards.map(card => ({
      appearance: card.dataset.palette, background: getComputedStyle(card).backgroundColor, color: getComputedStyle(card).color,
      heading: textLayout(card.querySelector('h3')), name: textLayout(card.querySelector(':scope > p > code')),
      slots: [...card.querySelectorAll('.terminal-slot')].map(slot => ({
        field: slot.dataset.ansi, label: textLayout(slot.querySelector('p')),
        sample: textLayout(slot.querySelector('code')), context: textLayout(slot.querySelector('small')),
      })),
    }));
  });
  assert.equal(observed.length, 2, 'Both static Terminal appearances must remain available');
  for (const [index, appearance] of ['Clair', 'Obscur'].entries()) {
    const card = observed[index], scheme = document.schemes[index];
    assert.equal(card.appearance, appearance);
    assert.equal(card.heading.text, appearance);
    assert.equal(card.name.text, scheme.name);
    assert.equal(card.background, terminalRgb(scheme.background));
    assert.equal(card.color, terminalRgb(scheme.foreground));
    assert.deepEqual(card.slots.map(slot => slot.field), terminalAnsi.map(([field]) => field));
    for (const [slotIndex, [field, label]] of terminalAnsi.entries()) {
      const slot = card.slots[slotIndex];
      const partner = appearance === 'Clair' && ['white', 'brightWhite'].includes(field) ? 'black'
        : appearance === 'Obscur' && ['black', 'brightBlack'].includes(field) ? 'white' : null;
      assert.equal(slot.label.text, `${slotIndex}: ${label}`);
      assert.equal(slot.sample.text, 'Aa 0123');
      assert.equal(slot.context.text, partner ? 'on ' + partner : 'on default');
      assert.equal(slot.sample.color, terminalRgb(scheme[field]), `${appearance} ${field} foreground`);
      assert.equal(slot.sample.background, terminalRgb(partner ? scheme[partner] : scheme.background), `${appearance} ${field} background`);
    }
    for (const node of [card.heading, card.name, ...card.slots.flatMap(slot => [slot.label, slot.sample, slot.context])]) {
      assert.ok(!node.missing && node.text.length > 0 && node.width > 0 && node.height > 0, 'Terminal specimen text unavailable: ' + JSON.stringify(node));
      assert.equal(node.visibility, 'visible'); assert.notEqual(node.display, 'none');
      assert.ok(Number(node.opacity) > 0);
      assert.ok(node.left >= -1 && node.right <= node.viewport + 1, JSON.stringify(node));
      if (node.clientWidth > 0) assert.ok(node.scrollWidth <= node.clientWidth + 1, JSON.stringify(node));
      assert.ok(node.rects.length > 0, 'Retain rendered text rather than an empty colored box');
      assert.ok(node.rects.every(rect => rect.left >= -1 && rect.right <= node.viewport + 1), JSON.stringify(node));
      assert.deepEqual(node.clippedBy, [], JSON.stringify(node));
    }
  }
  const last = page.locator('#terminal .terminal-palette').last().locator('.terminal-slot').last().locator('small');
  await last.scrollIntoViewIfNeeded();
  assert.ok(await last.evaluate(node => {
    const box = node.getBoundingClientRect(); return box.top >= -1 && box.bottom <= innerHeight + 1;
  }), 'The final labeled sample must remain reachable by scrolling');
  assert.equal(await page.locator('#downloads .download-card').count(), 17);
  return observed;
}

async function verifyTerminalDownloads(archiveBytes, checksumBytes, siteRoot) {
  const terminalRoot = path.join(siteRoot, 'terminal');
  assert.deepEqual(archiveBytes, await readFile(path.join(terminalRoot, terminalArchive)), 'Terminal archive bytes differ from captured package');
  assert.deepEqual(checksumBytes, await readFile(path.join(terminalRoot, 'SHA256SUMS')));
  const pairs = checksumBytes.toString('utf8').trimEnd().split('\n').map(line => {
    const match = /^([a-f0-9]{64})  ([A-Za-z0-9._-]+)$/.exec(line);
    assert.ok(match, 'Each checksum must identify one generated local file'); return match.slice(1);
  });
  assert.deepEqual(pairs.map(([, name]) => name).sort(), [terminalFragment, terminalArchive, 'LICENSE.txt', 'manifest.json'].sort());
  for (const [digest, name] of pairs) assert.equal(crypto.createHash('sha256').update(await readFile(path.join(terminalRoot, name))).digest('hex'), digest, 'Terminal checksum mismatch for ' + name);
  const fragment = JSON.parse(await readFile(path.join(terminalRoot, terminalFragment), 'utf8'));
  assertTerminalFragment(fragment);
  const archivePath = path.join(temp, `terminal-acquired-${crypto.createHash('sha256').update(archiveBytes).digest('hex')}.zip`);
  await writeFile(archivePath, archiveBytes);
  run(['-c', [
    'import pathlib,stat,sys,zipfile',
    'archive_path,terminal_root=map(pathlib.Path,sys.argv[1:])',
    `expected={${JSON.stringify(terminalFragment)},"LICENSE.txt"}`,
    'with zipfile.ZipFile(archive_path) as archive:',
    ' names=archive.namelist()',
    ' assert names==sorted(expected) and archive.testzip() is None',
    ' for info in archive.infolist():',
    '  name=pathlib.PurePosixPath(info.filename)',
    '  assert not name.is_absolute() and ".." not in name.parts and "\\\\" not in info.filename',
    '  assert stat.S_ISREG(info.external_attr >> 16)',
    '  assert archive.read(info.filename)==(terminal_root/info.filename).read_bytes()',
  ].join('\n'), archivePath, terminalRoot]);
  return { sha256: crypto.createHash('sha256').update(archiveBytes).digest('hex'), bytes: archiveBytes.length, schemes: fragment.schemes.map(scheme => scheme.name) };
}

async function terminalKeyboardAcquisition(page) {
  assert.equal(await page.evaluate(() => document.activeElement.id), 'terminal-preview-link');
  await page.keyboard.press('Enter');
  await page.waitForURL(url => url.hash === '#terminal');
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'terminal-download');
  const [archive] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
  assert.equal(await archive.failure(), null);
  assert.equal(archive.suggestedFilename(), terminalArchive);
  const archiveChunks = []; for await (const chunk of await archive.createReadStream()) archiveChunks.push(chunk);
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'terminal-checksums');
  const [checksums] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
  assert.equal(await checksums.failure(), null);
  const checksumChunks = []; for await (const chunk of await checksums.createReadStream()) checksumChunks.push(chunk);
  const acquisition = await verifyTerminalDownloads(Buffer.concat(archiveChunks), Buffer.concat(checksumChunks), site);
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'terminal-guide');
  const previewUrl = page.url(), guideUrl = origin + '/terminal/installation.md';
  const [guideResponse] = await Promise.all([page.waitForResponse(response => response.url() === guideUrl), page.keyboard.press('Enter')]);
  await page.waitForURL(guideUrl);
  assert.equal(guideResponse.status(), 200);
  const guide = await readFile(path.join(site, 'terminal', 'installation.md'));
  assert.deepEqual(await guideResponse.body(), guide);
  assert.deepEqual(guide, await readFile(path.join(root, 'docs', 'windows-terminal.md')));
  assert.equal((await page.locator('body').innerText()).trim(), guide.toString('utf8').trim());
  return { ...acquisition, previewUrl, guide: 'exact captured repository Markdown',
    guideScope: 'separate plaintext response and content; preview spacing stylesheet does not apply' };
}

test('Windows Terminal specimens show exact package colors and all labels at phone and enlarged fallback sizes', async () => {
  const fragment = JSON.parse(await readFile(path.join(site, 'terminal', terminalFragment), 'utf8'));
  for (const scenario of [{ width: 390, enlarged: false }, { width: 320, enlarged: true }]) {
    const { context, page, consoleErrors } = await pageFor({ viewport: { width: scenario.width, height: 844 }, missingFont: scenario.enlarged });
    try {
      if (scenario.enlarged) await page.addStyleTag({ content: 'html { font-size: 200%; }' });
      assert.equal(await page.locator('html').evaluate(node => getComputedStyle(node).fontSize), scenario.enlarged ? '32px' : '16px');
      for (const appearance of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name: appearance, exact: true }).click();
        assert.equal(await page.locator('html').getAttribute('data-theme'), appearance);
        const specimens = await checkTerminalSpecimens(page, fragment);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        results.scenarios.push({ name: 'complete Terminal color-table specimens', ...scenario, pageAppearance: appearance,
          appearances: specimens.map(card => card.appearance), labeledSlots: 32, nativeTerminalVerified: false, status: 'passed' });
      }
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
});

test('Windows Terminal no-script sequential keyboard journey acquires the exact ZIP, checksums and captured guide', async () => {
  const { context, page, consoleErrors } = await pageFor({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  try {
    const fragment = JSON.parse(await readFile(path.join(site, 'terminal', terminalFragment), 'utf8'));
    await checkTerminalSpecimens(page, fragment);
    await page.reload();
    let tabs = 0;
    while (await page.evaluate(() => document.activeElement?.id) !== 'terminal-preview-link' && tabs < 40) {
      await page.keyboard.press('Tab'); tabs++;
    }
    const acquisition = await terminalKeyboardAcquisition(page);
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'Terminal sequential no-script acquisition and guide', status: 'passed', tabs,
      ...acquisition, guide: 'exact captured repository Markdown', nativeTerminalVerified: false });
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

// These are user spacing overrides, not new design defaults. The separate
// Japanese and Arabic samples retain their writing-system-specific spacing.
const textSpacingOverride = `
  body :is(a, p, h1, h2, h3, h4, blockquote, span, strong, b, em, mark, code, pre, label, button, input, select, option, summary, small, li, figcaption):not(:lang(ja), :lang(ar)) {
    line-height: 1.5 !important;
    letter-spacing: .12em !important;
    word-spacing: .16em !important;
  }
  p:not(:lang(ja), :lang(ar)) { margin-block-end: 2em !important; }
`;
const spacingPackages = {
  Clair: { path: 'equicord/Clair-Equicord-0.1.2.theme.css', version: '0.1.2',
    sha256: '0d2184455e281c2e8cd9d5791006a7cc1939a3a5553253c7a6e45b5991bd8054' },
  Obscur: { path: 'equicord/Obscur.theme.css', version: '0.1.1',
    sha256: 'b2fc01e87f749c1138ca5635eb77f1463d2bcb2eac6d5de898bb8d840741d1dd' },
};

async function spacingContentBaseline(page) {
  return page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let node; (node = walker.nextNode());) {
      const parent = node.parentElement;
      if (!node.textContent.trim() || parent.closest('script, style, noscript, option, legend, .skip, #package-chooser, #local-package-checker, #appearance-status, #control-status')) continue;
      const range = document.createRange(); range.selectNodeContents(node);
      if (!range.getClientRects().length || getComputedStyle(parent).visibility !== 'visible') continue;
      const steps = [];
      for (let part = node; part !== document.body; part = part.parentNode) {
        steps.unshift([...part.parentNode.childNodes].indexOf(part));
      }
      const style = getComputedStyle(parent);
      nodes.push({ steps, text: node.textContent,
        typography: [style.fontSize, style.fontFamily, style.fontWeight, style.fontStyle],
        languageSpacing: parent.matches(':lang(ja), :lang(ar)')
          ? [style.lineHeight, style.letterSpacing, style.wordSpacing, style.marginBlockEnd] : null });
    }
    return { nodes, rootFontSize: getComputedStyle(document.documentElement).fontSize, width: innerWidth };
  });
}

async function assertTextSpacing(page, baseline) {
  const observed = await page.evaluate(({ nodes, rootFontSize, width }) => {
    const errors = [], nativeSelectLineHeight = [], counts = { retained: 0, admitted: 0, paragraphs: 0 };
    const minimumRatios = { lineHeight: Infinity, letterSpacing: Infinity, wordSpacing: Infinity, paragraph: Infinity };
    const label = node => node.id || node.tagName.toLowerCase();
    function inspectText(node) {
      const parent = node.parentElement, range = document.createRange();
      range.selectNodeContents(node);
      const rects = [...range.getClientRects()];
      if (!rects.length || rects.every(rect => !rect.width || !rect.height)) errors.push(`text unavailable: ${label(parent)}`);
      for (let ancestor = parent; ancestor; ancestor = ancestor.parentElement) {
        const style = getComputedStyle(ancestor), box = ancestor.getBoundingClientRect();
        if (style.visibility !== 'visible' || style.display === 'none' || Number(style.opacity) === 0) errors.push(`text unavailable: ${label(ancestor)}`);
        // Intentionally scrollable code remains available through its own pane.
        for (const rect of rects) {
          if (['hidden', 'clip'].includes(style.overflowX) && (rect.left < box.left - 1 || rect.right > box.right + 1)) errors.push(`text clipped horizontally: ${label(ancestor)}`);
          if (['hidden', 'clip'].includes(style.overflowY) && (rect.top < box.top - 1 || rect.bottom > box.bottom + 1)) errors.push(`text clipped vertically: ${label(ancestor)}`);
        }
      }
    }
    for (const expected of nodes) {
      const node = expected.steps.reduce((parent, index) => parent?.childNodes[index], document.body);
      if (!node || node.nodeType !== Node.TEXT_NODE || node.textContent !== expected.text) { errors.push('retained text changed or disappeared'); continue; }
      inspectText(node);
      const style = getComputedStyle(node.parentElement);
      const typography = [style.fontSize, style.fontFamily, style.fontWeight, style.fontStyle];
      if (JSON.stringify(typography) !== JSON.stringify(expected.typography)) errors.push(`non-spacing typography changed: ${label(node.parentElement)}`);
      if (expected.languageSpacing && JSON.stringify(expected.languageSpacing) !== JSON.stringify([style.lineHeight, style.letterSpacing, style.wordSpacing, style.marginBlockEnd])) errors.push(`writing-system sample spacing changed: ${label(node.parentElement)}`);
      counts.retained++;
    }
    // Assignment paragraphs contain only a link, a break and code. The text
    // walker reaches those children, so admit the paragraph's own spacing too.
    const elements = new Set(document.querySelectorAll('button, input:not([type="checkbox"]), select, summary, #icons [data-icon-kind="app"] > p'));
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node; (node = walker.nextNode());) {
      const parent = node.parentElement;
      if (!node.textContent.trim() || parent.closest('script, style, noscript, option, legend, .skip')) continue;
      const range = document.createRange(); range.selectNodeContents(node);
      const requiredResult = parent.closest('#package-choice-result:not([hidden]), #local-package-result:not([hidden])');
      if (!requiredResult && (!range.getClientRects().length || getComputedStyle(parent).visibility !== 'visible')) continue;
      inspectText(node);
      elements.add(parent);
    }
    for (const node of elements) {
      if (node.matches(':lang(ja), :lang(ar)') || !node.getClientRects().length) continue;
      const style = getComputedStyle(node), size = parseFloat(style.fontSize);
      for (const [property, minimum] of [['lineHeight', 1.5], ['letterSpacing', .12], ['wordSpacing', .16]]) {
        if (node.tagName === 'SELECT' && property === 'lineHeight' && style.lineHeight === 'normal') {
          nativeSelectLineHeight.push({ id: node.id, fontSize: style.fontSize, computed: style.lineHeight,
            letterSpacing: style.letterSpacing, wordSpacing: style.wordSpacing,
            scope: 'unverified native select metric; not admitted as 1.5' });
          continue;
        }
        minimumRatios[property] = Math.min(minimumRatios[property], parseFloat(style[property]) / size);
        if (!(parseFloat(style[property]) + .02 >= size * minimum)) errors.push(`spacing admission ${property}: ${label(node)} = ${style[property]}`);
      }
      if (node.tagName === 'P') {
        minimumRatios.paragraph = Math.min(minimumRatios.paragraph, parseFloat(style.marginBlockEnd) / size);
        if (!(parseFloat(style.marginBlockEnd) + .02 >= size * 2)) errors.push(`spacing admission paragraph: ${label(node)} = ${style.marginBlockEnd}`);
        counts.paragraphs++;
      }
      counts.admitted++;
    }
    if (getComputedStyle(document.documentElement).fontSize !== rootFontSize || innerWidth !== width) errors.push('spacing changed the root font size or viewport');
    const overflow = [];
    if (document.documentElement.scrollWidth > innerWidth + 1) {
      for (const node of document.querySelectorAll('body *')) {
        const box = node.getBoundingClientRect();
        if (box.width && !node.closest('pre, .skip') && (box.left < -1 || box.right > innerWidth + 1 || node.scrollWidth > node.clientWidth + 1)) {
          overflow.push({ element: label(node), text: node.textContent.trim().slice(0, 90),
            left: box.left, right: box.right, width: box.width, scrollWidth: node.scrollWidth,
            clientWidth: node.clientWidth, font: getComputedStyle(node).fontFamily });
        }
      }
    }
    return { errors: [...new Set(errors)], counts, minimumRatios, nativeSelectLineHeight, width: innerWidth,
      documentWidth: document.documentElement.scrollWidth, overflow: overflow.slice(0, 12) };
  }, baseline);
  assert.deepEqual(observed.errors, [], observed.errors.slice(0, 12).join('\n'));
  assert.equal(observed.counts.retained, baseline.nodes.length);
  assert.ok(observed.counts.retained > 150 && observed.counts.paragraphs > 50, 'Admit the real page, not an empty specimen');
  assert.ok(observed.documentWidth <= observed.width + 1, JSON.stringify(observed));
  return observed;
}

async function spacingKeyboardFocus(page, locator) {
  await locator.focus();
  await page.keyboard.press('Tab'); await page.keyboard.press('Shift+Tab');
  assert.ok(await locator.evaluate(node => document.activeElement === node));
  assert.ok(await locator.isVisible());
  assert.equal(await locator.evaluate(node => getComputedStyle(node).outlineWidth), '2px');
}

async function chooseSpacingPackage(page, appearance) {
  const target = page.locator('#package-target');
  await spacingKeyboardFocus(page, target);
  await page.keyboard.press('Home');
  await page.keyboard.press('ArrowDown'); await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Tab');
  assert.equal(await target.inputValue(), 'equicord');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'package-appearance');
  await page.keyboard.press('Home');
  if (appearance === 'Clair') await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Tab');
  assert.equal(await page.locator('#package-appearance').inputValue(), appearance);
  assert.ok(await page.locator('#package-choice-result').isVisible(), 'chooser did not render the selected package');
  const expected = spacingPackages[appearance];
  assert.equal(await page.locator('#package-choice-file').getAttribute('href'), 'downloads/' + expected.path);
  assert.equal(await page.locator('#package-choice-guide').getAttribute('href'), '#guide-equicord-' + appearance.toLowerCase());
  const text = await page.locator('#package-choice-result').innerText();
  assert.ok(text.includes('Package ' + expected.version) && text.includes(expected.sha256));
  assert.match(await page.locator('#package-choice-status').innerText(), new RegExp('Selected ' + appearance));
  return expected;
}

async function assertSpacingIdentity(page, locator, appearance, expected, { chooser = false } = {}) {
  const normalized = text => text.replace(/\s+/g, ' ').trim();
  const visible = normalized(await locator.innerText());
  const excerpts = [`${appearance} for Equibop ${chooser ? '+' : 'with'} Equicord`, 'Package ' + expected.version,
    'downloads/' + expected.path, expected.sha256,
    await page.locator('#equicord-downloads > p').first().textContent(),
    await page.locator('#equicord-' + appearance.toLowerCase() + ' small').first().textContent(),
    await page.locator('#client-mod-limits').textContent()];
  for (const excerpt of excerpts) assert.ok(visible.includes(normalized(excerpt)), `required package text unavailable: ${excerpt}`);
}

async function spacingPackageJourney(page, appearance, baseline) {
  const expected = await chooseSpacingPackage(page, appearance);
  const assertAppearance = async () => assert.equal(await page.locator('html').getAttribute('data-theme'), appearance);
  await assertAppearance();
  await assertSpacingIdentity(page, page.locator('#package-choice-result'), appearance, expected, { chooser: true });
  await assertTextSpacing(page, baseline);
  await spacingKeyboardFocus(page, page.locator('#package-choice-guide'));
  await page.keyboard.press('Enter');
  await waitForGuideDestination(page, 'guide-equicord-' + appearance.toLowerCase());
  const guide = page.locator('#guide-equicord-' + appearance.toLowerCase());
  assert.ok((await guide.innerText()).includes(expected.sha256));
  await guide.locator('a[href="#guide-equicord-procedure"]').focus();
  await page.keyboard.press('Enter'); await waitForGuideDestination(page, 'guide-equicord-procedure');
  const procedure = page.locator('#guide-equicord-procedure');
  for (const heading of ['Install', 'Switch', 'Remove and restore']) assert.ok(await procedure.getByRole('heading', { name: heading, exact: true }).isVisible());
  assert.match(await procedure.innerText(), /Open Themes Folder/);
  await assertTextSpacing(page, baseline); await assertAppearance();
  await spacingKeyboardFocus(page, page.locator('#package-choice-file'));
  const [saved] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
  assert.equal(await saved.failure(), null); assert.equal(saved.suggestedFilename(), path.basename(expected.path));
  const chunks = []; for await (const chunk of await saved.createReadStream()) chunks.push(chunk);
  const bytes = Buffer.concat(chunks);
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), expected.sha256);
  const input = page.locator('#local-package-file');
  await spacingKeyboardFocus(page, input);
  await input.setInputFiles({ name: path.basename(expected.path), mimeType: 'text/css', buffer: bytes });
  await waitForPackageState(page, 'matched');
  assert.equal(await page.locator('.local-file-hash code').textContent(), expected.sha256);
  assert.equal(await page.locator('#local-package-result .identified-package').count(), 1);
  assert.equal(await page.locator('#local-package-result .guide-link').getAttribute('href'), '#guide-equicord-' + appearance.toLowerCase());
  await assertSpacingIdentity(page, page.locator('#local-package-result .identified-package'), appearance, expected);
  await assertTextSpacing(page, baseline); await assertAppearance();
  const changed = Buffer.from(bytes); changed[0] ^= 1;
  await input.setInputFiles({ name: path.basename(expected.path), mimeType: 'text/css', buffer: changed });
  await waitForPackageState(page, 'no-match');
  assert.equal(await page.locator('.local-file-hash code').textContent(), crypto.createHash('sha256').update(changed).digest('hex'));
  assert.equal(await page.locator('#local-package-result .identified-package').count(), 0);
  await assertTextSpacing(page, baseline);
  await spacingKeyboardFocus(page, page.locator('#local-package-clear'));
  await page.keyboard.press('Enter'); await waitForPackageState(page, 'idle');
  assert.equal(await input.evaluate(node => node.files.length), 0);
  assert.ok(await page.locator('#local-package-result').isHidden());
  await assertAppearance();
  assert.equal(await page.locator('#package-target').inputValue(), 'equicord');
  assert.equal(await page.locator('#package-appearance').inputValue(), appearance);
  return { path: expected.path, sha256: expected.sha256, guide: 'guide-equicord-' + appearance.toLowerCase(),
    keyboardSelection: true, actualDownload: true, matchedAndChangedBytes: true, clear: true };
}

async function terminalSpacingAdmission(page) {
  const observed = await page.locator('#terminal').evaluate(section => {
    const errors = [], minimumRatios = { lineHeight: Infinity, letterSpacing: Infinity, wordSpacing: Infinity, paragraph: Infinity };
    const nodes = [...section.querySelectorAll('h2, h3, p, code, small, a')];
    let paragraphs = 0;
    for (const node of nodes) {
      const style = getComputedStyle(node), size = parseFloat(style.fontSize);
      const label = node.id || node.closest('[data-ansi]')?.dataset.ansi || node.tagName.toLowerCase();
      if (!node.getClientRects().length || style.visibility !== 'visible' || Number(style.opacity) === 0) errors.push('Terminal spacing text unavailable: ' + label);
      for (const [property, minimum] of [['lineHeight', 1.5], ['letterSpacing', .12], ['wordSpacing', .16]]) {
        minimumRatios[property] = Math.min(minimumRatios[property], parseFloat(style[property]) / size);
        if (!(parseFloat(style[property]) + .02 >= size * minimum)) errors.push(`Terminal spacing admission ${property}: ${label} = ${style[property]}`);
      }
      if (node.tagName === 'P') {
        minimumRatios.paragraph = Math.min(minimumRatios.paragraph, parseFloat(style.marginBlockEnd) / size);
        if (!(parseFloat(style.marginBlockEnd) + .02 >= size * 2)) errors.push('Terminal spacing admission paragraph: ' + label);
        paragraphs++;
      }
    }
    return { errors, nodes: nodes.length, paragraphs, minimumRatios,
      cards: section.querySelectorAll('.terminal-palette').length,
      labels: section.querySelectorAll('.terminal-slot > p').length,
      samples: section.querySelectorAll('.terminal-slot > code').length,
      contexts: section.querySelectorAll('.terminal-slot > small').length,
      schemeNames: section.querySelectorAll('.terminal-palette > p > code').length,
      actions: section.querySelectorAll('#terminal-download, #terminal-checksums, #terminal-guide').length };
  });
  assert.deepEqual(observed.errors, []);
  assert.deepEqual([observed.cards, observed.labels, observed.samples, observed.contexts, observed.schemeNames, observed.actions], [2, 32, 32, 32, 2, 3]);
  assert.ok(observed.nodes > 100 && observed.paragraphs >= 34, 'Admit the real Terminal text and every action');
  return observed;
}

async function terminalSpacingJourney(page, baseline, { javaScriptEnabled = true } = {}) {
  const fragment = JSON.parse(await readFile(path.join(site, 'terminal', terminalFragment), 'utf8'));
  const appearance = await page.locator('html').getAttribute('data-theme');
  const specimens = await checkTerminalSpecimens(page, fragment);
  const admission = await terminalSpacingAdmission(page);
  await spacingKeyboardFocus(page, page.locator('#terminal-preview-link'));
  const acquisition = await terminalKeyboardAcquisition(page);
  await page.goBack();
  await page.waitForURL(acquisition.previewUrl);
  // The guide is a separate plaintext response. Re-admit preview overrides
  // after returning rather than assuming that injected styles or page state persist.
  if (javaScriptEnabled) {
    if (await page.locator('html').evaluate(node => getComputedStyle(node).fontSize) !== baseline.rootFontSize) {
      await page.addStyleTag({ content: `html { font-size: ${baseline.rootFontSize}; }` });
    }
    await page.getByRole('button', { name: appearance, exact: true }).focus();
    await page.keyboard.press('Enter');
    await page.addStyleTag({ content: textSpacingOverride });
  }
  assert.equal(await page.locator('html').getAttribute('data-theme'), appearance);
  await assertTextSpacing(page, baseline);
  const returnedAdmission = await terminalSpacingAdmission(page);
  await checkTerminalSpecimens(page, fragment);
  return { ...acquisition, appearances: specimens.map(card => card.appearance), labeledSlots: 32, admission,
    returnedAdmission, returnedToPreview: true, previewOverridesReadmitted: true, nativeTerminalVerified: false };
}

test('text spacing alone preserves content and the keyboard package journey in both appearances', async () => {
  for (const appearance of ['Obscur', 'Clair']) {
    const { context, page, consoleErrors } = await pageFor();
    try {
      await page.getByRole('button', { name: appearance, exact: true }).focus(); await page.keyboard.press('Enter');
      const baseline = await spacingContentBaseline(page);
      assert.equal(baseline.rootFontSize, '16px'); assert.equal(baseline.width, 1280);
      await page.addStyleTag({ content: textSpacingOverride });
      const admission = await assertTextSpacing(page, baseline);
      await checkIconGallery(page);
      const journey = await spacingPackageJourney(page, appearance, baseline);
      const terminal = await terminalSpacingJourney(page, baseline);
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'text spacing only', appearance, status: 'passed', admission, journey, terminal,
        scope: 'four spacing overrides at unchanged default typography; English text, not native application or full WCAG acceptance' });
    } finally { await context.close(); }
  }
});

test('text spacing with narrow layout and enlarged fallback text is separate additional stress', async () => {
  for (const scenario of [{ width: 390, scale: 100, missingFont: false }, { width: 320, scale: 200, missingFont: true }]) {
    for (const appearance of ['Obscur', 'Clair']) {
      const { context, page, consoleErrors } = await pageFor({ viewport: { width: scenario.width, height: 844 }, missingFont: scenario.missingFont });
      try {
        if (scenario.scale === 200) await page.addStyleTag({ content: 'html { font-size: 200%; }' });
        await page.getByRole('button', { name: appearance, exact: true }).focus(); await page.keyboard.press('Enter');
        const baseline = await spacingContentBaseline(page);
        assert.equal(baseline.rootFontSize, scenario.scale === 200 ? '32px' : '16px');
        await page.addStyleTag({ content: textSpacingOverride });
        const admission = await assertTextSpacing(page, baseline);
        await checkIconGallery(page);
        const journey = await spacingPackageJourney(page, appearance, baseline);
        const terminal = await terminalSpacingJourney(page, baseline);
        assert.deepEqual(consoleErrors, []);
        results.scenarios.push({ name: 'text spacing additional responsive stress', appearance, ...scenario, status: 'passed', admission, journey, terminal,
          scope: 'narrow viewport and optional root-font enlargement, not browser zoom or spacing-only conformance' });
      } finally { await context.close(); }
    }
  }
});

test('text spacing keeps the no-script catalog and keyboard installation routes readable', async () => {
  const { context, page, consoleErrors } = await pageFor({ javaScriptEnabled: false });
  try {
    const baseline = await spacingContentBaseline(page);
    // Loading CSS does not depend on page script or a script-driven style-load
    // promise. Preserve the real script-disabled route throughout this check.
    await page.route('**/preview.css', async route => route.fulfill({ contentType: 'text/css',
      body: await readFile(path.join(site, 'preview.css'), 'utf8') + textSpacingOverride }));
    await page.reload();
    const admission = await assertTextSpacing(page, baseline);
    await checkIconGallery(page);
    assert.ok(await page.locator('#package-chooser').isHidden());
    assert.ok(await page.locator('#local-package-checker').isHidden());
    for (const appearance of ['Obscur', 'Clair']) {
      assert.ok(await page.locator(`.palette[data-palette="${appearance}"]`).isVisible());
      const expected = spacingPackages[appearance], card = page.locator('#equicord-' + appearance.toLowerCase());
      await spacingKeyboardFocus(page, card.locator('.guide-link')); await page.keyboard.press('Enter');
      await waitForGuideDestination(page, 'guide-equicord-' + appearance.toLowerCase());
      assert.ok((await page.locator('#guide-equicord-' + appearance.toLowerCase()).innerText()).includes(expected.sha256));
      await spacingKeyboardFocus(page, card.locator('a[download]'));
      const [saved] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
      const chunks = []; for await (const chunk of await saved.createReadStream()) chunks.push(chunk);
      assert.equal(await saved.failure(), null);
      assert.equal(crypto.createHash('sha256').update(Buffer.concat(chunks)).digest('hex'), expected.sha256);
    }
    const terminal = await terminalSpacingJourney(page, baseline, { javaScriptEnabled: false });
    await assertTextSpacing(page, baseline);
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'text spacing no-script static routes', status: 'passed', admission, terminal,
      scope: 'default reading appearance and both static palettes, not an operable no-script appearance switch' });
  } finally { await context.close(); }
});

test('text spacing qualification rejects missing overrides, collapsed assignment spacing, clipped prose and an inert chooser', async () => {
  for (const fault of ['word-spacing', 'gallery-paragraph-margin', 'clipped-prose', 'inert-chooser']) {
    const { context, page } = await pageFor({ setup: async context => {
      if (fault !== 'inert-chooser') return;
      const source = await readFile(path.join(site, 'preview.js'), 'utf8');
      const listener = "target.addEventListener('change', updatePackageChoice);";
      assert.equal(source.split(listener).length, 2, 'The controlled fault must target the real listener');
      await context.route('**/preview.js', route => route.fulfill({ contentType: 'text/javascript', body: source.replace(listener, '') }));
    } });
    try {
      const baseline = await spacingContentBaseline(page);
      await page.addStyleTag({ content: fault === 'word-spacing' ? textSpacingOverride.replace('word-spacing: .16em !important;', '') : textSpacingOverride });
      if (fault === 'word-spacing') await assert.rejects(assertTextSpacing(page, baseline), /spacing admission wordSpacing/);
      if (fault === 'gallery-paragraph-margin') {
        const paragraph = page.locator('#icons [data-icon-function="youtube"] > p');
        await paragraph.evaluate(node => node.style.setProperty('margin-block-end', '0px', 'important'));
        assert.equal(await paragraph.evaluate(node => getComputedStyle(node).marginBlockEnd), '0px');
        await assert.rejects(assertTextSpacing(page, baseline), /spacing admission paragraph: p/);
        await paragraph.evaluate(node => node.style.removeProperty('margin-block-end'));
        await assertTextSpacing(page, baseline);
      }
      if (fault === 'clipped-prose') {
        await chooseSpacingPackage(page, 'Obscur');
        const clipping = await page.addStyleTag({ content: '#package-choice-result p { height: 1px !important; overflow: hidden !important; }' });
        await assert.rejects(assertTextSpacing(page, baseline), /text clipped vertically/);
        await clipping.evaluate(node => node.remove());
        await page.addStyleTag({ content: '#package-choice-result .package-choice-path { display: none !important; }' });
        await assert.rejects(assertTextSpacing(page, baseline), /text unavailable/);
        await assert.rejects(assertSpacingIdentity(page, page.locator('#package-choice-result'), 'Obscur', spacingPackages.Obscur, { chooser: true }), /required package text unavailable/);
      }
      if (fault === 'inert-chooser') {
        await assertTextSpacing(page, baseline);
        await assert.rejects(chooseSpacingPackage(page, 'Obscur'), /chooser did not render/);
      }
      results.scenarios.push({ name: 'text spacing controlled oracle failure', fault, status: 'rejected as expected', scope: 'disposable harness fault, not a product defect' });
    } finally { await context.close(); }
  }
});

test('text spacing Terminal qualification rejects a hidden sample and altered downloaded ZIP bytes', async () => {
  for (const fault of ['hidden-terminal-sample', 'altered-terminal-zip']) {
    const { context, page, consoleErrors } = await pageFor();
    const downloaded = [];
    page.on('download', download => downloaded.push({ filename: download.suggestedFilename(), url: download.url() }));
    try {
      const baseline = await spacingContentBaseline(page);
      await page.addStyleTag({ content: textSpacingOverride });
      await assertTextSpacing(page, baseline);
      if (fault === 'hidden-terminal-sample') {
        const hiding = await page.addStyleTag({ content: '#terminal .terminal-palette[data-palette="Clair"] .terminal-slot[data-ansi="red"] > code { display: none !important; }' });
        await assert.rejects(terminalSpacingJourney(page, baseline), /Terminal specimen text unavailable/);
        await hiding.evaluate(node => node.remove());
        await terminalSpacingAdmission(page);
        await checkTerminalSpecimens(page, JSON.parse(await readFile(path.join(site, 'terminal', terminalFragment), 'utf8')));
      } else {
        // Change only this run's temporary served ZIP. Keep its independent
        // checksums and scheme fragment intact, then restore the fixture in finally.
        assert.ok(site.startsWith(temp + path.sep), 'Fault injection must stay inside the owned temporary preview');
        const fixtureArchive = path.join(site, 'terminal', terminalArchive);
        const original = await readFile(fixtureArchive), altered = Buffer.from(original);
        const checksums = await readFile(path.join(site, 'terminal', 'SHA256SUMS'));
        const fragment = await readFile(path.join(site, 'terminal', terminalFragment));
        altered[0] ^= 1;
        try {
          await writeFile(fixtureArchive, altered);
          assert.deepEqual(await readFile(fixtureArchive), altered, 'The controlled fixture fault must actually be present');
          await assert.rejects(terminalSpacingJourney(page, baseline), /Terminal checksum mismatch for Clair-Obscur-Windows-Terminal-0\.1\.0\.zip/);
          assert.deepEqual(downloaded.map(download => download.url), [origin + '/terminal/' + terminalArchive, origin + '/terminal/SHA256SUMS'], 'Reject bytes acquired by the real keyboard download controls');
          assert.deepEqual(await readFile(path.join(site, 'terminal', 'SHA256SUMS')), checksums);
          assert.deepEqual(await readFile(path.join(site, 'terminal', terminalFragment)), fragment);
        } finally { await writeFile(fixtureArchive, original); }
        assert.deepEqual(await readFile(fixtureArchive), original, 'Restore the owned fixture after the controlled failure');
      }
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'text spacing controlled Terminal oracle failure', fault, status: 'rejected as expected',
        actualDownloads: downloaded, fixtureRestored: true,
        scope: 'disposable hidden sample or changed served fixture bytes, not a product defect' });
    } finally { await context.close(); }
  }
});

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
  const requests = [], errors = [], journeys = [], packageJourneys = [], chooserJourneys = [], identificationJourneys = [], iconJourneys = [], terminalJourneys = [];
  const terminalDocument = JSON.parse(await readFile(path.join(relocated, 'terminal', terminalFragment), 'utf8'));
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
        const decodedIcons = await checkIconGallery(localPage);
        for (const relative of decodedIcons) {
          const bytes = await readFile(path.join(relocated, ...relative.split('/')));
          assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), inner.files[relative]);
        }
        await localPage.locator('#icon-artwork-download').focus();
        const [iconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
        assert.equal(await iconDownload.failure(), null);
        assert.equal(iconDownload.suggestedFilename(), path.basename(iconArchive));
        const iconChunks = []; for await (const chunk of await iconDownload.createReadStream()) iconChunks.push(chunk);
        const iconBytes = Buffer.concat(iconChunks), iconDigest = crypto.createHash('sha256').update(iconBytes).digest('hex');
        assert.deepEqual(iconBytes, await readFile(path.join(relocated, ...iconArchive.split('/'))));
        assert.equal(iconDigest, inner.files[iconArchive]);
        assert.equal(await readFile(path.join(relocated, 'icons', 'SVG-SHA256SUMS'), 'utf8'), iconChecksums(iconDigest));
        await localPage.locator('#icon-artwork-previous-download').focus();
        const [previousIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
        assert.equal(await previousIconDownload.failure(), null);
        assert.equal(previousIconDownload.suggestedFilename(), path.basename(previousIconArchive));
        const previousIconChunks = []; for await (const chunk of await previousIconDownload.createReadStream()) previousIconChunks.push(chunk);
        const previousIconBytes = Buffer.concat(previousIconChunks);
        assert.deepEqual(previousIconBytes, await readFile(path.join(relocated, ...previousIconArchive.split('/'))));
        assert.equal(crypto.createHash('sha256').update(previousIconBytes).digest('hex'), previousIconDigest);
        assert.equal(inner.files[previousIconArchive], previousIconDigest);
        await localPage.locator('#icon-artwork-legacy-download').focus();
        const [legacyIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
        assert.equal(await legacyIconDownload.failure(), null);
        assert.equal(legacyIconDownload.suggestedFilename(), path.basename(legacyIconArchive));
        const legacyIconChunks = []; for await (const chunk of await legacyIconDownload.createReadStream()) legacyIconChunks.push(chunk);
        const legacyIconBytes = Buffer.concat(legacyIconChunks);
        assert.deepEqual(legacyIconBytes, await readFile(path.join(relocated, ...legacyIconArchive.split('/'))));
        assert.equal(crypto.createHash('sha256').update(legacyIconBytes).digest('hex'), legacyIconDigest);
        assert.equal(inner.files[legacyIconArchive], legacyIconDigest);
        iconJourneys.push({ javaScriptEnabled, width, decoded: decodedIcons.length, sha256: iconDigest,
          previousSha256: previousIconDigest, legacySha256: legacyIconDigest,
          method: 'saved included current and both preserved SVG archives' });
        const terminalSpecimens = await checkTerminalSpecimens(localPage, terminalDocument);
        await localPage.locator('#terminal-download').focus();
        const [terminalZip] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
        assert.equal(await terminalZip.failure(), null);
        assert.equal(terminalZip.suggestedFilename(), terminalArchive);
        const terminalChunks = []; for await (const chunk of await terminalZip.createReadStream()) terminalChunks.push(chunk);
        await localPage.keyboard.press('Tab');
        assert.equal(await localPage.evaluate(() => document.activeElement.id), 'terminal-checksums');
        const terminalSumUrl = pathToFileURL(path.join(relocated, 'terminal', 'SHA256SUMS')).href;
        let terminalSumText;
        try {
          // Like the included CSS routes below, an extensionless local text
          // file opens in the browser. Qualify that actual consumer behavior.
          await Promise.all([localPage.waitForURL(terminalSumUrl, { timeout: 5000 }), localPage.keyboard.press('Enter')]);
          terminalSumText = await localPage.locator('pre').textContent();
          assert.equal(terminalSumText, await readFile(path.join(relocated, 'terminal', 'SHA256SUMS'), 'utf8'));
        } catch (error) {
          failures.push({ scenario: 'portable Terminal checksum activation', javaScriptEnabled, width,
            pageUrl: localPage.url(), error: error.message, observation: await localPage.evaluate(() => ({
              focusedId: document.activeElement?.id, focusedHref: document.activeElement?.getAttribute('href'),
              bodyText: document.body?.innerText.slice(0, 2400), title: document.title,
            })) });
          throw error;
        }
        const terminalAcquisition = await verifyTerminalDownloads(Buffer.concat(terminalChunks), Buffer.from(terminalSumText, 'utf8'), relocated);
        assert.equal(terminalAcquisition.sha256, inner.files['terminal/' + terminalArchive]);
        await localPage.goBack();
        await localPage.locator('#terminal-checksums').focus();
        await localPage.keyboard.press('Tab');
        assert.equal(await localPage.evaluate(() => document.activeElement.id), 'terminal-guide');
        const terminalGuideUrl = pathToFileURL(path.join(relocated, 'terminal', 'installation.md')).href;
        await Promise.all([localPage.waitForURL(terminalGuideUrl), localPage.keyboard.press('Enter')]);
        const terminalGuide = await readFile(path.join(relocated, 'terminal', 'installation.md'), 'utf8');
        assert.equal((await localPage.locator('body').textContent()).trim(), terminalGuide.trim());
        assert.equal(crypto.createHash('sha256').update(terminalGuide).digest('hex'), inner.files['terminal/installation.md']);
        await localPage.goBack();
        await localPage.evaluate(() => document.fonts.ready);
        terminalJourneys.push({ javaScriptEnabled, width, ...terminalAcquisition, appearances: terminalSpecimens.map(card => card.appearance),
          labeledSlots: 32, checksums: 'opened exact included plaintext and returned', guide: 'opened exact included Markdown and returned',
          method: 'focused archive control, keyboard ZIP acquisition and exact local text routes' });
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
          assert.equal(await localPage.locator(`.palette[data-palette="${appearance}"]`).evaluate(node => getComputedStyle(node).backgroundColor), background);
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
  assert.equal(iconJourneys.length, 4);
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
    protocol: 'file:', network: 'all external requests blocked', requests, errors, journeys, packageJourneys, chooserJourneys, identificationJourneys, iconJourneys, terminalJourneys,
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
    for (const [name, mode, background, text, filename, nativeFocusRepair] of [
      ['Obscur', 'dark', 'rgb(9, 9, 9)', 'rgb(244, 244, 244)', 'Obscur.theme.css', false],
      ['Clair', 'light', 'rgb(248, 247, 243)', 'rgb(36, 36, 36)', 'Clair.theme.css', false],
      ['Clair', 'light', 'rgb(248, 247, 243)', 'rgb(36, 36, 36)', 'Clair-Equicord-0.1.2.theme.css', true],
    ]) {
      const response = await context.request.get(`${origin}/downloads/equicord/${filename}`);
      assert.equal(response.status(), 200, filename);
      const css = await response.text();
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
        .native-control { position:relative; width:44px; height:24px; margin:16px; }
        #native-slider { width:100%; height:100%; background:#eee; }
        .focus-rings-ring {
          display:none; position:absolute; inset:0; box-sizing:border-box;
          box-shadow:0 0 0 4px var(--__adaptive-focus-ring-color,var(--focus-primary,#00b0f4));
          border-radius:var(--__adaptive-focus-ring-radius,4px); pointer-events:none;
        }
        .native-control:focus-within .focus-rings-ring { display:block; }
        .enable-forced-colors .focus-rings-ring {
          forced-color-adjust:none; --__adaptive-focus-ring-color:CanvasText!important;
          border:2px solid Canvas;
        }
        #system-colors { color:CanvasText; background:Canvas; }
      </style></head><body><p id="message-content-fixture">Regular <strong>bold</strong> <em>italic</em> <code>code</code></p>
      <button id="primary" class="vc-btn-base vc-btn-medium">Host control</button><button id="secondary">Secondary control</button>
      <a id="mention" href="#fixture">Mention</a>
      <span class="switch">Off</span><span class="switch checked">On<span class="vc-switch-indicator">Indicator</span></span>
      <div class="native-control"><div id="native-slider" role="slider" tabindex="0" aria-valuemin="12" aria-valuemax="24" aria-valuenow="16" aria-label="Fixture text size"></div>
        <div id="native-ring" class="focus-rings-ring" style="--__adaptive-focus-ring-color:rgba(255,255,255,0.7);--__adaptive-focus-ring-radius:9px"></div></div>
      <span id="system-colors">System color reference</span></body></html>`);
      // Color, radius, pointer and forced-color rules model the inspected host.
      // Position and size are deliberate fixture geometry, not native evidence.
      const nativeRing = () => page.locator('#native-ring').evaluate(node => {
        const style = getComputedStyle(node), box = node.getBoundingClientRect();
        const parentBox = node.parentElement.getBoundingClientRect();
        return {
          shadow:style.boxShadow, adaptiveColor:style.getPropertyValue('--__adaptive-focus-ring-color').trim(),
          display:style.display, forcedColorAdjust:style.forcedColorAdjust,
          border:{ width:style.borderTopWidth, style:style.borderTopStyle, color:style.borderTopColor },
          geometry:{ width:box.width, height:box.height, x:box.x - parentBox.x, y:box.y - parentBox.y,
            position:style.position, radius:style.borderRadius, pointerEvents:style.pointerEvents },
        };
      });
      await page.locator('#native-slider').focus();
      const originalNativeRing = await nativeRing();
      assert.equal(originalNativeRing.shadow, 'rgba(255, 255, 255, 0.7) 0px 0px 0px 4px');
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
      await page.locator('#native-slider').focus();
      const nativeFocus = await nativeRing();
      assert.equal(nativeFocus.display, 'block');
      assert.equal(await page.locator(':focus').getAttribute('id'), 'native-slider');
      assert.equal(nativeFocus.shadow, nativeFocusRepair ? `${color(expected.focus)} 0px 0px 0px 4px` : originalNativeRing.shadow);
      assert.deepEqual(nativeFocus.geometry, originalNativeRing.geometry);
      assert.equal(nativeFocus.geometry.radius, '9px');
      assert.equal(nativeFocus.geometry.pointerEvents, 'none');
      const hitTarget = await page.locator('#native-slider').evaluate(node => {
        const box = node.getBoundingClientRect();
        return document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2)?.id;
      });
      assert.equal(hitTarget, 'native-slider', 'The overlay must not capture the control hit target');
      await page.emulateMedia({ forcedColors:'active' });
      await page.evaluate(() => document.documentElement.classList.add('enable-forced-colors'));
      const forcedNativeFocus = await nativeRing();
      const systemColors = await page.locator('#system-colors').evaluate(node => ({
        text:getComputedStyle(node).color, canvas:getComputedStyle(node).backgroundColor,
      }));
      assert.equal(forcedNativeFocus.adaptiveColor, 'CanvasText', 'The host important system-color rule must win');
      assert.equal(forcedNativeFocus.forcedColorAdjust, 'none');
      assert.equal(forcedNativeFocus.shadow, `${systemColors.text} 0px 0px 0px 4px`);
      assert.deepEqual(forcedNativeFocus.border, { width:'2px', style:'solid', color:systemColors.canvas });
      assert.deepEqual(forcedNativeFocus.geometry, originalNativeRing.geometry);
      await page.emulateMedia({ forcedColors:'none' });
      await page.evaluate(value => document.documentElement.className = `theme-${value}`, mode === 'dark' ? 'light' : 'dark');
      assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(171, 205, 239)');
      assert.deepEqual(await nativeRing(), originalNativeRing, 'The opposite appearance must retain its native ring baseline');
      results.scenarios.push({ name: `${filename} Equicord host-contract fixture`, status: 'passed', rendered, focus,
        nativeFocus:{ original:originalNativeRing, candidate:nativeFocus, forced:forcedNativeFocus, nativeFocusRepair, hitTarget },
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
