(() => {
  const pendingControls = new Map();
  let pendingForms = new WeakSet();
  const loadingLinks = 'a.button[href], a[data-page-load][href]';
  const submittedControls = 'button[type="submit"]:not([hidden]):not(:disabled), button:not([type]):not([hidden]):not(:disabled), input[type="submit"]:not([hidden]):not(:disabled)';

  function start(control) {
    if (!control || pendingControls.has(control) || control.disabled) return;
    let wrapper;
    if (control instanceof HTMLInputElement) {
      wrapper = document.createElement('span');
      wrapper.className = 'button-loading-input';
      control.before(wrapper);
      wrapper.append(control);
    } else {
      control.classList.add('button-loading');
    }
    control.setAttribute('aria-busy', 'true');
    control.setAttribute('aria-disabled', 'true');
    pendingControls.set(control, wrapper);
    // Keep the clicked submit button enabled until the browser has collected its name and value.
    if ('disabled' in control) {
      setTimeout(() => {
        if (pendingControls.has(control)) control.disabled = true;
      }, 0);
    }
  }

  document.addEventListener('submit', event => {
    if (event.defaultPrevented) return;
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (pendingForms.has(form)) {
      event.preventDefault();
      return;
    }
    const control = event.submitter ?? form.querySelector(submittedControls);
    const target = control?.getAttribute('formtarget') || form.target;
    const method = control?.getAttribute('formmethod') || form.method;
    if ((target && target !== '_self') || method === 'dialog') return;
    pendingForms.add(form);
    start(control);
  });

  document.addEventListener('click', event => {
    const control = event.target?.closest?.('button, input, a');
    if (!pendingControls.has(control)) return;
    event.preventDefault();
    event.stopPropagation();
  }, true);

  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button !== 0) return;
    const control = event.target?.closest?.('button[data-page-load], ' + loadingLinks);
    if (!control) return;
    if (control instanceof HTMLAnchorElement) {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || control.matches('[download], [data-download]')) return;
      if (control.target && control.target !== '_self') return;
      const url = new URL(control.href);
      if (url.origin !== location.origin || (url.pathname === location.pathname && url.search === location.search && url.hash)) return;
    }
    start(control);
  });

  // Restore controls when the browser brings the previous document back from history.
  window.addEventListener('pageshow', event => {
    if (!event.persisted) return;
    for (const [control, wrapper] of pendingControls) {
      control.classList.remove('button-loading');
      control.removeAttribute('aria-busy');
      control.removeAttribute('aria-disabled');
      if ('disabled' in control) control.disabled = false;
      if (wrapper) wrapper.replaceWith(control);
    }
    pendingControls.clear();
    pendingForms = new WeakSet();
  });
})();
