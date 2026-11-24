/* Nuevo requerimiento, punto 1: al digitar el RUT del solicitante se avisa si es un funcionario
   municipal y su cargo. El aviso no bloquea el guardado; el servidor vuelve a identificarlo. */
(() => {
  'use strict';
  const campos = document.querySelectorAll('input[data-rut-funcionario]');
  if (!campos.length) return;

  function rutValido(valor) {
    const limpio = valor.trim().toUpperCase().replace(/\./g, '').replace('-', '');
    if (!/^[0-9]{2,8}[0-9K]$/.test(limpio)) return null;
    const cuerpo = limpio.slice(0, -1).replace(/^0+/, '');
    const dv = limpio.slice(-1);
    if (!cuerpo) return null;
    let suma = 0;
    [...cuerpo].reverse().forEach((digito, indice) => { suma += Number(digito) * (2 + (indice % 6)); });
    const resto = 11 - (suma % 11);
    const esperado = resto === 11 ? '0' : resto === 10 ? 'K' : String(resto);
    return dv === esperado ? `${cuerpo}-${dv}` : null;
  }

  function crearAviso(input) {
    const aviso = document.createElement('div');
    aviso.className = 'rut-aviso';
    aviso.id = `${input.id}_funcionario`;
    aviso.setAttribute('role', 'status');
    aviso.setAttribute('aria-live', 'polite');
    aviso.hidden = true;
    const ayuda = document.getElementById(`${input.id}_help`);
    (ayuda || input).after(aviso);
    input.setAttribute('aria-describedby', `${input.getAttribute('aria-describedby') || ''} ${aviso.id}`.trim());
    return aviso;
  }

  function mostrar(aviso, datos) {
    const titulo = document.createElement('p');
    titulo.className = 'rut-aviso-titulo';
    const etiqueta = document.createElement('span');
    etiqueta.className = 'rut-aviso-etiqueta';
    etiqueta.textContent = 'Funcionario municipal';
    const nombre = document.createElement('strong');
    nombre.textContent = datos.nombre;
    titulo.append(etiqueta, nombre);
    const cargo = document.createElement('p');
    cargo.className = 'rut-aviso-cargo';
    cargo.textContent = [datos.cargo_nombre, datos.delegacion && `Delegación ${datos.delegacion}`].filter(Boolean).join(' · ');
    const partes = [titulo, cargo];
    if (datos.funciones) {
      const funciones = document.createElement('p');
      funciones.className = 'rut-aviso-funciones';
      funciones.textContent = datos.funciones;
      partes.push(funciones);
    }
    if (datos.es_delegado) {
      const regla = document.createElement('p');
      regla.className = 'rut-aviso-regla';
      regla.textContent = 'El solicitante es el delegado: se registra como otra gestión y no suma puntaje.';
      partes.push(regla);
    }
    aviso.classList.toggle('es-delegado', Boolean(datos.es_delegado));
    aviso.replaceChildren(...partes);
    aviso.hidden = false;
  }

  campos.forEach(input => {
    const url = input.dataset.rutFuncionario;
    const token = input.form?.querySelector('[name="csrfmiddlewaretoken"]')?.value;
    if (!url || !token) return;
    const aviso = crearAviso(input);
    let consultado = '';
    let temporizador;
    let controlador;

    async function verificar() {
      const rut = rutValido(input.value);
      if (!rut) {
        consultado = '';
        aviso.hidden = true;
        return;
      }
      if (rut === consultado) return;
      consultado = rut;
      controlador?.abort();
      const actual = new AbortController();
      controlador = actual;
      try {
        const cuerpo = new FormData();
        cuerpo.append('rut', rut);
        const respuesta = await fetch(url, {
          method: 'POST', body: cuerpo, signal: actual.signal, credentials: 'same-origin',
          headers: { 'X-CSRFToken': token, Accept: 'application/json' },
        });
        if (!respuesta.ok || respuesta.redirected) throw new Error('rut');
        const datos = await respuesta.json();
        if (controlador !== actual) return;
        if (datos.funcionario) mostrar(aviso, datos);
        else aviso.hidden = true;
      } catch (error) {
        if (error.name !== 'AbortError') {
          consultado = '';
          aviso.hidden = true;
        }
      }
    }

    input.addEventListener('input', () => {
      clearTimeout(temporizador);
      temporizador = setTimeout(verificar, 350);
    });
    input.addEventListener('change', verificar);
    if (input.value) verificar();
  });
})();
