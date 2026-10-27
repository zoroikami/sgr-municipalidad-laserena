const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

test('el perfil usa la sesión Django y CSRF para guardar la foto', async () => {
    const requests = [];
    const context = vm.createContext({
        URL, Headers,
        document: { cookie: 'csrftoken=csrf-actual' },
        localStorage: { removeItem() {} },
        window: {
            location: { href: 'http://localhost/', origin: 'http://localhost' },
            fetch: async (url, options = {}) => {
                requests.push({ url, options });
                return { ok: true, json: async () => ({ success: true, user: { id: 7, foto_perfil: 'foto' } }) };
            }
        }
    });
    vm.runInContext('const fetch = (...args) => window.fetch(...args);', context);
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../evaluacion2/js/data_eval2.js'), 'utf8'), context);
    assert.equal((await vm.runInContext('sgrDb.getProfile()', context)).id, 7);
    assert.equal((await vm.runInContext('sgrDb.saveProfilePhoto("foto")', context)).foto_perfil, 'foto');
    assert.equal(requests[0].url, '/api/profile');
    assert.equal(requests[1].options.method, 'PUT');
    assert.equal(requests[1].options.headers.get('X-CSRFToken'), 'csrf-actual');
    assert.equal(requests[1].options.headers.has('Authorization'), false);
    assert.equal(requests[1].options.body, '{"photo":"foto"}');
});
