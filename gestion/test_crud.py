from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse
from .models import Delegacion, ItemMeta, Rol, TipoAtencion, SubAtencion, Usuario

class ProtectedCrudTests(TestCase):
    def setUp(self):
        self.delegacion = Delegacion.objects.create(codigo='DEL01', nombre='Centro', direccion='Centro 1')
        self.rol = Rol.objects.create(codigo='ROL01', nombre='Administrador', permisos='total')
        self.admin = Usuario.objects.create_superuser(username='admin', email='admin@example.test', password='ClavePrueba123!', nombre='Admin', delegacion=self.delegacion, rol=self.rol)
        self.client.force_login(self.admin)

    def test_anonymous_redirect_and_operation_permissions(self):
        self.client.logout()
        response = self.client.get('/gestion/delegaciones/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=', response.url)
        viewer = Usuario.objects.create_user(username='viewer', email='viewer@example.test', password='ClavePrueba123!')
        self.client.force_login(viewer)
        self.assertEqual(self.client.get('/gestion/delegaciones/').status_code, 403)
        viewer.user_permissions.add(Permission.objects.get(codename='view_delegacion'))
        self.assertEqual(self.client.get('/gestion/delegaciones/').status_code, 200)
        self.assertEqual(self.client.post('/gestion/delegaciones/nuevo/', {'nombre':'Nueva', 'direccion':'Calle 1', 'comuna':'La Serena', 'estado':'Activa'}).status_code, 403)

    def test_delegacion_complete_crud_with_bootstrap_modal(self):
        url = '/gestion/delegaciones/'
        response = self.client.get(url+'nuevo/')
        self.assertContains(response, 'id="crudModal"')
        self.assertContains(response, 'modal-dialog')
        self.assertContains(response, 'csrfmiddlewaretoken')
        result = self.client.post(url+'nuevo/', {'nombre':'Nueva', 'direccion':'Calle 2', 'comuna':'La Serena', 'estado':'Activa'})
        self.assertEqual(result.status_code, 302)
        obj = Delegacion.objects.get(nombre='Nueva')
        self.assertNotEqual(obj.codigo, self.delegacion.codigo)
        result = self.client.post(f'{url}{obj.pk}/editar/', {'nombre':'Actualizada', 'direccion':'Calle 3', 'comuna':'La Serena', 'estado':'Inactiva'})
        self.assertEqual(result.status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.nombre, 'Actualizada')
        self.client.get(f'{url}{obj.pk}/eliminar/')
        self.assertTrue(Delegacion.objects.filter(pk=obj.pk).exists())
        result = self.client.post(f'{url}{obj.pk}/eliminar/')
        self.assertEqual(result.status_code, 302)
        self.assertFalse(Delegacion.objects.filter(pk=obj.pk).exists())

    def test_form_errors_reopen_modal_and_do_not_save(self):
        response = self.client.post('/gestion/delegaciones/nuevo/', {'nombre':'  ', 'direccion':'', 'comuna':'La Serena', 'estado':'Activa'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['open_modal'])
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(Delegacion.objects.count(), 1)

    def test_search_filter_pagination_preserve_query(self):
        Delegacion.objects.bulk_create([Delegacion(codigo=f'DEL{i+2:02}', nombre=f'Zona {i:02}', direccion='Calle', estado='Activa') for i in range(17)])
        Delegacion.objects.create(codigo='DEL99', nombre='Zona inactiva', direccion='Calle', estado='Inactiva')
        response = self.client.get('/gestion/delegaciones/?q=Zona&estado=Activa&page=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['paginator'].count, 17)
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertContains(response, 'q=Zona')
        self.assertContains(response, 'estado=Activa')
        result = self.client.post('/gestion/delegaciones/nuevo/?q=Zona&estado=Activa&page=2', {'nombre':'Zona nueva', 'direccion':'Calle', 'comuna':'La Serena', 'estado':'Activa'})
        self.assertIn('q=Zona', result.url)
        self.assertIn('estado=Activa', result.url)

    def test_protected_delete_returns_message(self):
        response = self.client.post(f'/gestion/delegaciones/{self.delegacion.pk}/eliminar/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Delegacion.objects.filter(pk=self.delegacion.pk).exists())
        self.assertContains(response, 'registros asociados')

    def test_role_groups_and_territorial_scope(self):
        rol = Rol.objects.create(codigo='ROL03', nombre='Delegado')
        delegated = Usuario.objects.create_user(username='delegado', email='delegado@example.test', password='ClavePrueba123!', rol=rol, delegacion=self.delegacion)
        other = Delegacion.objects.create(codigo='DEL02', nombre='Otra', direccion='Otra')
        target = Usuario.objects.create_user(username='otro', email='otro@example.test', password='ClavePrueba123!', rol=Rol.objects.create(codigo='ROL04', nombre='Operador'), delegacion=other)
        self.client.force_login(delegated)
        self.assertEqual(self.client.get('/gestion/usuarios/').status_code, 200)
        self.assertEqual(self.client.get(f'/gestion/usuarios/{target.pk}/editar/').status_code, 404)
        self.assertEqual(self.client.post('/gestion/usuarios/nuevo/', {'rut':'11111111-1', 'nombre':'Escalada', 'email':'escalada@example.test', 'rol':self.rol.codigo, 'delegacion':self.delegacion.codigo, 'estado':'Activo', 'password':'ClavePrueba123!'}).status_code, 200)
        self.assertFalse(Usuario.objects.filter(email='escalada@example.test').exists())

    def test_other_catalog_forms_persist(self):
        cases = [
            ('roles', Rol, {'codigo':'ROL05','nombre':'Consultor','descripcion':'Lectura','permisos':'lectura','alcance':'Lectura','estado':'Activo'}),
            ('items-metas', ItemMeta, {'nombre':'Cobertura','descripcion':'Meta','unidad_medida':'Atenciones','meta_cantidad':100,'estado':'Activo'}),
            ('tipos-atencion', TipoAtencion, {'nombre':'Social','descripcion':'Atención social','estado':'Activo'}),
        ]
        for slug, model, payload in cases:
            with self.subTest(slug=slug):
                base=f'/gestion/{slug}/'
                response=self.client.post(base+'nuevo/', payload)
                self.assertEqual(response.status_code,302)
                obj=model.objects.get(nombre=payload['nombre'])
                response=self.client.post(f'{base}{obj.pk}/editar/', dict(payload,nombre='Modificado'))
                self.assertEqual(response.status_code,302)
                obj.refresh_from_db()
                self.assertEqual(obj.nombre,'Modificado')
                self.assertEqual(self.client.post(f'{base}{obj.pk}/eliminar/').status_code,302)
                self.assertFalse(model.objects.filter(pk=obj.pk).exists())

    def test_role_code_is_automatic_and_cannot_be_overwritten(self):
        Rol.objects.create(codigo='ROL02', nombre='Coordinador')
        response = self.client.get('/gestion/roles/nuevo/')
        self.assertNotIn('codigo', response.context['form'].fields)
        payload = {'nombre':'Apoyo comunal', 'descripcion':'Lectura', 'permisos':'lectura', 'alcance':'Comunal', 'estado':'Activo'}
        self.assertEqual(self.client.post('/gestion/roles/nuevo/', payload).status_code, 302)
        role = Rol.objects.get(nombre='Apoyo comunal')
        self.assertEqual(role.codigo, 'ROL03')
        self.assertEqual(self.client.post('/gestion/roles/nuevo/', dict(payload, nombre='Otro apoyo', codigo='ROL99')).status_code, 302)
        self.assertEqual(Rol.objects.get(nombre='Otro apoyo').codigo, 'ROL04')
        self.assertEqual(self.client.post(f'/gestion/roles/{role.pk}/editar/', dict(payload, nombre='Apoyo editado', codigo='ROL88')).status_code, 302)
        role.refresh_from_db()
        self.assertEqual(role.codigo, 'ROL03')

    def test_user_rut_has_live_validation_and_invalid_values_are_not_saved(self):
        response = self.client.get('/gestion/usuarios/nuevo/')
        self.assertIn('data-rut', response.context['form'].fields['rut'].widget.attrs)
        self.assertContains(response, 'id_rut_feedback')
        payload = {'rut':'12.345.678-9', 'nombre':'Prueba de RUT', 'email':'rut@example.test', 'rol':self.rol.codigo, 'delegacion':self.delegacion.codigo, 'estado':'Activo', 'password':'ClavePrueba123!'}
        response = self.client.post('/gestion/usuarios/nuevo/', payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn('rut', response.context['form'].errors)
        self.assertFalse(Usuario.objects.filter(email='rut@example.test').exists())

    def test_csrf_and_login_by_email(self):
        client=Client(enforce_csrf_checks=True)
        response=client.get('/acceso/')
        self.assertEqual(response.status_code,200)
        token=client.cookies['csrftoken'].value
        response=client.post('/acceso/?next=/gestion/delegaciones/',{'username':self.admin.email,'password':'ClavePrueba123!','csrfmiddlewaretoken':token})
        self.assertRedirects(response,'/gestion/delegaciones/')
        self.assertEqual(client.post('/gestion/delegaciones/nuevo/',{}).status_code,403)

    def test_shared_shell_hides_application_until_authenticated_and_shows_native_crud(self):
        anonymous = Client()
        response = anonymous.get('/')
        self.assertContains(response, '<div id="sgr-app-container" style="display: none;">')
        self.assertNotContains(response, 'btn-quick-login')
        self.assertNotContains(response, 'role-demo-bar')
        response = self.client.get('/gestion/delegaciones/')
        self.assertContains(response, '<div id="sgr-app-container" style="display: block;">')
        self.assertNotContains(response, 'btn-quick-login')

    def test_user_form_create_update_and_delete(self):
        role = Rol.objects.create(codigo='ROL04', nombre='Operador')
        payload = {'rut':'11.111.111-1', 'nombre':'Nuevo usuario', 'email':'nuevo@example.test', 'rol':role.codigo, 'delegacion':self.delegacion.codigo, 'estado':'Activo', 'password':'ClaveNueva123!'}
        response = self.client.post('/gestion/usuarios/nuevo/', payload)
        self.assertEqual(response.status_code, 302)
        user = Usuario.objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        response = self.client.post(f'/gestion/usuarios/{user.pk}/editar/', dict(payload, nombre='Usuario editado', password=''))
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.nombre, 'Usuario editado')
        self.assertTrue(user.check_password(payload['password']))
        self.assertEqual(self.client.post(f'/gestion/usuarios/{user.pk}/eliminar/').status_code, 302)
        self.assertFalse(Usuario.objects.filter(pk=user.pk).exists())

    def test_subatencion_form_create_update_delete_and_type_filter(self):
        tipo = TipoAtencion.objects.create(codigo='TA001', nombre='Social')
        another = TipoAtencion.objects.create(codigo='TA002', nombre='Salud')
        payload = {'nombre':'Ayuda social', 'tipo':tipo.codigo, 'estado':'Activa'}
        self.assertEqual(self.client.post('/gestion/sub-atenciones/nuevo/', payload).status_code, 302)
        obj = SubAtencion.objects.get(nombre='Ayuda social')
        self.assertEqual(self.client.post(f'/gestion/sub-atenciones/{obj.pk}/editar/', dict(payload,nombre='Ayuda editada')).status_code,302)
        self.assertEqual(self.client.get('/gestion/sub-atenciones/?tipo='+another.codigo).context['paginator'].count,0)
        self.assertEqual(self.client.get('/gestion/sub-atenciones/?tipo='+tipo.codigo).context['paginator'].count,1)
        self.assertEqual(self.client.post(f'/gestion/sub-atenciones/{obj.pk}/eliminar/').status_code,302)
        self.assertFalse(SubAtencion.objects.filter(pk=obj.pk).exists())

    def test_inactive_accounts_and_post_permissions(self):
        self.admin.estado='Inactivo'
        self.admin.save()
        self.assertEqual(self.client.get('/gestion/delegaciones/').status_code,403)
        self.assertEqual(self.client.post('/gestion/delegaciones/nuevo/',{}).status_code,403)

    def test_duplicate_rut_stays_in_modal_and_does_not_create(self):
        role = Rol.objects.create(codigo='ROL04', nombre='Operador')
        self.admin.rut='11111111-1'
        self.admin.save()
        response = self.client.post('/gestion/usuarios/nuevo/', {'rut':'11.111.111-1','nombre':'Duplicado','email':'duplicado@example.test','rol':role.codigo,'delegacion':self.delegacion.codigo,'estado':'Activo','password':'ClavePrueba123!'})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.context['form'].errors)
        self.assertTrue(response.context['open_modal'])
        self.assertFalse(Usuario.objects.filter(email='duplicado@example.test').exists())

    def test_direct_update_and_delete_require_own_permissions(self):
        user = Usuario.objects.create_user(username='lectura',email='lectura@example.test',password='ClavePrueba123!')
        user.user_permissions.add(Permission.objects.get(codename='view_delegacion'))
        self.client.force_login(user)
        base=f'/gestion/delegaciones/{self.delegacion.pk}/'
        for action in ('editar/', 'eliminar/'):
            self.assertEqual(self.client.get(base+action).status_code,403)
            self.assertEqual(self.client.post(base+action,{}).status_code,403)
        self.assertTrue(Delegacion.objects.filter(pk=self.delegacion.pk).exists())

    def test_deleting_last_record_on_page_returns_to_valid_page(self):
        Delegacion.objects.bulk_create([Delegacion(codigo=f'DEL{i+2:02}', nombre=f'Zona {i}', direccion='Calle') for i in range(15)])
        last=Delegacion.objects.order_by('id').last()
        response=self.client.post(f'/gestion/delegaciones/{last.pk}/eliminar/?page=2',follow=True)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['page_obj'].number,1)
        self.assertEqual(self.client.get('/gestion/delegaciones/?page=999').status_code,200)
        self.assertEqual(self.client.get('/gestion/delegaciones/?page=no-numero').status_code,200)
