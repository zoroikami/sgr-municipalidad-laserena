from django.contrib import admin
from django.urls import include, path, re_path
from django.shortcuts import redirect
from gestion import views
from gestion.crud_views import AccesoView
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('acceso/', AccesoView.as_view(), name='login'),
    path('salir/', LogoutView.as_view(), name='logout'),
    path('gestion/', include('gestion.urls')),
    path('', views.index),
    path('index.html', views.index),
    re_path(r'^evaluacion2/?(?:index\.html)?$', lambda request: redirect('/', permanent=True)),
    path('api/health', views.health),
    path('api/profile', views.profile),
    path('api/auth/<str:action>', views.auth),
    path('api/<str:resource>', views.collection),
    path('api/<str:resource>/<int:pk>', views.collection),
    re_path(r'^(?P<asset_path>(?:assets|evaluacion2/(?:css|js|assets)|mockup/(?:css|js|assets)|css|js)/.+)$', views.asset),
]
