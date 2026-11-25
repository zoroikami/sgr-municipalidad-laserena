from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .access import scoped
from .delegation import has_global_scope
from .forms import ScopedModelForm
from .integrado import primera_fecha_admisible, validar_fecha
from .integrado import CARGOS, SUBFAMILIAS, TERRITORIOS_TUBO
from .models import ActividadSGR, AusenciaSGR, CasoSocial, Delegacion, MetaFuncionario, GestionTubo, Organizacion, Atencion, ItemMeta, ReclamoSGR


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
        labels = {'fecha_constitucion': 'Fecha de constitución', 'fecha_inscripcion': 'Fecha de inscripción',
                  'registro_directiva': 'Registro de directiva', 'descripcion': 'Descripción'}
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
                   for key in ['fecha_constitucion', 'fecha_inscripcion']}
        help_texts = {
            'nombre': 'Escribe el nombre oficial de la organización.',
            'familia': 'Selecciona si la organización es territorial o funcional según su objetivo.',
            'domicilio': 'Indica la calle, el número y el sector de su sede o domicilio.',
            'socios_activos': 'Indica la cantidad actual de integrantes activos, sin decimales.',
            'fecha_constitucion': 'Selecciona el día, mes y año en que se constituyó la organización.',
            'registro_pj': 'Escribe el número de registro de su personalidad jurídica.',
            'fecha_inscripcion': 'Selecciona el día, mes y año de su inscripción en el registro.',
            'registro_directiva': 'Escribe el número o referencia del registro de la directiva vigente.',
            'verificada': 'Marca la casilla si ya comprobaste los antecedentes de la organización.',
            'descripcion': 'Describe el objetivo y las actividades principales de la organización.',
            'estado': 'Selecciona Activo para poder vincularla a nuevas gestiones.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opciones = [('', 'Selecciona la subfamilia')] + [
            (familia.capitalize(), [(nombre, nombre) for nombre in nombres]) for familia, nombres in SUBFAMILIAS.items()]
        actual = self.instance.subfamilia
        if actual and all(actual not in nombres for nombres in SUBFAMILIAS.values()):
            opciones.append(('Registrada', [(actual, actual)]))
        self.fields['subfamilia'].choices = opciones
        self.fields['subfamilia'].widget.attrs['class'] = 'form-select'
        self.fields['subfamilia'].help_text = 'Elige la clasificación del nuevo requerimiento según su objetivo y la familia elegida.'

    def clean(self):
        data = super().clean()
        familia, subfamilia = data.get('familia'), data.get('subfamilia')
        if familia and subfamilia and subfamilia in sum(SUBFAMILIAS.values(), []) and subfamilia not in SUBFAMILIAS[familia]:
            self.add_error('subfamilia', 'La subfamilia no corresponde a la familia elegida.')
        return data


class TextoConSugerencias(forms.TextInput):
    """Campo libre con sugerencias nativas (datalist): no restringe valores ya registrados."""
    def __init__(self, *args, sugerencias=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.sugerencias = list(sugerencias)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.sugerencias:
            context['widget']['attrs']['list'] = f"{context['widget']['attrs'].get('id', name)}_sugerencias"
        return context

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        if not self.sugerencias:
            return html
        lista = f"{(attrs or {}).get('id', name)}_sugerencias"
        opciones = format_html_join('', '<option value="{}"></option>', ((s,) for s in self.sugerencias))
        return format_html('{}<datalist id="{}">{}</datalist>', html, lista, opciones)


class GestionTuboForm(RelacionesForm):
    class Meta:
        model = GestionTubo
        fields = ['nombre', 'descripcion', 'fecha_solicitud', 'origen', 'solicitante', 'solicitante_rut',
                  'solicitante_telefono', 'territorio',
                  'responsable', 'fecha_compromiso', 'apoyo', 'observaciones', 'atencion', 'organizacion']
        labels = {'nombre': 'Actividad, solicitud o problema', 'descripcion': 'Descripción', 'fecha_solicitud': 'Fecha de solicitud',
                  'fecha_compromiso': 'Fecha de compromiso', 'atencion': 'Atención vinculada', 'organizacion': 'Organización'}
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
                   for key in ['fecha_solicitud', 'fecha_compromiso']}
        help_texts = {
            'nombre': 'Resume el asunto de la solicitud en un título breve.',
            'descripcion': 'Explica qué se solicita y los antecedentes para gestionar una solución.',
            'fecha_solicitud': 'Selecciona cuándo recibiste la solicitud; no puede ser una fecha futura.',
            'origen': 'Indica si la solicitud proviene del municipio (interno) o de la comunidad (externo).',
            'solicitante': 'Escribe los nombres y apellidos de quien solicita la gestión.',
            'territorio': 'Indica la localidad o el sector de la solicitud; puedes usar una sugerencia.',
            'responsable': 'Selecciona al funcionario que se hará cargo del seguimiento.',
            'fecha_compromiso': 'Selecciona el plazo acordado, igual o posterior a la fecha de solicitud.',
            'apoyo': 'Indica el área municipal o la persona que colaborará en la solución.',
            'observaciones': 'Agrega antecedentes o avances que ayuden al seguimiento.',
            'atencion': 'Vincula la atención abierta que originó esta gestión, si corresponde.',
            'organizacion': 'Vincula la organización relacionada con la solicitud, si corresponde.',
        }

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
        self.fields['territorio'].widget = TextoConSugerencias(attrs=self.fields['territorio'].widget.attrs,
                                                               sugerencias=self.territorios())
        # Nuevo requerimiento, puntos 1 y 2: identificar al solicitante y exigir su nombre y teléfono.
        self.fields['solicitante'].label = 'Nombre del solicitante'
        rut = self.fields['solicitante_rut']
        rut.help_text = ('Opcional. Sin puntos y con guion (ej.: 12345678-5). Si corresponde a un funcionario '
                         'municipal se indicará su cargo; si es el delegado, la gestión cuenta como otra gestión.')
        rut.widget.attrs.update({'placeholder': '12345678-5', 'spellcheck': 'false', 'autocomplete': 'off',
                                 'data-rut-funcionario': reverse('gestion:rut_funcionario')})
        telefono = self.fields['solicitante_telefono']
        telefono.widget.attrs.update({'type': 'tel', 'autocomplete': 'off', 'placeholder': '+56 9 1234 5678'})
        if not self.instance.pk:
            telefono.required = True
        telefono.help_text = 'Indica un número, por ejemplo +56 9 1234 5678. Sin nombre y teléfono del usuario no hay puntaje.'
        # Nuevo requerimiento, punto 4: las gestiones de la semana se ingresan hasta el lunes siguiente.
        if not self.instance.pk:
            hoy = timezone.localdate()
            primera = primera_fecha_admisible(hoy)
            self.fields['fecha_solicitud'].widget.attrs.update({'min': primera.isoformat(), 'max': hoy.isoformat()})
            self.fields['fecha_solicitud'].help_text = (f'Puedes ingresar solicitudes desde el {primera:%d/%m/%Y} hasta hoy: '
                                                        'la semana se cierra el lunes siguiente.')

    def clean_fecha_solicitud(self):
        fecha = self.cleaned_data.get('fecha_solicitud')
        if fecha and not self.instance.pk:
            try:
                validar_fecha(fecha)
            except ValidationError as error:
                raise forms.ValidationError(error.messages) from error
        return fecha

    def territorios(self):
        if not self.rel_org:
            return []
        from .management.commands.importar_organizaciones import canon
        delegacion = Delegacion.objects.filter(pk=self.rel_org).values_list('nombre', flat=True).first() or ''
        base = TERRITORIOS_TUBO.get(canon(delegacion), [])
        usados = (GestionTubo.objects.filter(delegacion_id=self.rel_org).exclude(territorio='')
                  .values_list('territorio', flat=True).distinct().order_by('territorio')[:40])
        vistos, resultado = set(), []
        for territorio in [*base, *usados]:
            clave = ' '.join(territorio.split()).casefold()
            if clave not in vistos:
                vistos.add(clave)
                resultado.append(' '.join(territorio.split()))
        return resultado

    def clean_solicitante_rut(self):
        from cuentas.rut import RutError, normalize_rut
        valor = self.cleaned_data.get('solicitante_rut', '').strip()
        if not valor:
            return ''
        try:
            return normalize_rut(valor)
        except RutError as error:
            raise forms.ValidationError(str(error)) from error


class ActividadSGRForm(RelacionesForm):
    class Meta:
        model = ActividadSGR
        fields = ['item', 'cargo', 'fecha', 'caso', 'descripcion', 'accion', 'derivado_a', 'tipo_gestion', 'solicitante_nombre',
                  'solicitante_telefono', 'solicitante_delegado', 'es_accion', 'imagen_verificacion', 'felicitacion',
                  'respaldo_formal']
        labels = {'item': 'Ítem', 'descripcion': 'Descripción', 'solicitante_nombre': 'Nombre del solicitante',
                  'solicitante_telefono': 'Teléfono del solicitante'}
        widgets = {'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}
        help_texts = {
            'item': 'Selecciona el ítem de la matriz que corresponde a la actividad y al cargo.',
            'descripcion': 'Describe la acción realizada y el resultado obtenido.',
            'accion': 'Opcional. Resume en pocas palabras qué hiciste, por ejemplo «Orientación telefónica» o «Gestionar poda».',
            'derivado_a': 'Opcional. Indica la persona, oficina o servicio al que derivaste el caso; déjalo vacío si no hubo derivación.',
            'tipo_gestion': 'Solo para el coordinador DISERCO: elige el tipo de gestión de la hoja COOR DISERCO.',
            'solicitante_nombre': 'Escribe los nombres y apellidos del usuario atendido para acreditar la actividad.',
            'solicitante_delegado': 'Marca si la solicitud proviene del delegado; cuenta como otra gestión.',
            'es_accion': 'Marca si ejecutaste la acción; una coordinación por sí sola no suma puntaje.',
            'felicitacion': 'Marca si registras una felicitación; requiere información del delegado para sumar.',
            'respaldo_formal': 'Indica la referencia del documento que respalda la felicitación informada al delegado.',
            'caso': 'Opcional. Si es la 1.ª, 2.ª o 3.ª gestión de un caso del gestor social, elige el caso abierto.',
            'imagen_verificacion': 'Marca si guardaste una foto de respaldo; nómbrala con el código que muestra la actividad.',
        }

    ingresar_tubo = forms.BooleanField(label='Ingresar al tubo de trabajo', required=False,
        help_text='Marca si la solicitud queda pendiente de solución: se crea la gestión en el tubo con estos datos.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.responsable = self.user
        self.fields['caso'].queryset = self.relaciones(CasoSocial).filter(estado='Abierto').order_by('-fecha_ingreso')
        self.fields['caso'].label_from_instance = lambda caso: f'{caso.codigo} · {caso.nombre}'
        self.fields['solicitante_telefono'].help_text = 'Indica un número, por ejemplo +56 9 1234 5678. Sin nombre y teléfono del usuario no hay puntaje.'
        if not self.user.has_perm('gestion.validar_delegado'):
            self.fields.pop('respaldo_formal')
        else:
            self.fields['responsable'] = forms.ModelChoiceField(label='Funcionario responsable',
                queryset=cuentas_ambito(self.rel_org, todas=self.rel_global), initial=self.user.pk,
                help_text='Selecciona al funcionario que realizó la actividad para cargar su cargo e ítems.',
                widget=forms.Select(attrs={'class': 'form-select', 'data-actividad-responsable': '',
                                           'aria-describedby': 'id_responsable_help id_responsable_errors'}))
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
        self.fields['tipo_gestion'].widget.attrs['data-solo-cargo'] = 'servicios'
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

    def clean_ingresar_tubo(self):
        # Punto 2: el tubo exige nombre y teléfono del usuario; se valida antes de guardar la actividad.
        ingresar = self.cleaned_data.get('ingresar_tubo')
        if ingresar and not (self.data.get('solicitante_nombre', '').strip() and self.data.get('solicitante_telefono', '').strip()):
            raise forms.ValidationError('Para ingresar al tubo escribe el nombre y el teléfono del usuario.')
        return ingresar


class AusenciaSGRForm(RelacionesForm):
    class Meta:
        model = AusenciaSGR
        fields = ['responsable', 'desde', 'hasta', 'motivo']
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}) for key in ['desde', 'hasta']}
        help_texts = {
            'responsable': 'Selecciona al funcionario que estuvo o estará ausente.',
            'desde': 'Selecciona el primer día de la ausencia, incluido.',
            'hasta': 'Selecciona el último día de la ausencia, incluido; no puede ser anterior al inicio.',
            'motivo': 'Selecciona la causa de la ausencia que ajustará los días hábiles de su meta.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.registrado_por = self.user
        self.fields['responsable'].queryset = cuentas_ambito(self.rel_org, todas=self.rel_global)


class ReclamoSGRForm(RelacionesForm):
    class Meta:
        model = ReclamoSGR
        fields = ['responsable', 'fecha', 'usuario_nombre', 'contacto', 'ubicacion', 'situacion', 'medio_escrito', 'informado_a']
        widgets = {'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}
        help_texts = {
            'responsable': 'Selecciona al funcionario al que se refiere el reclamo.',
            'fecha': 'Selecciona el día, mes y año del reclamo.',
            'usuario_nombre': 'Escribe los nombres y apellidos de quien presenta el reclamo.',
            'contacto': 'Indica el teléfono o correo de quien reclama para poder contactarlo.',
            'ubicacion': 'Indica el lugar donde ocurrió la situación reclamada.',
            'situacion': 'Describe los hechos que motivan el reclamo por mala atención.',
            'informado_a': 'Indica a qué persona o área se informó este reclamo.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.registrado_por = self.user
        self.fields['responsable'].queryset = cuentas_ambito(self.rel_org, todas=self.rel_global)
        self.fields['medio_escrito'].help_text = 'Selecciona el medio recibido: solo se aceptan reclamos escritos por mala atención del funcionario.'


class PeriodoSGRForm(forms.Form):
    anio = forms.IntegerField(label='Año', min_value=2020, max_value=2100)
    trimestre = forms.TypedChoiceField(label='Trimestre', choices=[(n, n) for n in range(1, 5)], coerce=int,
        help_text='Elige 1: ene-mar, 2: abr-jun, 3: jul-sep o 4: oct-dic.')
    responsable = forms.ModelChoiceField(label='Funcionario', queryset=get_user_model().objects.none())

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = get_user_model().objects.filter(
            perfil__delegacion_id__in=scoped(user, ItemMeta).values('delegacion_id'), is_active=True).exclude(groups__name='Cliente')
        self.fields['responsable'].label_from_instance = lambda account: account.get_full_name() or account.username
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
        self.fields['trimestre'].widget.attrs['aria-describedby'] = 'id_trimestre_help id_trimestre_errors'
        self.fields['responsable'].widget.attrs['aria-describedby'] = 'id_responsable_errors'


class MetaFuncionarioForm(forms.ModelForm):
    """Ajuste individual: las hojas G SOC2, G SOC3, G SOC5 y T OC 3 usan metas o ponderadores propios."""
    quitar = forms.BooleanField(label='Volver a la meta del cargo', required=False,
        help_text='Marca para eliminar el ajuste y usar la meta y el ponderador comunes del cargo.')

    class Meta:
        model = MetaFuncionario
        fields = ['meta_cantidad', 'ponderador']
        help_texts = {
            'meta_cantidad': 'Indica la meta trimestral de este funcionario para el ítem (por ejemplo, 15 beneficios).',
            'ponderador': 'Indica el peso del ítem en el resultado de este funcionario, entre 0 y 100 (por ejemplo, 25).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control' if not isinstance(field.widget, forms.CheckboxInput) else ''


class MetaSGRForm(forms.ModelForm):
    cargo_sgr = forms.ChoiceField(label='Cargo municipal', required=False, choices=[('', 'Común a todos los cargos')] + CARGOS,
        help_text='Selecciona el cargo al que aplica el ítem o déjalo común a todos los cargos.')
    class Meta:
        model = ItemMeta
        fields = ['indicador', 'meta_cantidad', 'ponderador', 'cargo_sgr']
        help_texts = {
            'indicador': 'Elige si medirás cantidad de acciones o porcentaje de gestiones realizadas del tubo.',
            'meta_cantidad': 'Indica la meta trimestral: cantidad de acciones o porcentaje realizado del tubo (ej.: 80).',
            'ponderador': 'Indica el peso del ítem en el resultado, entre 0 y 100; por ejemplo 25 para 25%.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['aria-describedby'] = f'id_{name}_help id_{name}_errors'


class CasoSocialForm(RelacionesForm):
    unique_name = False  # Una persona puede tener más de un caso social.
    ingresar_tubo = forms.BooleanField(label='Ingresar al tubo de trabajo', required=False,
        help_text='Marca para crear también una gestión de seguimiento vinculada a este caso.')
    devoluciones = forms.IntegerField(label='Devoluciones del informe', min_value=0, max_value=3, initial=0,
        help_text='Indica cuántas veces se devolvió el informe para corregirlo: de 0 a 3; no cambia el puntaje.')

    class Meta:
        from .models import CasoSocial
        model = CasoSocial
        fields = ['nombre', 'usuario_rut', 'usuario_telefono', 'responsable', 'fecha_ingreso',
                  'tipo', 'subatencion', 'descripcion', 'requiere_visita', 'fecha_programada_visita',
                  'devoluciones', 'estado', 'ingresar_tubo']
        labels = {'nombre': 'Nombre del usuario', 'descripcion': 'Descripción del caso'}
        widgets = {key: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
                   for key in ['fecha_ingreso', 'fecha_programada_visita']}
        help_texts = {
            'nombre': 'Escribe los nombres y apellidos de la persona atendida.',
            'usuario_rut': 'Indica su RUT sin puntos y con guion, por ejemplo 12345678-5; es opcional.',
            'usuario_telefono': 'Indica un teléfono de contacto, por ejemplo +56 9 1234 5678.',
            'responsable': 'Selecciona al funcionario de la delegación que se hará cargo del caso.',
            'fecha_ingreso': 'Selecciona el día en que ingresó el caso; no puede ser una fecha futura.',
            'tipo': 'Selecciona la categoría de atención que corresponde al caso.',
            'subatencion': 'Selecciona el trámite de la categoría elegida; verás su categoría junto al nombre.',
            'descripcion': 'Describe la situación y los antecedentes necesarios para atender el caso.',
            'requiere_visita': 'Marca si el caso necesita una visita en terreno.',
            'fecha_programada_visita': 'Selecciona la fecha acordada para la visita, igual o posterior al ingreso.',
            'estado': 'Selecciona Abierto mientras el caso siga en atención o Cerrado cuando concluya.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creating = not self.instance.pk
        self.fields['responsable'].queryset = cuentas_ambito(self.rel_org)
        self.fields['responsable'].label_from_instance = nombre_cuenta
        if self.creating:
            if self.fields['responsable'].queryset.filter(pk=self.user.pk).exists():
                self.fields['responsable'].initial = self.user.pk
        else:
            self.fields.pop('ingresar_tubo')
        from .models import TipoAtencion, SubAtencion
        self.fields['tipo'].queryset = self.relaciones(TipoAtencion).filter(estado='Activo')
        self.fields['subatencion'].queryset = self.relaciones(SubAtencion).filter(
            estado='Activo', tipo__estado='Activo', tipo__deleted_at__isnull=True).select_related('tipo')
        self.fields['subatencion'].label_from_instance = lambda sub: f'{sub.tipo.nombre}: {sub.nombre}'
        self.fields['usuario_rut'].widget.attrs.update({
            'placeholder': '12345678-5', 'spellcheck': 'false', 'autocomplete': 'off',
            'data-rut-funcionario': reverse('gestion:rut_funcionario'),
        })
        self.fields['usuario_telefono'].required = True
        self.fields['usuario_telefono'].widget.attrs.update({'type': 'tel', 'placeholder': '+56 9 1234 5678'})

    def clean_usuario_rut(self):
        from cuentas.rut import RutError, normalize_rut
        value = self.cleaned_data.get('usuario_rut', '').strip()
        if not value:
            return ''
        try:
            return normalize_rut(value)
        except RutError as error:
            raise forms.ValidationError(str(error)) from error

    def clean(self):
        data = super().clean()
        if data.get('subatencion') and not data.get('tipo'):
            self.add_error('tipo', 'Selecciona el tipo de atención de esta subatención.')
        if data.get('ingresar_tubo') and not self.user.has_perm('gestion.add_gestiontubo'):
            self.add_error('ingresar_tubo', 'Tu cuenta no tiene permiso para ingresar gestiones al tubo.')
        return data

    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)
        from django.db import transaction
        from .ingreso_tubo import ingresar_al_tubo
        with transaction.atomic():
            caso = super().save()
            if self.creating and self.cleaned_data.get('ingresar_tubo') and not caso.gestion_tubo_id:
                tema = ' / '.join(str(value.nombre) for value in (caso.tipo, caso.subatencion) if value)
                caso.gestion_tubo = ingresar_al_tubo(
                    delegacion=caso.delegacion, responsable=caso.responsable,
                    descripcion=caso.descripcion or f'Caso social: {tema or caso.nombre}',
                    solicitante=caso.nombre, telefono=caso.usuario_telefono,
                    fecha=caso.fecha_ingreso, sufijo=caso.codigo, rut=caso.usuario_rut,
                )
                caso.save(update_fields=['gestion_tubo', 'updated_at'])
            return caso
