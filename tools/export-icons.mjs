#!/usr/bin/env node
// Render only an exact supported generated SVG set, without changing existing output.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { createRequire } from 'node:module';

const root = fileURLToPath(new URL('../', import.meta.url));
const require = createRequire(import.meta.url);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const python = process.platform === 'win32' ? ['python', '-X', 'utf8'] : ['python3'];
const sizes = [512, 1024];

function runPython(args) {
  const result = spawnSync(python[0], [...python.slice(1), ...args], {
    cwd: root, encoding: 'utf8', windowsHide: true, timeout: 30000,
    maxBuffer: 4 * 1024 * 1024,
  });
  if (result.error) throw new Error(`Python qualification failed: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`Python qualification failed: ${(result.stderr || result.stdout).trim()}`);
  return result.stdout;
}

function argumentsFor(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 2) {
    const name = argv[index];
    if (!['--input', '--output'].includes(name) || options[name] || !argv[index + 1] || argv[index + 1].startsWith('--')) {
      throw new Error('Usage: node tools/export-icons.mjs --input GENERATED_SVG_DIRECTORY --output NEW_PNG_DIRECTORY');
    }
    options[name] = path.resolve(argv[index + 1]);
  }
  if (!options['--input'] || !options['--output']) {
    throw new Error('Both --input and --output are required');
  }
  return { input: options['--input'], output: options['--output'] };
}

const inputVersion = String.raw`
import json, sys
from pathlib import Path
from themeforge.icons import VERSIONS, _linked, _safe_output

source = _safe_output(Path(sys.argv[1]))
manifest_path = source / "manifest.json"
try:
    if _linked(manifest_path):
        raise ValueError("Icon input manifest must not contain links or reparse points")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as error:
    raise ValueError("Icon output differs: input manifest is missing or invalid") from error
version = manifest.get("version") if isinstance(manifest, dict) else None
if version not in VERSIONS:
    raise ValueError("Icon output differs: unsupported artwork version")
print(version)
`;

function checkInput(input, version) {
  runPython(['-m', 'themeforge.icons', '--output', input, '--version', version, '--check']);
}

const preflight = String.raw`
import hashlib, json, sys
from pathlib import Path
from themeforge.icons import ROOT, VERSIONS, _safe_output, build_icons, render_icons
from themeforge.tokens import load

source = _safe_output(Path(sys.argv[1]))
output = _safe_output(Path(sys.argv[2]))
version = sys.argv[3]
if version not in VERSIONS:
    raise ValueError("Unsupported artwork version")
if source == output or source in output.parents:
    raise ValueError("PNG output must not be inside the SVG input tree")
if output.exists():
    raise ValueError("PNG export requires a new output directory; existing entries are preserved")
document = load(ROOT / "tokens.json")
build_icons(document, source, check=True, version=version)
expected = render_icons(document, version=version)
manifest = json.loads(expected["manifest.json"])
license_payload = (ROOT / "LICENSE").read_bytes()
def digest(payload):
    return hashlib.sha256(payload).hexdigest()
result = {
    "version": manifest["version"],
    "token_version": manifest["token_version"],
    "source_manifest_sha256": digest(expected["manifest.json"]),
    "tokens_sha256": digest((ROOT / "tokens.json").read_bytes()),
    "generator_sha256": digest((ROOT / "themeforge/icons.py").read_bytes()),
    "license": license_payload.decode("utf-8"),
    "license_sha256": digest(license_payload),
    "functions": manifest["functions"],
    "palettes": {name: {role: document["themes"][name][role] for role in ("panel", "text", "accent")}
                 for name in ("Clair", "Obscur")},
    "files": [{**entry, "svg": expected[entry["path"]].decode("utf-8")}
              for entry in manifest["files"]],
}
if "catalog" in manifest:
    result.update(catalog=manifest["catalog"], catalog_date=manifest["catalog_date"],
                  catalog_scope=manifest["catalog_scope"],
                  catalog_module_sha256=digest((ROOT / "themeforge/icon_apps.py").read_bytes()))
output.parent.mkdir(parents=True, exist_ok=True)
output = _safe_output(output)
output.mkdir(exist_ok=False)
print(json.dumps(result))
`;

async function exportIcons(input, output) {
  // The CLI check and shared Python path policy run before any browser launch.
  const version = runPython(['-c', inputVersion, input]).trim();
  checkInput(input, version);
  const source = JSON.parse(runPython(['-c', preflight, input, output, version]));
  let browser, context;
  const records = [];
  const network = [], pageErrors = [];
  try {
    browser = await chromium.launch({
      channel: process.env.THEME_BROWSER_CHANNEL || 'chrome', headless: true,
      chromiumSandbox: true,
      args: ['--mute-audio', '--disable-gpu', '--renderer-process-limit=2'],
    });
    context = await browser.newContext({ offline: true, serviceWorkers: 'block', acceptDownloads: false });
    await context.route('**/*', async route => {
      network.push(route.request().url());
      await route.abort('blockedbyclient');
    });
    const page = await context.newPage();
    page.on('pageerror', error => pageErrors.push(String(error)));
    await page.setContent('<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; script-src \'none\'; style-src \'none\'; font-src \'none\'; connect-src \'none\'">');
    for (const appearance of ['Clair', 'Obscur']) {
      for (const size of sizes) await mkdir(path.join(output, appearance, String(size)), { recursive: true });
    }
    for (const file of source.files) {
      for (const size of sizes) {
        const rendered = await page.evaluate(async ({ svg, size, palette }) => {
          const image = new Image();
          image.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
          await image.decode();
          const canvas = document.createElement('canvas');
          canvas.width = canvas.height = size;
          canvas.getContext('2d').drawImage(image, 0, 0, size, size);
          const encoded = canvas.toDataURL('image/png');
          // Decode the actual encoded PNG, rather than checking the SVG canvas alone.
          const decoded = new Image();
          decoded.src = encoded;
          await decoded.decode();
          if (decoded.naturalWidth !== size || decoded.naturalHeight !== size) throw new Error('PNG dimensions differ');
          const check = document.createElement('canvas');
          check.width = check.height = size;
          const dc = check.getContext('2d', { willReadFrequently: true });
          dc.drawImage(decoded, 0, 0);
          const pixels = dc.getImageData(0, 0, size, size).data;
          const colors = Object.fromEntries(Object.entries(palette).map(([role, color]) =>
            [role, [1, 3, 5].map(offset => parseInt(color.slice(offset, offset + 2), 16))]));
          const colorEntries = Object.entries(colors);
          const counts = { panel: 0, text: 0, accent: 0, transparent: 0 };
          const bounds = { left: size, top: size, right: -1, bottom: -1 };
          let border = 0;
          for (let y = 0; y < size; y += 1) for (let x = 0; x < size; x += 1) {
            const index = (y * size + x) * 4;
            if (pixels[index + 3] === 0) { counts.transparent += 1; continue; }
            bounds.left = Math.min(bounds.left, x); bounds.top = Math.min(bounds.top, y);
            bounds.right = Math.max(bounds.right, x); bounds.bottom = Math.max(bounds.bottom, y);
            if (x === 0 || y === 0 || x === size - 1 || y === size - 1) border += 1;
            if (pixels[index + 3] !== 255) continue;
            for (const [role, rgb] of colorEntries) {
              if (pixels[index] === rgb[0] && pixels[index + 1] === rgb[1] && pixels[index + 2] === rgb[2]) counts[role] += 1;
            }
          }
          return { png: encoded.split(',')[1], counts, bounds, border };
        }, { svg: file.svg, size, palette: source.palettes[file.appearance] });
        assert.equal(rendered.border, 0, 'PNG must retain a transparent outer margin');
        assert.deepEqual(rendered.bounds, { left: size / 16, top: size / 16,
          right: size * 15 / 16 - 1, bottom: size * 15 / 16 - 1 });
        assert.ok(rendered.counts.transparent > 0 && rendered.counts.panel > size * size / 3 &&
          rendered.counts.text > 100 && rendered.counts.accent > 20, 'PNG must retain its tile and both visible glyph colors');
        const payload = Buffer.from(rendered.png, 'base64');
        const relative = `${file.appearance}/${size}/${file.function}.png`;
        await writeFile(path.join(output, relative), payload, { flag: 'wx' });
        records.push({ path: relative, appearance: file.appearance, function: file.function,
          width: size, height: size, bytes: payload.length, sha256: sha(payload),
          source_svg_sha256: file.sha256,
          pixel_check: { counts: rendered.counts, bounds: rendered.bounds,
            nontransparent_border_pixels: rendered.border } });
      }
    }
    assert.deepEqual(network, [], 'No network request is permitted');
    assert.deepEqual(pageErrors, [], 'Rendering errors are not accepted');
    // Retain any partial output if source changes or final qualification fails.
    checkInput(input, version);
    for (const file of source.files) assert.equal(sha(await readFile(path.join(input, file.path))), file.sha256, 'SVG input changed during export');
    assert.equal(sha(await readFile(path.join(input, 'manifest.json'))), source.source_manifest_sha256, 'SVG manifest changed during export');
    assert.equal(sha(await readFile(path.join(root, 'tokens.json'))), source.tokens_sha256, 'Tokens changed during export');
    assert.equal(sha(await readFile(path.join(root, 'themeforge/icons.py'))), source.generator_sha256, 'Generator changed during export');
    if (source.catalog) {
      assert.equal(sha(await readFile(path.join(root, 'themeforge/icon_apps.py'))), source.catalog_module_sha256,
        'Named-app catalog module changed during export');
    }
    assert.equal(sha(await readFile(path.join(root, 'LICENSE'))), source.license_sha256, 'License changed during export');
    const license = Buffer.from(source.license, 'utf8');
    await writeFile(path.join(output, 'LICENSE'), license, { flag: 'wx' });
    const manifest = {
      schema_version: 1, generator: 'clair-obscur-png-export', exporter_version: '0.3.0',
      version: source.version,
      token_version: source.token_version, source_manifest_sha256: source.source_manifest_sha256,
      tokens_sha256: source.tokens_sha256, svg_generator_sha256: source.generator_sha256,
      ...(source.catalog ? { catalog: source.catalog, catalog_date: source.catalog_date,
        catalog_scope: source.catalog_scope, svg_catalog_sha256: source.catalog_module_sha256 } : {}),
      exporter_sha256: sha(await readFile(fileURLToPath(import.meta.url))),
      license: { path: 'LICENSE', bytes: license.length, sha256: source.license_sha256 },
      renderer: { browser: browser.version(), channel: process.env.THEME_BROWSER_CHANNEL || 'chrome',
        playwright: require('playwright/package.json').version, node: process.version,
        mode: 'isolated headless', network_requests: 0 },
      appearances: ['Clair', 'Obscur'], sizes, functions: source.functions,
      alpha: 'RGBA with a transparent outer margin',
      scope: 'Original PNG icon artwork; no contact sheets, fonts, app installation or physical-phone acceptance',
      files: records,
    };
    await writeFile(path.join(output, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n', { flag: 'wx' });
  } finally {
    try { await context?.close(); }
    finally { await browser?.close(); }
  }
  console.log(`Exported ${records.length} PNG icons into a new directory; phone installation remains unverified`);
}

try {
  const { input, output } = argumentsFor(process.argv.slice(2));
  await exportIcons(input, output);
} catch (error) {
  console.error(`Icon export failed: ${error.message}`);
  process.exitCode = 1;
}
