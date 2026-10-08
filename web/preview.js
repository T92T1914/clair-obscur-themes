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
