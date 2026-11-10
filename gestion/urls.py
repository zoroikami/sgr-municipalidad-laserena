from django.urls import path
from . import views
from . import views_integrado

app_name = 'gestion'
urlpatterns = [
    path('tubo/', views_integrado.tablero, name='tablero'),
    path('tubo/<int:pk>/avanzar/', views_integrado.mover, name='tubo_mover'),
    path('sgr/', views_integrado.resultados, name='resultados_sgr'),
    path('sgr/actividad/', views_integrado.registrar, name='actividad_crear'),
    path('sgr/ausencia/', views_integrado.registrar, {'ausencia': True}, name='ausencia_crear'),
    path('sgr/meta/<int:pk>/', views_integrado.configurar_meta, name='meta_configurar'),
    path('', views.inicio, name='inicio'),
    path('api/health/', views.health, name='health'),
    path('portal/', views.portal, name='portal'),
    path('portal/atenciones/<int:pk>/', views.portal_detalle, name='portal_detalle'),
    path('catalogos/subatenciones/', views.subatenciones, name='subatenciones'),
    path('gestion/<slug:modulo>/', views.listado, name='listado'),
    path('gestion/<slug:modulo>/tabla/', views.tabla, name='tabla'),
    path('gestion/<slug:modulo>/crear/', views.crear, name='crear'),
    path('gestion/<slug:modulo>/exportar/', views.exportar, name='exportar'),
    path('gestion/<slug:modulo>/<int:pk>/', views.detalle, name='detalle'),
    path('gestion/<slug:modulo>/<int:pk>/editar/', views.editar, name='editar'),
    path('gestion/<slug:modulo>/<int:pk>/archivar/', views.archivar, name='archivar'),
]
