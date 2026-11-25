/* Roles y permisos: los contadores de cada módulo y del resumen siguen a las casillas antes de guardar. */
(() => {
  'use strict';
  const modulos = [...document.querySelectorAll('.permission-module')];
  if (!modulos.length) return;
  const totalPermisos = document.querySelector('[data-total-permisos]');
  const totalModulos = document.querySelector('[data-total-modulos]');

  const recalcular = () => {
    let permisos = 0, conAcceso = 0;
    modulos.forEach(modulo => {
      const cajas = [...modulo.querySelectorAll('input[type=checkbox]')];
      const marcados = cajas.filter(caja => caja.checked).length;
      const pastilla = modulo.querySelector('.permission-cantidad');
      if (pastilla) {
        pastilla.textContent = `${marcados} de ${cajas.length}`;
        pastilla.setAttribute('aria-label', `${marcados} de ${cajas.length} acciones habilitadas`);
      }
      modulo.dataset.tono = !marcados ? 'gris' : marcados === cajas.length ? 'verde' : 'ambar';
      permisos += marcados;
      if (marcados) conAcceso += 1;
    });
    if (totalPermisos) totalPermisos.textContent = permisos.toLocaleString('es-CL');
    if (totalModulos) totalModulos.textContent = conAcceso.toLocaleString('es-CL');
  };

  modulos.forEach(modulo => modulo.addEventListener('change', recalcular));
})();
