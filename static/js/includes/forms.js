// Native disclosure menus and links also work without JavaScript.
const menus = [...document.querySelectorAll('[data-menu]')];
for (const menu of menus) {
  menu.addEventListener('toggle', () => {
    if (!menu.open) return;
    for (const other of menus) {
      if (other !== menu) other.open = false;
    }
  });
}
document.addEventListener('click', event => {
  for (const menu of menus) {
    if (!menu.contains(event.target)) menu.open = false;
  }
});
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  const open = menus.find(menu => menu.open);
  if (open) {
    open.open = false;
    open.querySelector('summary').focus();
  }
});

const finder = document.querySelector('.service-finder');
if (finder) {
  finder.querySelector('.finder-search').hidden = false;
  const input = finder.querySelector('input');
  input.addEventListener('input', () => {
    const value = input.value.trim().toLocaleLowerCase();
    let matches = 0;
    for (const group of finder.querySelectorAll('section')) {
      for (const link of group.querySelectorAll('a')) {
        link.hidden = !link.textContent.toLocaleLowerCase().includes(value);
        if (!link.hidden) matches++;
      }
      group.hidden = !group.querySelector('a:not([hidden])');
    }
    finder.querySelector('.finder-empty').hidden = matches > 0;
  });
}

for (const button of document.querySelectorAll('.print-action')) {
  button.hidden = false;
  button.addEventListener('click', () => window.print());
}

const enrol = document.querySelector('[data-enrol]');
if (enrol) {
  const steps = [...enrol.querySelectorAll('[data-step]')];
  const next = enrol.querySelector('[data-next]');
  const back = enrol.querySelector('[data-back]');
  const submit = enrol.querySelector('[type="submit"]');
  const progress = enrol.querySelector('.stepper');
  const labels = steps.map((step, index) => {
    const item = document.createElement('li');
    item.textContent = (index + 1) + '. ' + step.dataset.step;
    progress.append(item);
    return item;
  });
  let current = 0;
  function show(index, focus) {
    current = index;
    steps.forEach((step, i) => {
      step.hidden = i !== index;
      labels[i].removeAttribute('aria-current');
    });
    labels[index].setAttribute('aria-current', 'step');
    progress.hidden = false;
    next.hidden = index === steps.length - 1;
    submit.hidden = !next.hidden;
    back.hidden = index === 0;
    if (focus) {
      const legend = steps[index].querySelector('legend');
      legend.tabIndex = -1;
      legend.focus();
    }
  }
  function advance() {
    const invalid = steps[current].querySelector(':invalid');
    if (invalid) invalid.reportValidity();
    else show(current + 1, true);
  }
  next.addEventListener('click', advance);
  back.addEventListener('click', () => show(current - 1, true));
  // Enter in an early step advances the form. The server validates every field on submission.
  enrol.addEventListener('keydown', event => {
    if (event.key === 'Enter' && event.target.matches('input') && !next.hidden) {
      event.preventDefault();
      advance();
    }
  });
  enrol.addEventListener('invalid', event => {
    const index = steps.indexOf(event.target.closest('[data-step]'));
    if (index !== -1 && steps[index].hidden) show(index, false);
  }, true);
  enrol.querySelector('#form-errors')?.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link) return;
    const field = document.getElementById(link.hash.slice(1));
    const index = steps.indexOf(field?.closest('[data-step]'));
    if (index !== -1) show(index, false);
  });
  const firstError = steps.findIndex(step => step.querySelector('[aria-invalid="true"], .errorlist'));
  show(Math.max(0, firstError), false);
}

const booking = document.querySelector('[data-booking-review]');
if (booking) {
  const fields = booking.querySelector('[data-edit-fields]');
  const reason = booking.elements.reason_for_visit;
  const preview = booking.querySelector('[data-review-copy]');
  const review = booking.querySelector('[data-review]');
  const edit = booking.querySelector('[data-edit]');
  const submit = booking.querySelector('[type="submit"]');
  function showReview(visible) {
    preview.hidden = !visible;
    fields.hidden = visible;
    edit.hidden = !visible;
    submit.hidden = !visible;
    review.hidden = visible;
  }
  review.addEventListener('click', () => {
    if (!booking.reportValidity()) return;
    preview.querySelector('p').textContent = reason.value;
    showReview(true);
    preview.tabIndex = -1;
    preview.focus();
  });
  edit.addEventListener('click', () => {
    showReview(false);
    reason.focus();
  });
  booking.addEventListener('submit', event => {
    if (preview.hidden) {
      event.preventDefault();
      review.click();
    }
  });
  showReview(false);
}

const chart = document.querySelector('[data-chart]');
if (chart) {
  const links = [...chart.querySelectorAll('.encounter-index a')];
  const panels = [...chart.querySelectorAll('[data-panel]')];
  function select(id) {
    const selected = panels.find(panel => panel.id === id) || panels[0];
    panels.forEach(panel => { panel.hidden = panel !== selected; });
    links.forEach(link => {
      if (link.hash === '#' + selected.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  const errors = chart.querySelector('#form-errors')?.closest('[data-panel]');
  select(errors?.id || location.hash.slice(1) || chart.dataset.chart);
  window.addEventListener('hashchange', () => select(location.hash.slice(1) || chart.dataset.chart));
  for (const link of links) {
    link.addEventListener('click', () => select(link.hash.slice(1)));
  }
}
document.getElementById('form-errors')?.focus();
