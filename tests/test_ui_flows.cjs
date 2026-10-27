const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

function createContext() {
    const elements = new Map();
    const storage = new Map();
    const alerts = [];
    const context = vm.createContext({
        console,
        window: { location: { origin: 'http://localhost' } },
        localStorage: {
            getItem: key => storage.get(key) ?? null,
            setItem: (key, value) => storage.set(key, value),
            removeItem: key => storage.delete(key)
        },
        document: {
            addEventListener() {},
            getElementById: id => elements.get(id),
            querySelectorAll: () => []
        },
        Swal: { fire: options => { alerts.push(options); return Promise.resolve({}); } },
        fetch: async () => { throw new Error('Sin conexión'); }
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../assets/municipal/rut.js'), 'utf8'), context);
    for (const file of ['data_eval2.js', 'app_eval2.js']) {
        vm.runInContext(fs.readFileSync(path.join(__dirname, '../evaluacion2/js', file), 'utf8'), context);
    }
    vm.runInContext('globalThis.app = new SGRApplication(); globalThis.database = sgrDb;', context);
    return { context, elements, storage, alerts, app: context.app, database: context.database };
}

test('una sesión ausente o inválida muestra login sin seleccionar un perfil', async () => {
    for (const storedSession of [null, '{inválido', JSON.stringify({ id: 999, estado: 'Activo' })]) {
        const { app, database, storage } = createContext();
        if (storedSession) storage.set('SGR_SESSION_USER', storedSession);
        database.init = async () => {};
        app.setupEventListeners = () => {};
        app.showAuthView = () => { app.authVisible = true; };
        app.showAppView = () => { app.appVisible = true; };
        await app.init();
        assert.equal(app.currentUser, null);
        assert.equal(app.authVisible, true);
        assert.equal(storage.has('SGR_SESSION_USER'), false);
    }
});

test('la paginación limita los botones y conserva extremos y página actual', () => {
    const { app, elements } = createContext();
    const footer = { innerHTML: '' };
    elements.set('pagination-delegaciones', footer);
    for (const page of [1, 2, 50, 99, 100]) {
        app.renderPaginationControls('delegaciones', 500, page, 100, (page - 1) * 5, 5);
        const numbers = [...footer.innerHTML.matchAll(/>(\d+)<\/button>/g)].map(match => Number(match[1]));
        assert.ok(numbers.length <= 7, `${numbers.length} botones para página ${page}`);
        assert.ok(numbers.includes(1));
        assert.ok(numbers.includes(100));
        assert.ok(numbers.includes(page));
        assert.match(footer.innerHTML, /aria-current="page"/);
    }
});

test('las sesiones de ingreso restauran únicamente usuarios activos y sus permisos actuales', async () => {
    for (const session of ['{inválido', JSON.stringify({ id: 999 }), JSON.stringify({ id: 1, rol_codigo: 'FALSO' })]) {
        const { app, database, storage } = createContext();
        storage.set('SGR_AUTH_SESSION_USER', session);
        database.init = async () => {};
        app.setupEventListeners = () => {};
        app.showAuthView = () => {};
        app.showAppView = () => { app.appVisible = true; };
        await app.init();
        if (session.includes('FALSO')) {
            assert.equal(app.currentUser.rol_codigo, database.data.usuarios.find(user => user.id === 1).rol_codigo);
            assert.equal(app.appVisible, true);
        } else {
            assert.equal(app.currentUser, null);
            assert.equal(storage.has('SGR_AUTH_SESSION_USER'), false);
        }
    }
});

test('la identidad incluye la paleta institucional y un logo vectorial sin mapa de bits', () => {
    const logo = fs.readFileSync(path.join(__dirname, '../assets/municipal/logo-la-serena.svg'), 'utf8');
    const brand = fs.readFileSync(path.join(__dirname, '../assets/municipal/brand.css'), 'utf8');
    assert.match(logo, /viewBox="46 47 716 199"/);
    assert.match(logo, /<path\s/);
    assert.doesNotMatch(logo, /<image\s|data:image/);
    for (const color of ['#DB3334', '#C41230', '#8B1D19']) {
        assert.ok(brand.toUpperCase().includes(color));
    }
});

test('el modo local genera códigos e ignora códigos enviados manualmente', async () => {
    const { database } = createContext();
    for (const [collection, expected] of [['delegaciones', 'DEL07'], ['items_metas', 'IT006'], ['roles', 'ROL06'], ['tipos_atencion', 'TA006'], ['sub_atenciones', 'SA011']]) {
        await database.createItem(collection, { nombre: 'Nuevo', codigo: 'MANUAL' });
        assert.equal(database.data[collection].at(-1).codigo, expected);
    }
});

test('los cinco formularios con correlativo no solicitan un código manual', () => {
    const { app, elements } = createContext();
    elements.set('sgr-crud-modal', { classList: { add() {} } });
    elements.set('modal-crud-title', {});
    elements.set('modal-crud-body', {});
    elements.set('btn-modal-save', { style: {} });
    for (const module of ['delegaciones', 'items_metas', 'roles', 'tipos_atencion', 'sub_atenciones']) {
        app.openModalNew(module);
        const html = elements.get('modal-crud-body').innerHTML;
        assert.doesNotMatch(html, /id="m-\w+-codigo"/, module);
        assert.match(html, /automáticamente/, module);
    }
});

test('guardar la foto usa la sesión autenticada sin enviar identificadores de usuario', async () => {
    const { database, context, storage } = createContext();
    database.hasBackend = true;
    storage.set('SGR_AUTH_SESSION_TOKEN', 'sesion-propia');
    let request;
    context.fetch = async (url, options) => {
        request = { url, ...options };
        return { ok: true, json: async () => ({ success: true, user: { id: 4, foto_perfil: 'foto-guardada' } }) };
    };
    const user = await database.saveProfilePhoto('foto-preparada');
    assert.equal(request.url, '/api/profile');
    assert.equal(request.method, 'PUT');
    assert.equal(request.headers.Authorization, 'Bearer sesion-propia');
    assert.deepEqual(JSON.parse(request.body), { photo: 'foto-preparada' });
    assert.equal(user.foto_perfil, 'foto-guardada');
});

test('una foto no se guarda en modo local cuando falta conexión a la base de datos', async () => {
    const { database, storage } = createContext();
    database.hasBackend = false;
    const before = JSON.stringify([...storage]);
    await assert.rejects(database.saveProfilePhoto('foto'), /conexión|servidor/i);
    assert.equal(JSON.stringify([...storage]), before);
});

test('los errores del servidor al guardar foto se propagan sin simular éxito', async () => {
    const { database, context, storage } = createContext();
    database.hasBackend = true;
    storage.set('SGR_AUTH_SESSION_TOKEN', 'sesion');
    context.fetch = async () => ({ ok: false, status: 401, json: async () => ({ message: 'Sesión expirada' }) });
    await assert.rejects(database.saveProfilePhoto(null), /Sesión expirada/);
});

test('la última foto seleccionada para un usuario prevalece aunque la anterior termine después', async () => {
    const { app, context, elements } = createContext();
    const pending = [];
    context.window.SGRProfileController = { preparePhoto: () => new Promise(resolve => pending.push(resolve)) };
    const input = { files: [{ type: 'image/png' }], value: '' };
    elements.set('m-usr-foto', input);
    elements.set('m-usr-foto-preview', {});
    elements.set('btn-modal-save', {});
    const first = app.selectNewUserPhoto(input);
    const second = app.selectNewUserPhoto(input);
    pending[1]('foto-ultima');
    await second;
    pending[0]('foto-anterior');
    await first;
    assert.equal(app.newUserPhoto, 'foto-ultima');
    assert.equal(elements.get('m-usr-foto-preview').src, 'foto-ultima');
});

test('crear usuarios en modo local rechaza un RUT inválido sin alterar los registros', async () => {
    const { database } = createContext();
    const count = database.data.usuarios.length;
    await assert.rejects(database.createItem('usuarios', { rut: '12.345.678-9', nombre: 'Inválido' }), /RUT/);
    assert.equal(database.data.usuarios.length, count);
    await assert.rejects(database.createItem('usuarios', { rut: '123456785', nombre: 'Duplicado' }), /registrado/);
    assert.equal(database.data.usuarios.length, count);
});

test('el ingreso de atención guarda el RUT validado y bloquea dígitos incorrectos', async () => {
    const { app, database, context, elements, alerts } = createContext();
    context.document.querySelector = () => null;
    for (const [id, value] of Object.entries({
        'atn-solicitante': 'Persona de prueba', 'atn-solicitante-rut': '11.111.111-2',
        'atn-tipo-select': 'TA001', 'atn-subtipo-select': 'SA001', 'atn-descripcion': 'Consulta'
    })) elements.set(id, { value, focus() {} });
    const saved = [];
    database.createItem = async (module, payload) => { saved.push(payload); return { folio: 'ATN-PRUEBA' }; };
    app.renderAtencionesTable = () => {};
    await app.submitIngresoAtencion();
    assert.equal(saved.length, 0);
    assert.equal(alerts.at(-1).icon, 'warning');
    elements.get('atn-solicitante-rut').value = '11.111.111-1';
    await app.submitIngresoAtencion();
    assert.equal(saved[0].solicitante_rut, '11111111-1');
    assert.equal(saved[0].solicitante_nombre, 'Persona de prueba');
    assert.equal(elements.get('atn-solicitante-rut').value, '');
});

test('una falla de autenticación del servidor no permite acceso local', async () => {
    const { app, database, elements, context, alerts } = createContext();
    elements.set('login-username', { value: 'harold.concha@laserena.cl' });
    elements.set('login-password', { value: 'CualquierClave' });
    database.hasBackend = true;
    context.fetch = async () => ({ ok: false, status: 500, json: async () => ({ success: false }) });
    await app.submitLogin();
    assert.equal(app.currentUser, null);
    assert.equal(alerts.at(-1).icon, 'error');
});

test('el modo local rechaza contraseñas arbitrarias', async () => {
    const { app, elements, alerts } = createContext();
    elements.set('login-username', { value: 'harold.concha@laserena.cl' });
    elements.set('login-password', { value: 'CualquierClave' });
    await app.submitLogin();
    assert.equal(app.currentUser, null);
    assert.equal(alerts.at(-1).icon, 'error');
});

test('los dos puntos de entrada no incluyen accesos rápidos ni barra de perfiles', () => {
    for (const entry of ['index.html', 'evaluacion2/index.html']) {
        const html = fs.readFileSync(path.join(__dirname, '..', entry), 'utf8');
        assert.doesNotMatch(html, /role-demo-bar|btn-quick-login|setCurrentUserByRole/);
    }
});

test('los errores de sincronización no activan silenciosamente el modo local', async () => {
    const { database, context } = createContext();
    context.fetch = async endpoint => endpoint === '/api/health'
        ? { ok: true }
        : { ok: false, json: async () => ({ error: 'Servidor no disponible' }) };
    await assert.rejects(database.init(), /No se pudieron actualizar/);
    assert.equal(database.hasBackend, true);
});

test('un error HTTP al cambiar contraseña no muestra éxito', async () => {
    const { app, database, context, elements, alerts } = createContext();
    database.hasBackend = true;
    elements.set('new-password-input', { value: 'NuevaClave123*' });
    elements.set('confirm-password-input', { value: 'NuevaClave123*' });
    context.fetch = async () => ({ ok: false, status: 500, json: async () => ({ message: 'Servidor no disponible' }) });
    await app.submitCrearNuevaPassword();
    assert.equal(alerts.at(-1).icon, 'error');
});

const searchFixtures = [
    {
        module: 'delegaciones', render: 'renderDelegaciones', tbody: 'tbody-delegaciones',
        record: { id: 1, codigo: 'DEL01', nombre: 'Centro', comuna: 'La Serena', estado: 'Activa', direccion: 'Calle oculta' },
        visibleQueries: ['del01', 'centro', 'la serena', ' ACTIVA '], hiddenQueries: ['calle oculta']
    },
    {
        module: 'roles', render: 'renderRoles', tbody: 'tbody-roles',
        record: { id: 1, codigo: 'ROL01', nombre: 'Administrador', alcance: 'Comunal', estado: 'Activo', descripcion: 'Descripción oculta', permisos: 'Permiso interno' },
        visibleQueries: ['rol01', 'administrador', 'comunal', 'activo'], hiddenQueries: ['descripción oculta', 'permiso interno']
    },
    {
        module: 'usuarios', render: 'renderUsuarios', tbody: 'tbody-usuarios',
        record: { id: 1, nombre: 'Ana Pérez', email: 'ana@example.test', rol_nombre: 'Operador', rol_codigo: 'ROL04', delegacion_nombre: 'Centro', delegacion_codigo: 'DEL01', estado: 'Activo', rut: '12.345.678-9', password_hash: 'ClaveOculta123' },
        visibleQueries: ['ana pérez', 'ana@example.test', 'operador', 'centro'], hiddenQueries: ['12.345.678-9', 'claveoculta123', 'rol04', 'del01', 'activo']
    },
    {
        module: 'items_metas', render: 'renderItemsMetas', tbody: 'tbody-items-metas',
        record: { id: 1, codigo: 'IT001', nombre: 'Cobertura', descripcion: 'Visitas vecinales', estado: 'Activo', unidad_medida: 'Unidad oculta', meta_cantidad: 91827 },
        visibleQueries: ['it001', 'cobertura', 'visitas vecinales', 'activo'], hiddenQueries: ['unidad oculta', '91827']
    },
    {
        module: 'tipos_atencion', render: 'renderTiposAtencion', tbody: 'tbody-tipos-atencion',
        record: { id: 1, codigo: 'TA001', nombre: 'Salud', descripcion: 'Consulta vecinal', estado: 'Activo', nota_interna: 'Nota oculta' },
        visibleQueries: ['ta001', 'salud', 'consulta vecinal', 'activo'], hiddenQueries: ['nota oculta']
    },
    {
        module: 'sub_atenciones', render: 'renderSubAtenciones', tbody: 'tbody-sub-atenciones',
        record: { id: 1, codigo: 'SA001', nombre: 'Subsidio', tipo_nombre: 'Social', estado: 'Activa', tipo_codigo: 'TA001' },
        visibleQueries: ['sa001', 'subsidio', 'social', 'activa'], hiddenQueries: ['ta001']
    },
    {
        module: 'atenciones', render: 'renderAtencionesTable', tbody: 'tbody-atenciones-historial',
        record: { id: 1, folio: 'ATN-2026-0001', solicitante_nombre: 'Ana Pérez', delegacion_nombre: 'Centro', delegacion_codigo: 'DEL01', tipo_nombre: 'Social', subtipo_nombre: 'Subsidio', responsable_nombre: 'Carlos Miranda', fecha_registro: '2026-10-13 09:30:00', solicitante_rut: '12.345.678-9', descripcion: 'Detalle oculto' },
        visibleQueries: ['atn-2026-0001', 'ana pérez', 'centro', 'social', 'subsidio', 'carlos miranda', '2026-10-13'], hiddenQueries: ['12.345.678-9', 'detalle oculto', 'del01']
    }
];

for (const fixture of searchFixtures) {
    test(`la búsqueda de ${fixture.module} coincide solo con sus columnas visibles`, () => {
        const { app, database, elements } = createContext();
        const tbody = { innerHTML: '' };
        elements.set(fixture.tbody, tbody);
        database.data[fixture.module] = [fixture.record];
        for (const [queries, expected] of [[fixture.visibleQueries, true], [fixture.hiddenQueries, false]]) {
            for (const query of queries) {
                app.pagination[fixture.module].search = query;
                app[fixture.render]();
                assert.equal(tbody.innerHTML.includes('class="record-name"'), expected, query);
            }
        }
    });
}

test('la búsqueda de usuarios incluye los códigos únicamente cuando se muestran como reemplazo del nombre', () => {
    const { app, database, elements } = createContext();
    const tbody = { innerHTML: '' };
    elements.set('tbody-usuarios', tbody);
    database.data.usuarios = [{ ...searchFixtures[2].record, rol_nombre: null, delegacion_nombre: '' }];
    for (const query of ['rol04', 'del01']) {
        app.pagination.usuarios.search = query;
        app.renderUsuarios();
        assert.match(tbody.innerHTML, /class="record-name"/);
    }
});

test('exportar respeta los mismos campos de búsqueda que la tabla', () => {
    for (const fixture of searchFixtures) {
        const { app, database, context } = createContext();
        context.exportToExcel = records => { context.exportedRecords = records; };
        database.data[fixture.module] = [fixture.record];
        for (const [queries, expected] of [[fixture.visibleQueries, 1], [fixture.hiddenQueries, 0]]) {
            for (const query of queries) {
                app.pagination[fixture.module].search = query;
                app.exportModuleToExcel(fixture.module);
                assert.equal(context.exportedRecords.length, expected, `${fixture.module}: ${query}`);
            }
        }
    }
});

test('la búsqueda recorre los registros del módulo y vuelve a la primera página', () => {
    const { app, database, elements } = createContext();
    const tbody = { innerHTML: '' };
    elements.set('tbody-delegaciones', tbody);
    database.data.delegaciones = Array.from({ length: 12 }, (_, index) => ({ ...searchFixtures[0].record, id: index + 1, nombre: `Delegación ${index + 1}` }));
    app.currentView = 'delegaciones';
    app.pagination.delegaciones.page = 2;
    app.onSearchInput('delegaciones', 'Delegación 12');
    assert.equal(app.pagination.delegaciones.page, 1);
    assert.match(tbody.innerHTML, /Delegación 12/);
    assert.doesNotMatch(tbody.innerHTML, /Delegación 6/);
});


test('las cantidades de meta son automáticas y la edición local conserva la cantidad asignada', async () => {
    const { database } = createContext();
    await database.createItem('items_metas', { nombre: 'Nueva meta', meta_cantidad: 999 });
    const item = database.data.items_metas.at(-1);
    assert.equal(item.meta_cantidad, 100);
    item.meta_cantidad = 150;
    await database.updateItem('items_metas', item.id, { nombre: 'Nombre actualizado', meta_cantidad: 1 });
    assert.equal(item.meta_cantidad, 150);
    assert.equal(database.data.items_metas.at(-1).meta_cantidad, 150);
    assert.equal(database.data.items_metas.at(-1).nombre, 'Nombre actualizado');
});

test('cancelar el recorte al crear usuario permite volver a seleccionar el mismo archivo', async () => {
    const { app, context, elements } = createContext();
    context.window.SGRProfileController = { preparePhoto: async () => null };
    const input = { files: [{ type: 'image/png' }], value: 'misma-foto.png' };
    elements.set('m-usr-foto', input);
    elements.set('m-usr-foto-preview', { src: 'foto-previa' });
    elements.set('btn-modal-save', {});
    app.newUserPhoto = 'foto-previa';
    await app.selectNewUserPhoto(input);
    assert.equal(input.value, '');
    assert.equal(app.newUserPhoto, 'foto-previa');
    assert.equal(elements.get('m-usr-foto-preview').src, 'foto-previa');
});

test('cerrar alta de usuario invalida la foto que todavía se está leyendo', async () => {
    const { app, context, elements } = createContext();
    let resolvePhoto, isCurrent;
    context.window.SGRProfileController = { preparePhoto: (file, check) => {
        isCurrent = check;
        return new Promise(resolve => { resolvePhoto = resolve; });
    } };
    const input = { files: [{ type: 'image/png' }], value: 'foto.png' };
    elements.set('m-usr-foto', input);
    elements.set('m-usr-foto-preview', { src: 'foto-previa' });
    elements.set('btn-modal-save', { style: {} });
    elements.set('sgr-crud-modal', { classList: { remove() {}, add() {} } });
    elements.set('modal-crud-title', {});
    elements.set('modal-crud-body', {});
    const pending = app.selectNewUserPhoto(input);
    app.closeCrudModal();
    assert.equal(isCurrent(), false);
    app.openModalEdit('items_metas', 1);
    assert.equal(elements.get('btn-modal-save').disabled, false);
    resolvePhoto('foto-tardía');
    await pending;
    assert.equal(elements.get('m-usr-foto-preview').src, 'foto-previa');
});

test('la cantidad de meta aparece de solo lectura tanto al crear como al editar', () => {
    const { app, elements } = createContext();
    elements.set('sgr-crud-modal', { classList: { add() {} } });
    elements.set('modal-crud-title', {});
    elements.set('modal-crud-body', {});
    elements.set('btn-modal-save', { style: {} });
    for (const open of [() => app.openModalNew('items_metas'), () => app.openModalEdit('items_metas', 1)]) {
        open();
        const html = elements.get('modal-crud-body').innerHTML;
        assert.match(html, /<input type="text" id="m-itm-meta"[^>]* readonly/);
        assert.doesNotMatch(html, /type="number" id="m-itm-meta"/);
    }
});
