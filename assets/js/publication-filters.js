// Progressive enhancement: every paper remains visible without JavaScript.
document.querySelectorAll('.publications').forEach((list) => {
  const controls = list.querySelector('.publication-filters');
  if (!controls) return;

  const buttons = Array.from(controls.querySelectorAll('button[data-subject]'));
  const papers = Array.from(list.querySelectorAll('[data-paper-subjects]')).map((paper) => ({
    item: paper.closest('li'),
    subjects: paper.dataset.paperSubjects.split(' '),
  }));
  const groups = Array.from(list.querySelectorAll('ol.bibliography'));
  const status = controls.querySelector('.publication-filter-status');

  function select(button) {
    const subject = button.dataset.subject;
    let count = 0;
    papers.forEach((paper) => {
      const matches = subject === 'all' || paper.subjects.includes(subject);
      paper.item.hidden = !matches;
      if (matches) count += 1;
    });
    groups.forEach((group) => {
      group.hidden = !Array.from(group.children).some((item) => !item.hidden);
      const heading = group.previousElementSibling;
      if (heading && heading.matches('h2.bibliography')) heading.hidden = group.hidden;
    });
    buttons.forEach((option) => option.setAttribute('aria-pressed', String(option === button)));
    status.textContent = subject === 'all'
      ? `All ${count} papers`
      : `${count} ${count === 1 ? 'paper' : 'papers'} · ${button.textContent.trim()}`;
  }

  buttons.forEach((button) => button.addEventListener('click', () => select(button)));
  select(buttons[0]);
  controls.hidden = false;
});
