"""Account photos stored in SQLite and scoped to an authenticated session."""
import base64
import binascii
import hashlib
import secrets
import time

DEFAULT_PHOTO = '/assets/municipal/avatar-default.svg'
MAX_PHOTO_BYTES = 512 * 1024
MAX_PROFILE_REQUEST = 768 * 1024
SESSION_SECONDS = 7 * 24 * 60 * 60


class ProfileError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def validate_photo(photo):
    if photo is None or photo == DEFAULT_PHOTO:
        return DEFAULT_PHOTO
    if not isinstance(photo, str):
        raise ProfileError(400, 'La foto debe ser una imagen JPEG o PNG.')
    if len(photo) > MAX_PROFILE_REQUEST:
        raise ProfileError(413, 'La foto preparada supera el tamaño permitido.')
    header, separator, encoded = photo.partition(',')
    if not separator or header not in ('data:image/jpeg;base64', 'data:image/png;base64'):
        raise ProfileError(400, 'Selecciona una imagen JPEG o PNG válida.')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ProfileError(400, 'No se pudo leer la imagen seleccionada.') from None
    if len(raw) > MAX_PHOTO_BYTES:
        raise ProfileError(413, 'La foto preparada supera los 512 KB.')
    valid = (header == 'data:image/png;base64' and len(raw) >= 45
             and raw.startswith(b'\x89PNG\r\n\x1a\n') and raw[12:16] == b'IHDR'
             and raw.endswith(b'IEND\xaeB`\x82')) or (
             header == 'data:image/jpeg;base64' and len(raw) >= 20
             and raw.startswith(b'\xff\xd8\xff') and raw.endswith(b'\xff\xd9'))
    if not valid:
        raise ProfileError(400, 'El archivo no contiene una imagen válida.')
    return photo


class ProfileStore:
    def __init__(self, connection):
        self.connection = connection
        connection.execute('''CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
            photo_data TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )''')
        connection.execute('''CREATE TABLE IF NOT EXISTS user_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            expires_at INTEGER NOT NULL
        )''')

    def photo(self, user_id):
        row = self.connection.execute('SELECT photo_data FROM user_profiles WHERE user_id=?', (user_id,)).fetchone()
        return row[0] if row else DEFAULT_PHOTO

    def set_photo(self, user_id, photo):
        photo = validate_photo(photo)
        self.connection.execute('''INSERT INTO user_profiles (user_id, photo_data, updated_at)
            VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET
            photo_data=excluded.photo_data, updated_at=excluded.updated_at''',
            (user_id, photo, int(time.time())))
        return photo

    def issue_session(self, user_id):
        token = secrets.token_urlsafe(32)
        self.connection.execute('DELETE FROM user_sessions WHERE expires_at <= ?', (int(time.time()),))
        self.connection.execute('INSERT INTO user_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)',
            (self.token_hash(token), user_id, int(time.time()) + SESSION_SECONDS))
        self.connection.commit()
        return token

    @staticmethod
    def token_hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def authenticate(self, authorization):
        scheme, _, token = (authorization or '').partition(' ')
        if scheme.lower() != 'bearer' or not token or len(token) > 256:
            raise ProfileError(401, 'Vuelve a iniciar sesión para acceder a tu perfil.')
        row = self.connection.execute('''SELECT u.id FROM user_sessions s
            JOIN usuarios u ON u.id=s.user_id
            WHERE s.token_hash=? AND s.expires_at>? AND u.estado='Activo' ''',
            (self.token_hash(token), int(time.time()))).fetchone()
        if not row:
            raise ProfileError(401, 'Tu sesión expiró. Vuelve a iniciar sesión.')
        return row[0]

    def profile(self, user_id):
        row = self.connection.execute('''SELECT u.id, u.rut, u.nombre, u.email, u.rol_codigo,
            r.nombre AS rol_nombre, u.delegacion_codigo, d.nombre AS delegacion_nombre, u.estado
            FROM usuarios u LEFT JOIN roles r ON r.codigo=u.rol_codigo
            LEFT JOIN delegaciones d ON d.codigo=u.delegacion_codigo WHERE u.id=?''', (user_id,)).fetchone()
        user = dict(row)
        user['foto_perfil'] = self.photo(user_id)
        return user

    def revoke(self, authorization):
        token = authorization.partition(' ')[2]
        self.connection.execute('DELETE FROM user_sessions WHERE token_hash=?', (self.token_hash(token),))
        self.connection.commit()
