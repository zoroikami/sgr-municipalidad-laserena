const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({ window: {}, document: { addEventListener() {}, getElementById() { return null; } } });
vm.runInContext(fs.readFileSync(path.join(__dirname, '../assets/municipal/rut.js'), 'utf8'), context);
const rut = context.window.ChileanRut;

test('RUT válido: normaliza puntos, guion y k y lo presenta con formato chileno', () => {
    for (const [input, expected] of [['12.345.678-5', '12345678-5'], ['123456785', '12345678-5'], [' 6-k ', '6-K'], ['14-0', '14-0']]) {
        assert.equal(rut.isValid(input), true, input);
        assert.equal(rut.normalize(input), expected, input);
    }
    assert.equal(rut.format('123456785'), '12.345.678-5');
});

test('RUT inválido: rechaza errores de dígito, separadores, letras y cero', () => {
    for (const input of ['12.345.678-9', '6-0', '14-K', '', '0-0', '00000000-0', '12.34.567-5', '12345678--5', 'ABC123456785', '123456789-2', '12 345 678-5', null, 123456785]) {
        assert.equal(rut.isValid(input), false, String(input));
        assert.throws(() => rut.normalize(input));
    }
});
