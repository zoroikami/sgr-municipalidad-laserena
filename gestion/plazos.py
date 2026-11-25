"""Agenda por fecha y avisos calculados con el cierre efectivamente registrado."""
from django.db.models import F, OuterRef, Subquery
from django.utils import timezone

from .models import Carta, HistorialEstado


def con_plazos(query):
    es_carta = query.model is Carta
    relacion = 'carta_id' if es_carta else 'gestion_tubo_id'
    campo_fecha = 'fecha_actividad' if es_carta else 'fecha_compromiso'
    estado_cierre = 'Finalizada' if es_carta else 'Realizado'
    cierre = HistorialEstado.objects.filter(**{relacion: OuterRef('pk')}, estado_nuevo=estado_cierre)
    cierre = cierre.order_by('-fecha', '-pk')
    return query.annotate(fecha_cierre=Subquery(cierre.values('fecha')[:1]),
        fecha_objetivo_cierre=Subquery(cierre.values('fecha_objetivo')[:1])).order_by(
        F(campo_fecha).asc(nulls_last=True), 'pk')


def contar_vencidos(query, hoy):
    if query.model is Carta:
        return query.filter(estado='En proceso', fecha_actividad__lt=hoy).count()
    return query.exclude(estado='Realizado').filter(fecha_compromiso__lt=hoy).count()


def etiquetar_plazos(registros, hoy):
    for obj in registros:
        es_carta = isinstance(obj, Carta)
        compromiso = obj.fecha_actividad if es_carta else obj.fecha_compromiso
        cerrado = obj.estado == ('Finalizada' if es_carta else 'Realizado')
        abierto = obj.estado == 'En proceso' if es_carta else not cerrado
        obj.plazo = obj.plazo_tipo = ''
        if cerrado:
            if (obj.fecha_cierre and obj.fecha_objetivo_cierre
                    and timezone.localdate(obj.fecha_cierre) > obj.fecha_objetivo_cierre):
                obj.plazo, obj.plazo_tipo = 'Realizado fuera de plazo', 'fuera-plazo'
        elif abierto and compromiso:
            dias = (compromiso - hoy).days
            if dias < 0:
                obj.plazo, obj.plazo_tipo = 'Vencido', 'vencido'
            elif dias <= 3:
                obj.plazo = 'Vence hoy' if dias == 0 else f'Vence en {dias} día' + ('s' if dias != 1 else '')
                obj.plazo_tipo = 'proximo'
    return registros
