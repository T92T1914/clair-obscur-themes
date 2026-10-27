// Resolve only presentation before paint. Storage is an optional visitor choice.
(() => {
  const root = document.documentElement;
  const key = 'clair-obscur-preview-appearance';
  const valid = new Set(['Auto', 'Clair', 'Obscur']);
  const system = typeof matchMedia === 'function' ? matchMedia('(prefers-color-scheme: light)') : null;
  let choice = 'Obscur';
  try {
    const saved = localStorage.getItem(key);
    if (valid.has(saved)) choice = saved;
  } catch { /* The static Obscur page needs no storage. */ }
  function apply() {
    const appearance = choice === 'Auto' ? (system?.matches ? 'Clair' : 'Obscur') : choice;
    root.dataset.theme = appearance;
    for (const button of document.querySelectorAll('button[data-appearance]')) {
      button.setAttribute('aria-pressed', String(button.dataset.appearance === choice));
    }
    const status = document.querySelector('#appearance-status');
    if (status) status.textContent = choice === 'Auto' ? `Showing ${appearance} from the system setting` : `Showing ${appearance}`;
  }
  apply();
  system?.addEventListener?.('change', () => { if (choice === 'Auto') apply(); });
  document.addEventListener('DOMContentLoaded', () => {
    apply();
    for (const button of document.querySelectorAll('button[data-appearance]')) {
      button.addEventListener('click', () => {
        if (!valid.has(button.dataset.appearance)) return;
        choice = button.dataset.appearance;
        apply();
        try { localStorage.setItem(key, choice); } catch { /* Optional preference. */ }
      });
    }
  });
})();
