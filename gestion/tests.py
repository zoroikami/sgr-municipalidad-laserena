from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from .models import Delegacion, Rol, TipoAtencion, SubAtencion, Atencion

class MigrationTests(TestCase):
    def setUp(self):
        self.delegacion = Delegacion.objects.create(codigo='DEL01', nombre='Centro', direccion='Centro 1')
        self.rol = Rol.objects.create(codigo='ROL01', nombre='Administrador', permisos='total')
        self.user = get_user_model().objects.create_user(username='admin', email='admin@example.test', password='PruebaSegura123!', nombre='Administrador', rut='12345678-5', rol=self.rol, delegacion=self.delegacion)

    def post(self, url, data):
        return self.client.post(url, data, content_type='application/json')

    def login(self):
        response = self.post('/api/auth/login', {'usuario': self.user.email, 'password': 'PruebaSegura123!'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password', response.json()['user'])

    def test_empty_database_has_no_imported_records(self):
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(Atencion.objects.count(), 0)

    def test_authentication_and_logout(self):
        self.assertEqual(self.client.get('/api/usuarios').status_code, 401)
        self.login()
        self.assertEqual(self.client.get('/api/profile').json()['user']['id'], self.user.id)
        self.assertEqual(self.client.get('/api/usuarios').status_code, 200)
        self.client.delete('/api/profile')
        self.assertEqual(self.client.get('/api/usuarios').status_code, 401)

    def test_crud_and_integrity(self):
        self.login()
        result = self.post('/api/tipos-atencion', {'nombre': 'Salud'})
        self.assertEqual(result.status_code, 201)
        tipo = result.json()['codigo']
        sub = self.post('/api/sub-atenciones', {'nombre': 'Consulta', 'tipo_codigo': tipo})
        self.assertEqual(sub.status_code, 201)
        self.assertEqual(self.client.get('/api/sub-atenciones?tipo=' + tipo).json()[0]['tipo_nombre'], 'Salud')
        self.assertEqual(self.client.delete('/api/tipos-atencion/' + str(result.json()['id'])).status_code, 400)
        self.assertEqual(self.client.put('/api/tipos-atencion/999', {'nombre':'X'}, content_type='application/json').status_code, 404)

    def test_hashed_password_and_login_by_rut(self):
        self.assertNotEqual(self.user.password, 'PruebaSegura123!')
        self.assertEqual(self.post('/api/auth/login', {'usuario': '12.345.678-5', 'password': 'PruebaSegura123!'}).status_code, 200)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recovery_requires_verified_code(self):
        self.assertEqual(self.post('/api/auth/cambiar-password', {'email':self.user.email, 'password':'OtraClave123!'}).status_code, 403)
        response = self.post('/api/auth/recuperar-codigo', {'email':self.user.email})
        self.assertNotIn('demo_code', response.json())
        code = mail.outbox[0].body.split()[-1]
        self.assertEqual(self.post('/api/auth/validar-codigo', {'email':self.user.email, 'codigo':code}).status_code, 200)
        self.assertEqual(self.post('/api/auth/cambiar-password', {'email':self.user.email, 'password':'OtraClave123!'}).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OtraClave123!'))
        self.assertEqual(self.post('/api/auth/cambiar-password', {'email':self.user.email, 'password':'OtraClave123!'}).status_code, 403)

    def test_permissions(self):
        self.user.rol = Rol.objects.create(codigo='ROL05', nombre='Consulta', permisos='lectura')
        self.user.save()
        self.login()
        self.assertEqual(self.post('/api/delegaciones', {'nombre':'Otra', 'direccion':'X'}).status_code, 403)

    def test_public_files_are_allowlisted(self):
        for path in ['/', '/evaluacion2/js/app_eval2.js', '/assets/municipal/brand.css']:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        for path in ['/server.py', '/.env', '/db.sqlite3', '/database/sgr_laserena.db']:
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_atencion_and_all_catalogs(self):
        self.login()
        for resource, payload in [
            ('delegaciones', {'nombre':'Sur', 'direccion':'Calle 2'}),
            ('roles', {'codigo':'ROL04', 'nombre':'Operador', 'permisos':'operador'}),
            ('items-metas', {'nombre':'Meta', 'meta_cantidad':120}),
            ('tipos-atencion', {'nombre':'Social'}),
        ]:
            response = self.post('/api/' + resource, payload)
            self.assertEqual(response.status_code, 201, response.content)
            record_id = response.json()['id']
            self.assertEqual(self.client.put(f'/api/{resource}/{record_id}', {'nombre':'Editado'}, content_type='application/json').status_code, 200)
        tipo = TipoAtencion.objects.first()
        sub = SubAtencion.objects.create(codigo='SA001', nombre='Ayuda', tipo=tipo)
        response = self.post('/api/atenciones', {'solicitante_nombre':'Vecino', 'solicitante_rut':'12345678-5', 'delegacion_codigo':self.delegacion.codigo, 'tipo_codigo':tipo.codigo, 'subtipo_codigo':sub.codigo, 'descripcion':'Solicitud', 'responsable_nombre':'Falsificado'})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()['folio'].startswith('ATN-'))
        self.assertEqual(Atencion.objects.get().responsable_nombre, self.user.nombre)
        self.assertEqual(self.client.get('/api/stats').json()['atenciones'], 1)

    def test_usuario_creation_and_password_not_exposed(self):
        self.login()
        response = self.post('/api/usuarios', {'rut':'11.111.111-1', 'nombre':'Nuevo', 'email':'nuevo@example.test', 'password':'NuevaClave123!', 'rol_codigo':self.rol.codigo, 'delegacion_codigo':self.delegacion.codigo})
        self.assertEqual(response.status_code, 201, response.content)
        user = get_user_model().objects.get(pk=response.json()['id'])
        self.assertTrue(user.check_password('NuevaClave123!'))
        self.assertNotIn('password', self.client.get('/api/usuarios').json()[0])
        self.assertEqual(self.client.delete('/api/usuarios/' + str(user.pk)).status_code, 200)

    def test_delegation_scope_and_privilege_escalation(self):
        delegado = Rol.objects.create(codigo='ROL03', nombre='Delegado')
        operador = Rol.objects.create(codigo='ROL04', nombre='Operador')
        other = Delegacion.objects.create(codigo='DEL02', nombre='Otra', direccion='Otra 2')
        get_user_model().objects.create_user(username='ajeno', email='otro@example.test', password='Clave123!', rol=operador, delegacion=other)
        self.user.rol = delegado
        self.user.save()
        self.login()
        self.assertEqual(self.client.get('/api/usuarios').json(), [])
        response = self.post('/api/usuarios', {'rut':'22222222-2', 'nombre':'Escalada', 'email':'escala@example.test', 'password':'Clave123!', 'rol_codigo':self.rol.codigo, 'delegacion_codigo':self.delegacion.codigo})
        self.assertEqual(response.status_code, 403)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recovery_attempt_limit_and_no_magic_code(self):
        self.post('/api/auth/recuperar-codigo', {'email':self.user.email})
        from .models import Recuperacion
        rec = Recuperacion.objects.get()
        from django.contrib.auth.hashers import make_password
        rec.codigo_hash = make_password('654321')
        rec.save()
        for _ in range(3):
            self.assertEqual(self.post('/api/auth/validar-codigo', {'email':self.user.email, 'codigo':'123456'}).status_code, 400)
        self.assertEqual(self.post('/api/auth/validar-codigo', {'email':self.user.email, 'codigo':'654321'}).status_code, 429)

    def test_csrf_enforced_including_login_rotation(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        payload = {'usuario':self.user.email, 'password':'PruebaSegura123!'}
        self.assertEqual(client.post('/api/auth/login', payload, content_type='application/json').status_code, 403)
        client.get('/api/health')
        token = client.cookies['csrftoken'].value
        response = client.post('/api/auth/login', payload, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        new_token = client.cookies['csrftoken'].value
        self.assertNotEqual(token, new_token)
        response = client.post('/api/delegaciones', {'nombre':'Otra', 'direccion':'X'}, content_type='application/json', HTTP_X_CSRFTOKEN=new_token)
        self.assertEqual(response.status_code, 201)

    def test_invalid_json_and_unknown_resource(self):
        self.login()
        self.assertEqual(self.client.post('/api/delegaciones', '{', content_type='application/json').status_code, 400)
        self.assertEqual(self.post('/api/delegaciones', []).status_code, 400)
        self.assertEqual(self.client.get('/api/no-existe').status_code, 404)
