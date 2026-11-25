"""Avisos en tiempo real de tubo, cartas, casos sociales y Resultados SGR.

Cada cambio guardado avisa a los paneles de su delegación sin enviar datos del registro: el navegador vuelve a
pedir la página y la vista reaplica permisos y ámbito. Las escrituras con .update() avisan desde su vista.
"""
from django.db.models.signals import post_delete, post_save


def notificar(delegacion_id, *modulos):
    from .realtime import notify_after_commit
    if not delegacion_id:
        return
    for modulo in dict.fromkeys(modulos):
        notify_after_commit(delegacion_id, modulo=modulo)


def modulos_de(instancia):
    """Módulo fuente del cambio; realtime deriva qué paneles dependen de él (el tubo también mueve SGR)."""
    from .models import ActividadSGR, AusenciaSGR, Carta, CasoSocial, GestionTubo, ItemMeta, MetaFuncionario, ReclamoSGR
    if isinstance(instancia, GestionTubo):
        return instancia.delegacion_id, ('tubo',)
    if isinstance(instancia, Carta):
        return instancia.delegacion_id, ('cartas',)
    if isinstance(instancia, CasoSocial):
        return instancia.delegacion_id, ('casos',)
    if isinstance(instancia, ActividadSGR):
        return instancia.delegacion_id, ('sgr', 'casos') if instancia.caso_id else ('sgr',)
    if isinstance(instancia, MetaFuncionario):
        return instancia.item.delegacion_id if instancia.item_id else None, ('sgr',)
    if isinstance(instancia, (AusenciaSGR, ReclamoSGR, ItemMeta)):
        return instancia.delegacion_id, ('sgr',)
    return None, ()


def al_cambiar(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return  # cargas de fixtures
    delegacion_id, modulos = modulos_de(instance)
    notificar(delegacion_id, *modulos)


def conectar():
    from .models import ActividadSGR, AusenciaSGR, Carta, CasoSocial, GestionTubo, ItemMeta, MetaFuncionario, ReclamoSGR
    for modelo in (GestionTubo, Carta, CasoSocial, ActividadSGR, AusenciaSGR, ReclamoSGR, ItemMeta, MetaFuncionario):
        post_save.connect(al_cambiar, sender=modelo, dispatch_uid=f'tiempo_real_guardar_{modelo.__name__}')
        post_delete.connect(al_cambiar, sender=modelo, dispatch_uid=f'tiempo_real_borrar_{modelo.__name__}')
