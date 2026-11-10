(() => {
  'use strict';
  document.querySelectorAll('[data-password-target]').forEach(button => {
    const input = document.getElementById(button.dataset.passwordTarget);
    if (!(input instanceof HTMLInputElement) || input.type !== 'password') return;
    button.hidden = false;
    button.addEventListener('click', () => {
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      button.textContent = visible ? 'Ocultar' : 'Mostrar';
      button.setAttribute('aria-label', visible ? 'Ocultar contraseña' : 'Mostrar contraseña');
      button.setAttribute('aria-pressed', String(visible));
    });
  });
})();
