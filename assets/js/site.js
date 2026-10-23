// Progressive enhancement: the theme toggle and abstract toggles appear only when this runs.

// Theme: follows the system until the reader chooses, then remembers the choice.
document.querySelectorAll('.theme-toggle').forEach((toggle) => {
  const root = document.documentElement;
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)');
  const current = () => root.dataset.theme || (systemDark.matches ? 'dark' : 'light');
  const label = () => {
    toggle.textContent = current() === 'dark' ? 'Light theme' : 'Dark theme';
  };

  toggle.addEventListener('click', () => {
    const next = current() === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    try {
      localStorage.setItem('theme', next);
    } catch (error) {}
    label();
  });
  systemDark.addEventListener('change', label);
  label();
  toggle.closest('li').hidden = false;
});

// Abstracts in publication lists open in place.
document.querySelectorAll('.abstract-toggle').forEach((toggle) => {
  const abstract = document.getElementById(toggle.getAttribute('aria-controls'));
  if (!abstract) return;

  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open));
    abstract.hidden = !open;
  });
  toggle.closest('li').hidden = false;
});
