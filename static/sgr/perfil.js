(() => {
  'use strict';
  const form = document.querySelector('#profile-form');
  if (!form) return;
  const input = form.querySelector('[name="foto"]');
  const source = document.querySelector('#crop-source');
  const panel = document.querySelector('#crop-panel');
  const previewPanel = document.querySelector('#crop-preview-panel');
  const preview = document.querySelector('#crop-preview');
  const status = document.querySelector('#crop-status');
  const save = document.querySelector('#profile-save');
  const apply = document.querySelector('#crop-apply');
  let cropper = null;
  let original = null;
  let sourceURL = null;
  let previewURL = null;
  let finalFile = null;
  let sequence = 0;

  function releaseSource() {
    if (cropper) cropper.destroy();
    cropper = null;
    original = null;
    if (sourceURL) URL.revokeObjectURL(sourceURL);
    sourceURL = null;
    panel.hidden = true;
  }

  function cancel() {
    sequence += 1;
    releaseSource();
    if (previewURL) URL.revokeObjectURL(previewURL);
    previewURL = null;
    finalFile = null;
    input.value = '';
    previewPanel.hidden = true;
    save.disabled = false;
    status.textContent = 'Se conservará tu foto actual.';
  }

  input.addEventListener('change', () => {
    const file = input.files[0];
    if (!file) return;
    cancel();
    const generation = sequence;
    if (!['image/jpeg', 'image/png'].includes(file.type) || file.size > 2 * 1024 * 1024) {
      status.textContent = 'Selecciona un JPEG o PNG de hasta 2 MiB.';
      return;
    }
    if (typeof window.Croppr !== 'function') {
      status.textContent = 'No se pudo cargar el recorte. Recarga la página e intenta nuevamente.';
      return;
    }
    save.disabled = true;
    sourceURL = URL.createObjectURL(file);
    original = new Image();
    const image = original;
    image.onload = () => {
      if (generation !== sequence) return;
      source.onload = () => {
        if (generation !== sequence) return;
        cropper = new window.Croppr(source, {
          aspectRatio: 1, startSize: [80, 80, '%'], minSize: [1, 1, 'px'], returnMode: 'real',
          onInitialize: () => {
            status.textContent = 'Ajusta el recorte y selecciona Usar este recorte.';
            apply.disabled = false;
          }
        });
      };
      panel.hidden = false;
      source.src = sourceURL;
    };
    image.onerror = () => {
      if (generation !== sequence) return;
      cancel();
      status.textContent = 'No pudimos leer la foto. Selecciona otra imagen.';
    };
    apply.disabled = true;
    image.src = sourceURL;
  });

  function adjustCrop(dx = 0, dy = 0, scale = 1) {
    if (!cropper) return;
    const bounds = cropper.imageEl.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    const box = cropper.getValue('raw');
    const maximum = Math.min(bounds.width, bounds.height);
    const side = Math.min(maximum, Math.max(Math.min(16, maximum), box.width * scale));
    const x = Math.max(0, Math.min(bounds.width - side, box.x + (box.width - side) / 2 + dx));
    const y = Math.max(0, Math.min(bounds.height - side, box.y + (box.height - side) / 2 + dy));
    // Croppr's public move/scale methods do not enforce pointer-drag constraints.
    cropper.resizeTo(side, side, [0, 0]);
    cropper.moveTo(x, y);
  }

  form.querySelectorAll('[data-crop-move]').forEach(button => {
    button.addEventListener('click', () => {
      if (!cropper) return;
      const direction = button.dataset.cropMove;
      const step = 10;
      adjustCrop(direction === 'left' ? -step : direction === 'right' ? step : 0,
        direction === 'up' ? -step : direction === 'down' ? step : 0);
    });
  });
  form.querySelectorAll('[data-crop-scale]').forEach(button => {
    button.addEventListener('click', () => {
      adjustCrop(0, 0, Number(button.dataset.cropScale));
    });
  });

  apply.addEventListener('click', () => {
    if (!cropper || !original) return;
    const generation = sequence;
    const box = cropper.getValue('real');
    const x = Math.max(0, Math.min(original.naturalWidth - 1, Math.round(box.x)));
    const y = Math.max(0, Math.min(original.naturalHeight - 1, Math.round(box.y)));
    const side = Math.floor(Math.min(box.width, box.height, original.naturalWidth - x, original.naturalHeight - y));
    if (!Number.isFinite(side) || side < 1) {
      status.textContent = 'Amplía el área seleccionada antes de aplicar el recorte.';
      return;
    }
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = Math.min(512, side);
    const context = canvas.getContext('2d');
    if (!context || canvas.width < 1) return;
    context.drawImage(original, x, y, side, side, 0, 0, canvas.width, canvas.height);
    apply.disabled = true;
    canvas.toBlob(blob => {
      if (generation !== sequence) return;
      if (!blob) {
        apply.disabled = false;
        status.textContent = 'No se pudo preparar el recorte. Intenta nuevamente.';
        return;
      }
      finalFile = new File([blob], 'perfil.png', { type: 'image/png' });
      const transfer = new DataTransfer();
      transfer.items.add(finalFile);
      input.files = transfer.files;
      if (previewURL) URL.revokeObjectURL(previewURL);
      previewURL = URL.createObjectURL(blob);
      preview.src = previewURL;
      previewPanel.hidden = false;
      releaseSource();
      save.disabled = false;
      status.textContent = 'Recorte listo. Guarda tu perfil para aplicar la nueva foto.';
      save.focus();
    }, 'image/png');
  });

  document.querySelector('#crop-cancel').addEventListener('click', cancel);
  form.addEventListener('submit', event => {
    if (!panel.hidden || (input.files.length && !finalFile)) {
      event.preventDefault();
      status.textContent = 'Aplica el recorte o cancela la foto antes de guardar.';
      return;
    }
    save.disabled = true;
    status.textContent = 'Guardando tu perfil…';
  });
})();
