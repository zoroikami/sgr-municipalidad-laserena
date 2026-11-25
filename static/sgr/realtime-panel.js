/* Los sockets solo avisan: cada panel se obtiene otra vez por su vista GET autorizada. */
(() => {
  'use strict';

  const allowed = new Set(['tubo', 'cartas', 'casos', 'sgr']);
  document.querySelectorAll('[data-realtime-panel]').forEach((region, index) => {
    const module = region.dataset.realtimeModule;
    const status = document.querySelectorAll('[data-realtime-status]')[index];
    if (!allowed.has(module) || !status || region.dataset.realtimeReady) return;
    region.dataset.realtimeReady = 'true';
    const message = document.createElement('span');
    const update = document.createElement('button');
    update.type = 'button';
    update.className = 'btn btn-outline-secondary btn-sm flex-shrink-0';
    update.textContent = 'Actualizar';
    update.hidden = true;
    status.setAttribute('aria-live', 'polite');
    // Reservar la altura del aviso evita mover las tarjetas al conectar o reconectar.
    status.classList.add('d-flex', 'align-items-center', 'gap-2');
    status.style.minHeight = 'var(--legacy-control-height)';
    message.className = 'flex-grow-1';
    message.style.minWidth = '0';
    status.replaceChildren(message, document.createTextNode(' '), update);

    let socket;
    let pending = false;
    let fetching = false;
    let stopped = false;
    let attempts = 0;
    let retryTimer;
    let refreshTimer;
    let controller;

    function setStatus(state, text, showUpdate = false) {
      if (status.dataset.state !== state) status.dataset.state = state;
      if (message.textContent !== text) message.textContent = text;
      if (update.hidden === showUpdate) update.hidden = !showUpdate;
    }

    function interacting() {
      const active = document.activeElement;
      return (region.contains(active) && active.matches('input, select, textarea, [contenteditable="true"]'))
        || Boolean(document.querySelector('.tubo-arrastrando, .swal2-container'));
    }

    function defer() {
      setStatus('pending', 'Hay cambios nuevos', true);
      if (!refreshTimer && !stopped) {
        refreshTimer = window.setTimeout(() => {
          refreshTimer = null;
          refresh();
        }, 250);
      }
    }

    function fieldKey(field) {
      const form = field.form;
      return [form?.getAttribute('action') || '', form?.dataset.destino || '', field.name, field.type].join('|');
    }

    function drafts(root) {
      const saved = new Map();
      root.querySelectorAll('input[name], textarea[name], select[name]').forEach(field => {
        if (['hidden', 'file', 'submit', 'button'].includes(field.type)) return;
        const check = ['checkbox', 'radio'].includes(field.type);
        if (check ? field.checked !== field.defaultChecked : field.value !== field.defaultValue) {
          saved.set(fieldKey(field), {value: field.value, checked: field.checked});
        }
      });
      return saved;
    }

    function focusKey(element) {
      if (!element || !region.contains(element)) return null;
      return {id: element.id, tag: element.tagName, href: element.getAttribute('href'),
        form: element.closest('form')?.getAttribute('action'), text: element.textContent.trim()};
    }

    function restoreFocus(key) {
      if (!key) return;
      const target = Array.from(region.querySelectorAll('a, button, [tabindex]')).find(el =>
        (key.id && el.id === key.id) || (el.tagName === key.tag && el.getAttribute('href') === key.href
          && el.closest('form')?.getAttribute('action') === key.form && el.textContent.trim() === key.text));
      target?.focus({preventScroll: true});
    }

    async function refresh() {
      if (stopped || fetching || !pending) return;
      if (interacting()) { defer(); return; }
      pending = false;
      fetching = true;
      const requestedUrl = window.location.href;
      controller = new AbortController();
      setStatus('connecting', 'Actualizando los registros…');
      try {
        const response = await fetch(requestedUrl, {credentials: 'same-origin', cache: 'no-store',
          headers: {Accept: 'text/html', 'X-Requested-With': 'XMLHttpRequest'}, signal: controller.signal});
        if (!response.ok || response.redirected) throw new Error('panel');
        const documentCopy = new DOMParser().parseFromString(await response.text(), 'text/html');
        const replacement = region.id ? documentCopy.getElementById(region.id)
          : documentCopy.querySelector(`[data-realtime-panel][data-realtime-module="${module}"]`);
        if (!replacement || replacement.dataset.realtimeModule !== module) throw new Error('panel');
        if (stopped || requestedUrl !== window.location.href) return;
        // El usuario puede comenzar a escribir o arrastrar mientras termina el GET.
        if (interacting()) { pending = true; defer(); return; }
        const savedDrafts = drafts(region);
        const focus = focusKey(document.activeElement);
        const x = window.scrollX, y = window.scrollY;
        const scrollSelector = '.table-responsive, .tubo-columnas, .tubo-columna';
        const scrolls = Array.from(region.querySelectorAll(scrollSelector), el => [el.scrollLeft, el.scrollTop]);
        region.replaceChildren(...Array.from(replacement.childNodes));
        region.querySelectorAll('input[name], textarea[name], select[name]').forEach(field => {
          const saved = savedDrafts.get(fieldKey(field));
          if (!saved || ['hidden', 'file'].includes(field.type)) return;
          field.value = saved.value;
          if (['checkbox', 'radio'].includes(field.type)) field.checked = saved.checked;
        });
        document.dispatchEvent(new CustomEvent('sgr:content-updated', {detail: {region}}));
        region.querySelectorAll(scrollSelector).forEach((el, i) => {
          if (scrolls[i]) { el.scrollLeft = scrolls[i][0]; el.scrollTop = scrolls[i][1]; }
        });
        restoreFocus(focus);
        window.scrollTo({left: x, top: y, behavior: 'instant'});
        if (pending) defer();
        else if (socket && socket.readyState === window.WebSocket.OPEN) setStatus('connected', 'Conectado. Datos actualizados con los filtros actuales.');
        else setStatus('disconnected', 'Datos actualizados. La conexión en tiempo real está interrumpida.', true);
      } catch (error) {
        if (!stopped && error.name !== 'AbortError') {
          setStatus('error', 'No pudimos actualizar. Conservamos los datos visibles; puedes volver a intentarlo.', true);
        }
      } finally {
        fetching = false;
        if (pending && !stopped) defer();
      }
    }

    function invalidate() {
      pending = true;
      refresh();
    }

    function connect() {
      if (stopped) return;
      setStatus('connecting', 'Conectando actualizaciones en tiempo real…');
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(`${protocol}//${window.location.host}/ws/modulos/${module}/`);
      socket.addEventListener('open', () => { attempts = 0; invalidate(); });
      socket.addEventListener('message', event => {
        try { if (JSON.parse(event.data).type === 'tabla.cambio') invalidate(); } catch { /* Aviso inválido. */ }
      });
      socket.addEventListener('error', () => {
        if (!stopped) setStatus('error', 'La conexión en tiempo real tuvo un problema.');
      });
      socket.addEventListener('close', () => {
        if (stopped) return;
        setStatus('disconnected', 'Sin conexión en tiempo real. Intentando reconectar…');
        if (attempts < 6) {
          retryTimer = window.setTimeout(connect, Math.min(1000 * (2 ** attempts++), 30000));
        } else {
          setStatus('disconnected', 'No se pudo restablecer la conexión. Recarga la página para reconectar.');
        }
      });
    }

    update.addEventListener('click', invalidate);
    region.addEventListener('focusout', () => { if (pending) defer(); });
    region.addEventListener('dragend', () => { if (pending) defer(); });
    window.addEventListener('pagehide', () => {
      stopped = true;
      window.clearTimeout(retryTimer);
      window.clearTimeout(refreshTimer);
      refreshTimer = null;
      controller?.abort();
      socket?.close();
    });
    window.addEventListener('pageshow', event => {
      if (event.persisted) { stopped = false; attempts = 0; connect(); }
    });
    if (window.WebSocket) connect();
    else setStatus('error', 'Tu navegador no admite actualizaciones en tiempo real. Puedes actualizar los datos con el botón.', true);
  });
})();
