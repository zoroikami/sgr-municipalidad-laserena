# Sistema de Gestión de Resultados (SGR)
## Ilustre Municipalidad de La Serena - Dirección de Servicios Comunitarios (DISERCO)

![Estado](https://img.shields.io/badge/Evaluaci%C3%B3n-Primera%20Entrega%20(100%20pts)-brightgreen?style=for-the-badge)
![Institución](https://img.shields.io/badge/INACAP-Proyecto%20Integrado-blue?style=for-the-badge)
![MySQL](https://img.shields.io/badge/MySQL-8.0%20(3FN)-orange?style=for-the-badge)
![HTML5/CSS3/JS](https://img.shields.io/badge/Mockup-HTML5%20%2F%20CSS3%20%2F%20JS-yellow?style=for-the-badge)
![Planner](https://img.shields.io/badge/Gesti%C3%B3n-%C3%81gil%20Microsoft%20Planner-blueviolet?style=for-the-badge)

---

## 1. Información Institucional y Académica

- **Institución:** INACAP
- **Carrera:** Analista en Informática / Ingeniería en Informática / Ingeniería en Ciberseguridad
- **Asignatura:** Proyecto Integrado
- **Profesor Guía:** Jorge Cortés
- **Período Académico:** Segundo Semestre 2026
- **Entrega Evaluada:** Primera Evaluación: Análisis y Diseño de Software (Planificación, Requerimientos, Modelado UML, Base de Datos y Mockup Funcional)
- **Calificación Objetivo:** 100 / 100 Puntos

---

## 2. Descripción General del Proyecto

El **Sistema de Gestión de Resultados (SGR)** es una solución de software integral concebida para modernizar, transparentar y controlar el cumplimiento de metas y compromisos vecinales en las **6 Delegaciones Municipales** de la comuna de La Serena:
1. **Delegación Centro** (Casco histórico y comercio comunal)
2. **Delegación Las Compañías** (Mayor densidad poblacional y alta actividad comunitaria)
3. **Delegación La Pampa** (Sectores residenciales consolidados y áreas verdes)
4. **Delegación La Antena - La Florida** (Comités de vivienda y programas sociales)
5. **Delegación Avenida del Mar** (Borde costero turístico y fiscalización de bienes públicos)
6. **Delegación Rural** (Algarrobito, Las Rojas, Lambert, Altovalsol y valles interiores)

### Pilares Funcionales del SGR:
- **Trazabilidad Inalterable de Evidencias:** Cada actividad en terreno genera un código único correlativo (`EVI-2026-XXXX`) respaldado por fotografía obligatoria con georreferenciación.
- **Segregación de Funciones y Control de Calidad:** Bandeja técnica exclusiva para el Verificador Municipal, quien dictamina la aprobación o rechazo fundamentado de las evidencias.
- **Motor Matemático de Semáforo Diario:** Cálculo dinámico de cumplimiento ponderado al 100% y semaforización proporcional (*Verde, Ámbar, Rojo*) evaluada contra los días transcurridos del trimestre.
- **Atención Social Multietapa:** Registro unificado de personas usuarias vulnerables permitiendo concatenar hasta 3 gestiones por beneficiario sin duplicar la ficha (Regla `RN-10`).
- **Tubo de Trabajo y Agenda Colectiva:** Tablero Kanban territorial con 4 estados (*Ingresado, Pendiente, En Proceso, Realizado*) con alertas operativas de compromisos vencidos.
- **Bitácora Inmutable de Auditoría:** Registro de cada transacción con marca de tiempo, IP, usuario y datos previos/nuevos en formato JSON.

---

## 3. Matriz de Entregables y Rúbrica Oficial (100 Puntos)

Todos los artefactos requeridos por la rúbrica institucional se encuentran formalmente construidos y enlazados:

| Criterio Rúbrica | Puntos | Entregable Oficial | Ubicación en el Repositorio |
| :--- | :---: | :--- | :--- |
| **1. Planner / Jira** | 15 pts | Planificación operativa completa en Microsoft Planner con 8 depósitos, 22 tareas con DoD y flujo Kanban. | [`gestion_agil/backlog_planner_sgr.md`](gestion_agil/backlog_planner_sgr.md) |
| **2. Diagrama Requerimientos** | 10 pts | Diagrama jerárquico SysML (Visual Paradigm) y Matriz de Trazabilidad multidimensional. | [`diagramas/diagrama_requerimientos.svg`](diagramas/diagrama_requerimientos.svg)<br>[`diagramas/matriz_trazabilidad.md`](diagramas/matriz_trazabilidad.md) |
| **3. Caso de Uso General** | 10 pts | Modelo UML 2.5 formal con límite del sistema, 6 actores primarios y 1 actor secundario. | [`diagramas/caso_uso_general.svg`](diagramas/caso_uso_general.svg)<br>[`diagramas/caso_uso_general.puml`](diagramas/caso_uso_general.puml) |
| **4. Casos Específicos + Fichas** | 20 pts | 12 Casos de uso detallados individuales en PlantUML + Fichas textuales completas + 8 micro-fichas de extensión. | [`diagramas/casos_uso_detallados/`](diagramas/casos_uso_detallados/)<br>[`especificaciones/fichas_casos_uso.md`](especificaciones/fichas_casos_uso.md) |
| **5. Diagrama de Clases** | 15 pts | Modelo formal de clases UML 2.5: 14 clases de dominio, atributos tipados, visibilidad `+`/`-`/`#`, métodos y multiplicidades. | [`diagramas/diagrama_clases_sgr.svg`](diagramas/diagrama_clases_sgr.svg)<br>[`diagramas/diagrama_clases_sgr.puml`](diagramas/diagrama_clases_sgr.puml) |
| **6. DER MySQL** | 10 pts | Modelo Entidad-Relación relacional normalizado en 3FN para MySQL 8.0 (14 tablas con PKs, FKs y tablas N:M). | [`diagramas/der_mysql_sgr.svg`](diagramas/der_mysql_sgr.svg)<br>[`diagramas/der_mysql_sgr.puml`](diagramas/der_mysql_sgr.puml) |
| **7. Script SQL Ejecutable** | 10 pts | Script MySQL 8.0 `database_sgr.sql` con 17 tablas, restricciones `ON DELETE RESTRICT` y 18 bloques de datos semilla reales. | [`base_datos/database_sgr.sql`](base_datos/database_sgr.sql) |
| **8. Mockup Funcional + Git** | 10 pts | Prototipo web interactivo y responsivo con 10 vistas, cálculo dinámico de semáforos y modales de validación. | [`mockup/`](mockup/) ([`index.html`](mockup/index.html), [`styles.css`](mockup/css/styles.css), [`app.js`](mockup/js/app.js)) |
| **Informe Consolidado** | Requisito | Documento técnico formal unificado con carátula institucional de INACAP y justificación integral. | [`INFORME_PRIMERA_EVALUACION_SGR.md`](INFORME_PRIMERA_EVALUACION_SGR.md)<br>[`INFORME_PRIMERA_EVALUACION_SGR.html`](INFORME_PRIMERA_EVALUACION_SGR.html) |

---

## 4. Estructura de Carpetas del Repositorio

```text
PROYECTO INTEGRADO/
│
├── .gitignore                          # Exclusión de archivos temporales y entornos virtuales
├── README.md                           # Documentación técnica general del repositorio
├── INFORME_PRIMERA_EVALUACION_SGR.md   # Informe técnico consolidado oficial en formato Markdown
├── INFORME_PRIMERA_EVALUACION_SGR.html # Versión HTML imprimible y exportable a PDF
├── generar_informe_html.py             # Script compilador del informe técnico
│
├── gestion_agil/                       # Entregable 1: Planificación Operativa
│   └── backlog_planner_sgr.md          # 8 Depósitos, 22 tareas, DoD, hitos y convención Git
│
├── diagramas/                          # Entregables 2, 3, 5 y 6: Modelado UML y Datos
│   ├── diagrama_requerimientos.puml    # Código fuente SysML / Visual Paradigm
│   ├── diagrama_requerimientos.svg     # Diagrama vectorial en alta definición
│   ├── matriz_trazabilidad.md          # Matriz cruzada (RF, CU, Mockup, Tabla BD, Regla)
│   ├── caso_uso_general.puml           # Diagrama general UML 2.5 con límite del sistema
│   ├── caso_uso_general.svg            # Gráfico vectorial del caso de uso general
│   ├── diagrama_clases_sgr.puml        # Diagrama de clases del dominio (14 clases)
│   ├── diagrama_clases_sgr.svg         # Gráfico vectorial de clases UML
│   ├── der_mysql_sgr.puml              # Modelo Entidad-Relación para MySQL 8.0 en 3FN
│   ├── der_mysql_sgr.svg               # Gráfico vectorial del DER relacional
│   │
│   └── casos_uso_detallados/           # Entregable 4: 12 Casos de Uso Específicos
│       ├── CU-01_autenticacion_acceso.puml
│       ├── CU-02_registrar_actividad_evidencia.puml
│       ├── CU-03_generar_codigo_verificador.puml
│       ├── CU-04_validar_evidencia_fotografica.puml
│       ├── CU-05_registrar_atencion_social_multietapa.puml
│       ├── CU-06_crear_compromiso_agenda_colectiva.puml
│       ├── CU-07_actualizar_estado_compromiso.puml
│       ├── CU-08_calcular_avance_semaforo_diario.puml
│       ├── CU-09_consultar_tablero_delegacion.puml
│       ├── CU-10_configurar_metas_ponderadores_periodo.puml
│       ├── CU-11_administrar_catalogos_servicios.puml
│       └── CU-12_auditoria_trazabilidad_cambios.puml
│
├── especificaciones/                  # Entregable 4: Fichas Textuales
│   └── fichas_casos_uso.md             # 12 Fichas maestras completas + 8 cuadros de extensión
│
├── base_datos/                         # Entregable 7: Persistencia y Script SQL
│   └── database_sgr.sql                # Script ejecutable MySQL 8.0 verificado con seed data
│
└── mockup/                             # Entregable 8: Prototipo Web Funcional Interactivo
    ├── index.html                      # Aplicación SPA con 10 vistas y 7 modales
    ├── README.md                       # Guía específica de arquitectura y navegación
    ├── css/
    │   └── styles.css                  # Sistema de diseño con colores corporativos de La Serena
    ├── js/
    │   ├── data.js                     # Base de datos en memoria y datos semilla comunales
    │   ├── calculations.js             # Motor matemático de avance y semáforos diarios
    │   └── app.js                      # Controlador de eventos, navegación y modales
    └── assets/
        ├── logo_laserena.jpg           # Escudo oficial de la Municipalidad de La Serena
        ├── evidencia_terreno.jpg       # Fotografía de prueba en terreno (Algarrobito)
        └── evidencia_social.jpg        # Fotografía de prueba de gestión social
```

---


---

## 6. Flujo de Trabajo Colaborativo en Git y GitHub (`crear proyecto.pdf`)

El proyecto sigue estrictamente el flujo de trabajo institucional **GitHub Flow**:

### Política de Ramas:
- La rama `main` contiene código de producción estable y verificado.
- Nadie programa directamente sobre `main`.
- Toda nueva característica se desarrolla en una rama vinculada a una tarea de Planner:
  - `feature/SGR-[ID]-[descripcion-corta]`
  - Ejemplo: `feature/SGR-06-codigo-evidencia`
  - Ejemplo: `feature/SGR-12-validacion-verificador`
  - Ejemplo: `feature/SGR-19-semaforo-diario`

### Formato Obligatorio de Commits:
Cada commit se encabeza con el identificador de la tarea de Planner, seguido de una descripción en tiempo imperativo:
- `SGR-01: Inicialización del repositorio institucional y estructura del SGR La Serena`
- `SGR-06: Generación automática de código correlativo único EVI-2026 para actividades`
- `SGR-12: Implementación de visor de evidencias con zoom y dictamen de aprobación`
- `SGR-19: Algoritmo dinámico de cálculo de semáforo proporcional diario`




---

## 7. Segunda Evaluación: Mantenedores, Acceso, Roles y Pruebas

Para la **Segunda Evaluación**, se incorporó la solución operativa integral que cubre el 100% de la pauta y rúbrica oficial:

### Módulos y Pantallas Implementadas:
1. **Acceso al Sistema (Login):** Validación de credenciales institucionales, diferenciación de perfiles y estados de cuenta.
2. **Flujo de Recuperación de Contraseña (3 Pasos):**
   * **Paso 1 (Solicitar Código):** Formulario con respuesta neutra de seguridad institucional.
   * **Paso 2 (Validar Código):** 6 casillas independientes con captura individual, soporte para pegar (paste), expiración de 10 min y límite estricto de 3 intentos fallidos.
   * **Paso 3 (Crear Nueva Clave):** Validación en tiempo real de políticas de complejidad (mínimo 8 caracteres, mayúscula, número y símbolo especial) y retorno al login.
3. **Los Seis Mantenedores (CRUD Completos):**
   * **CRUD Delegaciones:** Código, nombre, dirección, comuna y estado.
   * **CRUD Roles:** Código, nombre, descripción, permisos, alcance y estado.
   * **CRUD Usuarios:** RUT, nombre, correo, rol, delegación asignada y estado.
   * **CRUD Ítems y Metas:** Código, nombre, descripción, unidad de medida, meta y estado.
   * **CRUD Tipo de Atención:** Código, nombre, descripción y estado.
   * **CRUD Sub Atención:** Código, nombre, tipo de atención asociado y estado con validación de integridad referencial.
   * *Cada mantenedor incluye:* Buscador inteligente en tiempo real, filtro por estado, paginación dinámica, modales de Crear/Editar/Ver y botón funcional de **Exportar a Excel (.xlsx)** con SheetJS.
4. **Ingreso de Atención Ciudadana:** Formulario dependiente en cascada (Tipo de Atención $\rightarrow$ Subatención), contexto de delegación bloqueado al usuario activo, responsable y timestamp automáticos, y generación de folio correlativo único (`ATN-2026-XXXX`).
5. **Identidad Visual y Cabecera de Delegación:** Normas gráficas de La Serena (`#8e1525`), logotipo oficial, SweetAlert2 en todas las alertas y distintivo permanente de delegación activa con selector para perfiles comunales.
6. **Demostración de Roles:** Conmutador evaluativo y control estricto de permisos entre Superadministrador, Coordinador, Delegado Municipal y Operador.

### Credenciales de Demostración para el Evaluador:

| Perfil | Nombre | Correo Electrónico | Contraseña | Alcance Autorizado |
| :--- | :--- | :--- | :--- | :--- |
| **Superadministrador** | Harold Concha | `harold.concha@laserena.cl` | `Admin123*` | Todas las delegaciones y todos los mantenedores |
| **Coordinador** | Keoni Vergara | `keoni.vergara@laserena.cl` | `Coord123*` | Supervisión comunal, metas y atenciones |
| **Delegado Municipal** | Claudio Romo | `claudio.romo@laserena.cl` | `Deleg123*` | Delegación Las Compañías (`DEL02`) |
| **Operador / Ventanilla** | Carlos Miranda | `carlos.miranda@laserena.cl` | `Oper123*` | Ingreso de atención en Delegación Centro (`DEL01`) |
| **Consultor** | Luis Ejemplo | `luis@example.test` | `Luis1234*` | Sólo lectura y auditoría |

### Instrucciones de Ejecución Local:

```bash
# 1. Inicializar base de datos SQLite relacional
python server.py --init-db

# 2. Iniciar el servidor SGR (Backend API + Interfaz Web)
python server.py --port 8000

# 3. Acceder en el navegador:
# Portal General:     http://localhost:8000/
# Segunda Evaluación: http://localhost:8000/evaluacion2/index.html
# API Health:         http://localhost:8000/api/health
```

### Instrucciones de Despliegue en AWS EC2:

El repositorio incluye el script automatizado [`deploy_ec2.sh`](deploy_ec2.sh) que instala dependencias y configura un servicio `systemd` en el puerto 80:

```bash
# En la instancia EC2 (Ubuntu o Amazon Linux):
chmod +x deploy_ec2.sh
./deploy_ec2.sh
```

### Plan y Evidencias de Pruebas:
El informe formal y registro de pruebas de estrés (RPS, percentil 95 y matriz de casos de prueba) se encuentra en:
* [`docs/PLAN_DE_PRUEBAS_EVAL2.md`](docs/PLAN_DE_PRUEBAS_EVAL2.md)

---

## 8. Equipo de Desarrollo y Asignación de Roles

| Integrante | Rol en el Proyecto |
| :--- | :--- |
| **Harold Concha** | Desarrollador 1 (Dev 1) - Módulos de Acceso, Auditoría y Seguridad |
| **Keoni Vergara** | Desarrollador 2 (Dev 2) - Mantenedores Maestros, Motor de Datos y Despliegue AWS |
| **Claudio Romo** | Desarrollador 3 (Dev 3) - Atención Ciudadana, Integración UI y Pruebas Funcionales |

---

## 9. Licencia y Derechos Institucionales

Este proyecto ha sido desarrollado exclusivamente con fines académicos para la asignatura **Proyecto Integrado** de la carrera de Informática en **INACAP**, bajo la tutela del docente **Jorge Cortés**.  
Todos los derechos sobre la identidad visual pertenecen a la **Ilustre Municipalidad de La Serena (2026)**.

