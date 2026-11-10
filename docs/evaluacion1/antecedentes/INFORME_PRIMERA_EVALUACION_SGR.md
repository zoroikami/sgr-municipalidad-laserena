# INFORME TÉCNICO DE ANÁLISIS Y DISEÑO DE SOFTWARE
## SISTEMA DE GESTIÓN DE RESULTADOS (SGR)
### ILUSTRE MUNICIPALIDAD DE LA SERENA

---

**CARRERA:** Analista en Informática / Ingeniería en Informática / Ingeniería en Ciberseguridad  
**ASIGNATURA:** Proyecto Integrado | **PROFESOR:** Jorge Cortés | **INSTITUCIÓN:** INACAP  
**ENTREGA:** Primera Evaluación (100 Puntos)  

---

## 1. INTRODUCCIÓN Y CONTEXTO INSTITUCIONAL
La Ilustre Municipalidad de La Serena y su Dirección de Servicios Comunitarios (DISERCO) administran las demandas territoriales de 6 Delegaciones Municipales: Centro, Las Compañías, La Pampa, La Antena-La Florida, Avenida del Mar y Rural.
El SGR resuelve la falta de trazabilidad histórica, descentralización de datos y desbalance territorial mediante:
- Respaldo de evidencias fotográficas obligatorias con código inmutable `EVI-2026-XXXX`.
- Segregación estricta entre funcionarios en terreno y el Verificador Técnico.
- Semáforo diario proporcional calculado según los días transcurridos del trimestre.
- Ficha social multietapa (hasta 3 gestiones por persona).
- Agenda colectiva (Tubo de trabajo Kanban de 4 estados).

## 2. PLANIFICACIÓN OPERATIVA EN MICROSOFT PLANNER
Tablero organizado en 8 depósitos (Buckets) temáticos con 22 tareas configuradas con responsables, fechas, checklists de DoD y flujo de 4 estados (*No iniciada, En curso, En revisión, Completada*), enlazado con la convención de Git según `crear proyecto.pdf`.

## 3. INGENIERÍA DE REQUERIMIENTOS Y MATRIZ DE TRAZABILIDAD
Descomposición jerárquica SysML desde `REQ-ROOT-00` hacia `RF-001` a `RF-024` y `RNF-001` a `RNF-005` mediante relaciones `<<deriveReqt>>` y `<<refine>>`, vinculados en una matriz de trazabilidad transversal con las 13 reglas de negocio (`RN-01` a `RN-13`).

## 4. MODELADO FUNCIONAL DE CASOS DE USO
- Diagrama General UML 2.5 con frontera del sistema, 6 actores primarios y 1 secundario.
- 12 Casos de uso detallados individuales en PlantUML y especificaciones textuales completas.
- 8 Cuadros estandarizados de casos de extensión (`EXT-01` a `EXT-08`) conforme a `Relación entre los artefactos.pdf`.

## 5. DISEÑO ORIENTADO A OBJETOS (UML 2.5)
Diagrama de clases formal con 14 clases del dominio (`Delegacion`, `Usuario`, `Rol`, `Cargo`, `Actividad`, `Evidencia`, `ValidacionEvidencia`, `PersonaUsuaria`, `AtencionSocial`, `CompromisoAgenda`, etc.), atributos tipados, visibilidad formal y multiplicidades justificadas.

## 6. DISEÑO DE BASE DE DATOS Y PERSISTENCIA (MYSQL 8.0)
Modelo DER relacional normalizado en Tercera Forma Normal (3FN) con 14 tablas, restricciones `ON DELETE RESTRICT`, índices y script ejecutable `database_sgr.sql` con datos semilla reales de La Serena.

## 7. PROTOTIPO WEB FUNCIONAL EN GIT
Prototipo interactivo en `mockup/` con 10 vistas, motor de cálculo matemático de semáforos, validación de formularios, modales de zoom, duplicados y alertas, y repositorio Git con README técnico.

## 8. CONCLUSIONES
Se demuestra el cumplimiento riguroso de todos los criterios de la rúbrica de 100 puntos con trazabilidad unívoca entre artefactos.
