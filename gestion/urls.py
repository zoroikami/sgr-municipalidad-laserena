from django.urls import path
from . import crud_views as views

app_name = 'gestion'
urlpatterns = [
    path('delegaciones/', views.DelegacionListView.as_view(), name='delegaciones-list'),
    path('delegaciones/nuevo/', views.DelegacionCreateView.as_view(), name='delegaciones-create'),
    path('delegaciones/<int:pk>/editar/', views.DelegacionUpdateView.as_view(), name='delegaciones-update'),
    path('delegaciones/<int:pk>/eliminar/', views.DelegacionDeleteView.as_view(), name='delegaciones-delete'),
    path('roles/', views.RolListView.as_view(), name='roles-list'),
    path('roles/nuevo/', views.RolCreateView.as_view(), name='roles-create'),
    path('roles/<int:pk>/editar/', views.RolUpdateView.as_view(), name='roles-update'),
    path('roles/<int:pk>/eliminar/', views.RolDeleteView.as_view(), name='roles-delete'),
    path('usuarios/', views.UsuarioListView.as_view(), name='usuarios-list'),
    path('usuarios/nuevo/', views.UsuarioCreateView.as_view(), name='usuarios-create'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuarios-update'),
    path('usuarios/<int:pk>/eliminar/', views.UsuarioDeleteView.as_view(), name='usuarios-delete'),
    path('items-metas/', views.ItemMetaListView.as_view(), name='items-metas-list'),
    path('items-metas/nuevo/', views.ItemMetaCreateView.as_view(), name='items-metas-create'),
    path('items-metas/<int:pk>/editar/', views.ItemMetaUpdateView.as_view(), name='items-metas-update'),
    path('items-metas/<int:pk>/eliminar/', views.ItemMetaDeleteView.as_view(), name='items-metas-delete'),
    path('tipos-atencion/', views.TipoAtencionListView.as_view(), name='tipos-atencion-list'),
    path('tipos-atencion/nuevo/', views.TipoAtencionCreateView.as_view(), name='tipos-atencion-create'),
    path('tipos-atencion/<int:pk>/editar/', views.TipoAtencionUpdateView.as_view(), name='tipos-atencion-update'),
    path('tipos-atencion/<int:pk>/eliminar/', views.TipoAtencionDeleteView.as_view(), name='tipos-atencion-delete'),
    path('sub-atenciones/', views.SubAtencionListView.as_view(), name='sub-atenciones-list'),
    path('sub-atenciones/nuevo/', views.SubAtencionCreateView.as_view(), name='sub-atenciones-create'),
    path('sub-atenciones/<int:pk>/editar/', views.SubAtencionUpdateView.as_view(), name='sub-atenciones-update'),
    path('sub-atenciones/<int:pk>/eliminar/', views.SubAtencionDeleteView.as_view(), name='sub-atenciones-delete'),
]
