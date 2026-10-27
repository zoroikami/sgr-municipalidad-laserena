const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const { test } = require('node:test');

function setup() {
    const elements = new Map();
    const alerts = [];
    for (const id of ['header-user-avatar', 'profile-photo-preview', 'profile-photo-file', 'profile-choose-photo', 'profile-remove-photo', 'profile-save-photo', 'profile-status', 'sgr-profile-modal', 'profile-close', 'profile-user-name', 'profile-user-email', 'profile-user-role', 'profile-user-delegation']) {
        elements.set(id, { disabled: false, hidden: true, textContent: '', value: '', src: '',
            setAttribute() {}, classList: { add() {}, remove() {} }, focus() {} });
    }
    const app = { currentUser: { id: 4, nombre: 'Ana Pérez', email: 'ana@example.test', rol_codigo: 'ROL04', foto_perfil: 'foto-anterior' },
        updateHeaderUserInfo() { app.controller.renderHeader(); }, showAuthView() {} };
    const database = { getProfile: async () => ({ ...app.currentUser }), saveProfilePhoto: async () => { throw new Error('Sin conexión'); } };
    const context = vm.createContext({ window: {}, sgrDb: database,
        document: { body: { style: {} }, activeElement: null, addEventListener() {}, getElementById: id => elements.get(id) },
        localStorage: { removeItem() {} },
        Swal: { fire: async options => { alerts.push(options); return { isConfirmed: false }; } },
        URL: { createObjectURL() { throw new Error('No debe decodificar archivos rechazados'); } }
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../evaluacion2/js/profile.js'), 'utf8'), context);
    const controller = new context.window.SGRProfileController(app);
    app.controller = controller;
    return { controller, app, database, elements, alerts, context };
}

test('un funcionario común puede abrir su perfil y ver su foto', async () => {
    const { controller, elements } = setup();
    await controller.open();
    assert.equal(elements.get('sgr-profile-modal').hidden, false);
    assert.equal(elements.get('profile-user-name').textContent, 'Ana Pérez');
    assert.equal(elements.get('profile-photo-preview').src, 'foto-anterior');
});

test('guardar foto actualiza la cabecera solo después de persistirla', async () => {
    const { controller, app, database, elements, alerts } = setup();
    await controller.open();
    controller.pendingPhoto = 'foto-nueva';
    database.saveProfilePhoto = async photo => ({ ...app.currentUser, foto_perfil: photo });
    await controller.save();
    assert.equal(app.currentUser.foto_perfil, 'foto-nueva');
    assert.equal(elements.get('header-user-avatar').src, 'foto-nueva');
    assert.equal(controller.pendingPhoto, undefined);
    assert.equal(alerts.at(-1).icon, 'success');
    assert.equal(elements.get('sgr-profile-modal').hidden, true);
    assert.equal(controller.opened, false);
});

test('una falla de guardado conserva la foto anterior y la previsualización pendiente', async () => {
    const { controller, app, alerts, elements } = setup();
    await controller.open();
    controller.pendingPhoto = 'foto-nueva';
    await controller.save();
    assert.equal(app.currentUser.foto_perfil, 'foto-anterior');
    assert.equal(controller.pendingPhoto, 'foto-nueva');
    assert.equal(elements.get('profile-save-photo').disabled, false);
    assert.equal(alerts.at(-1).icon, 'error');
    assert.equal(elements.get('sgr-profile-modal').hidden, false);
});

test('cancelar el descarte conserva abierto el perfil y su foto pendiente', async () => {
    const { controller, elements } = setup();
    await controller.open();
    controller.pendingPhoto = 'foto-nueva';
    await controller.close();
    assert.equal(elements.get('sgr-profile-modal').hidden, false);
    assert.equal(controller.pendingPhoto, 'foto-nueva');
});

test('sin foto la cabecera muestra el avatar predeterminado', () => {
    const { controller, app, elements } = setup();
    app.currentUser.foto_perfil = null;
    controller.renderHeader();
    assert.equal(elements.get('header-user-avatar').src, '/assets/municipal/avatar-default.svg');
});

test('la selección rechaza documentos y fotos demasiado grandes antes de decodificar', async () => {
    const { context } = setup();
    const prepare = context.window.SGRProfileController.preparePhoto;
    await assert.rejects(prepare({ type: 'image/svg+xml', size: 100 }), /JPG/);
    await assert.rejects(prepare({ type: 'image/jpeg', size: 6 * 1024 * 1024 }), /5 MB/);
});

test('una petición de perfil antigua no cierra la sesión ni el perfil de un nuevo usuario', async () => {
    const { controller, app, database, elements, alerts } = setup();
    let rejectOld;
    database.getProfile = () => new Promise((resolve, reject) => { rejectOld = reject; });
    const oldRequest = controller.open();
    controller.dismiss();
    app.currentUser = { id: 5, nombre: 'Otra persona', email: 'otra@example.test', rol_codigo: 'ROL04' };
    database.getProfile = async () => ({ ...app.currentUser });
    await controller.open();
    const error = new Error('Sesión anterior expirada');
    error.status = 401;
    rejectOld(error);
    await oldRequest;
    assert.equal(app.currentUser.id, 5);
    assert.equal(elements.get('sgr-profile-modal').hidden, false);
    assert.equal(alerts.length, 0);
});


test('cancelar el recorte conserva la foto pendiente anterior', async () => {
    const { controller, context } = setup();
    await controller.open();
    controller.pendingPhoto = 'borrador-anterior';
    context.window.SGRProfileController.preparePhoto = async () => null;
    await controller.selectPhoto({ files: [{ type: 'image/png', size: 100 }] });
    assert.equal(controller.pendingPhoto, 'borrador-anterior');
});
