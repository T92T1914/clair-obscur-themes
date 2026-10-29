// Each card owns its asset URL. Page appearance never selects a keyboard file.
(() => {
  const chooser = document.querySelector('#keyboard-chooser');
  const platform = document.querySelector('#keyboard-platform');
  const appearance = document.querySelector('#keyboard-appearance');
  const status = document.querySelector('#keyboard-choice-status');
  const cards = [...document.querySelectorAll('[data-keyboard-platform][data-keyboard-appearance]')];
  if (!chooser || !platform || !appearance || !status || cards.length !== 4) return;
  const update = () => {
    for (const card of cards) card.hidden = card.dataset.keyboardPlatform !== platform.value ||
      (appearance.value !== 'both' && card.dataset.keyboardAppearance !== appearance.value);
    const label = platform.selectedOptions[0].textContent;
    status.textContent = label + ': ' + (appearance.value === 'both' ? 'comparing Clair and Obscur' : appearance.value) +
      '. Design choice is independent of page appearance.';
  };
  platform.addEventListener('change', update);
  appearance.addEventListener('change', update);
  chooser.addEventListener('submit', event => event.preventDefault());
  for (const image of document.querySelectorAll('[data-keyboard-background]')) {
    const id = image.dataset.keyboardBackground;
    const link = document.querySelector('[data-keyboard-download="' + id + '"]');
    const message = document.querySelector('[data-keyboard-asset-status="' + id + '"]');
    if (!link || !message) continue;
    const unavailable = () => {
      link.hidden = true;
      image.hidden = true;
      message.textContent = 'Background unavailable in this copy. Keep a native plain theme, or obtain the complete companion bundle. No substitute image was selected.';
    };
    image.addEventListener('error', unavailable, { once: true });
    if (image.complete && image.naturalWidth === 0) unavailable();
  }
  update();
  chooser.hidden = false;
})();

// Keep the static gallery complete if this optional enhancement cannot initialize.
(() => {
  const finder = document.querySelector('#icon-finder');
  const query = document.querySelector('#icon-query');
  const kind = document.querySelector('#icon-kind');
  const mapping = document.querySelector('#icon-mapping');
  const clear = document.querySelector('#icon-clear');
  const status = document.querySelector('#icon-filter-status');
  const empty = document.querySelector('#icon-filter-empty');
  if (!finder || !query || !kind || !mapping || !clear || !status || !empty) return;
  const normalize = value => value.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase().replace(/['\u2019]/gu, '');
  const records = [...document.querySelectorAll('#icons .icon-card')].map(card => {
    const heading = card.querySelector('h4')?.textContent;
    const id = card.dataset.iconFunction;
    const type = card.dataset.iconKind;
    const mappingState = card.dataset.iconMapping;
    const packageId = card.querySelector('code')?.textContent || '';
    const group = card.closest('section[aria-labelledby]');
    if (!heading || !id || !['app', 'function'].includes(type) || !['included', 'manual'].includes(mappingState) || !group || (type === 'app' && !packageId)) return null;
    return { card, type, mappingState, group, text: normalize([heading, id, packageId].join(' ')) };
  });
  if (!records.length || records.some(record => !record)) return;
  const groups = [...new Set(records.map(record => record.group))];
  function updateIconFilter() {
    const terms = normalize(query.value).trim().split(/\s+/u).filter(Boolean);
    let shown = 0;
    for (const record of records) {
      const matches = (kind.value === 'all' || kind.value === record.type) &&
        (mapping.value === 'all' || mapping.value === record.mappingState) &&
        terms.every(term => record.text.includes(term));
      record.card.hidden = !matches;
      if (matches) shown++;
    }
    for (const group of groups) group.hidden = !records.some(record => record.group === group && !record.card.hidden);
    status.textContent = `Showing ${shown} of ${records.length} choices.`;
    empty.hidden = shown !== 0;
  }
  query.addEventListener('input', updateIconFilter);
  kind.addEventListener('change', updateIconFilter);
  mapping.addEventListener('change', updateIconFilter);
  finder.addEventListener('submit', event => event.preventDefault());
  clear.addEventListener('click', () => {
    query.value = '';
    kind.value = 'all';
    mapping.value = 'all';
    updateIconFilter();
    query.focus();
  });
  updateIconFilter();
  finder.hidden = false;
})();

// PNGs are prepared only on request from the corresponding local SVG image.
// Local-file pages keep the SVG fallback because their canvases are not origin-clean.
(() => {
  const help = document.querySelector('#icon-png-help');
  const status = document.querySelector('#icon-png-status');
  const buttons = [...document.querySelectorAll('#icons [data-icon-png]')];
  if (!help || !status || !buttons.length) return;
  if (!['http:', 'https:'].includes(location.protocol)) {
    help.textContent = 'Direct PNG downloads require the hosted preview. This local copy keeps every SVG archive and the full PNG export instructions below.';
    return;
  }
  const probe = document.createElement('canvas');
  try {
    if (typeof probe.toBlob !== 'function' || !probe.getContext('2d') ||
        typeof URL.createObjectURL !== 'function' || typeof URL.revokeObjectURL !== 'function') return;
  } catch { return; }
  const records = buttons.map(button => {
    const card = button.closest('[data-icon-function]');
    const image = button.closest('figure')?.querySelector('img');
    const id = card?.dataset.iconFunction;
    const version = card?.dataset.iconVersion;
    const appearance = button.dataset.iconAppearance;
    if (!image || !/^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/u.test(id || '') ||
        !/^\d+\.\d+\.\d+$/u.test(version || '') || !['Clair', 'Obscur'].includes(appearance)) return null;
    const source = `icons/${appearance}/${id}.svg`;
    const filename = `Clair-Obscur-${version}-${appearance}-${id}-512.png`;
    if (image.getAttribute('src') !== source || button.dataset.iconFilename !== filename) return null;
    const url = new URL(source, location.href);
    if (url.origin !== location.origin) return null;
    return { button, image, source: url.href, filename };
  });
  if (records.some(record => !record)) return;
  let preparing = false;
  for (const record of records) {
    const { button, image, source, filename } = record;
    button.addEventListener('click', async () => {
      if (preparing) return;
      preparing = true;
      for (const pending of records) pending.button.setAttribute('aria-disabled', 'true');
      status.textContent = `Preparing ${filename}...`;
      try {
        if (!image.complete || image.naturalWidth !== 512 || image.naturalHeight !== 512 ||
            image.currentSrc !== source) throw new Error('The icon image is unavailable');
        await image.decode();
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 512;
        const context = canvas.getContext('2d');
        if (!context) throw new Error('PNG rendering is unavailable');
        context.drawImage(image, 0, 0, 512, 512);
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
        if (!blob || blob.type !== 'image/png' || !blob.size) throw new Error('PNG encoding failed');
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.hidden = true;
        document.body.append(link);
        try { link.click(); }
        finally {
          link.remove();
          // Let the browser acquire the blob before releasing its temporary URL.
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        }
        status.textContent = `Prepared ${filename}. Your browser handles the download.`;
      } catch {
        status.textContent = 'Could not prepare this PNG. Try again after the image loads, or use the SVG archive and PNG export instructions below.';
      } finally {
        for (const pending of records) pending.button.removeAttribute('aria-disabled');
        preparing = false;
      }
    });
    button.hidden = false;
  }
  help.textContent = 'Use PNG 512 beside an appearance to prepare that individual image in your browser. Each file is 512 by 512 pixels with a transparent outer margin. The full SVG archives and two-size PNG export remain available.';
})();

document.querySelector('#sample-button').addEventListener('click', () => {
  document.querySelector('#control-status').textContent = 'Control activated. This specimen changes no application settings.';
});

const chooser = document.querySelector('#package-chooser');
const target = document.querySelector('#package-target');
const packageAppearance = document.querySelector('#package-appearance');
const choiceStatus = document.querySelector('#package-choice-status');
const choiceResult = document.querySelector('#package-choice-result');
if (chooser && target && packageAppearance && choiceStatus && choiceResult) {
  function updatePackageChoice() {
    choiceResult.replaceChildren();
    choiceResult.hidden = true;
    if (!target.value) {
      choiceStatus.textContent = 'Choose a target to see its package and matching local guide.';
      return;
    }
    const appearance = packageAppearance.value;
    const anchor = `guide-${target.value}-${appearance.toLowerCase()}`;
    const route = [...document.querySelectorAll('#downloads .download-card .guide-link')]
      .find(link => link.getAttribute('href') === '#' + anchor);
    const card = route?.closest('.download-card');
    const group = card?.closest('.platform-group');
    const guide = document.getElementById(anchor);
    const action = card?.querySelector('a.button[download]');
    const identity = guide?.querySelector('p');
    const hash = guide?.querySelector('.package-hash');
    const limits = card?.querySelector('small:not(.local-package-path)');
    const description = group?.querySelector('p');
    if (!action || !identity || !hash || !limits || !description) {
      choiceStatus.textContent = 'This package route is unavailable in this preview. Use the full catalog below.';
      return;
    }
    const label = target.selectedOptions[0].textContent;
    const heading = document.createElement('h4');
    heading.textContent = `${appearance} for ${label}`;
    const packageIdentity = identity.cloneNode(true);
    // Reuse captured identity text without adding a second filename action.
    packageIdentity.querySelectorAll('a').forEach(link => link.replaceWith(document.createTextNode(link.textContent)));
    packageIdentity.querySelectorAll('.local-package-path').forEach(node => node.remove());
    const pathLine = document.createElement('p');
    pathLine.className = 'package-choice-path';
    const pathValue = document.createElement('code');
    pathValue.setAttribute('translate', 'no');
    pathValue.textContent = action.getAttribute('href');
    pathLine.append('Package file: ', pathValue);
    const packageAction = action.cloneNode(true);
    packageAction.id = 'package-choice-file';
    const guideAction = route.cloneNode(true);
    guideAction.id = 'package-choice-guide';
    const actions = document.createElement('div');
    actions.className = 'chooser-actions';
    actions.append(packageAction, guideAction);
    choiceResult.append(heading, packageIdentity, pathLine, hash.cloneNode(true),
      limits.cloneNode(true), description.cloneNode(true), actions);
    const sharedLimits = group.dataset.sharedLimits && document.getElementById(group.dataset.sharedLimits);
    if (sharedLimits) {
      const copy = sharedLimits.cloneNode(true);
      copy.removeAttribute('id');
      choiceResult.append(copy);
    }
    choiceStatus.textContent = `Selected ${appearance} for ${label}. Package: ${card.querySelector('h4').textContent}.`;
    choiceResult.hidden = false;
  }
  target.addEventListener('change', updatePackageChoice);
  packageAppearance.addEventListener('change', updatePackageChoice);
  updatePackageChoice();
  chooser.hidden = false;
}

const checker = document.querySelector('#local-package-checker');
const localFile = document.querySelector('#local-package-file');
const clearFile = document.querySelector('#local-package-clear');
const fileSelection = document.querySelector('#local-package-selection');
const fileStatus = document.querySelector('#local-package-status');
const fileResult = document.querySelector('#local-package-result');
const fileBound = document.querySelector('#local-package-bound');
if (checker && localFile && clearFile && fileSelection && fileStatus && fileResult && fileBound) {
  let generation = 0;
  let references = [];
  let maxBytes = 0;
  let validCatalog = false;
  try {
    const routes = [...document.querySelectorAll('#downloads .download-card .guide-link')];
    const anchors = new Set();
    const paths = new Map();
    references = routes.map(route => {
      const href = route.getAttribute('href');
      const guide = href?.startsWith('#guide-') && document.getElementById(href.slice(1));
      const card = route.closest('.download-card');
      const group = card?.closest('.platform-group');
      const action = card?.querySelector('a.button[download]');
      const identity = guide?.querySelector('p');
      const hash = guide?.querySelector('.package-hash');
      const digest = hash?.querySelector('code')?.textContent.trim();
      const heading = guide?.querySelector('h4');
      const limits = card?.querySelector('small:not(.local-package-path)');
      const description = group?.querySelector('p');
      const sharedLimits = group?.dataset.sharedLimits && document.getElementById(group.dataset.sharedLimits);
      const sizeText = card?.dataset.packageBytes;
      const bytes = Number(sizeText);
      const path = action?.getAttribute('href');
      if (!guide || !identity || !heading || !limits || !description || !/^[0-9a-f]{64}$/.test(digest)
          || !/^[1-9]\d*$/.test(sizeText) || !Number.isSafeInteger(bytes)
          || !path?.startsWith('downloads/') || identity.querySelector('a[download]')?.getAttribute('href') !== path
          || anchors.has(href) || (group.dataset.sharedLimits && !sharedLimits)) {
        throw new Error('Incomplete captured package reference');
      }
      const previous = paths.get(path);
      if (previous && (previous.digest !== digest || previous.bytes !== bytes)) {
        throw new Error('Conflicting captured package reference');
      }
      paths.set(path, { digest, bytes });
      anchors.add(href);
      return { route, identity, hash, digest, heading, limits, description, sharedLimits, path, bytes };
    });
    const expectedAnchors = new Set([...target.options].filter(option => option.value).flatMap(option =>
      [...packageAppearance.options].map(appearance => `#guide-${option.value}-${appearance.value.toLowerCase()}`)));
    if (!references.length || expectedAnchors.size !== anchors.size
        || [...expectedAnchors].some(anchor => !anchors.has(anchor))) {
      throw new Error('Missing captured package references');
    }
    maxBytes = Math.max(...references.map(reference => reference.bytes));
    validCatalog = true;
    fileBound.textContent = `Package files only, up to ${maxBytes.toLocaleString('en-US')} bytes, the largest package referenced here. Larger files are not read.`;
  } catch {
    references = [];
    localFile.disabled = true;
    fileBound.textContent = 'The captured package references are unavailable. Use the full catalog and its guide hashes below.';
  }

  function setFileState(state, message) {
    checker.dataset.state = state;
    fileStatus.textContent = message;
  }
  function resetFileResult() {
    fileResult.replaceChildren();
    fileResult.hidden = true;
    fileSelection.textContent = '';
  }
  function hashingAvailable() {
    return typeof File !== 'undefined' && typeof File.prototype.arrayBuffer === 'function'
      && typeof globalThis.crypto?.subtle?.digest === 'function';
  }
  function showReadyState() {
    if (!validCatalog) {
      setFileState('unavailable', 'Package identification is unavailable because the captured references are incomplete. No digest was computed. Compare the guide hashes or Theme build checksums below.');
    } else if (!hashingAvailable()) {
      setFileState('unavailable', 'Local file reading or SHA-256 is unavailable in this browser context. No digest was computed. Compare the guide hashes or Theme build checksums below.');
    } else {
      setFileState('idle', 'Select a package file to identify its matching local guides.');
    }
  }
  function showFileMatch(reference) {
    const item = document.createElement('article');
    item.className = 'identified-package';
    const heading = document.createElement('h4');
    heading.textContent = reference.heading.textContent;
    const identity = reference.identity.cloneNode(true);
    identity.querySelectorAll('a').forEach(link => link.replaceWith(document.createTextNode(link.textContent)));
    identity.querySelectorAll('.local-package-path').forEach(node => node.remove());
    const pathLine = document.createElement('p');
    pathLine.className = 'identified-package-path';
    const pathValue = document.createElement('code');
    pathValue.setAttribute('translate', 'no');
    pathValue.textContent = reference.path;
    pathLine.append('Referenced package file: ', pathValue);
    item.append(heading, identity, pathLine, reference.hash.cloneNode(true),
      reference.limits.cloneNode(true), reference.description.cloneNode(true), reference.route.cloneNode(true));
    if (reference.sharedLimits) {
      const copy = reference.sharedLimits.cloneNode(true);
      copy.removeAttribute('id');
      item.append(copy);
    }
    fileResult.append(item);
  }
  localFile.addEventListener('change', async () => {
    const owner = ++generation;
    resetFileResult();
    const file = localFile.files[0];
    if (!file) { showReadyState(); return; }
    fileSelection.textContent = `Selected file: ${file.name} (${file.size.toLocaleString('en-US')} bytes).`;
    if (!validCatalog) { showReadyState(); return; }
    if (!Number.isSafeInteger(file.size) || file.size < 0 || file.size > maxBytes) {
      setFileState('size-rejected', `This file exceeds the ${maxBytes.toLocaleString('en-US')}-byte package limit. It was not read and no digest was computed. Use the separate source or kit checksums for those archives.`);
      return;
    }
    if (!hashingAvailable() || typeof file.arrayBuffer !== 'function') {
      setFileState('unavailable', 'Local file reading or SHA-256 is unavailable in this browser context. No digest was computed. Compare the guide hashes or Theme build checksums below.');
      return;
    }
    setFileState('checking', 'Reading the selected package and computing its local SHA-256.');
    let bytes;
    try {
      bytes = await file.arrayBuffer();
      if (owner !== generation) return;
      if (!(bytes instanceof ArrayBuffer) || bytes.byteLength !== file.size) throw new Error('Incomplete file read');
    } catch {
      if (owner === generation) setFileState('read-failed', 'The selected file could not be read completely. No digest was computed. Select it again or use the guide hashes below.');
      return;
    }
    let digest;
    try {
      const hashed = await globalThis.crypto.subtle.digest('SHA-256', bytes);
      if (owner !== generation) return;
      if (!(hashed instanceof ArrayBuffer) || hashed.byteLength !== 32) throw new Error('Incomplete SHA-256 result');
      digest = [...new Uint8Array(hashed)].map(byte => byte.toString(16).padStart(2, '0')).join('');
    } catch {
      if (owner === generation) setFileState('hash-failed', 'Local SHA-256 could not be computed. No digest comparison was made. Select the file again or use the guide hashes below.');
      return;
    }
    const digestLine = document.createElement('p');
    digestLine.className = 'local-file-hash';
    const digestValue = document.createElement('code');
    digestValue.setAttribute('translate', 'no');
    digestValue.textContent = digest;
    digestLine.append('Computed SHA-256: ', digestValue);
    fileResult.append(digestLine);
    const matches = references.filter(reference => reference.digest === digest);
    matches.forEach(showFileMatch);
    setFileState(matches.length ? 'matched' : 'no-match', matches.length
      ? `The selected bytes match the SHA-256 reference captured here for ${matches.length} target and appearance ${matches.length === 1 ? 'guide' : 'guides'}.`
      : 'The computed SHA-256 matches no package referenced by this preview. This result does not establish file origin, safety or native compatibility.');
    fileResult.hidden = false;
  });
  clearFile.addEventListener('click', () => {
    generation++;
    localFile.value = '';
    resetFileResult();
    showReadyState();
  });
  showReadyState();
  checker.hidden = false;
}
