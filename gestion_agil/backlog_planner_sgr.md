# Planificación Operativa en Microsoft Planner
## Sistema de Gestión de Resultados (SGR) - Ilustre Municipalidad de La Serena

**Asignatura:** Proyecto Integrado | **Profesor:** Jorge Cortés | **Institución:** INACAP
**Herramienta Oficial de Planificación:** Microsoft Planner (Ecosistema Microsoft 365)

---

## 1. Estructura del Tablero en Microsoft Planner

El proyecto se gestiona en el plan **"SGR - Municipalidad de La Serena 2026"**, organizado en **8 Depósitos (Buckets)** temáticos:

1. **[B1] Descubrimiento, Arquitectura y Prototipo UI** (Hitos iniciales y diseño base)
2. **[B2] Gestión de Identidad, Perfiles y Delegaciones** (Autenticación y control de acceso)
3. **[B3] Registro Operativo y Evidencias en Terreno** (Captura de actividades y código EVI-2026)
4. **[B4] Bandeja de Verificación y Control de Calidad** (Revisión técnica de evidencias)
5. **[B5] Atención Social Multietapa** (Ficha ciudadana y concatenación de hasta 3 gestiones)
6. **[B6] Tubo de Trabajo y Agenda Colectiva** (Compromisos vecinales y alertas de plazo)
7. **[B7] Motor de Semáforo Diario y Analítica** (Cálculo ponderado y tableros territoriales)
8. **[B8] Administración, Base de Datos y Auditoría** (Configuración de metas, DER SQL y bitácora)

---

## 2. Catálogo de Tareas Detalladas en Microsoft Planner

### [B1] Descubrimiento, Arquitectura y Prototipo UI
- **SGR-01: Prototipo Base de Interfaz Web Institucional** (Completada | Dev Frontend | Urgente)
  - [x] Maquetar estructura semántica HTML5 y estilos corporativos La Serena.
  - [x] Implementar barra superior con selector de roles y buscador.
  - [x] Configurar repositorio Git con rama main y commits formales.
- **SGR-02: Matriz Interactiva de Trazabilidad en Pantalla** (Completada | QA / Frontend | Media)
  - [x] Crear tabla con filtros por módulo funcional.
  - [x] Enlazar cada fila con la sección correspondiente del prototipo.

### [B2] Gestión de Identidad, Perfiles y Delegaciones
- **SGR-03: Control de Acceso y Autenticación por Delegación** (Completada | Backend | Urgente)
  - [x] Validar sesión activa y delegación asignada.
  - [x] Adaptar menú lateral según permisos del rol activo.
- **SGR-04: Parametrización Territorial de las 6 Delegaciones** (Completada | DBA | Importante)
  - [x] Cargar catálogo de delegaciones (Centro, Las Compañías, La Pampa, La Antena, Av. del Mar, Rural).
  - [x] Asociar usuarios a sus jurisdicciones oficiales.

### [B3] Registro Operativo y Evidencias en Terreno
- **SGR-05: Formulario de Registro Dinámico según Cargo** (Completada | Fullstack | Importante)
  - [x] Filtrar ítems por cargo del funcionario.
- **SGR-06: Generación Automática del Código de Evidencia EVI-2026-XXXX** (Completada | Backend | Urgente)
  - [x] Algoritmo de clave correlativa inmutable `EVI-2026-XXXX`.
- **SGR-07: Carga y Validación de Fotografía** (Completada | Frontend | Media)
  - [x] Dropzone con validación de imagen JPG/PNG.
- **SGR-08: Detección y Modal de Registro Duplicado** (Completada | QA / Frontend | Importante)
  - [x] Evaluar colisión de fecha, ítem y solicitante.
- **SGR-09: Validación de Campos Obligatorios y Modal de Error** (Completada | Frontend | Importante)
  - [x] Resaltado en rojo y modal explicativo ante campos vacíos.

### [B4] Bandeja de Verificación y Control de Calidad
- **SGR-10: Bandeja de Evidencias Pendientes por Delegación** (Completada | Frontend | Importante)
- **SGR-11: Modal de Validación con Visor Fotográfico y Zoom** (Completada | Frontend | Importante)
- **SGR-12: Aprobación y Rechazo Técnico de Evidencias** (Completada | Fullstack | Urgente)
  - [x] Dictamen vinculante que actualiza semáforo y exige fundamento en caso de rechazo.

### [B5] Atención Social Multietapa
- **SGR-13: Registro Único de Persona Usuaria** (Completada | Backend | Importante)
- **SGR-14: Concatenación de Gestiones Sucesivas - Límite 3 Etapas** (Completada | Fullstack | Urgente)
  - [x] Línea de tiempo cronológica y bloqueo de 4ta gestión por tope reglamentario (RN-10).

### [B6] Tubo de Trabajo y Agenda Colectiva
- **SGR-15: Tablero Kanban de Compromisos Territoriales** (Completada | Frontend | Importante)
- **SGR-16: Formulario de Creación de Compromiso Vecinal** (Completada | Frontend | Media)
- **SGR-17: Sistema de Alertas por Vencimiento de Plazos** (Completada | Fullstack | Importante)
  - [x] Insignia roja y modal de alerta operativa ante plazos expirados.

### [B7] Motor de Semáforo Diario y Analítica
- **SGR-18: Algoritmo de Cumplimiento Ponderado al 100%** (Completada | Backend | Urgente)
- **SGR-19: Algoritmo del Semáforo Proporcional Diario** (Completada | Backend | Urgente)
  - [x] Comparación del avance real contra el día del trimestre (Día 76/91).
- **SGR-20: Tablero Resumen de Delegación y Gráficos Chart.js** (Completada | Frontend | Media)

### [B8] Administración, Base de Datos y Auditoría
- **SGR-21: Configuración de Períodos y Validación de Ponderaciones** (Completada | Fullstack | Importante)
  - [x] Control estricto de suma exacta al 100% de los ponderadores.
- **SGR-22: Bitácora Inmutable de Auditoría de Cambios** (Completada | Ciberseguridad | Importante)
  - [x] Registro JSON con marca de tiempo, IP, usuario y datos previos/nuevos.

---

## 3. Flujo de Estados y Convención Git / Planner
- **Estados:** *No iniciada* -> *En curso* -> *En revisión* -> *Completada*.
- **Ramas Git:** `feature/SGR-XX-descripcion`
- **Commits:** `git commit -m "SGR-XX: Descripción formal del cambio"`
