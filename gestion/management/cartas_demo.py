"""Semillas de correspondencia ficticia; no sobrescribir revisiones."""
from datetime import date, timedelta

from gestion.models import Carta


def seed_cartas(orgs, users):
    for number in range(12):
        local = number < 6
        Carta.all_objects.get_or_create(codigo_anterior=f'CAR-DEMO-{number + 1:03}', defaults={
            'delegacion': orgs[0 if local else 1],
            'nombre': f'Actividad ficticia de correspondencia {number + 1:02}',
            'fecha': date(2026, 11, 6) - timedelta(days=number),
            'numero_ingreso': f'DEMO-CAR-{number + 1:04}',
            'para': ['Alcaldesa', 'Delegado', 'Otro'][number % 3],
            'remite': f'Remitente ficticio {number + 1:02}',
            'encargado': users['editor_a' if local else 'lector_b'],
            'estado': ['En proceso', 'Aprobada', 'Finalizada', 'No aplica'][number % 4],
            'pronunciamiento': 'Para conocimiento. Antecedente ficticio de demostración.',
            'derivada_a': 'Unidad municipal ficticia',
            'observacion': 'Registro ficticio para presentar el seguimiento de correspondencia.'})
