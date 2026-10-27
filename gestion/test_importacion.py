import io
import sqlite3
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import Atencion, Delegacion, Rol, Secuencia, Usuario
from .views import next_code


class ImportacionAnteriorTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / 'anterior.db'
        with sqlite3.connect(self.source) as db:
            db.executescript('''
                CREATE TABLE delegaciones (codigo, nombre, direccion, comuna, estado, creado_en);
                INSERT INTO delegaciones VALUES ('DEL01','Centro','Calle 1','La Serena','Activa','2026-08-01 10:00:00');
                CREATE TABLE roles (codigo, nombre, descripcion, permisos, alcance, estado);
                INSERT INTO roles VALUES ('ROL01','Administrador','','total','Comunal','Activo');
                CREATE TABLE items_metas (codigo, nombre, descripcion, unidad_medida, meta_cantidad, estado);
                INSERT INTO items_metas VALUES ('IT001','Cobertura','','Atenciones',150,'Activo');
                CREATE TABLE tipos_atencion (codigo, nombre, descripcion, estado);
                INSERT INTO tipos_atencion VALUES ('TA001','Social','','Activo');
                CREATE TABLE sub_atenciones (codigo, nombre, tipo_codigo, estado);
                INSERT INTO sub_atenciones VALUES ('SA001','Apoyo social','TA001','Activa');
                CREATE TABLE usuarios (id, rut, nombre, email, password_hash, rol_codigo, delegacion_codigo, estado);
                INSERT INTO usuarios VALUES (1,'12.345.678-5','Administración','admin@example.test','ClaveAntigua123!','ROL01','DEL01','Activo');
                INSERT INTO usuarios VALUES (2,'11.111.111-1','Ejemplo','ejemplo@example.test','ClaveEjemplo123!','ROL01','DEL01','Activo');
                CREATE TABLE atenciones (folio, solicitante_rut, solicitante_nombre, delegacion_codigo, tipo_codigo, subtipo_codigo, descripcion, responsable_nombre, fecha_registro);
                INSERT INTO atenciones VALUES ('ATN-2026-0003','12.345.678-5','Vecina','DEL01','TA001','SA001','Apoyo','Administración','2026-08-02 11:30:00');
            ''')
        self.admin = Usuario.objects.create_superuser(username='admin', email='admin@example.test', password='ClaveActual123!')

    def run_import(self):
        call_command('recuperar_datos_anteriores', str(self.source), stdout=io.StringIO())

    def test_recovers_relations_without_replacing_current_account_or_password(self):
        original_password = self.admin.password
        self.run_import()
        self.admin.refresh_from_db()
        self.assertEqual(Usuario.objects.count(), 2)
        self.assertEqual(self.admin.password, original_password)
        self.assertEqual(self.admin.username, 'admin')
        self.assertTrue(self.admin.is_superuser)
        self.assertEqual(self.admin.nombre, 'Administración')
        self.assertEqual(self.admin.rol_id, 'ROL01')
        self.assertEqual(self.admin.delegacion_id, 'DEL01')
        imported = Usuario.objects.get(email='ejemplo@example.test')
        self.assertTrue(imported.check_password('ClaveEjemplo123!'))
        self.assertNotEqual(imported.password, 'ClaveEjemplo123!')
        self.assertTrue(imported.groups.filter(name='SGR:ROL01').exists())
        attention = Atencion.objects.get()
        self.assertEqual(attention.subtipo.tipo_id, attention.tipo_id)
        self.assertEqual(attention.fecha_registro.year, 2026)
        self.assertEqual(attention.fecha_registro.month, 8)
        self.assertEqual(next_code('atenciones-2026', 'ATN-2026-', 4), 'ATN-2026-0004')

    def test_repeated_import_preserves_edited_data_and_does_not_duplicate(self):
        self.run_import()
        Delegacion.objects.filter(codigo='DEL01').update(nombre='Centro actualizado')
        self.admin.nombre = 'Mi nombre actual'
        self.admin.save(update_fields=['nombre'])
        self.run_import()
        self.assertEqual(Delegacion.objects.count(), 1)
        self.assertEqual(Rol.objects.count(), 1)
        self.assertEqual(Usuario.objects.count(), 2)
        self.assertEqual(Atencion.objects.count(), 1)
        self.assertEqual(Delegacion.objects.get().nombre, 'Centro actualizado')
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.nombre, 'Mi nombre actual')

    def test_invalid_reference_rolls_back_all_imported_records(self):
        with sqlite3.connect(self.source) as db:
            db.execute("UPDATE sub_atenciones SET tipo_codigo='NO-EXISTE'")
        with self.assertRaises(CommandError):
            self.run_import()
        self.assertFalse(Delegacion.objects.exists())
        self.assertFalse(Rol.objects.exists())
        self.assertFalse(Secuencia.objects.exists())
        self.assertEqual(Usuario.objects.count(), 1)
