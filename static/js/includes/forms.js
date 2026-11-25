const formErrors = document.getElementById('form-errors');
if (formErrors) formErrors.focus();

for (const button of document.querySelectorAll('.print-action')) {
  button.hidden = false;
  button.addEventListener('click', () => window.print());
}

const menuButton = document.querySelector('.menu-toggle');
const navigation = document.getElementById('clinic-nav');
if (menuButton && navigation) {
  const narrow = window.matchMedia('(max-width: 860px)');
  function setMenu(open) {
    menuButton.setAttribute('aria-expanded', String(open));
    navigation.hidden = narrow.matches && !open;
  }
  function updateLayout() {
    menuButton.hidden = !narrow.matches;
    setMenu(false);
  }
  menuButton.addEventListener('click', () => setMenu(navigation.hidden));
  narrow.addEventListener('change', updateLayout);
  updateLayout();
}

const accountMenu = document.querySelector('.account-menu');
document.addEventListener('click', event => {
  if (accountMenu?.open && !accountMenu.contains(event.target)) accountMenu.open = false;
});
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  if (accountMenu?.open) {
    accountMenu.open = false;
    accountMenu.querySelector('summary').focus();
  } else if (menuButton?.getAttribute('aria-expanded') === 'true') {
    menuButton.click();
    menuButton.focus();
  }
});
