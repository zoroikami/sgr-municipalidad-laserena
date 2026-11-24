(() => {
  'use strict';

  document.querySelectorAll('[data-tablero-dnd]').forEach(board => {
    const cards = board.querySelectorAll('.tubo-tarjeta[draggable="true"]');
    if (!window.Swal || !HTMLFormElement.prototype.requestSubmit) {
      cards.forEach(card => card.removeAttribute('draggable'));
      return;
    }
    board.classList.add('tubo-dnd-listo');
    const columns = Array.from(board.querySelectorAll('.tubo-columna[data-estado]'));
    const interactive = 'a, button, input, select, textarea, [contenteditable="true"]';
    let dragged = null;
    let busy = false;
    let startedOnControl = false;

    function destinationForm(column) {
      if (!dragged || !column) return null;
      return Array.from(dragged.querySelectorAll('form[data-destino]'))
        .find(form => form.dataset.destino === column.dataset.estado) || null;
    }

    function clearDrag() {
      dragged?.classList.remove('tubo-arrastrando');
      columns.forEach(column => column.classList.remove('tubo-destino', 'tubo-sobre-destino'));
      dragged = null;
    }

    async function confirmMove(form, card) {
      busy = true;
      const note = form.elements.namedItem('observacion');
      const code = card.querySelector('.tubo-codigos strong').textContent.trim();
      try {
        const result = await window.Swal.fire({
          titleText: 'Cambiar estado',
          text: `${code}: ${form.dataset.destino}.`,
          input: 'textarea', inputLabel: 'Observación (opcional)',
          inputValue: note.value, inputAttributes: { maxlength: '2000' },
          showCancelButton: true, focusCancel: true,
          confirmButtonText: 'Mover tarjeta', cancelButtonText: 'Cancelar',
          buttonsStyling: false,
          customClass: {
            confirmButton: 'btn btn-primary m-2',
            cancelButton: 'btn btn-outline-secondary m-2'
          }
        });
        if (result.isConfirmed) {
          note.value = result.value || '';
          form.requestSubmit();
        }
      } finally {
        busy = false;
      }
    }

    board.addEventListener('pointerdown', event => {
      startedOnControl = Boolean(event.target.closest(interactive));
    });
    board.addEventListener('dragstart', event => {
      const card = event.target.closest('.tubo-tarjeta[draggable="true"]');
      if (!card || busy || startedOnControl || event.target.closest(interactive)) {
        event.preventDefault();
        return;
      }
      dragged = card;
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', card.querySelector('.tubo-codigos strong').textContent.trim());
      card.classList.add('tubo-arrastrando');
      columns.forEach(column => column.classList.toggle('tubo-destino', Boolean(destinationForm(column))));
    });
    board.addEventListener('dragover', event => {
      const column = event.target.closest('.tubo-columna');
      if (!destinationForm(column)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      columns.forEach(item => item.classList.toggle('tubo-sobre-destino', item === column));
    });
    board.addEventListener('dragleave', event => {
      const column = event.target.closest('.tubo-columna');
      if (column && !column.contains(event.relatedTarget)) column.classList.remove('tubo-sobre-destino');
    });
    board.addEventListener('drop', event => {
      const form = destinationForm(event.target.closest('.tubo-columna'));
      if (!form || busy) return;
      event.preventDefault();
      const card = dragged;
      clearDrag();
      void confirmMove(form, card);
    });
    board.addEventListener('dragend', clearDrag);
  });
})();
