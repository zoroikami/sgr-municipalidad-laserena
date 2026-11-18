/* Listas dependientes de los formularios (RF-003 y requisitos de la segunda entrega):
   cada lista muestra solo las opciones de la delegación y del cargo que corresponden. */
(() => {
  'use strict';
  const form = document.querySelector('#record-form');
  if (!form) return;

  const normalizar = text => text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  // Cuenta global: al elegir la delegación se recarga el formulario con sus opciones.
  form.querySelectorAll('[data-recargar-delegacion]').forEach(select => {
    select.addEventListener('change', () => {
      if (!/^\d{1,12}$/.test(select.value)) return;
      const url = new URL(window.location.href);
      url.searchParams.set('delegacion', select.value);
      window.location.assign(url);
    });
  });

  // Buscador para listas largas: filtra sin perder la opción seleccionada.
  function hacerBuscable(select) {
    if (select.dataset.buscadorListo || select.disabled) return;
    const opciones = Array.from(select.options);
    if (opciones.length <= 15) return;
    select.dataset.buscadorListo = 'true';
    const input = document.createElement('input');
    input.type = 'search';
    input.className = 'form-control select-buscador';
    input.placeholder = 'Escribe para buscar…';
    input.setAttribute('aria-label', `Buscar en ${select.labels?.[0]?.textContent.trim() || 'la lista'}`);
    input.setAttribute('aria-controls', select.id);
    const estado = document.createElement('small');
    estado.className = 'select-buscador-estado';
    estado.setAttribute('aria-live', 'polite');
    select.before(input);
    select.after(estado);
    const total = opciones.filter(option => option.value).length;
    estado.textContent = `${total} opciones`;
    input.addEventListener('input', () => {
      const termino = normalizar(input.value.trim());
      const seleccion = select.value;
      const visibles = opciones.filter(option => !option.value || option.value === seleccion
        || !termino || normalizar(option.textContent).includes(termino));
      select.replaceChildren(...visibles);
      select.value = seleccion;
      const coincidencias = visibles.filter(option => option.value && normalizar(option.textContent).includes(termino)).length;
      estado.textContent = termino ? `${coincidencias} de ${total} opciones` : `${total} opciones`;
    });
  }
  form.querySelectorAll('select[data-buscable]').forEach(hacerBuscable);

  // RF-003: al cambiar funcionario o cargo se cargan únicamente los ítems de ese cargo.
  const itemsUrl = form.dataset.itemsUrl;
  const item = form.querySelector('[name="item"]');
  const cargo = form.querySelector('[data-actividad-cargo]');
  const responsable = form.querySelector('[data-actividad-responsable]');
  if (!itemsUrl || !item || !cargo) return;
  let controller;
  async function recargarItems() {
    controller?.abort();
    const actual = new AbortController();
    controller = actual;
    const url = new URL(itemsUrl, window.location.origin);
    const delegacion = new URL(window.location.href).searchParams.get('delegacion');
    if (delegacion) url.searchParams.set('delegacion', delegacion);
    if (responsable?.value) url.searchParams.set('responsable', responsable.value);
    if (cargo.value) url.searchParams.set('cargo', cargo.value);
    try {
      const response = await fetch(url, { signal: actual.signal, credentials: 'same-origin', headers: { Accept: 'application/json' } });
      if (!response.ok || response.redirected) throw new Error('items');
      const data = await response.json();
      if (controller !== actual || !Array.isArray(data.items)) return;
      const previo = item.value;
      item.replaceChildren(new Option('---------', ''), ...data.items.map(it => new Option(it.nombre, String(it.id))));
      item.value = data.items.some(it => String(it.id) === previo) ? previo : '';
      delete item.dataset.buscadorListo;
      item.previousElementSibling?.classList.contains('select-buscador') && item.previousElementSibling.remove();
      item.nextElementSibling?.classList.contains('select-buscador-estado') && item.nextElementSibling.remove();
      hacerBuscable(item);
      cargo.value = data.cargo || '';
      cargo.disabled = Boolean(data.cargo_fijo);
    } catch (error) {
      if (error.name !== 'AbortError') item.setCustomValidity('');
    }
  }
  responsable?.addEventListener('change', recargarItems);
  cargo.addEventListener('change', recargarItems);
})();
