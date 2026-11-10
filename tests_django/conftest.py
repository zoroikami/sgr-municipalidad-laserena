import pytest
from django.contrib.auth import get_user_model

from cuentas.models import Perfil
from cuentas.roles import configure_groups
from gestion.models import Atencion, Delegacion, ItemMeta, SubAtencion, TipoAtencion


@pytest.fixture
def mundo(db):
    from django.contrib.auth.models import Group
    configure_groups()
    a = Delegacion.objects.create(codigo='DEL01', nombre='Centro', direccion='Centro 1')
    b = Delegacion.objects.create(codigo='DEL02', nombre='Las Compañías', direccion='Norte 1')
    users = {}
    for number, (alias, role, org) in enumerate([
        ('admin_a', 'Delegado Municipal', a), ('editor_a', 'Operador / Funcionario', a),
        ('lector_a', 'Consultor', a), ('lector_b', 'Consultor', b),
        ('cliente_1', 'Cliente', a), ('cliente_2', 'Cliente', a),
        ('coordinador', 'Coordinador', a),
    ], start=1):
        user = get_user_model().objects.create_user(alias, f'{alias}@example.test', 'Ensayo#Privado2026')
        user.groups.add(Group.objects.get(name=role))
        # Valid and distinct RUTs, generated from deterministic fixture bodies.
        body = str(11000000 + number)
        total = sum(int(n) * (2 + i % 6) for i, n in enumerate(reversed(body)))
        dv = 11 - total % 11
        rut = body + '-' + ('0' if dv == 11 else 'K' if dv == 10 else str(dv))
        Perfil.objects.create(user=user, delegacion=org, rut=rut)
        users[alias] = user
    tipo_a = TipoAtencion.objects.create(delegacion=a, nombre='Social')
    tipo_b = TipoAtencion.objects.create(delegacion=b, nombre='Salud')
    sub_a = SubAtencion.objects.create(delegacion=a, tipo=tipo_a, nombre='Subsidios')
    sub_b = SubAtencion.objects.create(delegacion=b, tipo=tipo_b, nombre='Farmacia')
    meta_a = ItemMeta.objects.create(delegacion=a, nombre='Cobertura A', unidad_medida='Atenciones')
    meta_b = ItemMeta.objects.create(delegacion=b, nombre='Reserva B', unidad_medida='Atenciones')
    atn_a = Atencion.objects.create(delegacion=a, tipo=tipo_a, subatencion=sub_a,
        responsable=users['editor_a'], cliente=users['cliente_1'], solicitante_rut='12345678-5',
        solicitante_nombre='Alicia Centro', descripcion='Solicitud Centro')
    atn_b = Atencion.objects.create(delegacion=b, tipo=tipo_b, subatencion=sub_b,
        responsable=users['lector_b'], solicitante_rut='12345678-5',
        solicitante_nombre='Bernarda Norte', descripcion='Solicitud Norte')
    atn_2 = Atencion.objects.create(delegacion=a, tipo=tipo_a, subatencion=sub_a,
        responsable=users['editor_a'], cliente=users['cliente_2'], solicitante_rut='12345678-5',
        solicitante_nombre='Carolina Centro', descripcion='Solicitud Cliente 2')
    return dict(a=a, b=b, users=users, tipo_a=tipo_a, tipo_b=tipo_b, sub_a=sub_a, sub_b=sub_b,
                meta_a=meta_a, meta_b=meta_b, atn_a=atn_a, atn_b=atn_b, atn_2=atn_2)
