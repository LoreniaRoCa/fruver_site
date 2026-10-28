from django import template

from vacaciones.logica import formatear_dias

register = template.Library()


@register.filter
def dias(valor):
    """15.0 -> 15, 7.5 -> 7.5"""
    if valor is None or valor == '':
        return ''
    return formatear_dias(valor)
