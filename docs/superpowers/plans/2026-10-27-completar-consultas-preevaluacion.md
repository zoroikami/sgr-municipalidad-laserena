# Completar y verificar los CRUD de preevaluación

Objetivo: terminar los seis CRUD Django existentes del Escritorio, integrando los requisitos de consulta de Clase 10 y corrigiendo defectos comprobados en validación y alcance. Se conserva el diseño institucional, las CBV, ModelForm, Bootstrap local, SweetAlert2 y la API de compatibilidad.

Recursos: /Users/harold/Desktop/sgr-municipalidad-laserena; rama feature/migracion-django con cambios locales previos que deben conservarse. Verificador disponible: .venv/bin/python manage.py test gestion (33 pruebas iniciales, OK), check y makemigrations --check --dry-run. Navegador contra base temporal aislada para el recorrido visual.

Autonomía: implementar y verificar localmente en esta carpeta, autorizado por el usuario. Una revisión completa y hasta tres ciclos de reparación por fallo; si persiste una limitación externa, entregar el avance y la evidencia. Una única revisión independiente de código, de solo lectura, sin delegación adicional ni ramas alternativas. No hacer push, desplegar, modificar .env, cargar datos ficticios en la base habitual ni descartar cambios previos.

Arquitectura: ampliar CrudAccessMixin con page_size validado {5,15,30}, preferencia por catálogo en request.session, ordenamiento mediante mapa explícito de campos y desempate por PK, y QueryDict conservado en enlaces/formularios/redirecciones. Mantener scoping antes de filtros y paginación. Limitar el selector de delegación al alcance real del usuario. Reutilizar Bootstrap en las seis pantallas existentes.

- [x] Agregar pruebas de preferencia por catálogo, tamaño inválido, combinación búsqueda/filtro/orden/página, conservación tras guardar, datos ajenos en selectores y edición territorial.
- [x] Ejecutar las nuevas pruebas y confirmar que detectan las carencias.
- [x] Completar crud_views.py y list.html; probar las seis entidades y los filtros combinados.
- [x] Corregir únicamente problemas de validación/permisos reproducidos con pruebas.
- [x] Verificar en navegador login, crear/editar, error de formulario, confirmación SweetAlert2 y cancelación, consulta combinada y recarga. Base temporal aislada. La eliminación confirmada por POST se verifica con pruebas Django, sin borrar datos habituales desde el navegador.
- [x] Ejecutar suite completa, check, revisión de migraciones y pruebas JavaScript vigentes.
- [x] Actualizar guía de defensa con rutas y pruebas observadas; entregar resumen de cambios y límites.

Cierre: pruebas aprobadas, tamaños 5/15/30 persistentes, orden permitido, parámetros conservados y recorrido visual verificado. La defensa oral y el puntaje no son verificables automáticamente. Auditoría estructural y borrado lógico quedan fuera de esta etapa de CRUD, para evitar migraciones y cambios de semántica de eliminación no necesarios para la pauta inmediata.

Salida: cambios locales revisables y docs/PREEVALUACION_III.md actualizado; informe breve en outputs de este chat. No se publica ni se integra automáticamente.

Resultado: 51 pruebas Django y 18 pruebas JavaScript aprobadas; check, migraciones y diff sin incidencias. Revisión independiente encontró una escalada por roles territoriales con permisos totales; se reprodujo con cinco pruebas fallidas y se corrigió en formularios, queryset y API. El servidor habitual responde en 127.0.0.1:8000.
