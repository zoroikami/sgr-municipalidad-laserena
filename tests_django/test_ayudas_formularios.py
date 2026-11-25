"""Las ayudas cubren también los campos que dependen del rol y del estado."""
from html.parser import HTMLParser
import os
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.template.loader import render_to_string
from django.urls import resolve, reverse
from django.utils.html import strip_tags

from cuentas.forms import GroupPermissionsForm, ManagedUserForm, MunicipalAuthenticationForm, ProfileForm
from gestion.forms import AtencionForm, DelegacionForm, ItemMetaForm, SubAtencionForm, TipoAtencionForm
from gestion.forms_cartas import CartaForm
from gestion.forms_integrado import (
    ActividadSGRForm, AusenciaSGRForm, GestionTuboForm, MetaSGRForm, OrganizacionForm, ReclamoSGRForm,
)
from gestion.models import Carta, GestionTubo
from gestion.public_forms import PublicConsultationForm
from gestion.seguimiento import configurar_estado_formulario


SCOPED_FORMS = (ItemMetaForm, TipoAtencionForm, SubAtencionForm, DelegacionForm, AtencionForm,
                OrganizacionForm, GestionTuboForm, ActividadSGRForm, AusenciaSGRForm, ReclamoSGRForm, CartaForm)


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.by_id = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.by_id[attrs['id']] = attrs


def assert_linked_help(form, html, suffix):
    elements = Elements(html).by_id
    for field in form.visible_fields():
        help_id = field.auto_id + suffix
        assert help_id in elements, (type(form).__name__, field.name)
        assert 'field-help' in elements[help_id].get('class', '').split()
        control = elements[field.auto_id]
        assert help_id in control.get('aria-describedby', '').split(), (type(form).__name__, field.name)


@pytest.mark.django_db
def test_cada_campo_visible_tiene_ayuda_incluso_con_campos_dinamicos(mundo):
    delegado = mundo['users']['admin_a']
    delegado.user_permissions.add(Permission.objects.get(codename='validar_delegado'))
    global_user = mundo['users']['coordinador']
    global_user.is_superuser = True
    forms = [cls(user=user) for user in (delegado, global_user) for cls in SCOPED_FORMS]
    forms += [ProfileForm(), ManagedUserForm(actor=delegado), ManagedUserForm(actor=global_user),
              ManagedUserForm(actor=global_user, instance=delegado), MunicipalAuthenticationForm(),
              PublicConsultationForm(), MetaSGRForm(), GroupPermissionsForm()]
    for cls, obj in ((GestionTuboForm, GestionTubo(estado='Pendiente')),
                     (CartaForm, Carta(estado='En proceso'))):
        form = cls(user=delegado, instance=obj)
        configurar_estado_formulario(form, obj)
        forms.append(form)
    missing = [f'{type(form).__name__}.{field.name}' for form in forms for field in form.visible_fields()
               if not strip_tags(str(field.help_text)).strip()]
    assert not missing, missing


@pytest.mark.django_db
def test_ayudas_de_contrasena_preservan_los_validadores(mundo):
    user = mundo['users']['editor_a']
    for route in ('password_change', 'password_reset', 'password_reset_confirm'):
        kwargs = {'uidb64': 'MQ', 'token': 'set-password'} if route.endswith('confirm') else {}
        view = resolve(reverse('cuentas:' + route, kwargs=kwargs)).func
        cls = view.view_initkwargs.get('form_class', view.view_class.form_class)
        form = cls() if route == 'password_reset' else cls(user)
        assert all(field.help_text for field in form.visible_fields()), route
        if 'new_password1' in form.fields:
            from django.contrib.auth.password_validation import password_validators_help_text_html
            assert str(password_validators_help_text_html()) in str(form.fields['new_password1'].help_text)
        assert_linked_help(form, render_to_string('cuentas/_fields.html', {'form': form}), '_helptext')


@pytest.mark.django_db
def test_ayudas_renderizadas_y_vinculadas_en_formularios(mundo):
    user = mundo['users']['admin_a']
    user.user_permissions.add(Permission.objects.get(codename='validar_delegado'))
    for cls in SCOPED_FORMS + (MetaSGRForm,):
        form = cls() if cls is MetaSGRForm else cls(user=user)
        if cls in (GestionTuboForm, CartaForm):
            configurar_estado_formulario(form, form.instance)
        html = render_to_string('gestion/formulario.html', {'form': form})
        assert_linked_help(form, html, '_help')
    for form in (ProfileForm(), ManagedUserForm(actor=user), MunicipalAuthenticationForm(), PublicConsultationForm()):
        html = render_to_string('cuentas/_fields.html', {'form': form})
        assert_linked_help(form, html, '_helptext')


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(os.environ.get('SGR_RUN_FORM_HELP_QA') != '1', reason='Capturas optativas en BD aislada.')
def test_ayudas_en_navegador_375_y_1280(mundo):
    from django.conf import settings
    from django.test import Client
    from playwright.sync_api import sync_playwright
    from tests_django.test_qa_navegador import isolated_asgi

    output = Path(os.environ['SGR_QA_OUTPUT'])
    output.mkdir(parents=True, exist_ok=True)
    delegado = mundo['users']['admin_a']
    delegado.user_permissions.add(Permission.objects.get(codename='validar_delegado'))
    global_user = mundo['users']['coordinador']
    global_user.is_superuser = global_user.is_staff = True
    global_user.save()
    cookies = {}
    for key, user in (('delegado', delegado), ('global', global_user)):
        client = Client()
        client.force_login(user)
        cookies[key] = client.cookies[settings.SESSION_COOKIE_NAME].value
    pages = (
        ('tubo', 'delegado', reverse('gestion:crear', args=['tubo']), '#record-form'),
        ('actividad', 'delegado', reverse('gestion:actividad_crear'), '#record-form'),
        ('usuario', 'global', reverse('cuentas:usuario_crear'), '.account-section form'),
    )
    with isolated_asgi() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (375, 1280):
            for name, role, route, selector in pages:
                context = browser.new_context(viewport={'width': width, 'height': 900})
                context.add_cookies([{'name': settings.SESSION_COOKIE_NAME, 'value': cookies[role], 'url': base}])
                page = context.new_page()
                response = page.goto(base + route)
                assert response.status == 200, (name, response.status)
                page.locator(selector).wait_for(state='visible')
                page.evaluate('document.fonts.ready')
                failures = page.locator(selector).evaluate("""form => {
                    const problems = [];
                    for (const input of form.querySelectorAll('input:not([type=hidden]),select,textarea')) {
                        if (input.type === 'checkbox') {
                            const r = input.getBoundingClientRect();
                            if (r.width > 32 || r.height > 32) problems.push(input.name + ': casilla deformada');
                        }
                        const refs = (input.getAttribute('aria-describedby') || '').split(/\\s+/);
                        const help = refs.map(id => document.getElementById(id))
                            .find(el => el && el.classList.contains('field-help'));
                        if (!help || !help.textContent.trim()) problems.push(input.name + ': falta ayuda');
                        else {
                            const r = help.getBoundingClientRect();
                            if (r.left < 0 || r.right > innerWidth + 1 || help.scrollWidth > help.clientWidth + 1)
                                problems.push(input.name + ': ayuda desbordada');
                        }
                    }
                    if (document.documentElement.scrollWidth > innerWidth + 1) problems.push('página desbordada');
                    return problems;
                }""")
                assert not failures, (name, width, failures)
                page.screenshot(path=str(output / f'{name}-{width}-inicio.png'), full_page=True)
                page.locator(selector + ' button[type=submit]').scroll_into_view_if_needed()
                page.screenshot(path=str(output / f'{name}-{width}-final.png'), full_page=True)
                context.close()
        browser.close()
