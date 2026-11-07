(() => {
  'use strict';

  // Event delegation also covers archive forms inserted by table refreshes.
  document.addEventListener('submit', async event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.matches('.archive-form')) return;
    event.preventDefault();
    if (form.dataset.confirming === 'true') return;
    form.dataset.confirming = 'true';
    let confirmed = false;
    try {
      if (window.Swal) {
        const result = await window.Swal.fire({
          title: '¿Archivar este registro?',
          text: `${form.dataset.record || 'El registro'} dejará de aparecer en los listados activos.`,
          icon: 'warning', showCancelButton: true, focusCancel: true,
          confirmButtonText: 'Archivar registro', cancelButtonText: 'Cancelar',
          buttonsStyling: false,
          customClass: { confirmButton: 'btn btn-primary m-2', cancelButton: 'btn btn-outline-secondary m-2' }
        });
        confirmed = result.isConfirmed;
      } else {
        confirmed = window.confirm('¿Archivar este registro? Dejará de aparecer en los listados activos.');
      }
      if (confirmed) HTMLFormElement.prototype.submit.call(form);
    } finally {
      delete form.dataset.confirming;
    }
  });

  document.querySelectorAll('.field-errors').forEach(errors => {
    if (!errors.textContent.trim()) return;
    const wrapper = errors.closest('.form-field');
    if (!wrapper) return;
    wrapper.classList.add('has-error');
    wrapper.querySelectorAll('input, select, textarea').forEach(input => input.setAttribute('aria-invalid', 'true'));
  });

  const modalElement = document.querySelector('#record-modal');
  if (modalElement && window.bootstrap?.Modal) {
    document.documentElement.classList.add('modal-enhanced');
    const modal = new window.bootstrap.Modal(modalElement);
    modalElement.addEventListener('shown.bs.modal', () => {
      const target = modalElement.querySelector('.error-summary, input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea');
      target?.focus();
    });
    modalElement.addEventListener('hidden.bs.modal', () => {
      window.location.assign(modalElement.dataset.returnUrl);
    });
    modal.show();
  } else {
    const errors = document.querySelector('.error-summary, .account-section .alert-danger');
    if (errors) { errors.tabIndex = -1; errors.focus(); }
  }

  const recordForm = document.querySelector('[data-subatenciones-url]');
  if (recordForm) {
    const type = recordForm.querySelector('[name="tipo"]');
    const sub = recordForm.querySelector('[name="subatencion"]');
    const status = document.querySelector('#subatencion-status');
    const save = recordForm.querySelector('[type="submit"]');
    let controller;
    async function updateSubatenciones(preserve) {
      controller?.abort();
      const currentController = new AbortController();
      controller = currentController;
      const previous = preserve ? sub.value : '';
      const selected = type.value;
      sub.replaceChildren(new Option('Selecciona una subatención', ''));
      if (!/^\d{1,12}$/.test(selected) || !Array.from(type.options).some(option => option.value === selected)) {
        sub.disabled = true;
        save.disabled = false;
        status.textContent = 'Selecciona primero un tipo de atención.';
        return;
      }
      sub.disabled = true;
      save.disabled = true;
      status.textContent = 'Cargando subatenciones…';
      const url = new URL(recordForm.dataset.subatencionesUrl, window.location.origin);
      url.searchParams.set('tipo', selected);
      try {
        const response = await fetch(url, { signal: currentController.signal, credentials: 'same-origin', headers: { Accept: 'application/json' } });
        if (!response.ok || response.redirected) throw new Error('subatenciones');
        const data = await response.json();
        if (!Array.isArray(data.results)) throw new Error('subatenciones');
        if (controller !== currentController) return;
        data.results.forEach(item => sub.add(new Option(item.nombre, String(item.id))));
        sub.value = previous;
        sub.disabled = false;
        save.disabled = false;
        status.textContent = data.results.length ? 'Selecciona la subatención que corresponde.' : 'Este tipo no tiene subatenciones activas. Selecciona otro tipo.';
      } catch (error) {
        if (error.name === 'AbortError' || controller !== currentController) return;
        save.disabled = false;
        status.textContent = 'No pudimos cargar las subatenciones. Vuelve a seleccionar el tipo para intentar nuevamente.';
      }
    }
    if (type && sub) {
      type.addEventListener('change', () => updateSubatenciones(false));
      updateSubatenciones(true);
    }
  }

  const table = document.querySelector('[data-realtime-table]');
  const status = document.querySelector('#realtime-status');
  if (!table || !status) return;
  if (!window.WebSocket) {
    status.dataset.state = 'error';
    status.textContent = 'Tu navegador no admite actualizaciones en tiempo real. Recarga la página para consultar cambios.';
    return;
  }
  let socket;
  let fetching = false;
  let pending = false;
  let reconnects = 0;
  let reconnectTimer;
  let stopped = false;

  function setStatus(state, message) {
    status.dataset.state = state;
    status.textContent = message;
  }
  async function refreshTable() {
    pending = true;
    if (fetching) return;
    fetching = true;
    try {
      while (pending && !stopped) {
        pending = false;
        setStatus('connecting', 'Conexión activa. Actualizando los registros…');
        const url = new URL(table.dataset.tableUrl, window.location.origin);
        url.search = window.location.search;
        try {
          const response = await fetch(url, {
            credentials: 'same-origin', cache: 'no-store',
            headers: { Accept: 'text/html', 'X-Requested-With': 'XMLHttpRequest' }
          });
          if (!response.ok || response.redirected) throw new Error('tabla');
          const html = await response.text();
          const fragment = new DOMParser().parseFromString(html, 'text/html');
          if (!fragment.querySelector('.records-table')) throw new Error('tabla');
          if (stopped) return;
          const region = document.querySelector('#tabla-region');
          // Keep the focused table action when the same record still exists.
          const active = region.contains(document.activeElement) ? document.activeElement : null;
          const focusedHref = active?.getAttribute('href');
          const focusedAction = active?.closest('form')?.getAttribute('action');
          region.replaceChildren(...Array.from(fragment.body.childNodes));
          if (focusedHref) Array.from(region.querySelectorAll('a')).find(a => a.getAttribute('href') === focusedHref)?.focus();
          else if (focusedAction) Array.from(region.querySelectorAll('form')).find(form => form.getAttribute('action') === focusedAction)?.querySelector('button')?.focus();
          if (!pending && socket?.readyState === WebSocket.OPEN) setStatus('connected', 'Conectado. Tabla actualizada con los filtros actuales.');
        } catch {
          setStatus('error', 'No pudimos actualizar la tabla. Conservamos los datos visibles; recarga la página para consultar el estado actual.');
        }
      }
    } finally {
      fetching = false;
    }
  }
  function connect() {
    if (stopped) return;
    setStatus('connecting', 'Conectando actualizaciones en tiempo real…');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    socket = new WebSocket(`${protocol}//${window.location.host}/ws/atenciones/`);
    socket.addEventListener('open', () => {
      reconnects = 0;
      refreshTable();
    });
    socket.addEventListener('message', event => {
      try { if (JSON.parse(event.data).type === 'tabla.cambio') refreshTable(); } catch { /* Ignore non-table messages. */ }
    });
    socket.addEventListener('error', () => setStatus('error', 'La conexión en tiempo real tuvo un problema. Los datos visibles pueden haber cambiado.'));
    socket.addEventListener('close', () => {
      if (stopped) return;
      setStatus('disconnected', 'Sin conexión en tiempo real. Los datos visibles pueden haber cambiado.');
      if (reconnects < 6) {
        const delay = Math.min(1000 * (2 ** reconnects), 30000);
        reconnects += 1;
        reconnectTimer = window.setTimeout(connect, delay);
      } else {
        setStatus('disconnected', 'No se pudo restablecer la conexión. Recarga la página para consultar cambios.');
      }
    });
  }
  window.addEventListener('pagehide', () => {
    stopped = true;
    window.clearTimeout(reconnectTimer);
    socket?.close();
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted) { stopped = false; reconnects = 0; connect(); }
  });
  connect();
})();
