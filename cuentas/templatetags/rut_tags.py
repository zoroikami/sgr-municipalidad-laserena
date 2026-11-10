from django import template

from cuentas.rut import format_rut

register = template.Library()
register.filter('rut_formateado', format_rut)
