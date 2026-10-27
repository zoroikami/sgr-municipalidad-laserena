import json
import re
import secrets
import smtplib
import logging
from datetime import timedelta
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.db.models.deletion import ProtectedError
from django.forms.models import model_to_dict
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.staticfiles import finders
from profile_service import ProfileError, validate_photo
from rut import RutError, normalize_rut
from .models import Delegacion, Rol, Usuario, ItemMeta, TipoAtencion, SubAtencion, Atencion, Recuperacion, Secuencia

RESOURCES = {
    'delegaciones': (Delegacion, 'DEL', 2), 'roles': (Rol, 'ROL', 2),
    'usuarios': (Usuario, '', 0), 'items-metas': (ItemMeta, 'IT', 3),
    'tipos-atencion': (TipoAtencion, 'TA', 3), 'sub-atenciones': (SubAtencion, 'SA', 3),
    'atenciones': (Atencion, 'ATN', 4),
}

def error(message, status=400):
    return JsonResponse({'success': False, 'message': message}, status=status)

def api(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            request.data = json.loads(request.body or b'{}') if request.method in ('POST', 'PUT', 'PATCH') else {}
            if not isinstance(request.data, dict):
                return error('Se requiere un objeto JSON.')
            return view(request, *args, **kwargs)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return error('JSON inválido.')
        except ProtectedError:
            return error('No se puede eliminar: existen registros asociados.')
        except IntegrityError:
            return error('El código, RUT o correo ya está registrado, o la referencia es inválida.', 409)
        except ValidationError as exc:
            return error(' '.join(exc.messages))
        except ProfileError as exc:
            return error(str(exc), exc.status)
        except RutError as exc:
            return error(str(exc))
        except (ValueError, TypeError):
            return error('Los datos enviados no son válidos.')
    return wrapped

def authenticated(request):
    return request.user.is_authenticated and request.user.is_active and request.user.estado == 'Activo'

def communal(user):
    return user.is_superuser or user.rol_id in ('ROL01', 'ROL02') or (user.rol and user.rol.permisos == 'total')

def serialize(obj):
    if isinstance(obj, Usuario):
        return {'id':obj.id, 'rut':obj.rut, 'nombre':obj.nombre or obj.username, 'email':obj.email,
                'rol_codigo':'ROL01' if obj.is_superuser else obj.rol_id,
                'rol_nombre':obj.rol.nombre if obj.rol else ('Superadministrador' if obj.is_superuser else ''),
                'alcance':obj.rol.alcance if obj.rol else '', 'delegacion_codigo':obj.delegacion_id,
                'delegacion_nombre':obj.delegacion.nombre if obj.delegacion else '', 'estado':obj.estado,
                'foto_perfil':obj.foto_perfil}
    result = model_to_dict(obj)
    for field in ('delegacion', 'tipo', 'subtipo'):
        if hasattr(obj, field):
            related = getattr(obj, field)
            result.pop(field, None)
            result[field + '_codigo'] = related.codigo
            result[field + '_nombre'] = related.nombre
    if isinstance(obj, Atencion):
        result['fecha_registro'] = timezone.localtime(obj.fecha_registro).strftime('%Y-%m-%d %H:%M:%S')
    return result

@ensure_csrf_cookie
def index(request):
    return render(request, 'index.html')

@ensure_csrf_cookie
def health(request):
    return JsonResponse({'status':'OK', 'service':'SGR La Serena', 'backend':'Django', 'timestamp':timezone.now().isoformat()})

def asset(request, asset_path):
    if asset_path.startswith(('css/', 'js/')):
        asset_path = 'evaluacion2/' + asset_path
    suffix = Path(asset_path).suffix.lower()
    if suffix not in {'.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.ico', '.woff', '.woff2', '.ttf'}:
        raise Http404
    root = settings.STATIC_ROOT.resolve()
    candidate = (root / asset_path).resolve()
    filename = candidate if candidate.is_relative_to(root) and candidate.is_file() else finders.find(asset_path)
    if not filename:
        raise Http404
    return FileResponse(open(filename, 'rb'))

@api
def profile(request):
    if not authenticated(request):
        return error('Debe iniciar sesión.', 401)
    if request.method == 'DELETE':
        logout(request)
        return JsonResponse({'success':True})
    if request.method == 'PUT':
        if set(request.data) != {'photo'}:
            return error('Envíe únicamente la foto del perfil.')
        request.user.foto_perfil = validate_photo(request.data['photo'])
        request.user.save(update_fields=['foto_perfil'])
    elif request.method != 'GET':
        return error('Método no permitido.', 405)
    return JsonResponse({'success':True, 'user':serialize(request.user)})

@api
def auth(request, action):
    if request.method != 'POST':
        return error('Método no permitido.', 405)
    body = request.data
    if action == 'login':
        identifier = str(body.get('usuario', '')).strip()
        try:
            rut = normalize_rut(identifier)
        except RutError:
            rut = identifier.replace('.', '').upper()
        user = Usuario.objects.filter(Q(email__iexact=identifier) | Q(username__iexact=identifier) | Q(nombre__iexact=identifier) | Q(rut__iexact=rut)).first()
        if not user or not user.check_password(body.get('password', '')):
            return error('Credenciales inválidas.', 401)
        if not user.is_active or user.estado != 'Activo':
            return error('Cuenta inactiva o suspendida.', 403)
        login(request, user)
        return JsonResponse({'success':True, 'user':serialize(user)})
    email = str(body.get('email', '')).strip().lower()
    if not email:
        return error('El correo es obligatorio.')
    if action == 'recuperar-codigo':
        user = Usuario.objects.filter(email__iexact=email, is_active=True, estado='Activo').first()
        if user:
            recent = Recuperacion.objects.filter(usuario=user, expiracion__gt=timezone.now() + timedelta(minutes=9)).exists()
            if not recent:
                code = f'{secrets.randbelow(1000000):06d}'
                with transaction.atomic():
                    Recuperacion.objects.filter(usuario=user, usado=False).update(usado=True)
                    Recuperacion.objects.create(usuario=user, codigo_hash=make_password(code), expiracion=timezone.now()+timedelta(minutes=10))
                try:
                    send_mail('Recuperación de contraseña SGR', f'Su código de verificación es: {code}', settings.DEFAULT_FROM_EMAIL, [email])
                except (OSError, smtplib.SMTPException):
                    logging.getLogger(__name__).exception('No se pudo enviar el correo de recuperación')
        return JsonResponse({'success':True, 'message':'Si la cuenta existe, recibirás un código de 6 dígitos.', 'expires_in_minutes':10})
    if action == 'validar-codigo':
        with transaction.atomic():
            rec = Recuperacion.objects.select_for_update().filter(usuario__email__iexact=email, usado=False).order_by('-id').first()
            if not rec or rec.expiracion <= timezone.now():
                return error('Código vencido o solicitud inexistente.')
            if rec.intentos >= 3:
                return error('Se superó el límite de 3 intentos. Solicite otro código.', 429)
            if not check_password(str(body.get('codigo', '')), rec.codigo_hash):
                rec.intentos += 1
                rec.save(update_fields=['intentos'])
                return error(f'Código incorrecto. Le quedan {3-rec.intentos} intentos.')
            rec.verificado = True
            rec.save(update_fields=['verificado'])
            request.session['recovery_id'] = rec.id
        return JsonResponse({'success':True})
    if action == 'cambiar-password':
        with transaction.atomic():
            rec = Recuperacion.objects.select_for_update().filter(pk=request.session.get('recovery_id'), usuario__email__iexact=email, verificado=True, usado=False, expiracion__gt=timezone.now()).first()
            if not rec:
                return error('Debe verificar el código antes de cambiar la contraseña.', 403)
            password = body.get('password', '')
            validate_password(password, rec.usuario)
            if not (re.search('[A-Z]', password) and re.search('[0-9]', password) and re.search('[^A-Za-z0-9]', password)):
                return error('Use mayúscula, número y símbolo.')
            rec.usuario.set_password(password)
            rec.usuario.save(update_fields=['password'])
            rec.usado = True
            rec.save(update_fields=['usado'])
            request.session.pop('recovery_id', None)
        return JsonResponse({'success':True})
    return error('Endpoint no encontrado.', 404)

def next_code(resource, prefix, width):
    seq, _ = Secuencia.objects.get_or_create(nombre=resource)
    Secuencia.objects.filter(pk=seq.pk).update(valor=F('valor') + 1)
    seq.refresh_from_db()
    return f'{prefix}{seq.valor:0{width}d}'

def can_write(user, resource):
    if user.is_superuser or (user.rol and user.rol.permisos == 'total'):
        return True
    allowed = {
        'ROL01':set(RESOURCES), 'ROL02':{'delegaciones', 'items-metas', 'tipos-atencion', 'sub-atenciones', 'atenciones'},
        'ROL03':{'usuarios', 'items-metas', 'atenciones'}, 'ROL04':{'atenciones'},
    }
    return resource in allowed.get(user.rol_id, set())

@api
def collection(request, resource, pk=None):
    if not authenticated(request):
        return error('Debe iniciar sesión.', 401)
    if resource == 'stats' and request.method == 'GET':
        return JsonResponse({key.replace('-', '_'):scoped(request.user, model).count() for key,(model,_,_) in RESOURCES.items()})
    if resource not in RESOURCES:
        return error('Recurso no encontrado.', 404)
    model, prefix, width = RESOURCES[resource]
    records = scoped(request.user, model)
    if request.method == 'GET':
        if pk:
            obj = records.filter(pk=pk).first()
            return JsonResponse(serialize(obj)) if obj else error('Registro no encontrado.', 404)
        delegation = request.GET.get('delegacion')
        if delegation and delegation != 'ALL' and model in (Usuario, Atencion):
            records = records.filter(delegacion_id=delegation)
        if model == SubAtencion and request.GET.get('tipo'):
            records = records.filter(tipo_id=request.GET['tipo'])
        return JsonResponse([serialize(obj) for obj in records], safe=False)
    if request.method not in ('POST', 'PUT', 'DELETE') or (request.method == 'POST' and pk) or (request.method != 'POST' and not pk):
        return error('Método no permitido.', 405)
    if not can_write(request.user, resource):
        return error('No tiene permisos para realizar esta operación.', 403)
    with transaction.atomic():
        obj = records.filter(pk=pk).first() if pk else model()
        if obj is None:
            return error('Registro no encontrado.', 404)
        if request.method == 'DELETE':
            if model == Atencion:
                return error('No se permite eliminar atenciones.', 405)
            if model == Usuario and obj.pk == request.user.pk:
                return error('No puede eliminar su propia cuenta.')
            obj.delete()
            return JsonResponse({'success':True})
        if model == Atencion and pk:
            return error('No se permite editar atenciones.', 405)
        body = request.data
        excluded = {'id', 'codigo', 'folio', 'responsable_nombre', 'fecha_registro', 'creado_en'}
        if model == Usuario:
            fields = {'rut', 'nombre', 'email', 'estado'}
        else:
            fields = {field.name for field in model._meta.fields if not field.is_relation} - excluded
        if model == ItemMeta:
            fields.discard('meta_cantidad')
        for field in fields:
            if field in body:
                value = body[field]
                setattr(obj, field, value.strip() if isinstance(value, str) else value)
        for field in ('delegacion', 'rol', 'tipo', 'subtipo'):
            if hasattr(model, field) and field + '_codigo' in body:
                setattr(obj, field + '_id', body[field + '_codigo'])
        if model == Usuario:
            if not all((obj.rut, obj.nombre, obj.email, obj.rol_id, obj.delegacion_id)):
                return error('RUT, nombre, correo, rol y delegación son obligatorios.')
            obj.email = obj.email.lower()
            obj.rut = normalize_rut(obj.rut)
            if Usuario.objects.filter(rut=obj.rut).exclude(pk=obj.pk).exists():
                return error('El RUT ya está registrado en el sistema.', 409)
            if not pk:
                obj.username = obj.email
                obj.foto_perfil = validate_photo(body.get('foto_perfil'))
            if not communal(request.user):
                if obj.rol_id not in ('ROL04', 'ROL05'):
                    return error('Solo puede administrar operadores y consultores.', 403)
                obj.delegacion_id = request.user.delegacion_id
            if not pk or body.get('password'):
                password = body.get('password', '')
                validate_password(password, obj)
                obj.set_password(password)
        if not pk and model != Usuario:
            if model == Atencion:
                obj.solicitante_rut = normalize_rut(obj.solicitante_rut)
                year = timezone.localdate().year
                obj.folio = next_code(f'atenciones-{year}', f'ATN-{year}-', 4)
                obj.responsable_nombre = request.user.nombre or request.user.username
                if not communal(request.user):
                    obj.delegacion_id = request.user.delegacion_id
                if obj.subtipo_id and obj.tipo_id and not SubAtencion.objects.filter(codigo=obj.subtipo_id, tipo_id=obj.tipo_id).exists():
                    return error('La subatención no pertenece al tipo seleccionado.')
            else:
                supplied = str(body.get('codigo', '')).strip().upper()
                if supplied and resource not in ('delegaciones', 'items-metas'):
                    obj.codigo = supplied
                else:
                    code = next_code(resource, prefix, width)
                    while model.objects.filter(codigo=code).exists():
                        code = next_code(resource, prefix, width)
                    obj.codigo = code
        obj.full_clean(exclude=['password'] if model == Usuario else None)
        obj.save()
        result = {'success':True, 'id':obj.pk, 'message':'Registro guardado correctamente.'}
        if hasattr(obj, 'codigo'):
            result['codigo'] = obj.codigo
        if model == Atencion:
            result.update(folio=obj.folio, fecha_registro=serialize(obj)['fecha_registro'])
        return JsonResponse(result, status=201 if request.method == 'POST' else 200)

def scoped(user, model):
    records = model.objects.all().order_by('-id' if model == Atencion else 'id')
    if not communal(user) and model in (Usuario, Atencion):
        records = records.filter(delegacion_id=user.delegacion_id)
        if model == Usuario:
            records = records.filter(is_superuser=False, rol_id__in=['ROL04', 'ROL05'])
    return records
