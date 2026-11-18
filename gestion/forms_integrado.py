from django import forms
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone

from .access import scoped
from .delegation import has_global_scope
from .forms import ScopedModelForm
from .integrado import primera_fecha_admisible, validar_fecha
from .integrado import CARGOS, SUBFAMILIAS
from .models import ActividadSGR, AusenciaSGR, GestionTubo, Organizacion, Atencion, ItemMeta, ReclamoSGR


def nombre_cuenta(account):
    return account.get_full_name() or account.username


def cuentas_ambito(org_id, todas=False):
    users = get_user_model().objects.filter(is_active=True).exclude(groups__name='Cliente')
    if todas:
        return users.filter(perfil__delegacion__estado='Activo', perfil__delegacion__deleted_at__isnull=True)
    return users.filter(perfil__delegacion_id=org_id) if org_id else users.none()


class RelacionesForm(ScopedModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A global account's submitted delegation also constrains every relation.
        org = self.org_id
        if org is None and self.is_bound and has_global_scope(self.user) and not self.instance.pk:
            org = self.data.get('delegacion')
        self.rel_org = int(org) if str(org).isdigit() else None
        # Una cuenta global elige primero la delegación; recién entonces se cargan sus relaciones.
        self.rel_global = False

    def relaciones(self, model):
        if self.rel_global:
            return scoped(self.user, model).filter(delegacion__estado='Activo', delegacion__deleted_at__isnull=True)
        return model.objects.filter(delegacion_id=self.rel_org)


class OrganizacionForm(ScopedModelForm):
    subfamilia = forms.ChoiceField(label='Subfamilia', required=False)

    class Meta:
        model = Organizacion
        fields = ['nombre', 'familia', 'subfamilia', 'domicilio', 'socios_activos', 'fecha_constitucion',
                  'registro_pj', 'fecha_inscripcion', 'registro_directiva', 'verificada', 'descripcion', 'estado']
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
                   for key in ['fecha_constitucion', 'fecha_inscripcion']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opciones = [('', 'Selecciona la subfamilia')] + [
            (familia.capitalize(), [(nombre, nombre) for nombre in nombres]) for familia, nombres in SUBFAMILIAS.items()]
        actual = self.instance.subfamilia
        if actual and all(actual not in nombres for nombres in SUBFAMILIAS.values()):
            opciones.append(('Registrada', [(actual, actual)]))
        self.fields['subfamilia'].choices = opciones
        self.fields['subfamilia'].widget.attrs['class'] = 'form-select'
        self.fields['subfamilia'].help_text = 'Clasificación del nuevo requerimiento según el objetivo de la organización.'

    def clean(self):
        data = super().clean()
        familia, subfamilia = data.get('familia'), data.get('subfamilia')
        if familia and subfamilia and subfamilia in sum(SUBFAMILIAS.values(), []) and subfamilia not in SUBFAMILIAS[familia]:
            self.add_error('subfamilia', 'La subfamilia no corresponde a la familia elegida.')
        return data


class GestionTuboForm(RelacionesForm):
    class Meta:
        model = GestionTubo
        fields = ['nombre', 'descripcion', 'fecha_solicitud', 'origen', 'solicitante', 'territorio',
                  'responsable', 'fecha_compromiso', 'apoyo', 'observaciones', 'atencion', 'organizacion']
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
                   for key in ['fecha_solicitud', 'fecha_compromiso']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = cuentas_ambito(self.rel_org, todas=self.rel_global)
        self.fields['responsable'].label_from_instance = nombre_cuenta
        for campo, model in [('atencion', Atencion), ('organizacion', Organizacion)]:
            self.fields[campo].queryset = self.relaciones(model)
        # Solo atenciones abiertas pueden originar un compromiso; se conserva la ya vinculada.
        abiertas = Q(estado__in=['Ingresada', 'En proceso'])
        if self.instance.atencion_id:
            abiertas |= Q(pk=self.instance.atencion_id)
        self.fields['atencion'].queryset = self.fields['atencion'].queryset.filter(abiertas).order_by('-created_at')
        self.fields['atencion'].label_from_instance = lambda a: f'{a.folio} · {a.solicitante_nombre}'
        self.fields['organizacion'].queryset = self.fields['organizacion'].queryset.order_by('nombre')
        for campo in ('atencion', 'organizacion'):
            self.fields[campo].widget.attrs['data-buscable'] = ''


class ActividadSGRForm(RelacionesForm):
    class Meta:
        model = ActividadSGR
        fields = ['item', 'cargo', 'fecha', 'descripcion', 'solicitante_nombre', 'solicitante_telefono',
                  'solicitante_delegado', 'es_accion', 'felicitacion', 'respaldo_formal']
        widgets = {'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.responsable = self.user
        self.fields['solicitante_telefono'].help_text = 'Sin nombre y teléfono del usuario, la actividad no suma puntaje.'
        if not self.user.has_perm('gestion.validar_delegado'):
            self.fields.pop('respaldo_formal')
        else:
            self.fields['responsable'] = forms.ModelChoiceField(label='Funcionario responsable',
                queryset=cuentas_ambito(self.rel_org, todas=self.rel_global), initial=self.user.pk,
                widget=forms.Select(attrs={'class': 'form-select', 'data-actividad-responsable': ''}))
            self.fields['responsable'].label_from_instance = nombre_cuenta
            self.order_fields(['delegacion', 'responsable'])
        # RF-003: al conocer el cargo se cargan únicamente sus ítems de medición vigentes.
        self.responsable_actual = self.resolver_responsable()
        perfil = getattr(self.responsable_actual, 'perfil', None)
        self.cargo_asignado = getattr(perfil, 'cargo_sgr', '') or ''
        cargo = self.cargo_asignado or str((self.data if self.is_bound else self.initial).get('cargo') or '')
        cargo = cargo if cargo in dict(CARGOS) else ''
        campo_cargo = self.fields['cargo']
        campo_cargo.widget.attrs['data-actividad-cargo'] = ''
        if self.cargo_asignado:
            campo_cargo.disabled = True
            campo_cargo.initial = self.cargo_asignado
            campo_cargo.help_text = 'Cargo municipal asignado al funcionario en Usuarios.'
        else:
            campo_cargo.initial = cargo or None
            campo_cargo.help_text = 'El funcionario no tiene cargo asignado: elige el cargo para ver sus ítems.'
        items = self.relaciones(ItemMeta).filter(estado='Activo', indicador='cantidad')
        filtro = Q(cargo_sgr='') | Q(cargo_sgr=cargo) if cargo else Q(cargo_sgr='')
        self.fields['item'].queryset = items.filter(filtro).order_by('nombre')
        self.fields['item'].widget.attrs['data-buscable'] = ''
        self.cargo_efectivo = cargo
        hoy = timezone.localdate()
        self.fields['fecha'].initial = hoy
        self.fields['fecha'].widget.attrs.update({'min': primera_fecha_admisible(hoy).isoformat(), 'max': hoy.isoformat()})
        self.fields['fecha'].help_text = (f'Puedes registrar desde el {primera_fecha_admisible(hoy):%d/%m/%Y} hasta hoy: '
                                          'la semana se cierra el lunes siguiente.')

    def resolver_responsable(self):
        campo = self.fields.get('responsable')
        if campo is None:
            return self.user
        valor = (self.data if self.is_bound else self.initial).get('responsable')
        if valor is not None and str(valor).isdigit():
            elegido = campo.queryset.filter(pk=int(valor)).select_related('perfil').first()
            if elegido:
                return elegido
        return self.user if campo.queryset.filter(pk=self.user.pk).exists() or not self.is_bound else None

    def clean(self):
        data = super().clean()
        if data.get('responsable'):
            self.instance.responsable = data['responsable']
        perfil = getattr(self.instance.responsable, 'perfil', None) if self.instance.responsable_id else None
        if perfil and perfil.cargo_sgr:
            data['cargo'] = perfil.cargo_sgr
        item = data.get('item')
        if item and item.cargo_sgr and data.get('cargo') and item.cargo_sgr != data['cargo']:
            self.add_error('item', 'El ítem no corresponde al cargo del funcionario.')
        return data

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        validar_fecha(fecha)
        return fecha


class AusenciaSGRForm(RelacionesForm):
    class Meta:
        model = AusenciaSGR
        fields = ['responsable', 'desde', 'hasta', 'motivo']
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}) for key in ['desde', 'hasta']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.registrado_por = self.user
        self.fields['responsable'].queryset = cuentas_ambito(self.rel_org, todas=self.rel_global)


class ReclamoSGRForm(RelacionesForm):
    class Meta:
        model = ReclamoSGR
        fields = ['responsable', 'fecha', 'usuario_nombre', 'contacto', 'ubicacion', 'situacion', 'medio_escrito', 'informado_a']
        widgets = {'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.registrado_por = self.user
        self.fields['responsable'].queryset = cuentas_ambito(self.rel_org, todas=self.rel_global)
        self.fields['medio_escrito'].help_text = 'Solo se aceptan reclamos escritos por mala atención del funcionario.'


class PeriodoSGRForm(forms.Form):
    anio = forms.IntegerField(label='Año', min_value=2020, max_value=2100)
    trimestre = forms.TypedChoiceField(label='Trimestre', choices=[(n, n) for n in range(1, 5)], coerce=int)
    responsable = forms.ModelChoiceField(label='Funcionario', queryset=get_user_model().objects.none())

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = get_user_model().objects.filter(
            perfil__delegacion_id__in=scoped(user, ItemMeta).values('delegacion_id'), is_active=True).exclude(groups__name='Cliente')
        self.fields['responsable'].label_from_instance = lambda account: account.get_full_name() or account.username
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
        self.fields['responsable'].widget.attrs['aria-describedby'] = 'id_responsable_errors'


class MetaSGRForm(forms.ModelForm):
    cargo_sgr = forms.ChoiceField(label='Cargo municipal', required=False, choices=[('', 'Común a todos los cargos')] + CARGOS)
    class Meta:
        model = ItemMeta
        fields = ['indicador', 'meta_cantidad', 'ponderador', 'cargo_sgr']
