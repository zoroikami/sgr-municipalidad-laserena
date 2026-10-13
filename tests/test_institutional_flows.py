import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from http.server import HTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server


class InstitutionalFlowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.directory.name) / 'test.db')
        self.database_patch = patch.object(server, 'DB_PATH', self.database_path)
        self.database_patch.start()
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript('''
                CREATE TABLE delegaciones (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE, nombre TEXT, direccion TEXT, comuna TEXT, estado TEXT);
                CREATE TABLE items_metas (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE, nombre TEXT, descripcion TEXT,
                    unidad_medida TEXT, meta_cantidad INTEGER, estado TEXT);
                CREATE TABLE roles (codigo TEXT, nombre TEXT, alcance TEXT);
                CREATE TABLE usuarios (id INTEGER PRIMARY KEY, rut TEXT, nombre TEXT,
                    email TEXT, password_hash TEXT, rol_codigo TEXT,
                    delegacion_codigo TEXT, estado TEXT);
                INSERT INTO delegaciones VALUES (1, 'DEL01', 'Centro', 'Dirección', 'La Serena', 'Activa');
                INSERT INTO roles VALUES ('ROL01', 'Superadministrador', 'Comunal');
                INSERT INTO usuarios VALUES (1, '12345678-5', 'Usuario', 'usuario@example.test',
                    'ClaveReal123*', 'ROL01', 'DEL01', 'Activo');
            ''')
        self.http_server = HTTPServer(('127.0.0.1', 0), server.SGRRequestHandler)
        self.thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f'http://127.0.0.1:{self.http_server.server_port}'

    def tearDown(self):
        self.http_server.shutdown()
        self.http_server.server_close()
        self.thread.join()
        self.database_patch.stop()
        self.directory.cleanup()

    def post(self, path, payload):
        request = Request(self.base_url + path, data=json.dumps(payload).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_delegation_code_is_generated_and_ignores_client_code(self):
        for code, expected in [(None, 'DEL02'), ('MANUAL', 'DEL03')]:
            payload = {'nombre': 'Nueva delegación', 'direccion': 'Dirección nueva'}
            if code:
                payload['codigo'] = code
            status, result = self.post('/api/delegaciones', payload)
            self.assertEqual(status, 201, result)
            self.assertEqual(result['codigo'], expected)
            with sqlite3.connect(self.database_path) as connection:
                self.assertEqual(connection.execute('SELECT codigo FROM delegaciones WHERE id=?',
                                                   (result['id'],)).fetchone()[0], expected)

    def test_item_codes_follow_highest_existing_suffix(self):
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("INSERT INTO items_metas (codigo, nombre) VALUES ('IT009', 'Anterior')")
        status, result = self.post('/api/items-metas', {'nombre': 'Nueva meta', 'codigo': 'MANUAL'})
        self.assertEqual(status, 201, result)
        self.assertEqual(result['codigo'], 'IT010')

    def test_invalid_creation_does_not_consume_a_code(self):
        status, _ = self.post('/api/delegaciones', {'direccion': 'Dirección'})
        self.assertEqual(status, 400)
        status, result = self.post('/api/delegaciones', {'nombre': 'Nueva', 'direccion': 'Dirección'})
        self.assertEqual(status, 201, result)
        self.assertEqual(result['codigo'], 'DEL02')

    def test_login_rejects_universal_demo_password(self):
        status, result = self.post('/api/auth/login',
                                   {'usuario': 'usuario@example.test', 'password': 'Admin123*'})
        self.assertEqual(status, 401, result)

    def test_login_accepts_actual_account_password(self):
        status, result = self.post('/api/auth/login',
                                   {'usuario': 'usuario@example.test', 'password': 'ClaveReal123*'})
        self.assertEqual(status, 200, result)
        self.assertNotIn('password_hash', result['user'])


if __name__ == '__main__':
    unittest.main()
