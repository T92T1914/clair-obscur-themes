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
