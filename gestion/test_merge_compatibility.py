from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .models import Atencion, Delegacion, ItemMeta, Rol, SubAtencion, TipoAtencion


PHOTO = ('data:image/png;base64,'
         'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aY7sAAAAASUVORK5CYII=')
DEFAULT_PHOTO = '/assets/municipal/avatar-default.svg'


class MainCompatibilityTests(TestCase):
    def setUp(self):
        self.delegacion = Delegacion.objects.create(codigo='DEL01', nombre='Centro', direccion='Centro 1')
        self.rol = Rol.objects.create(codigo='ROL01', nombre='Administrador', permisos='total')
        self.user = get_user_model().objects.create_user(
            username='admin', email='admin@example.test', password='PruebaSegura123!',
            rut='12345678-5', nombre='Administrador', rol=self.rol, delegacion=self.delegacion)
        self.client.force_login(self.user)

    def post_user(self, **changes):
        payload = dict(rut='11.111.111-1', nombre='Nuevo', email='nuevo@example.test',
                       password='NuevaClave123!', rol_codigo=self.rol.codigo,
                       delegacion_codigo=self.delegacion.codigo)
        payload.update(changes)
        return self.client.post('/api/usuarios', payload, content_type='application/json')

    def test_profile_photo_persists_with_django_session_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get('/api/health')
        self.assertEqual(client.put('/api/profile', {'photo': PHOTO}, content_type='application/json').status_code, 403)
        response = client.put('/api/profile', {'photo': PHOTO}, content_type='application/json',
                              HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['user']['foto_perfil'], PHOTO)
        self.client.logout()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/api/profile').json()['user']['foto_perfil'], PHOTO)

    def test_profile_rejects_other_user_fields_and_restores_default_photo(self):
        self.assertEqual(self.client.put('/api/profile', {'photo': PHOTO, 'user_id': 999}, content_type='application/json').status_code, 400)
        self.client.put('/api/profile', {'photo': PHOTO}, content_type='application/json')
        response = self.client.put('/api/profile', {'photo': None}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['user']['foto_perfil'], DEFAULT_PHOTO)

    def test_new_user_photo_is_saved_and_invalid_photo_does_not_create_user(self):
        response = self.post_user(foto_perfil='data:image/png;base64,aG9sYQ==')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(get_user_model().objects.filter(email='nuevo@example.test').exists())
        response = self.post_user(foto_perfil=PHOTO)
        self.assertEqual(response.status_code, 201, response.content)
        users = self.client.get('/api/usuarios').json()
        self.assertEqual(next(user for user in users if user['email'] == 'nuevo@example.test')['foto_perfil'], PHOTO)

    def test_user_rut_is_validated_and_equivalent_formats_are_duplicates(self):
        self.assertEqual(self.post_user(rut='11.111.111-2').status_code, 400)
        self.assertEqual(self.post_user().status_code, 201)
        self.assertEqual(get_user_model().objects.get(email='nuevo@example.test').rut, '11111111-1')
        self.assertEqual(self.post_user(rut='111111111', email='duplicado@example.test').status_code, 409)

    def test_role_api_assigns_code_instead_of_accepting_a_manual_value(self):
        response = self.client.post('/api/roles', {'nombre':'Consulta comunal', 'permisos':'lectura', 'codigo':'ROL99'}, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        role = Rol.objects.get(nombre='Consulta comunal')
        self.assertEqual(role.codigo, 'ROL02')
        self.assertEqual(self.client.put(f'/api/roles/{role.pk}', {'codigo':'ROL88', 'nombre':'Consulta editada'}, content_type='application/json').status_code, 200)
        role.refresh_from_db()
        self.assertEqual(role.codigo, 'ROL02')

    def test_attention_requires_valid_rut_and_stores_normalized_value(self):
        tipo = TipoAtencion.objects.create(codigo='TA001', nombre='Social')
        sub = SubAtencion.objects.create(codigo='SA001', nombre='Ayuda', tipo=tipo)
        payload = dict(solicitante_nombre='Vecino', descripcion='Consulta',
                       tipo_codigo=tipo.codigo, subtipo_codigo=sub.codigo,
                       delegacion_codigo=self.delegacion.codigo)
        for rut in (None, '', '11.111.111-2'):
            with self.subTest(rut=rut):
                response = self.client.post('/api/atenciones', dict(payload, solicitante_rut=rut), content_type='application/json')
                self.assertEqual(response.status_code, 400, response.content)
        response = self.client.post('/api/atenciones', dict(payload, solicitante_rut='11.111.111-1'), content_type='application/json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Atencion.objects.get().solicitante_rut, '11111111-1')

    def test_attention_modelform_normalizes_rut_and_rejects_bad_check_digit(self):
        from .forms import AtencionForm
        tipo = TipoAtencion.objects.create(codigo='TA001', nombre='Social')
        sub = SubAtencion.objects.create(codigo='SA001', nombre='Ayuda', tipo=tipo)
        payload = dict(folio='ATN-2026-0001', solicitante_rut='11.111.111-1',
                       solicitante_nombre='Vecina', delegacion=self.delegacion.codigo,
                       tipo=tipo.codigo, subtipo=sub.codigo, descripcion='Consulta',
                       responsable_nombre='Administrador')
        form = AtencionForm(data=payload)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['solicitante_rut'], '11111111-1')
        invalid = AtencionForm(data=dict(payload, solicitante_rut='11.111.111-2'))
        self.assertFalse(invalid.is_valid())
        self.assertIn('solicitante_rut', invalid.errors)

    def test_meta_quantity_remains_automatic_on_create_and_edit(self):
        response = self.client.post('/api/items-metas', {'nombre': 'Cobertura', 'meta_cantidad': 999}, content_type='application/json')
        self.assertEqual(response.status_code, 201, response.content)
        item = ItemMeta.objects.get()
        self.assertEqual(item.meta_cantidad, 100)
        self.client.put(f'/api/items-metas/{item.pk}', {'nombre': 'Editado', 'meta_cantidad': 777}, content_type='application/json')
        item.refresh_from_db()
        self.assertEqual(item.meta_cantidad, 100)
