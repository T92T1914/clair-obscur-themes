const choices = [...document.querySelectorAll('[data-appearance]')];
for (const choice of choices) {
  choice.addEventListener('click', () => {
    const appearance = choice.dataset.appearance;
    if (!['Clair', 'Obscur'].includes(appearance)) return;
    document.documentElement.dataset.theme = appearance;
    for (const button of choices) button.setAttribute('aria-pressed', String(button === choice));
    document.querySelector('#appearance-status').textContent = `Showing ${appearance}`;
  });
}
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
