from django.urls import path
from . import views
from . import public_views
from . import views_integrado
from . import views_tablero
from . import views_funcionarios

app_name = 'gestion'
urlpatterns = [
    path('cartas/tablero/', views_tablero.cartas_tablero, name='cartas_tablero'),
    path('cartas/<int:pk>/avanzar/', views_tablero.cartas_mover, name='cartas_mover'),
    path('tubo/', views_integrado.tablero, name='tablero'),
    path('tubo/<int:pk>/avanzar/', views_integrado.mover, name='tubo_mover'),
    path('funcionarios/rut/', views_funcionarios.rut_funcionario, name='rut_funcionario'),
    path('sgr/', views_integrado.resultados, name='resultados_sgr'),
    path('sgr/actividad/', views_integrado.registrar, name='actividad_crear'),
    path('sgr/ausencia/', views_integrado.registrar, {'ausencia': True}, name='ausencia_crear'),
    path('sgr/reclamo/', views_integrado.registrar, {'reclamo': True}, name='reclamo_crear'),
    path('sgr/items/', views_integrado.items_actividad, name='items_actividad'),
    path('sgr/actividad/<int:pk>/verificar/', views_integrado.verificar_actividad, name='actividad_verificar'),
    path('sgr/meta/<int:pk>/funcionario/<int:user_pk>/', views_integrado.meta_funcionario, name='meta_funcionario'),
    path('sgr/meta/<int:pk>/', views_integrado.configurar_meta, name='meta_configurar'),
    path('', views.inicio, name='inicio'),
    path('consulta/', public_views.consulta_publica, name='consulta_publica'),
    path('gestion/atenciones/<int:pk>/correo-consulta/', public_views.enviar_codigo_consulta, name='enviar_codigo_consulta'),
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
