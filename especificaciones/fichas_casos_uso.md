# Especificación Textual de Casos de Uso
## Sistema de Gestión de Resultados (SGR) - Ilustre Municipalidad de La Serena

### CU-01: Autenticar Usuario y Controlar Sesión por Rol
- **Identificador:** CU-01 | **Actor Principal:** Funcionario Municipal (todos los roles)
- **Objetivo:** Verificar identidad y restringir vistas según cargo y delegación.
- **Precondiciones:** Usuario registrado y activo en MySQL.
- **Flujo Principal:** 1. Ingresar credenciales -> 2. Validar hash criptográfico -> 3. Cargar perfil y delegación -> 4. Crear sesión segura.
- **Flujos Alternativos:** 1a. Conmutación rápida en selector de demostración del header.
- **Excepciones:** 2a. Credenciales inválidas -> notificar error; 2b. Cuenta inactiva -> bloquear acceso.
- **Reglas:** RN-01, RN-02 | **Includes:** Validar Credenciales | **Extends:** Notificar Credenciales Inválidas.

### CU-02: Registrar Actividad en Terreno con Evidencia Fotográfica
- **Identificador:** CU-02 | **Actor Principal:** Funcionario Territorial
- **Objetivo:** Ingresar actividad en terreno con fotografía probatoria y código correlativo.
- **Precondiciones:** Sesión activa con rol Funcionario Territorial.
- **Flujo Principal:** 1. Acceder a formulario -> 2. Filtrar ítems por cargo -> 3. Ingresar sector, solicitante y descripción -> 4. Adjuntar fotografía -> 5. Validar obligatoriedad -> 6. Generar código correlativo -> 7. Guardar en estado Pendiente.
- **Excepciones:** 5a. Campos obligatorios vacíos -> abrir modal `modal-error-validacion`; 5b. Registro idéntico detectado -> abrir modal `modal-duplicado`.
- **Reglas:** RN-03, RN-04, RN-05, RN-06 | **Includes:** CU-03 Generar Código, Validar Datos | **Extends:** EXT-01 Notificar Duplicado, EXT-02 Error Validación.

### CU-03: Generar Código Único de Evidencia (EVI-2026-XXXX)
- **Identificador:** CU-03 | **Actor:** Sistema SGR
- **Objetivo:** Asignar correlativo alfanumérico irrepetible para trazabilidad.
- **Flujo Principal:** 1. Consultar último número de 2026 -> 2. Incrementar en transacción atómica -> 3. Formatear como `EVI-2026-XXXX` -> 4. Asociar a evidencia.
- **Reglas:** RN-04 (Inmutabilidad).

### CU-04: Validar y Dictaminar Evidencia Fotográfica en Bandeja Técnica
- **Identificador:** CU-04 | **Actor Principal:** Verificador Técnico Municipal
- **Objetivo:** Auditar fotografías en terreno y dictaminar aprobación o rechazo fundamentado.
- **Flujo Principal:** 1. Abrir bandeja -> 2. Seleccionar evidencia -> 3. Abrir modal con zoom fotográfico -> 4. Redactar observación -> 5. Confirmar Aprobación -> 6. Actualizar avance y semáforo (CU-08).
- **Flujo Alternativo:** 5a. Rechazar evidencia con justificación obligatoria.
- **Excepciones:** 5b. Rechazo sin fundamentación -> EXT-03 Exigir Dictamen.
- **Reglas:** RN-01, RN-08 | **Includes:** CU-08 Calcular Semáforo | **Extends:** EXT-03 Exigir Dictamen por Rechazo.

### CU-05: Registrar Atención Social Multietapa (Hasta 3 Gestiones)
- **Identificador:** CU-05 | **Actor Principal:** Gestor Social
- **Objetivo:** Dar seguimiento a personas vulnerables concatenando hasta 3 etapas en la misma ficha.
- **Flujo Principal:** 1. Buscar beneficiario por RUT -> 2. Abrir línea de tiempo -> 3. Ingresar nueva gestión -> 4. Incrementar contador (máx 3) -> 5. Guardar.
- **Excepciones:** 4a. Beneficiario ya tiene 3 gestiones -> EXT-04 Bloquear Cuarta Gestión (RN-10).
- **Reglas:** RN-09, RN-10 | **Extends:** EXT-04 Bloquear Cuarta Gestión.

### CU-06: Crear Compromiso Comunitario en Agenda Colectiva
- **Identificador:** CU-06 | **Actor Principal:** Delegado Municipal / Funcionario
- **Objetivo:** Registrar compromiso de reunión vecinal en el tablero Kanban.
- **Flujo Principal:** 1. Abrir modal -> 2. Ingresar origen, dirigente, territorio y fecha límite -> 3. Asignar responsable -> 4. Crear tarjeta en columna Ingresado.
- **Reglas:** RN-11, RN-12.

### CU-07: Actualizar Estado de Compromiso en Tubo de Trabajo
- **Identificador:** CU-07 | **Actor Principal:** Funcionario / Delegado
- **Objetivo:** Mover compromisos entre: Ingresado -> Pendiente -> En Proceso -> Realizado.
- **Excepciones:** Tarjeta sobrepasa fecha límite sin finalizar -> EXT-05 Notificar Compromiso Vencido (modal `modal-alerta-vencido`).
- **Reglas:** RN-11, RN-12 | **Extends:** EXT-05 Compromiso Vencido.

### CU-08: Calcular Cumplimiento Ponderado y Semáforo Diario
- **Identificador:** CU-08 | **Actor:** Motor de Cálculo SGR
- **Objetivo:** Sumar avances ponderados al 100% y comparar contra día del período (ej. Día 76/91 = 83.5% ideal).
- **Flujo:** Verde si avance >= ideal; Ámbar si avance está a menos de 15% del ideal; Rojo si retraso >= 15%.
- **Reglas:** RN-13 (Semáforo Proporcional).

### CU-09: Consultar Tablero Consolidado y Reportería Territorial
- **Identificador:** CU-09 | **Actor:** Delegado Municipal / DISERCO
- **Objetivo:** Supervisar tabla consolidada de personal, semáforos y gráficos comparativos Chart.js.

### CU-10: Configurar Período de Medición, Metas y Ponderadores
- **Identificador:** CU-10 | **Actor:** Administrador Central
- **Objetivo:** Parametrizar trimestres y validar que ponderaciones sumen exactamente 100%.
- **Excepciones:** Suma <> 100% -> EXT-06 Rechazar Configuración.
- **Reglas:** RN-13 | **Extends:** EXT-06 Rechazar Configuración Suma Distinta a 100%.

### CU-11: Administrar Catálogos de Servicios y 6 Delegaciones
- **Identificador:** CU-11 | **Actor:** Administrador Central
- **Objetivo:** Administrar datos maestros de Centro, Las Compañías, La Pampa, La Antena, Av. del Mar y Rural.

### CU-12: Auditar Bitácora Inmutable de Eventos
- **Identificador:** CU-12 | **Actor:** Oficial de Seguridad / Auditor
- **Objetivo:** Consultar bitácora inalterable con IP, usuario, fecha y valores JSON previos/nuevos.

---

## Cuadros Estandarizados de Casos de Uso de Extensión (<<extend>>)
- **EXT-01 Notificar Registro Duplicado:** Caso Base CU-02 | Condición: Misma fecha, ítem y solicitante | Resultado: Modal `modal-duplicado` y bloqueo.
- **EXT-02 Gestionar Error de Validación:** Caso Base CU-02/CU-06 | Condición: Campos vacíos | Resultado: Modal `modal-error-validacion`.
- **EXT-03 Exigir Dictamen por Rechazo:** Caso Base CU-04 | Condición: Rechazo sin texto | Resultado: Alerta de fundamentación obligatoria.
- **EXT-04 Bloquear Cuarta Gestión Social:** Caso Base CU-05 | Condición: Contador = 3 | Resultado: Bloqueo de nueva atención (RN-10).
- **EXT-05 Notificar Compromiso Vencido:** Caso Base CU-07 | Condición: Fecha vencida | Resultado: Modal `modal-alerta-vencido` y estilo rojo.
- **EXT-06 Rechazar Configuración Suma <> 100%:** Caso Base CU-10 | Condición: Suma <> 100% | Resultado: Alerta de corrección matemática.
