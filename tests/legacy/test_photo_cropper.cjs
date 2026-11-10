const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { test } = require('node:test');

function geometry(width, height) {
    const context = vm.createContext({ window: {} });
    vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, '../evaluacion2/js/photo-cropper.js'), 'utf8'), context);
    return new context.window.SGRPhotoCropGeometry(width, height);
}

test('el recorte inicial centra fotos horizontales y verticales sin deformarlas', () => {
    for (const [width, height, x, y] of [[1200, 800, 200, 0], [800, 1200, 0, 200]]) {
        const model = geometry(width, height);
        const rect = model.sourceRect();
        assert.equal(rect.x, x);
        assert.equal(rect.y, y);
        assert.equal(rect.side, 800);
    }
});

test('arrastrar y acercar siempre mantiene el recorte dentro de la foto original', () => {
    for (const [width, height] of [[1200, 800], [800, 1200], [100, 100]]) {
        const model = geometry(width, height);
        for (const zoom of [1, 1.5, 4, 9, 0]) {
            model.setZoom(zoom);
            for (const delta of [-10000, 10000]) {
                model.move(delta, delta);
                const rect = model.sourceRect();
                assert.ok(rect.x >= -1e-9 && rect.y >= -1e-9);
                assert.ok(rect.x + rect.side <= width + 1e-9);
                assert.ok(rect.y + rect.side <= height + 1e-9);
                assert.ok(rect.side > 0);
            }
        }
    }
});

test('el zoom conserva el punto elegido y centrar restaura el recorte original', () => {
    const model = geometry(1200, 800);
    model.move(80, 0);
    const before = model.sourceRect();
    model.setZoom(2);
    const after = model.sourceRect();
    assert.equal(before.x + before.side / 2, after.x + after.side / 2);
    model.reset();
    assert.equal(model.zoom, 1);
    assert.equal(model.sourceRect().x, 200);
});

function editor({ contextAvailable = true, decode = true } = {}) {
    const elements = new Map();
    const revoked = [];
    const drawings = [];
    const document = { activeElement: null, body: { style: { overflow: 'hidden' } }, addEventListener() {},
        getElementById: id => elements.get(id) };
    for (const id of ['sgr-photo-crop-modal', 'photo-crop-canvas', 'photo-crop-zoom', 'photo-crop-close',
        'photo-crop-cancel', 'photo-crop-use', 'photo-crop-reset', 'photo-crop-zoom-value']) {
        const listeners = new Map();
        elements.set(id, { hidden: true, value: '1', classList: { add() {}, remove() {} },
            focus() { document.activeElement = this; }, addEventListener(type, callback) { listeners.set(type, callback); },
            fire(type, event = {}) { return listeners.get(type)?.(event); },
            getContext() { return contextAvailable ? { fillRect() {}, drawImage(...args) { drawings.push(args); } } : null; },
            toDataURL: () => 'data:image/jpeg;base64,recorte',
            getBoundingClientRect: () => ({ width: 256 }),
            setPointerCapture() {}, hasPointerCapture: () => false, querySelectorAll: () => [] });
    }
    const context = vm.createContext({ window: {}, document, URL: {
        createObjectURL: () => 'blob:foto', revokeObjectURL: url => revoked.push(url)
    }, Image: class { naturalWidth = 1200; naturalHeight = 800; set src(value) { if (decode) this.onload(); else this.onerror(); } },
    Swal: { fire: async () => {}, isVisible: () => false } });
    vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, '../evaluacion2/js/photo-cropper.js'), 'utf8'), context);
    return { Cropper: context.window.SGRPhotoCropper, elements, drawings, revoked, document };
}

test('el editor permite mover y acercar antes de exportar el recorte confirmado', async () => {
    const { Cropper, elements, drawings, revoked, document } = editor();
    const result = Cropper.edit({});
    await Promise.resolve();
    assert.equal(Cropper.active, true);
    assert.equal(elements.get('sgr-photo-crop-modal').hidden, false);
    const zoom = elements.get('photo-crop-zoom');
    zoom.value = '2'; zoom.fire('input');
    const canvas = elements.get('photo-crop-canvas');
    canvas.fire('pointerdown', { pointerId: 1, button: 0, clientX: 0, clientY: 0 });
    canvas.fire('pointermove', { pointerId: 1, clientX: 40, clientY: 20 });
    const rect = Cropper.instance.model.sourceRect();
    assert.ok(rect.x < 400 && rect.y < 200);
    assert.equal(drawings.at(-1)[1], rect.x);
    await elements.get('photo-crop-use').fire('click');
    assert.equal(await result, 'data:image/jpeg;base64,recorte');
    assert.equal(Cropper.active, false);
    assert.equal(elements.get('sgr-photo-crop-modal').hidden, true);
    assert.equal(document.body.style.overflow, 'hidden');
    assert.deepEqual(revoked, ['blob:foto']);
});

test('Escape cancela solo el recorte, libera la imagen y no cierra el diálogo de origen', async () => {
    const { Cropper, revoked } = editor();
    const result = Cropper.edit({});
    await Promise.resolve();
    let stopped = false;
    Cropper.instance.handleKeydown({ key: 'Escape', preventDefault() {}, stopImmediatePropagation() { stopped = true; } });
    assert.equal(await result, null);
    assert.equal(stopped, true);
    assert.equal(Cropper.active, false);
    assert.deepEqual(revoked, ['blob:foto']);
});

test('un error de lectura o canvas deja cerrado el editor y libera la imagen', async () => {
    for (const options of [{ decode: false }, { contextAvailable: false }]) {
        const { Cropper, elements, revoked } = editor(options);
        await assert.rejects(Cropper.edit({}), /leer|preparar/);
        assert.equal(Cropper.active, false);
        assert.equal(elements.get('sgr-photo-crop-modal').hidden, true);
        assert.deepEqual(revoked, ['blob:foto']);
    }
});

test('si el formulario de origen se cerró durante la lectura no aparece un editor huérfano', async () => {
    const { Cropper, elements, revoked } = editor();
    assert.equal(await Cropper.edit({}, () => false), null);
    assert.equal(Cropper.active, false);
    assert.equal(elements.get('sgr-photo-crop-modal').hidden, true);
    assert.deepEqual(revoked, ['blob:foto']);
});
