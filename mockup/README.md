# Sistema de Gestión de Resultados (SGR) - Ilustre Municipalidad de La Serena
## Prototipo Funcional de Alta Fidelidad (Mockup Interactivo)

Este repositorio contiene el prototipo web interactivo del **Sistema de Gestión de Resultados (SGR)** desarrollado para la **Ilustre Municipalidad de La Serena**, correspondiente a la entrega de la **Primera Evaluación de Análisis y Diseño de Software (INACAP)**.

---

## 1. Descripción del Proyecto

El SGR es una plataforma tecnológica diseñada para ordenar, registrar, medir y controlar la gestión operativa y comunitaria en las seis delegaciones municipales de La Serena (*Rural, Las Compañías, La Pampa, La Antena-La Florida, Centro y Avenida del Mar*). 

El sistema reemplaza las planillas dispersas por una arquitectura centralizada que vincula:
- **Actividades en terreno:** Con código de evidencia único e inmutable (`EVI-2026-XXXX`).
- **Verificación técnica DISERCO:** Validación de evidencias fotográficas para otorgar puntos de avance.
- **Agenda Colectiva (Tubo de Trabajo):** Seguimiento de compromisos comunitarios con un umbral mínimo de cumplimiento exigido del **80%**.
- **Semáforo Diario de Desempeño:** Cálculo matemático del avance real vs la meta acumulada esperada según los días transcurridos del período trimestral.
- **Atención Social Multietapa:** Gestión de hasta 3 gestiones por persona sin duplicación de ficha.

---

## 2. Tecnologías Utilizadas

- **Estructura:** HTML5 Semántico y Accesible.
- **Estilos:** Vanilla CSS3 con diseño responsivo, variables CSS dinámicas (CSS Custom Properties), efectos de cristal (Glassmorphism), micro-animaciones y paleta cromática oficial de La Serena (*Navy Blue #0f2744* y *Dorado #d69e2e*).
- **Tipografía:** Google Fonts (*Outfit* para títulos institucionales y *Plus Jakarta Sans* para lectura técnica).
- **Lógica e Interacción:** JavaScript Modular ES6+ nativo (SPA - Single Page Application con enrutamiento de vistas sin recarga).
- **Visualización de Datos:** [Chart.js](https://www.chartjs.org/) (v4) para gráficos comparativos de funcionarios y diagramas de estado de compromisos.
- **Iconografía:** [Lucide Icons](https://lucide.dev/) para interfaces modernas y limpias.
- **Persistencia Local:** `localStorage` con inicialización de datos semilla comunales reales y botón de reseteo rápido.

---

## 3. Instrucciones de Ejecución

### Opción 1: Ejecución Directa en el Navegador (Sin dependencias)
1. Abra el archivo `mockup/index.html` (o `mockup.html` en la raíz) haciendo doble clic en cualquier navegador moderno (*Google Chrome, Microsoft Edge, Mozilla Firefox o Safari*).
2. La aplicación cargará automáticamente con datos de demostración pre-configurados.

### Opción 2: Servidor Local (Recomendado para desarrollo)
Puede ejecutar un servidor web ligero con Python o Node.js:
```bash
# Con Python 3
python -m http.server 8000

# Abrir en el navegador:
# http://localhost:8000/mockup/
```

---

## 4. Guía de Recorrido y Demostración de Requisitos (Rúbrica)

| Pantalla / Módulo | Funcionalidad Clave | Casos de Uso / Reglas Asociadas |
| :--- | :--- | :--- |
| **Mi Desempeño (Ficha)** | Cálculo de % de cumplimiento por ítem, avance ponderado (máx 150%) y semáforo diario dinámico (Verde/Ámbar/Rojo). | CU-08, RN-001, RN-004, RN-005, RN-007, RN-008 |
| **Registro de Actividades** | Formulario oficial (8.1), generación de código correlativo único (`EVI-2026-XXXX`), carga de foto y vinculación a agenda. | CU-02, RN-010, RF-009, RF-010 |
| **Bandeja de Verificación** | Visor de fotografía en alta definición, dictamen técnico (Aprobar/Rechazar) y recálculo instantáneo de avance. | CU-04, RN-009, RF-014, CA-01, CA-02 |
| **Agenda Colectiva (Kanban)** | Tablero de 4 estados (*Ingresado, Pendiente, En Proceso, Realizado*), alerta de compromisos vencidos y control de umbral 80%. | CU-06, CU-07, RN-006, CA-03 |
| **Tablero Delegación** | Métricas consolidadas, semáforos de equipo, comparativa gráfica con Chart.js y tabla de últimos ingresos. | CU-09, RF-024, RF-026 |
| **Atención Social** | Visualizador de ficha social con seguimiento de hasta 3 gestiones por persona sin duplicación de registro. | CU-05, RN-012, HU-03, CA-04 |
| **Monitor Semáforo** | Simulador en tiempo real con controles deslizantes para días transcurridos y avance porcentual. | CU-08, RN-007, RN-008 |
| **Modales de Excepción** | Modales funcionales de: Actividad duplicada (CU-07), Error de validación (CU-08/09) y Compromiso vencido (CA-03). | CU-07, CU-08, CU-09, CA-03 |

---

## 5. Control de Roles y Perfiles Disponibles

En la barra superior (Top Navbar), el selector **"Cambiar Usuario"** permite alternar en cualquier momento entre:
1. **Carlos Miranda Vera:** Funcionario Territorial (Delegación Rural).
2. **Marcela Gómez Pizarro:** Gestora Social (Delegación Las Compañías).
3. **Roberto Henríquez Plaza:** Supervisor DISERCO / Verificador de Evidencias.
4. **Ximena Alvarado Morales:** Delegada Municipal Rural.
5. **Rodrigo Tapia Santander:** Administrador Central SGR (Control de Gestión).

---

## 6. Integración con Git

El proyecto se encuentra versionado localmente bajo Git, con una estructura modular que separa presentación (`css/`), lógica (`js/`) y recursos visuales (`assets/`).
