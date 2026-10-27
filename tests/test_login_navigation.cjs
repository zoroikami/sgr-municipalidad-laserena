const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

function application({ next = '', native = '' } = {}) {
    const assigned = [];
    const modules = ['atenciones', 'delegaciones', 'roles'].map(name => ({
        style: {}, getAttribute() { return name; }
    }));
    const elements = {
        'login-next': { value: next },
        'sgr-native-navigation': { textContent: JSON.stringify([['delegaciones', 'Delegaciones', '/gestion/delegaciones/']]) }
    };
    const context = vm.createContext({
        URL,
        window: { location: { origin: 'http://localhost', href: 'http://localhost/acceso/', assign(url) { assigned.push(url); } } },
        document: { body: { dataset: { nativeCrud: native } }, addEventListener() {},
            getElementById(id) { return elements[id]; }, querySelectorAll() { return modules; } }
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../evaluacion2/js/app_eval2.js'), 'utf8'), context);
    return { app: vm.runInContext('new SGRApplication()', context), assigned, modules, context, elements };
}

test('el login envía la contraseña completa, incluidos los espacios de los extremos', async () => {
    const {app, context, elements} = application();
    elements['login-username'] = {value:' admin '};
    elements['login-password'] = {value:' ClaveConEspacios123! '};
    let payload;
    context.sgrDb = {hasBackend:true};
    context.Swal = {fire() {}};
    context.fetch = async (_url, options) => {
        payload = JSON.parse(options.body);
        return {ok:false, status:401, json:async () => ({message:'Credenciales inválidas.'})};
    };
    await app.submitLogin({preventDefault() {}});
    assert.deepEqual(payload, {usuario:'admin', password:' ClaveConEspacios123! '});
});

test('el login original vuelve al CRUD solicitado con su consulta', () => {
    const { app, assigned } = application({next:'/gestion/delegaciones/?q=Zona&page_size=5'});
    assert.equal(app.redirectAfterLogin(), true);
    assert.deepEqual(assigned, ['/gestion/delegaciones/?q=Zona&page_size=5']);
});

test('el login no redirige a otro sitio ni vuelve a su propia pantalla', () => {
    for (const next of ['https://otro.example/gestion/', '//otro.example/', '/acceso/?next=/']) {
        const {app, assigned} = application({next});
        assert.equal(app.redirectAfterLogin(), false);
        assert.deepEqual(assigned, []);
    }
});

test('la barra original permite volver desde un CRUD a Atención Ciudadana', () => {
    const {app, assigned} = application({native:'delegaciones'});
    app.navigateTo('atenciones');
    assert.deepEqual(assigned, ['/?view=atenciones']);
});

test('la barra del CRUD respeta los permisos Django aunque no haya un rol SGR', () => {
    const {app, assigned, modules} = application({native:'delegaciones'});
    app.currentUser = {rol_codigo:null};
    app.applyRolePermissions();
    assert.equal(modules[1].style.display, '');
    assert.equal(modules[2].style.display, 'none');
    assert.deepEqual(assigned, []);
});
