# Matriz de Requerimientos y Trazabilidad Transversal
## Sistema de Gestión de Resultados (SGR) - Ilustre Municipalidad de La Serena

| ID | Nombre Requerimiento | Actor Principal | Módulo SGR | Caso de Uso | Pantalla Mockup | Tabla BD MySQL | Tarea Planner | Regla de Negocio |
| :---: | :--- | :--- | :--- | :---: | :--- | :--- | :---: | :---: |
| **RF-01** | Autenticación y control de acceso | Todos los funcionarios | Seguridad / Acceso | `CU-01` | Header institucional | `usuario`, `usuario_rol`, `rol` | SGR-03 | RN-01 |
| **RF-02** | Selector y cambio de rol activo | Administrador / Evaluador | Seguridad / Acceso | `CU-01` | Selector en barra superior | `rol`, `cargo` | SGR-01 | RN-01 |
| **RF-03** | Asignación territorial a delegación | Administrador / DISERCO | Gestión Territorial | `CU-01`, `CU-11` | Header / Configuración | `delegacion`, `usuario` | SGR-04 | RN-02 |
| **RF-04** | Filtro dinámico de ítems por cargo | Funcionario Territorial | Registro Actividades | `CU-02` | Vista `view-actividades` | `meta_item`, `item_medicion` | SGR-05 | RN-03 |
| **RF-05** | Generación de código EVI-2026-XXXX | Sistema SGR | Registro Actividades | `CU-03` | Vista `view-actividades` | `evidencia`, `actividad` | SGR-06 | RN-04 |
| **RF-06** | Carga de fotografía con georreferencia | Funcionario Territorial | Registro Actividades | `CU-02` | Vista `view-actividades` | `evidencia` | SGR-07 | RN-05 |
| **RF-07** | Detección de registro duplicado | Sistema SGR | Registro Actividades | `CU-02`, ext. `EXT-01` | Modal `modal-duplicado` | `actividad` | SGR-08 | RN-06 |
| **RF-08** | Validación de campos obligatorios | Sistema SGR | Registro Actividades | `CU-02`, ext. `EXT-02` | Modal `modal-error-validacion` | `actividad` | SGR-09 | RN-07 |
| **RF-09** | Bandeja de evidencias pendientes | Verificador Técnico | Control de Calidad | `CU-04` | Vista `view-validacion` | `evidencia`, `actividad` | SGR-10 | RN-08 |
| **RF-10** | Visor de imagen en alta resolución | Verificador Técnico | Control de Calidad | `CU-04` | Modal `modal-evidencia` | `evidencia` | SGR-11 | RN-08 |
| **RF-11** | Aprobación técnica de evidencia | Verificador Técnico | Control de Calidad | `CU-04` | Modal `modal-evidencia` | `validacion_evidencia`, `evidencia` | SGR-12 | RN-08 |
| **RF-12** | Rechazo con dictamen obligatorio | Verificador Técnico | Control de Calidad | `CU-04`, ext. `EXT-03` | Modal `modal-evidencia` | `validacion_evidencia`, `evidencia` | SGR-12 | RN-08 |
| **RF-13** | Registro de beneficiario social único | Gestor Social | Atención Social | `CU-05` | Vista `view-social` | `persona_usuaria` | SGR-13 | RN-09 |
| **RF-14** | Concatenación de hasta 3 gestiones | Gestor Social | Atención Social | `CU-05` | Modal `modal-caso-social` | `atencion_social` | SGR-14 | RN-10 |
| **RF-15** | Bloqueo de cuarta gestión en período | Sistema SGR | Atención Social | `CU-05`, ext. `EXT-04` | Modal `modal-caso-social` | `atencion_social` | SGR-14 | RN-10 |
| **RF-16** | Línea de tiempo de intervenciones | Gestor Social / Delegado | Atención Social | `CU-05` | Modal `modal-caso-social` | `atencion_social` | SGR-14 | RN-10 |
| **RF-17** | Creación de compromiso territorial | Delegado / Funcionario | Agenda Colectiva | `CU-06` | Modal `modal-nuevo-compromiso` | `compromiso_agenda` | SGR-16 | RN-11 |
| **RF-18** | Flujo Kanban de 4 estados | Funcionario / Delegado | Agenda Colectiva | `CU-07` | Vista `view-agenda` | `compromiso_agenda` | SGR-15 | RN-11 |
| **RF-19** | Alerta de compromisos vencidos | Sistema SGR | Agenda Colectiva | `CU-07`, ext. `EXT-05` | Modal `modal-alerta-vencido` | `compromiso_agenda` | SGR-17 | RN-12 |
| **RF-20** | Reasignación de compromiso | Delegado Municipal | Agenda Colectiva | `CU-07` | Vista `view-agenda` | `compromiso_agenda` | SGR-15 | RN-11 |
| **RF-21** | Cálculo ponderado al 100% | Sistema SGR | Motor de Cálculo | `CU-08` | Vista `view-ficha` / `view-resumen` | `meta_item`, `actividad` | SGR-18 | RN-13 |
| **RF-22** | Semáforo proporcional diario | Sistema SGR | Motor de Cálculo | `CU-08` | Vista `view-ficha` / `view-semaforo` | `indicador_desempeno` | SGR-19 | RN-13 |
| **RF-23** | Tablero resumen de delegación | Delegado Municipal | Panel Resumen | `CU-09` | Vista `view-resumen` | `usuario`, `indicador_desempeno` | SGR-20 | RN-13 |
| **RF-24** | Gráficos estadísticos y radar | Delegado / DISERCO | Panel Resumen | `CU-09` | Vista `view-resumen` (Chart.js) | `indicador_desempeno` | SGR-20 | RN-13 |
| **RF-25** | Buscador omnibox multicriterio | Todos los perfiles | Búsqueda Global | `CU-04`, `CU-09` | Modal `modal-search` | `actividad`, `evidencia` | SGR-01 | RN-01 |
| **RF-26** | Parametrización de período y metas | Administrador Central | Configuración | `CU-10` | Vista `view-config` | `periodo_medicion`, `meta_item` | SGR-21 | RN-13 |
| **RF-27** | Validación de ponderación al 100% | Sistema SGR | Configuración | `CU-10`, ext. `EXT-06` | Vista `view-config` | `meta_item` | SGR-21 | RN-13 |
| **RF-28** | Catálogo de servicios comunitarios | Administrador Central | Configuración | `CU-11` | Vista `view-config` | `item_medicion` | SGR-21 | RN-03 |
| **RF-29** | Bitácora inmutable de auditoría | Sistema SGR | Auditoría / Seguridad | `CU-12` | Vista `view-auditoria` | `registro_auditoria` | SGR-22 | RN-01 |
