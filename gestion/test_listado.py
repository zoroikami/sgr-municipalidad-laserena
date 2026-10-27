"""Consultas combinadas y aislamiento del CRUD, con datos independientes del equipo."""
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase

from .models import Delegacion, ItemMeta, Rol, Usuario


class CrudListingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.delegacion = Delegacion.objects.create(
            codigo='DEL01', nombre='Centro', direccion='Calle central')
        cls.admin = Usuario.objects.create_superuser(
            username='admin-listado', email='admin-listado@example.test',
            password='ClavePrueba123!', delegacion=cls.delegacion)
        Delegacion.objects.bulk_create([
            Delegacion(codigo=f'DEL{i + 1:02}', nombre=f'Zona {i:02}',
                       direccion='Avenida costera', estado='Activa')
            for i in range(1, 32)
        ])
        Delegacion.objects.create(codigo='DEL99', nombre='Zona inactiva',
                                  direccion='Calle interior', estado='Inactiva')
        ItemMeta.objects.bulk_create([
            ItemMeta(codigo=f'IT{i:03}', nombre=f'Meta {i:02}')
            for i in range(1, 17)
        ])

    def setUp(self):
        self.client.force_login(self.admin)

    def test_page_size_is_remembered_after_refresh(self):
        response = self.client.get('/gestion/delegaciones/?page_size=5')
        self.assertEqual(len(response.context['records']), 5)
        response = self.client.get('/gestion/delegaciones/')
        self.assertEqual(len(response.context['records']), 5)
        self.assertEqual(response.context['page_size'], 5)

    def test_page_size_is_independent_for_each_catalog(self):
        self.client.get('/gestion/delegaciones/?page_size=30')
        response = self.client.get('/gestion/items-metas/')
        self.assertEqual(len(response.context['records']), 15)
        self.assertEqual(response.context['page_size'], 15)
        response = self.client.get('/gestion/delegaciones/')
        self.assertEqual(len(response.context['records']), 30)

    def test_invalid_page_sizes_keep_the_last_valid_preference(self):
        self.client.get('/gestion/delegaciones/?page_size=5')
        for value in ('5000', '0', '-1', 'incorrecto'):
            with self.subTest(value=value):
                response = self.client.get('/gestion/delegaciones/', {'page_size': value})
                self.assertEqual(len(response.context['records']), 5)

    def test_search_filter_order_and_page_work_together(self):
        response = self.client.get('/gestion/delegaciones/', {
            'q': 'Zona', 'estado': 'Activa', 'order': '-nombre',
            'page_size': '5', 'page': '2',
        })
        self.assertEqual(response.context['paginator'].count, 31)
        self.assertEqual(
            [record.nombre for record in response.context['records']],
            ['Zona 26', 'Zona 25', 'Zona 24', 'Zona 23', 'Zona 22'])
        self.assertContains(response, 'order=-nombre')
        self.assertContains(response, 'page_size=5')

    def test_unrecognized_order_uses_the_default_sort(self):
        response = self.client.get('/gestion/delegaciones/', {
            'q': 'Zona', 'estado': 'Activa', 'order': 'password', 'page_size': '5',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['records'][0].nombre, 'Zona 01')
        self.assertEqual(response.context['ordering'], 'nombre')

    def test_equal_names_have_stable_pages(self):
        duplicates = [Delegacion.objects.create(
            codigo=f'DUP{i:02}', nombre='Mismo nombre', direccion='Calle')
            for i in range(7)]
        response = self.client.get('/gestion/delegaciones/', {
            'q': 'Mismo nombre', 'page_size': '5', 'page': '2', 'order': 'nombre',
        })
        self.assertEqual([record.pk for record in response.context['records']],
                         [duplicates[5].pk, duplicates[6].pk])

    def test_save_preserves_the_combined_query(self):
        response = self.client.post(
            '/gestion/delegaciones/nuevo/?q=Zona&estado=Activa&order=-nombre&page_size=5&page=2',
            {'nombre': 'Zona nueva', 'direccion': 'Calle nueva',
             'comuna': 'La Serena', 'estado': 'Activa'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(parse_qs(urlsplit(response.url).query), {
            'q': ['Zona'], 'estado': ['Activa'], 'order': ['-nombre'],
            'page_size': ['5'], 'page': ['2'],
        })

    def test_search_includes_visible_address(self):
        response = self.client.get('/gestion/delegaciones/?q=costera')
        self.assertEqual(response.context['paginator'].count, 31)

    def test_all_six_catalogs_offer_page_size_and_order(self):
        for slug in ('delegaciones', 'roles', 'usuarios', 'items-metas',
                     'tipos-atencion', 'sub-atenciones'):
            with self.subTest(slug=slug):
                response = self.client.get(f'/gestion/{slug}/')
                self.assertContains(response, 'name="page_size"')
                self.assertContains(response, 'name="order"')
                self.assertEqual(response.context['page_size'], 15)

    def test_delegation_filter_only_offers_the_actors_scope(self):
        rol = Rol.objects.create(codigo='ROL03', nombre='Delegado')
        delegado = Usuario.objects.create_user(
            username='delegado-listado', email='delegado-listado@example.test',
            rol=rol, delegacion=self.delegacion)
        self.client.force_login(delegado)
        response = self.client.get('/gestion/usuarios/')
        self.assertEqual(list(response.context['delegaciones']), [self.delegacion])

    def test_delegate_without_delegation_is_denied_user_management(self):
        rol = Rol.objects.create(codigo='ROL03', nombre='Delegado')
        delegado = Usuario.objects.create_user(
            username='sin-delegacion', email='sin-delegacion@example.test', rol=rol)
        self.client.force_login(delegado)
        self.assertEqual(self.client.get('/gestion/usuarios/').status_code, 403)

    def test_sorting_and_filters_do_not_expand_the_delegates_scope(self):
        rol = Rol.objects.create(codigo='ROL03', nombre='Delegado')
        operador = Rol.objects.create(codigo='ROL04', nombre='Operador')
        delegado = Usuario.objects.create_user(
            username='delegado-ambito', email='delegado-ambito@example.test',
            rol=rol, delegacion=self.delegacion)
        own_user = Usuario.objects.create_user(
            username='operador-propio', nombre='Operador propio',
            email='propio@example.test', rol=operador, delegacion=self.delegacion)
        foreign_delegation = Delegacion.objects.get(codigo='DEL02')
        Usuario.objects.create_user(
            username='operador-ajeno', nombre='Operador ajeno',
            email='ajeno@example.test', rol=operador, delegacion=foreign_delegation)
        self.client.force_login(delegado)
        response = self.client.get('/gestion/usuarios/', {
            'q': 'Operador', 'order': '-email', 'page_size': '5',
        })
        self.assertEqual(list(response.context['records']), [own_user])
        response = self.client.get('/gestion/usuarios/', {
            'q': 'Operador', 'delegacion': foreign_delegation.codigo,
            'order': '-email', 'page_size': '30',
        })
        self.assertEqual(response.context['paginator'].count, 0)

    def test_a_total_role_receives_native_write_permissions(self):
        rol = Rol.objects.create(codigo='ROL05', nombre='Consultor', permisos='total')
        user = Usuario.objects.create_user(
            username='total-configurable', email='total-configurable@example.test',
            rol=rol, delegacion=self.delegacion)
        self.client.force_login(user)
        self.assertEqual(self.client.get('/gestion/delegaciones/nuevo/').status_code, 200)

    def territorial_accounts(self):
        delegated_role = Rol.objects.create(codigo='ROL03', nombre='Delegado')
        total_role = Rol.objects.create(codigo='ROL05', nombre='Consulta global', permisos='total')
        actor = Usuario.objects.create_user(
            username='delegado-seguro', email='delegado-seguro@example.test',
            rol=delegated_role, delegacion=self.delegacion)
        target = Usuario.objects.create_user(
            username='objetivo-total', email='objetivo-total@example.test',
            password='ClaveOriginal123!', nombre='Cuenta global',
            rol=total_role, delegacion=self.delegacion)
        self.client.force_login(actor)
        return target, total_role

    def test_delegate_cannot_assign_a_total_role(self):
        _, total_role = self.territorial_accounts()
        response = self.client.post('/gestion/usuarios/nuevo/', {
            'rut': '11111111-1', 'nombre': 'Nueva cuenta',
            'email': 'escalada@example.test', 'rol': total_role.codigo,
            'delegacion': self.delegacion.codigo, 'estado': 'Activo',
            'password': 'ClavePrueba123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('rol', response.context['form'].errors)
        self.assertFalse(Usuario.objects.filter(email='escalada@example.test').exists())

    def test_delegate_cannot_edit_or_delete_a_total_account(self):
        target, _ = self.territorial_accounts()
        response = self.client.get('/gestion/usuarios/')
        self.assertNotIn(target.pk, [user.pk for user in response.context['records']])
        for action in ('editar', 'eliminar'):
            with self.subTest(action=action):
                url = f'/gestion/usuarios/{target.pk}/{action}/'
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {}).status_code, 404)
        target.refresh_from_db()
        self.assertTrue(target.check_password('ClaveOriginal123!'))

    def test_compatibility_api_also_blocks_total_account_assignment(self):
        _, total_role = self.territorial_accounts()
        response = self.client.post('/api/usuarios', {
            'rut': '11111111-1', 'nombre': 'Nueva cuenta',
            'email': 'escalada-api@example.test', 'rol_codigo': total_role.codigo,
            'delegacion_codigo': self.delegacion.codigo, 'estado': 'Activo',
            'password': 'ClavePrueba123!',
        }, content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Usuario.objects.filter(email='escalada-api@example.test').exists())

    def test_compatibility_api_hides_total_accounts_from_delegates(self):
        target, _ = self.territorial_accounts()
        self.assertEqual(self.client.get(f'/api/usuarios/{target.pk}').status_code, 404)
        self.assertEqual(self.client.put(f'/api/usuarios/{target.pk}', {},
                                        content_type='application/json').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/usuarios/{target.pk}').status_code, 404)

    def test_compatibility_api_requires_delegation_for_user_management(self):
        rol = Rol.objects.create(codigo='ROL03', nombre='Delegado')
        actor = Usuario.objects.create_user(
            username='api-sin-ambito', email='api-sin-ambito@example.test', rol=rol)
        self.client.force_login(actor)
        self.assertEqual(self.client.get('/api/usuarios').status_code, 403)
