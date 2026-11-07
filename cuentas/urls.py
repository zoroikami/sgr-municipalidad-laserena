from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import MunicipalAuthenticationForm

app_name = 'cuentas'
urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='cuentas/login.html', authentication_form=MunicipalAuthenticationForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page=reverse_lazy('cuentas:login')), name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('foto/<int:pk>/', views.foto, name='foto'),
    path('clave/', auth_views.PasswordChangeView.as_view(template_name='cuentas/password_change.html', success_url=reverse_lazy('cuentas:password_change_done')), name='password_change'),
    path('clave/lista/', auth_views.PasswordChangeDoneView.as_view(template_name='cuentas/password_change_done.html'), name='password_change_done'),
    path('recuperar/', auth_views.PasswordResetView.as_view(template_name='cuentas/password_reset.html', email_template_name='cuentas/password_reset_email.txt', subject_template_name='cuentas/password_reset_subject.txt', success_url=reverse_lazy('cuentas:password_reset_done')), name='password_reset'),
    path('recuperar/enviado/', auth_views.PasswordResetDoneView.as_view(template_name='cuentas/password_reset_done.html'), name='password_reset_done'),
    path('recuperar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='cuentas/password_reset_confirm.html', success_url=reverse_lazy('cuentas:password_reset_complete')), name='password_reset_confirm'),
    path('recuperar/lista/', auth_views.PasswordResetCompleteView.as_view(template_name='cuentas/password_reset_complete.html'), name='password_reset_complete'),
    path('usuarios/', views.usuarios, name='usuarios'),
    path('usuarios/nuevo/', views.usuario_form, name='usuario_crear'),
    path('usuarios/<int:pk>/editar/', views.usuario_form, name='usuario_editar'),
    path('roles/', views.roles, name='roles'),
]
