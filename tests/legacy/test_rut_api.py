import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server


class RutApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = str(Path(self.directory.name) / 'rut.db')
        self.db_patch = patch.object(server, 'DB_PATH', self.db)
        self.db_patch.start()
        server.init_db()
        self.http = HTTPServer(('127.0.0.1', 0), server.SGRRequestHandler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.http.server_port}'

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.db_patch.stop()
        self.directory.cleanup()

    def post(self, path, payload):
        request = Request(self.url + path, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_user_creation_rejects_invalid_rut_and_stores_valid_normalized_rut(self):
        payload = {'nombre': 'Prueba RUT', 'email': 'rut@example.test', 'rut': '11.111.111-2'}
        status, _ = self.post('/api/usuarios', payload)
        self.assertEqual(status, 400)
        payload['rut'] = '11.111.111-1'
        status, result = self.post('/api/usuarios', payload)
        self.assertEqual(status, 201, result)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute('SELECT rut FROM usuarios WHERE id=?', (result['id'],)).fetchone()[0], '11111111-1')

    def test_equivalent_formatted_rut_cannot_create_duplicate_user(self):
        status, _ = self.post('/api/usuarios', {'nombre': 'Duplicado', 'email': 'duplicado@example.test', 'rut': '123456785'})
        self.assertEqual(status, 409)

    def test_attention_requires_valid_rut_and_never_invents_one(self):
        payload = {'solicitante_nombre': 'Persona de prueba', 'descripcion': 'Consulta',
                   'tipo_codigo': 'TA001', 'subtipo_codigo': 'SA001', 'delegacion_codigo': 'DEL01'}
        for value in (None, '', '11.111.111-2'):
            with self.subTest(rut=value):
                payload['solicitante_rut'] = value
                status, _ = self.post('/api/atenciones', payload)
                self.assertEqual(status, 400)
        payload['solicitante_rut'] = '11.111.111-1'
        status, result = self.post('/api/atenciones', payload)
        self.assertEqual(status, 201, result)
        with sqlite3.connect(self.db) as connection:
            row = connection.execute('SELECT solicitante_rut FROM atenciones WHERE folio=?', (result['folio'],)).fetchone()
            self.assertEqual(row[0], '11111111-1')


if __name__ == '__main__':
    unittest.main()
