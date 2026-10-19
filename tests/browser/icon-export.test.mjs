import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { inflateSync } from 'node:zlib';
import { mkdtemp, readFile, writeFile, mkdir, cp, rm, readdir, symlink, lstat, readlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const exporter = path.join(root, 'tools', 'export-icons.mjs');
const python = process.platform === 'win32' ? ['py', '-3.11', '-X', 'utf8'] : ['python3'];
const baseFunctions = ('phone messages contacts camera gallery settings calendar clock files notes mail browser maps ' +
  'music video store wallet calculator weather health fitness voice-recorder home search').split(' ');
// Independent assignment identities, rather than an inventory imported from the generator.
const firstApps = [
  ['google-chrome', 'Google Chrome', 'com.android.chrome'],
  ['youtube', 'YouTube', 'com.google.android.youtube'],
  ['google-maps', 'Google Maps', 'com.google.android.apps.maps'],
  ['gmail', 'Gmail', 'com.google.android.gm'],
  ['google-photos', 'Google Photos', 'com.google.android.apps.photos'],
  ['google-messages', 'Google Messages', 'com.google.android.apps.messaging'],
  ['google-calendar', 'Google Calendar', 'com.google.android.calendar'],
  ['google-drive', 'Google Drive', 'com.google.android.apps.docs'],
  ['samsung-browser', 'Samsung Browser', 'com.sec.android.app.sbrowser'],
  ['samsung-notes', 'Samsung Notes', 'com.samsung.android.app.notes'],
  ['samsung-health', 'Samsung Health', 'com.sec.android.app.shealth'],
  ['garmin-connect', 'Garmin Connect', 'com.garmin.android.apps.connectmobile'],
  ['whatsapp', 'WhatsApp', 'com.whatsapp'],
  ['messenger', 'Messenger', 'com.facebook.orca'],
  ['instagram', 'Instagram', 'com.instagram.android'],
  ['facebook', 'Facebook', 'com.facebook.katana'],
  ['snapchat', 'Snapchat', 'com.snapchat.android'],
  ['tiktok', 'TikTok', 'com.zhiliaoapp.musically'],
  ['discord', 'Discord', 'com.discord'],
  ['reddit', 'Reddit', 'com.reddit.frontpage'],
  ['pinterest', 'Pinterest', 'com.pinterest'],
  ['telegram', 'Telegram', 'org.telegram.messenger'],
  ['spotify', 'Spotify', 'com.spotify.music'],
  ['netflix', 'Netflix', 'com.netflix.mediaclient'],
  ['amazon-shopping', 'Amazon Shopping', 'com.amazon.mShop.android.shopping'],
  ['walmart', 'Walmart', 'com.walmart.android'],
  ['temu', 'Temu', 'com.einnovation.temu'],
  ['uber', 'Uber', 'com.ubercab'],
  ['doordash', 'DoorDash', 'com.dd.doordash'],
  ['paypal', 'PayPal', 'com.paypal.android.p2pmobile'],
  ['outlook', 'Microsoft Outlook', 'com.microsoft.office.outlook'],
  ['chatgpt', 'ChatGPT', 'com.openai.chatgpt'],
  ['firefox', 'Firefox', 'org.mozilla.firefox'],
];
const addedApps = [
  ['x', 'X', 'com.twitter.android'],
  ['threads', 'Threads', 'com.instagram.barcelona'],
  ['signal', 'Signal', 'org.thoughtcrime.securesms'],
  ['twitch', 'Twitch', 'tv.twitch.android.app'],
  ['capcut', 'CapCut', 'com.lemon.lvoverseas'],
  ['disney-plus', 'Disney+', 'com.disney.disneyplus'],
  ['prime-video', 'Prime Video', 'com.amazon.avod.thirdpartyclient'],
  ['microsoft-teams', 'Teams', 'com.microsoft.teams'],
  ['zoom', 'Zoom', 'us.zoom.videomeetings'],
  ['google-meet', 'Google Meet', 'com.google.android.apps.tachyon'],
  ['google-docs', 'Google Docs', 'com.google.android.apps.docs.editors.docs'],
  ['google-sheets', 'Google Sheets', 'com.google.android.apps.docs.editors.sheets'],
  ['onedrive', 'OneDrive', 'com.microsoft.skydrive'],
  ['google-translate', 'Google Translate', 'com.google.android.apps.translate'],
  ['google-keep', 'Google Keep', 'com.google.android.keep'],
  ['google-wallet', 'Google Wallet', 'com.google.android.apps.walletnfcrel'],
  ['cash-app', 'Cash App', 'com.squareup.cash'],
  ['venmo', 'Venmo', 'com.venmo'],
  ['ebay', 'eBay', 'com.ebay.mobile'],
  ['mcdonalds', "McDonald's", 'com.mcdonalds.app'],
  ['starbucks', 'Starbucks', 'com.starbucks.mobilecard'],
  ['duolingo', 'Duolingo', 'com.duolingo'],
  ['waze', 'Waze', 'com.waze'],
  ['canva', 'Canva', 'com.canva.editor'],
];
const thirdApps = [
  ['linkedin', 'LinkedIn', 'com.linkedin.android'],
  ['github', 'GitHub', 'com.github.android'],
  ['notion', 'Notion', 'notion.id'],
  ['microsoft-edge', 'Microsoft Edge', 'com.microsoft.emmx'],
  ['brave', 'Brave', 'com.brave.browser'],
  ['microsoft-authenticator', 'Microsoft Authenticator', 'com.azure.authenticator'],
  ['google-authenticator', 'Google Authenticator', 'com.google.android.apps.authenticator2'],
  ['samsung-smartthings', 'SmartThings', 'com.samsung.android.oneconnect'],
];
const secondApps = [...firstApps, ...addedApps];
const apps = [...secondApps, ...thirdApps];
const firstFunctions = [...baseFunctions, ...firstApps.map(([id]) => id)];
const secondFunctions = [...baseFunctions, ...secondApps.map(([id]) => id)];
const functions = [...baseFunctions, ...apps.map(([id]) => id)];
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
let temporary, source, sourceBefore, legacySource, legacyBefore, previousSource, previousBefore,
  firstSource, firstBefore, secondSource, secondBefore;

function execute(command, args, options = {}) {
  return spawnSync(command, args, { cwd: root, encoding: 'utf8', windowsHide: true,
    timeout: 180000, maxBuffer: 4 * 1024 * 1024, ...options });
}

function exportTo(input, output, negative = false) {
  // A bad channel proves admission errors occur before browser selection/launch.
  return execute(process.execPath, [exporter, '--input', input, '--output', output], {
    env: { ...process.env, ...(negative ? { THEME_BROWSER_CHANNEL: 'unavailable-before-admission-test' } : {}) },
  });
}

async function snapshot(directory) {
  const files = {};
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      for (const [name, digest] of Object.entries(await snapshot(path.join(directory, entry.name)))) {
        files[`${entry.name}/${name}`] = digest;
      }
    } else files[entry.name] = sha(await readFile(path.join(directory, entry.name)));
  }
  return files;
}

function assertFailedBeforeBrowser(result, expected) {
  assert.ifError(result.error);
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.match(result.stderr, expected);
  assert.doesNotMatch(result.stderr, /browserType\.launch|unavailable-before-admission-test/);
}

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const value of bytes) {
    crc ^= value;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

// Decode saved PNG bytes independently of the browser's canvas and admission code.
function decodeRgba(bytes, size) {
  assert.deepEqual([...bytes.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  const compressed = [];
  let offset = 8, header = false, end = false;
  while (offset < bytes.length) {
    const length = bytes.readUInt32BE(offset);
    const kind = bytes.toString('ascii', offset + 4, offset + 8);
    assert.ok(offset + 12 + length <= bytes.length, 'PNG chunk is complete');
    assert.equal(crc32(bytes.subarray(offset + 4, offset + 8 + length)), bytes.readUInt32BE(offset + 8 + length));
    const data = bytes.subarray(offset + 8, offset + 8 + length);
    if (kind === 'IHDR') {
      assert.equal(header, false); header = true;
      assert.equal(length, 13); assert.equal(data.readUInt32BE(0), size); assert.equal(data.readUInt32BE(4), size);
      assert.deepEqual([...data.subarray(8)], [8, 6, 0, 0, 0], '8-bit noninterlaced RGBA PNG');
    } else if (kind === 'IDAT') compressed.push(data);
    else if (kind === 'IEND') { assert.equal(length, 0); end = true; }
    offset += length + 12;
    if (end) break;
  }
  assert.ok(header && end && compressed.length > 0);
  assert.equal(offset, bytes.length);
  const stride = size * 4;
  const raw = inflateSync(Buffer.concat(compressed), { maxOutputLength: (stride + 1) * size });
  assert.equal(raw.length, (stride + 1) * size);
  const rgba = Buffer.alloc(stride * size);
  const paeth = (a, b, c) => {
    const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
    return pa <= pb && pa <= pc ? a : (pb <= pc ? b : c);
  };
  for (let y = 0; y < size; y += 1) {
    const filter = raw[y * (stride + 1)];
    assert.ok(filter <= 4);
    for (let index = 0; index < stride; index += 1) {
      const current = y * stride + index;
      const left = index >= 4 ? rgba[current - 4] : 0;
      const above = y > 0 ? rgba[current - stride] : 0;
      const upperLeft = y > 0 && index >= 4 ? rgba[current - stride - 4] : 0;
      const prediction = filter === 0 ? 0 : filter === 1 ? left : filter === 2 ? above :
        filter === 3 ? Math.floor((left + above) / 2) : paeth(left, above, upperLeft);
      rgba[current] = (raw[y * (stride + 1) + index + 1] + prediction) & 255;
    }
  }
  return rgba;
}

before(async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'clair-obscur-icon-export-'));
  source = path.join(temporary, 'svg');
  const result = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', source]);
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  sourceBefore = await snapshot(source);
  legacySource = path.join(temporary, 'legacy-svg');
  const legacy = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', legacySource, '--version', '0.1.0']);
  assert.ifError(legacy.error);
  assert.equal(legacy.status, 0, legacy.stdout + legacy.stderr);
  legacyBefore = await snapshot(legacySource);
  previousSource = path.join(temporary, 'previous-svg');
  const previous = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', previousSource, '--version', '0.2.0']);
  assert.ifError(previous.error);
  assert.equal(previous.status, 0, previous.stdout + previous.stderr);
  previousBefore = await snapshot(previousSource);
  firstSource = path.join(temporary, 'first-app-svg');
  const first = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', firstSource, '--version', '0.3.0']);
  assert.ifError(first.error);
  assert.equal(first.status, 0, first.stdout + first.stderr);
  firstBefore = await snapshot(firstSource);
  assert.equal(firstBefore['manifest.json'], 'd52bfef3a1504cfa90117c155458479677f5ecf27a9b98f99df9c3b8c87d15e3',
    'The accepted first-collection manifest remains exact');
  secondSource = path.join(temporary, 'second-app-svg');
  const second = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', secondSource, '--version', '0.4.0']);
  assert.ifError(second.error);
  assert.equal(second.status, 0, second.stdout + second.stderr);
  secondBefore = await snapshot(secondSource);
  assert.equal(secondBefore['manifest.json'], 'e41b32db1e23c63564957f253d81c449f8aa1f85493890cc07908ad1906c7527',
    'The accepted second-collection manifest remains exact');
});

after(async () => {
  if (temporary) {
    assert.equal(path.dirname(temporary).toLowerCase(), tmpdir().toLowerCase());
    assert.ok(path.basename(temporary).startsWith('clair-obscur-icon-export-'));
    await rm(temporary, { recursive: true });
  }
});

test('PNG command exports all 356 usable icons with independent saved-file decoding and assignment identities', async () => {
  const output = path.join(temporary, 'png');
  const result = exportTo(source, output);
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /Exported 356 PNG icons/);
  const manifestBytes = await readFile(path.join(output, 'manifest.json'));
  const manifest = JSON.parse(manifestBytes);
  const expected = ['manifest.json', 'LICENSE'];
  assert.equal(manifest.version, '0.5.0');
  assert.equal(manifest.exporter_version, '0.5.0');
  assert.equal(manifest.files.length, 356);
  assert.deepEqual(manifest.functions, functions);
  assert.equal(manifest.source_manifest_sha256, sourceBefore['manifest.json']);
  assert.equal(manifest.tokens_sha256, sha(await readFile(path.join(root, 'tokens.json'))));
  assert.equal(manifest.svg_generator_sha256, sha(await readFile(path.join(root, 'themeforge/icons.py'))));
  assert.equal(manifest.svg_catalog_sha256, sha(await readFile(path.join(root, 'themeforge/icon_apps.py'))));
  const svgManifest = JSON.parse(await readFile(path.join(source, 'manifest.json')));
  assert.deepEqual(manifest.catalog, svgManifest.catalog, 'Complete admitted assignment metadata survives PNG export');
  assert.equal(manifest.catalog.length, 89);
  assert.equal(manifest.catalog_date, '2026-10-19');
  assert.equal(manifest.catalog_scope, svgManifest.catalog_scope);
  assert.match(manifest.catalog_scope, /Not an ordered popularity chart or exhaustive catalog/);
  assert.deepEqual(manifest.catalog.filter(entry => entry.kind === 'function').map(entry => entry.id), baseFunctions);
  assert.deepEqual(manifest.catalog.filter(entry => entry.kind === 'app').map(entry =>
    [entry.id, entry.label, entry.android_package]), apps);
  for (const entry of manifest.catalog.filter(entry => entry.kind === 'app')) {
    assert.equal(entry.store_url, `https://play.google.com/store/apps/details?id=${entry.android_package}`);
    for (const field of ['category', 'store_title', 'selection_basis']) assert.ok(entry[field].trim());
  }
  assert.equal(manifest.exporter_sha256, sha(await readFile(exporter)));
  const license = await readFile(path.join(output, 'LICENSE'));
  assert.deepEqual(license, await readFile(path.join(root, 'LICENSE')));
  assert.deepEqual(manifest.license, { path: 'LICENSE', bytes: license.length, sha256: sha(license) });
  assert.equal(manifest.renderer.mode, 'isolated headless');
  assert.equal(manifest.renderer.network_requests, 0);
  assert.ok(manifest.renderer.browser && manifest.renderer.playwright && manifest.renderer.node);
  assert.equal(manifestBytes.toString().includes(root), false, 'No checkout path enters the export manifest');
  assert.equal(manifestBytes.toString().includes(temporary), false, 'No temporary or user path enters the export manifest');
  const palettes = JSON.parse(await readFile(path.join(root, 'tokens.json'))).themes;
  const records = new Map(manifest.files.map(record => [record.path, record]));
  assert.equal(records.size, 356);
  for (const appearance of ['Clair', 'Obscur']) for (const size of [512, 1024]) {
    const hashes = functions.map(name => records.get(`${appearance}/${size}/${name}.png`)?.sha256);
    assert.equal(new Set(hashes).size, 89, `${appearance}/${size} retains 89 distinct drawings`);
    assert.equal(hashes.includes(undefined), false);
  }
  for (const appearance of ['Clair', 'Obscur']) for (const size of [512, 1024]) for (const name of functions) {
    const relative = `${appearance}/${size}/${name}.png`;
    expected.push(relative);
    const bytes = await readFile(path.join(output, relative));
    const record = records.get(relative);
    assert.ok(record);
    assert.equal(record.sha256, sha(bytes)); assert.equal(record.bytes, bytes.length);
    assert.equal(record.source_svg_sha256, sourceBefore[`${appearance}/${name}.svg`]);
    assert.equal(record.width, size); assert.equal(record.height, size);
    assert.equal(record.pixel_check.nontransparent_border_pixels, 0);
    assert.ok(record.pixel_check.counts.text > 100 && record.pixel_check.counts.accent > 20);
    const rgba = decodeRgba(bytes, size);
    const colors = ['panel', 'text', 'accent'].map(role => {
      const value = palettes[appearance][role];
      return [1, 3, 5].map(offset => parseInt(value.slice(offset, offset + 2), 16));
    });
    const counts = [0, 0, 0];
    let transparent = 0;
    for (let y = 0; y < size; y += 1) for (let x = 0; x < size; x += 1) {
      const index = (y * size + x) * 4, alpha = rgba[index + 3];
      if (alpha === 0) transparent += 1;
      if (x < size / 16 || y < size / 16 || x >= size * 15 / 16 || y >= size * 15 / 16) assert.equal(alpha, 0, 'Full outer margin stays transparent');
      if (alpha !== 255) continue;
      for (let role = 0; role < colors.length; role += 1) {
        if (rgba[index] === colors[role][0] && rgba[index + 1] === colors[role][1] && rgba[index + 2] === colors[role][2]) counts[role] += 1;
      }
    }
    assert.ok(transparent > 0 && counts[0] > size * size / 3 && counts[1] > 100 && counts[2] > 20, `${relative} preserves its visible drawing`);
  }
  assert.deepEqual(Object.keys(await snapshot(output)).sort(), expected.sort());
  assert.deepEqual(await snapshot(source), sourceBefore);
});

for (const version of ['0.1.0', '0.2.0', '0.3.0', '0.4.0']) test(`accepted ${version} SVG artwork exports its complete PNG set with its own version and source identities`, async () => {
  const historical = {
    '0.1.0': { input: legacySource, before: legacyBefore, functions: baseFunctions, images: 96 },
    '0.2.0': { input: previousSource, before: previousBefore, functions: baseFunctions, images: 96 },
    '0.3.0': { input: firstSource, before: firstBefore, functions: firstFunctions, images: 228,
      apps: firstApps, date: '2026-10-18' },
    '0.4.0': { input: secondSource, before: secondBefore, functions: secondFunctions, images: 324,
      apps: secondApps, date: '2026-10-19' },
  }[version];
  const historicalSource = historical.input, historicalBefore = historical.before;
  const historicalFunctions = historical.functions, imageCount = historical.images;
  const output = path.join(temporary, `historical-png-${version}`);
  const result = exportTo(historicalSource, output);
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, new RegExp(`Exported ${imageCount} PNG icons`));
  const manifest = JSON.parse(await readFile(path.join(output, 'manifest.json')));
  assert.equal(manifest.version, version);
  assert.equal(manifest.exporter_version, '0.5.0');
  assert.equal(manifest.source_manifest_sha256, historicalBefore['manifest.json']);
  assert.deepEqual(manifest.functions, historicalFunctions);
  if (historical.apps) {
    const svgManifest = JSON.parse(await readFile(path.join(historicalSource, 'manifest.json')));
    for (const field of ['catalog', 'catalog_date', 'catalog_scope']) assert.deepEqual(manifest[field], svgManifest[field]);
    assert.equal(manifest.catalog_date, historical.date, 'Historical inspection date is preserved');
    assert.deepEqual(manifest.catalog.filter(entry => entry.kind === 'app').map(entry =>
      [entry.id, entry.label, entry.android_package]), historical.apps);
    assert.equal(manifest.svg_catalog_sha256, sha(await readFile(path.join(root, 'themeforge/icon_apps.py'))),
      'A new rebuild records the catalog module actually used, without rewriting old PNG deliveries');
  } else for (const field of ['catalog', 'catalog_date', 'catalog_scope', 'svg_catalog_sha256']) {
    assert.equal(Object.hasOwn(manifest, field), false, 'Historical functions do not acquire named-app metadata');
  }
  assert.deepEqual(manifest.sizes, [512, 1024]);
  assert.equal(manifest.renderer.network_requests, 0);
  const expected = ['LICENSE', 'manifest.json'];
  assert.equal(manifest.files.length, imageCount);
  const records = new Map(manifest.files.map(record => [record.path, record]));
  assert.equal(records.size, imageCount);
  for (const appearance of ['Clair', 'Obscur']) for (const size of [512, 1024]) {
    const hashes = [];
    for (const name of historicalFunctions) {
      const relative = `${appearance}/${size}/${name}.png`;
      expected.push(relative);
      const record = records.get(relative);
      assert.ok(record, `${relative} has a manifest record`);
      const bytes = await readFile(path.join(output, relative));
      assert.equal(record.sha256, sha(bytes));
      assert.equal(record.bytes, bytes.length);
      assert.equal(record.source_svg_sha256, historicalBefore[`${appearance}/${name}.svg`]);
      assert.equal(record.width, size); assert.equal(record.height, size);
      hashes.push(record.sha256);
      if (name === 'phone' || name === 'camera') {
        const rgba = decodeRgba(bytes, size);
        assert.equal(rgba[3], 0, 'Legacy PNG keeps its transparent corner');
        assert.ok(rgba.some((value, index) => index % 4 === 3 && value > 0), 'Legacy drawing remains visible');
      }
    }
    assert.equal(new Set(hashes).size, historicalFunctions.length, `${appearance}/${size} retains every historical drawing`);
  }
  assert.deepEqual(Object.keys(await snapshot(output)).sort(), expected.sort());
  assert.deepEqual(await snapshot(historicalSource), historicalBefore);
  assert.deepEqual(await snapshot(source), sourceBefore);
});

test('unknown and mismatched artwork versions are refused before output reservation or browser launch', async () => {
  const admitted = [['0.1.0', legacySource], ['0.2.0', previousSource], ['0.3.0', firstSource],
    ['0.4.0', secondSource], ['0.5.0', source]];
  const cases = [['unknown', source, '9.9.9']];
  for (const [actual, original] of admitted) for (const [claimed] of admitted) {
    if (actual !== claimed) cases.push([`${actual}-as-${claimed}`, original, claimed]);
  }
  for (const [name, original, version] of cases) {
    const input = path.join(temporary, name);
    await cp(original, input, { recursive: true });
    const manifestPath = path.join(input, 'manifest.json');
    const manifest = JSON.parse(await readFile(manifestPath));
    manifest.version = version;
    await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
    const before = await snapshot(input);
    const output = path.join(temporary, `${name}-output`);
    assertFailedBeforeBrowser(exportTo(input, output, true), name === 'unknown' ? /unsupported artwork version/ : /Icon output differs/);
    await assert.rejects(lstat(output), { code: 'ENOENT' });
    assert.deepEqual(await snapshot(input), before);
  }
});

test('altered app assignments and mixed previous/current artwork fail admission without changing their evidence', async () => {
  for (const mutation of ['label', 'android_package', 'store_url', 'store_title', 'category',
    'selection_basis', 'catalog_date', 'catalog_scope', 'historical-first-label', 'historical-second-label',
    'mixed-version-svg', 'mixed-version-manifest']) {
    const input = path.join(temporary, `assignment-${mutation}`);
    await cp(mutation === 'historical-first-label' ? firstSource :
      mutation === 'historical-second-label' ? secondSource : source, input, { recursive: true });
    const manifestPath = path.join(input, 'manifest.json');
    const manifest = JSON.parse(await readFile(manifestPath));
    if (mutation === 'mixed-version-svg') {
      await cp(path.join(secondSource, 'Clair', 'x.svg'), path.join(input, 'Clair', 'github.svg'));
    } else if (mutation === 'mixed-version-manifest') {
      await cp(path.join(secondSource, 'manifest.json'), manifestPath);
    } else {
      if (mutation.startsWith('catalog_')) manifest[mutation] = 'unqualified replacement';
      else if (mutation === 'historical-first-label') manifest.catalog.find(entry => entry.id === 'google-chrome').label = 'unqualified replacement';
      else if (mutation === 'historical-second-label') manifest.catalog.find(entry => entry.id === 'google-meet').label = 'unqualified replacement';
      else manifest.catalog.find(entry => entry.id === 'github')[mutation] = 'unqualified replacement';
      await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
    }
    const before = await snapshot(input);
    const output = path.join(temporary, `assignment-${mutation}-output`);
    assertFailedBeforeBrowser(exportTo(input, output, true), /Icon output differs/);
    await assert.rejects(lstat(output), { code: 'ENOENT' });
    assert.deepEqual(await snapshot(input), before);
  }
});

test('a catalog module edit during export refuses the final manifest and preserves rendered evidence', async () => {
  // A disposable source copy introduces a harmless module edit at the final
  // qualification boundary. The admitted drawings and input manifest stay valid,
  // so the catalog identity check, rather than an unrelated parse error, must fail.
  const fixture = path.join(temporary, 'catalog-drift-fixture');
  await mkdir(path.join(fixture, 'tools'), { recursive: true });
  await cp(path.join(root, 'themeforge'), path.join(fixture, 'themeforge'), { recursive: true });
  for (const name of ['tokens.json', 'LICENSE', 'package.json']) {
    await cp(path.join(root, name), path.join(fixture, name));
  }
  await symlink(path.join(root, 'node_modules'), path.join(fixture, 'node_modules'),
    process.platform === 'win32' ? 'junction' : 'dir');
  const original = await readFile(exporter, 'utf8');
  const boundary = '    // Retain any partial output if source changes or final qualification fails.\n';
  assert.equal(original.split(boundary).length, 2, 'One explicit final qualification boundary is instrumented');
  const fixtureExporter = path.join(fixture, 'tools', 'export-icons.mjs');
  await writeFile(fixtureExporter, original.replace(boundary, boundary +
    "    await writeFile(path.join(root, 'themeforge/icon_apps.py'), '\\n# Owned drift fixture\\n', { flag: 'a' });\n"));
  const output = path.join(temporary, 'catalog-drift-output');
  const result = execute(process.execPath, [fixtureExporter, '--input', source, '--output', output]);
  assert.ifError(result.error);
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.match(result.stderr, /Named-app catalog module changed during export/);
  assert.doesNotMatch(result.stderr, /Icon output differs|browserType\.launch|SyntaxError|ModuleNotFoundError/);
  assert.equal((await lstat(path.join(output, 'Clair', '512', 'google-chrome.png'))).isFile(), true,
    'The source-change refusal retains completed image evidence');
  await assert.rejects(lstat(path.join(output, 'manifest.json')), { code: 'ENOENT' });
  assert.deepEqual(await snapshot(source), sourceBefore);
  assert.equal(await readFile(exporter, 'utf8'), original, 'The real exporter was never patched');
  assert.notEqual(sha(await readFile(path.join(fixture, 'themeforge/icon_apps.py'))),
    sha(await readFile(path.join(root, 'themeforge/icon_apps.py'))));
});

test('changed, missing and extra SVG or manifest inputs fail before browser launch and preserve evidence', async () => {
  for (const mutation of ['changed-svg', 'missing-svg', 'extra-svg', 'changed-manifest', 'missing-manifest', 'extra-directory']) {
    const input = path.join(temporary, mutation);
    await cp(source, input, { recursive: true });
    if (mutation === 'changed-svg') await writeFile(path.join(input, 'Clair', 'phone.svg'), '<svg/>');
    if (mutation === 'missing-svg') await rm(path.join(input, 'Clair', 'phone.svg'));
    if (mutation === 'extra-svg') await writeFile(path.join(input, 'Clair', 'extra.svg'), '<svg/>');
    if (mutation === 'changed-manifest') await writeFile(path.join(input, 'manifest.json'), '{}');
    if (mutation === 'missing-manifest') await rm(path.join(input, 'manifest.json'));
    if (mutation === 'extra-directory') await mkdir(path.join(input, 'extra'));
    const before = await snapshot(input);
    const output = path.join(temporary, `${mutation}-output`);
    assertFailedBeforeBrowser(exportTo(input, output, true), /Icon output differs/);
    await assert.rejects(lstat(output), { code: 'ENOENT' });
    assert.deepEqual(await snapshot(input), before);
    if (mutation === 'extra-directory') assert.equal((await lstat(path.join(input, 'extra'))).isDirectory(), true);
  }
});

test('existing, nested-input, root and managed output paths are refused before browser launch', async () => {
  const occupied = path.join(temporary, 'occupied');
  const empty = path.join(temporary, 'empty');
  const existingFile = path.join(temporary, 'existing-file');
  await mkdir(occupied); await writeFile(path.join(occupied, 'keep.txt'), 'preserve');
  await mkdir(empty); await writeFile(existingFile, 'preserve file');
  for (const target of [occupied, empty, existingFile]) {
    assertFailedBeforeBrowser(exportTo(source, target, true), /new output directory/);
  }
  assert.deepEqual(await snapshot(occupied), { 'keep.txt': sha('preserve') });
  assert.deepEqual(await readdir(empty), []);
  assert.equal(await readFile(existingFile, 'utf8'), 'preserve file');
  assertFailedBeforeBrowser(exportTo(source, path.join(source, 'new-output'), true), /must not be inside the SVG input tree/);
  await assert.rejects(lstat(path.join(source, 'new-output')), { code: 'ENOENT' });
  assertFailedBeforeBrowser(exportTo(source, path.parse(root).root, true), /filesystem root/);
  assertFailedBeforeBrowser(exportTo(source, path.join(root, 'dist', 'icon-export-test'), true), /managed desktop dist/);
  assert.deepEqual(await snapshot(source), sourceBefore);
});

test('linked or junction output ancestors are refused before browser launch without modifying their target', async () => {
  const destination = path.join(temporary, 'link-target');
  const linked = path.join(temporary, 'linked-output-parent');
  await mkdir(destination); await writeFile(path.join(destination, 'keep.txt'), 'unchanged');
  await symlink(destination, linked, process.platform === 'win32' ? 'junction' : 'dir');
  assertFailedBeforeBrowser(exportTo(source, path.join(linked, 'png'), true), /links or reparse/);
  assert.deepEqual(await snapshot(destination), { 'keep.txt': sha('unchanged') });
  const linkedInput = path.join(temporary, 'linked-input');
  await symlink(source, linkedInput, process.platform === 'win32' ? 'junction' : 'dir');
  const output = path.join(temporary, 'linked-input-output');
  assertFailedBeforeBrowser(exportTo(linkedInput, output, true), /links or reparse/);
  await assert.rejects(lstat(output), { code: 'ENOENT' });
  assert.deepEqual(await snapshot(source), sourceBefore);
});

test('a linked child manifest is refused before parsing its owned target or launching a browser', async t => {
  for (const [name, contents] of [
    ['malformed', '{owned malformed JSON fixture'],
    ['unsupported', JSON.stringify({ version: '9.9.9' })],
  ]) {
    const input = path.join(temporary, `linked-manifest-${name}`);
    await cp(source, input, { recursive: true });
    const manifestPath = path.join(input, 'manifest.json');
    await rm(manifestPath);
    const target = path.join(temporary, `manifest-target-${name}.json`);
    await writeFile(target, contents);
    try {
      await symlink(target, manifestPath, 'file');
    } catch (error) {
      if (process.platform === 'win32' && ['EPERM', 'EACCES', 'ENOTSUP', 'ENOSYS'].includes(error.code)) {
        t.skip(`Windows file symlink fixture unavailable: ${error.code}`);
        return;
      }
      throw error;
    }
    const before = await snapshot(input);
    const targetBefore = await readFile(target);
    const linkBefore = await readlink(manifestPath);
    const output = path.join(temporary, `linked-manifest-${name}-output`);
    const result = exportTo(input, output, true);
    assertFailedBeforeBrowser(result, /links? or reparse/);
    assert.doesNotMatch(result.stderr, /missing or invalid|unsupported artwork version|JSONDecodeError/,
      'Link refusal must precede target parsing or version admission');
    await assert.rejects(lstat(output), { code: 'ENOENT' });
    assert.equal((await lstat(manifestPath)).isSymbolicLink(), true);
    assert.equal(await readlink(manifestPath), linkBefore);
    assert.deepEqual(await readFile(target), targetBefore);
    assert.deepEqual(await snapshot(input), before);
  }
});

test('a failed renderer retains its newly reserved output and never repairs it on a second attempt', async () => {
  const output = path.join(temporary, 'failed-render-output');
  const result = exportTo(source, output, true);
  assert.ifError(result.error);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /browserType\.launch/);
  assert.equal((await lstat(output)).isDirectory(), true);
  assert.deepEqual(await readdir(output), []);
  assert.deepEqual(await snapshot(source), sourceBefore);
  assertFailedBeforeBrowser(exportTo(source, output, true), /new output directory/);
  assert.deepEqual(await readdir(output), []);
});
