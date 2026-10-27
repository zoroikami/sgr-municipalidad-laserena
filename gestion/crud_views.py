"""CRUD HTML protegido. La API anterior permanece disponible como compatibilidad."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import QueryDict
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from . import forms
from .models import Delegacion, Rol, Usuario, ItemMeta, TipoAtencion, SubAtencion
from .views import communal, next_code


CATALOGS = {
    'delegaciones': (Delegacion, forms.DelegacionForm, 'Delegaciones', 'delegación', 'DEL', 2),
    'roles': (Rol, forms.RolForm, 'Roles', 'rol', 'ROL', 2),
    'usuarios': (Usuario, forms.UsuarioForm, 'Usuarios', 'usuario', '', 0),
    'items-metas': (ItemMeta, forms.ItemMetaForm, 'Ítems y metas', 'ítem y meta', 'IT', 3),
    'tipos-atencion': (TipoAtencion, forms.TipoAtencionForm, 'Tipos de atención', 'tipo de atención', 'TA', 3),
    'sub-atenciones': (SubAtencion, forms.SubAtencionForm, 'Subatenciones', 'subatención', 'SA', 3),
}

class AccesoView(LoginView):
    template_name = 'gestion/login.html'
    authentication_form = forms.AccesoForm
    redirect_authenticated_user = True


class CrudAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
    slug = None
    action = 'view'
    template_name = 'gestion/list.html'
    paginate_by = None  # Se pagina una sola vez con get_page, también en Create/Update.
    allowed_page_sizes = (5, 15, 30)
    default_page_size = 15

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and (not request.user.is_active or request.user.estado != 'Activo'):
            raise PermissionDenied
        if (request.user.is_authenticated and self.model == Usuario
                and not communal(request.user) and not request.user.delegacion_id):
            raise PermissionDenied('La cuenta no tiene una delegación asignada.')
        return super().dispatch(request, *args, **kwargs)

    def get_permission_required(self):
        name = self.model._meta.model_name
        return (f'gestion.view_{name}', f'gestion.{self.action}_{name}')

    def base_queryset(self):
        queryset = self.model.objects.all().order_by('id')
        if self.model == Usuario:
            queryset = queryset.select_related('rol', 'delegacion')
            if not communal(self.request.user):
                queryset = queryset.filter(
                    delegacion_id=self.request.user.delegacion_id,
                    is_superuser=False, rol_id__in=['ROL04', 'ROL05'],
                ).exclude(rol__permisos='total')
        if self.model == SubAtencion:
            queryset = queryset.select_related('tipo')
        return queryset

    def get_queryset(self):
        return self.base_queryset()

    def get_page_size(self):
        """Solo las opciones visibles pueden cambiar la preferencia de sesión."""
        session_key = f'crud_page_size_{self.slug}'
        selected = self.request.GET.get('page_size')
        if selected in {str(size) for size in self.allowed_page_sizes}:
            self.request.session[session_key] = int(selected)
        saved = self.request.session.get(session_key, self.default_page_size)
        return saved if saved in self.allowed_page_sizes else self.default_page_size

    def get_ordering_options(self):
        options = [
            ('nombre', 'Nombre: A a Z'), ('-nombre', 'Nombre: Z a A'),
            ('estado', 'Estado: A a Z'), ('-estado', 'Estado: Z a A'),
        ]
        if self.model == Usuario:
            options.extend([('email', 'Correo: A a Z'), ('-email', 'Correo: Z a A')])
        else:
            options.extend([('codigo', 'Código: ascendente'), ('-codigo', 'Código: descendente')])
        return options

    def get_ordering(self):
        allowed = dict(self.get_ordering_options())
        requested = self.request.GET.get('order', 'nombre')
        return requested if requested in allowed else 'nombre'

    def filtered_queryset(self):
        # Los filtros afectan al listado, nunca la búsqueda del objeto a editar.
        queryset = self.base_queryset()
        query = self.request.GET.get('q', '').strip()[:200]
        if query:
            lookup = Q(nombre__icontains=query)
            search_fields = {
                Usuario: ['email', 'rut', 'username', 'rol__nombre', 'delegacion__nombre'],
                Delegacion: ['codigo', 'direccion', 'comuna'],
                SubAtencion: ['codigo', 'tipo__nombre'],
            }.get(self.model, ['codigo', 'descripcion'])
            for field in search_fields:
                lookup |= Q(**{f'{field}__icontains':query})
            queryset = queryset.filter(lookup)
        estado = self.request.GET.get('estado', '')
        if estado:
            queryset = queryset.filter(estado=estado)
        if self.model == Usuario and self.request.GET.get('delegacion'):
            queryset = queryset.filter(delegacion_id=self.request.GET['delegacion'])
        if self.model == SubAtencion and self.request.GET.get('tipo'):
            queryset = queryset.filter(tipo_id=self.request.GET['tipo'])
        # El id desempata nombres/códigos repetidos para no saltar filas entre páginas.
        return queryset.order_by(self.get_ordering(), 'id')

    def query_parameters(self):
        params = QueryDict(mutable=True)
        for key in ('q', 'estado', 'delegacion', 'tipo', 'page'):
            if self.request.GET.get(key):
                params[key] = self.request.GET[key]
        params['order'] = self.get_ordering()
        params['page_size'] = str(self.get_page_size())
        return params

    def preserved_query(self):
        return self.query_parameters().urlencode()

    def get_success_url(self):
        url = reverse(f'gestion:{self.slug}-list')
        query = self.preserved_query()
        return f'{url}?{query}' if query else url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = Paginator(self.filtered_queryset(), self.get_page_size())
        page = paginator.get_page(self.request.GET.get('page'))
        name = self.model._meta.model_name
        context.update(
            native_crud=True,
            catalog_slug=self.slug, catalog_title=CATALOGS[self.slug][2], singular=CATALOGS[self.slug][3],
            page_obj=page, paginator=paginator, records=page.object_list,
            object_list=page.object_list, is_paginated=page.has_other_pages(),
            page_range=paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1),
            page_size=self.get_page_size(), page_sizes=self.allowed_page_sizes,
            ordering=self.get_ordering(), ordering_options=self.get_ordering_options(),
            query_params=self.query_parameters(),
            list_url=self.get_success_url(),
            base_list_url=reverse(f'gestion:{self.slug}-list'),
            create_url=reverse(f'gestion:{self.slug}-create'),
            can_add=self.request.user.has_perm(f'gestion.add_{name}'),
            can_change=self.request.user.has_perm(f'gestion.change_{name}'),
            can_delete=self.request.user.has_perm(f'gestion.delete_{name}'),
            navigation=[(key, value[2], reverse(f'gestion:{key}-list')) for key,value in CATALOGS.items() if self.request.user.has_perm(f'gestion.view_{value[0]._meta.model_name}')],
            estados=['Activa','Inactiva'] if self.model in (Delegacion,SubAtencion) else ['Activo','Inactivo'],
            delegaciones=(Delegacion.objects.order_by('nombre') if communal(self.request.user)
                          else Delegacion.objects.filter(codigo=self.request.user.delegacion_id))
                         if self.model == Usuario else None,
            tipos=TipoAtencion.objects.order_by('nombre') if self.model == SubAtencion else None,
        )
        return context


class CatalogListView(CrudAccessMixin, ListView):
    def get_queryset(self):
        return self.filtered_queryset()


class FormContextMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['open_modal'] = True
        context['editing'] = bool(self.object)
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                if not form.instance.pk and hasattr(form.instance, 'codigo') and not form.cleaned_data.get('codigo'):
                    _, _, _, _, prefix, width = CATALOGS[self.slug]
                    code = next_code(self.slug, prefix, width)
                    while self.model.objects.filter(codigo=code).exists():
                        code = next_code(self.slug, prefix, width)
                    form.instance.codigo = code
                return super().form_valid(form)
        except IntegrityError:
            form.add_error(None, 'El registro entra en conflicto con otro existente. Revise código, RUT y correo.')
            return self.form_invalid(form)


class CatalogCreateView(FormContextMixin, CrudAccessMixin, SuccessMessageMixin, CreateView):
    action = 'add'
    success_message = 'Registro creado correctamente.'


class CatalogUpdateView(FormContextMixin, CrudAccessMixin, SuccessMessageMixin, UpdateView):
    action = 'change'
    success_message = 'Registro actualizado correctamente.'


class CatalogDeleteView(CrudAccessMixin, DeleteView):
    action = 'delete'
    template_name = 'gestion/confirm_delete.html'

    def form_valid(self, form):
        if self.model == Usuario and self.object.pk == self.request.user.pk:
            messages.error(self.request, 'No puede eliminar su propia cuenta.')
            return redirect(self.get_success_url())
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'No se puede eliminar: existen registros asociados.')
            return redirect(self.get_success_url())
        messages.success(self.request, 'Registro eliminado correctamente.')
        return response


# Clases explícitas para localizar y defender cada entidad en la evaluación.
class DelegacionListView(CatalogListView):
    model = Delegacion
    slug = 'delegaciones'

class DelegacionCreateView(CatalogCreateView):
    model = Delegacion
    form_class = forms.DelegacionForm
    slug = 'delegaciones'

class DelegacionUpdateView(CatalogUpdateView):
    model = Delegacion
    form_class = forms.DelegacionForm
    slug = 'delegaciones'

class DelegacionDeleteView(CatalogDeleteView):
    model = Delegacion
    slug = 'delegaciones'

class RolListView(CatalogListView):
    model = Rol
    slug = 'roles'

class RolCreateView(CatalogCreateView):
    model = Rol
    form_class = forms.RolForm
    slug = 'roles'

class RolUpdateView(CatalogUpdateView):
    model = Rol
    form_class = forms.RolForm
    slug = 'roles'

class RolDeleteView(CatalogDeleteView):
    model = Rol
    slug = 'roles'

class UsuarioListView(CatalogListView):
    model = Usuario
    slug = 'usuarios'

class UsuarioCreateView(CatalogCreateView):
    model = Usuario
    form_class = forms.UsuarioForm
    slug = 'usuarios'

class UsuarioUpdateView(CatalogUpdateView):
    model = Usuario
    form_class = forms.UsuarioForm
    slug = 'usuarios'

class UsuarioDeleteView(CatalogDeleteView):
    model = Usuario
    slug = 'usuarios'

class ItemMetaListView(CatalogListView):
    model = ItemMeta
    slug = 'items-metas'

class ItemMetaCreateView(CatalogCreateView):
    model = ItemMeta
    form_class = forms.ItemMetaForm
    slug = 'items-metas'

class ItemMetaUpdateView(CatalogUpdateView):
    model = ItemMeta
    form_class = forms.ItemMetaForm
    slug = 'items-metas'

class ItemMetaDeleteView(CatalogDeleteView):
    model = ItemMeta
    slug = 'items-metas'

class TipoAtencionListView(CatalogListView):
    model = TipoAtencion
    slug = 'tipos-atencion'

class TipoAtencionCreateView(CatalogCreateView):
    model = TipoAtencion
    form_class = forms.TipoAtencionForm
    slug = 'tipos-atencion'

class TipoAtencionUpdateView(CatalogUpdateView):
    model = TipoAtencion
    form_class = forms.TipoAtencionForm
    slug = 'tipos-atencion'

class TipoAtencionDeleteView(CatalogDeleteView):
    model = TipoAtencion
    slug = 'tipos-atencion'

class SubAtencionListView(CatalogListView):
    model = SubAtencion
    slug = 'sub-atenciones'

class SubAtencionCreateView(CatalogCreateView):
    model = SubAtencion
    form_class = forms.SubAtencionForm
    slug = 'sub-atenciones'

class SubAtencionUpdateView(CatalogUpdateView):
    model = SubAtencion
    form_class = forms.SubAtencionForm
    slug = 'sub-atenciones'

class SubAtencionDeleteView(CatalogDeleteView):
    model = SubAtencion
    slug = 'sub-atenciones'
