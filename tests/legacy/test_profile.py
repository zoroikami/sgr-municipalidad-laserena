import base64
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

PHOTO = 'data:image/png;base64,' + base64.b64encode(base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aY7sAAAAASUVORK5CYII='
)).decode()
DEFAULT_PHOTO = '/assets/municipal/avatar-default.svg'


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = str(Path(self.directory.name) / 'profile.db')
        self.db_patch = patch.object(server, 'DB_PATH', self.db)
        self.db_patch.start()
        server.init_db()
        with sqlite3.connect(self.db) as connection:
            for uid in (1001, 1002):
                connection.execute('''INSERT INTO usuarios
                    (id, rut, nombre, email, password_hash, rol_codigo, delegacion_codigo, estado)
                    VALUES (?, ?, ?, ?, 'Prueba123*', 'ROL04', 'DEL01', 'Activo')''',
                    (uid, str(uid), f'Usuario {uid}', f'usuario{uid}@example.test'))
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

    def request(self, method, path, payload=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = Request(self.url + path, method=method, headers=headers,
                          data=json.dumps(payload).encode() if payload is not None else None)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def login(self, uid=1001):
        status, result = self.request('POST', '/api/auth/login',
            {'usuario': f'usuario{uid}@example.test', 'password': 'Prueba123*'})
        self.assertEqual(status, 200, result)
        return result['token'], result['user']

    def test_common_user_can_save_photo_and_it_survives_a_new_login(self):
        token, user = self.login()
        self.assertEqual(user.get('foto_perfil'), DEFAULT_PHOTO)
        status, result = self.request('PUT', '/api/profile', {'photo': PHOTO}, token)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['user']['foto_perfil'], PHOTO)
        new_token, user = self.login()
        self.assertEqual(user['foto_perfil'], PHOTO)
        self.assertNotEqual(token, new_token)
        with sqlite3.connect(self.db) as connection:
            photo = connection.execute('SELECT photo_data FROM user_profiles WHERE user_id=1001').fetchone()[0]
            self.assertEqual(photo, PHOTO)

    def test_profile_requires_a_valid_session(self):
        for method, payload in [('GET', None), ('PUT', {'photo': PHOTO})]:
            for token in (None, 'token-inventado'):
                status, _ = self.request(method, '/api/profile', payload, token)
                self.assertEqual(status, 401)

    def test_cannot_choose_another_user_or_edit_role_from_profile(self):
        token, _ = self.login()
        for payload in ({'photo': PHOTO, 'user_id': 1002}, {'photo': PHOTO, 'rol_codigo': 'ROL01'}):
            status, _ = self.request('PUT', '/api/profile', payload, token)
            self.assertEqual(status, 400)
        other_token, other = self.login(1002)
        status, result = self.request('GET', '/api/profile', token=other_token)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['user']['foto_perfil'], DEFAULT_PHOTO)
        self.assertEqual(other['rol_codigo'], 'ROL04')

    def test_invalid_images_are_rejected_without_losing_previous_photo(self):
        token, _ = self.login()
        self.request('PUT', '/api/profile', {'photo': PHOTO}, token)
        for photo in ('https://example.test/photo.jpg', 'data:image/svg+xml;base64,PHN2Zy8+',
                      'data:image/png;base64,aG9sYQ==', 'data:image/png;base64,???', 123,
                      'data:image/png;base64,' + base64.b64encode(b'x' * (512 * 1024 + 1)).decode()):
            status, _ = self.request('PUT', '/api/profile', {'photo': photo}, token)
            self.assertIn(status, (400, 413))
        status, result = self.request('GET', '/api/profile', token=token)
        self.assertEqual(result['user']['foto_perfil'], PHOTO)

    def test_remove_photo_restores_default_in_database(self):
        token, _ = self.login()
        self.request('PUT', '/api/profile', {'photo': PHOTO}, token)
        status, result = self.request('PUT', '/api/profile', {'photo': None}, token)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['user']['foto_perfil'], DEFAULT_PHOTO)
        self.assertEqual(self.login()[1]['foto_perfil'], DEFAULT_PHOTO)

    def test_logout_revokes_only_its_own_session(self):
        token, _ = self.login()
        other_token, _ = self.login(1002)
        status, _ = self.request('DELETE', '/api/profile/session', token=token)
        self.assertEqual(status, 200)
        self.assertEqual(self.request('GET', '/api/profile', token=token)[0], 401)
        self.assertEqual(self.request('GET', '/api/profile', token=other_token)[0], 200)

    def test_new_user_photo_is_saved_at_creation_or_gets_default(self):
        for uid, photo in [(2001, PHOTO), (2002, None)]:
            payload = {'rut': {2001: '11.111.111-1', 2002: '22.222.222-2'}[uid], 'nombre': f'Usuario {uid}',
                       'email': f'usuario{uid}@example.test', 'password': 'Prueba123*'}
            if photo:
                payload['foto_perfil'] = photo
            status, result = self.request('POST', '/api/usuarios', payload)
            self.assertEqual(status, 201, result)
            self.assertEqual(self.login(uid)[1]['foto_perfil'], photo or DEFAULT_PHOTO)

    def test_invalid_photo_does_not_create_a_partial_user(self):
        status, _ = self.request('POST', '/api/usuarios', {'rut': '33.333.333-3', 'nombre': 'Inválido',
            'email': 'invalido@example.test', 'foto_perfil': 'data:image/png;base64,aG9sYQ=='})
        self.assertEqual(status, 400)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM usuarios WHERE email='invalido@example.test'").fetchone()[0], 0)

    def test_inactive_and_expired_sessions_cannot_update_photo(self):
        token, _ = self.login()
        with sqlite3.connect(self.db) as connection:
            connection.execute('UPDATE user_sessions SET expires_at=0 WHERE user_id=1001')
        self.assertEqual(self.request('PUT', '/api/profile', {'photo': PHOTO}, token)[0], 401)
        token, _ = self.login()
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE usuarios SET estado='Inactivo' WHERE id=1001")
        self.assertEqual(self.request('PUT', '/api/profile', {'photo': PHOTO}, token)[0], 401)


if __name__ == '__main__':
    unittest.main()
