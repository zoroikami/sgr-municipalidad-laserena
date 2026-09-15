/**
 * SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - MUNICIPALIDAD DE LA SERENA
 * data.js - Datos semilla y almacenamiento de estado local (localStorage)
 */

const SGR_DEFAULT_DATA = {
    periodoActivo: {
        id: "PER-2026-Q3",
        nombre: "Tercer Trimestre 2026 (Q3)",
        fechaInicio: "2026-07-01",
        fechaTermino: "2026-09-30",
        diasTotales: 91,
        diasTranscurridos: 45,
        metaEsperadaPct: 49.45, // (45 / 91) * 100
        estado: "ACTIVO"
    },
    delegaciones: [
        { id: "DEL-RUR", nombre: "Delegación Rural", encargado: "Ximena Alvarado Morales", zona: "El Romero, Lambert, Algarrobito, Las Rojas", funcionariosCount: 14 },
        { id: "DEL-COM", nombre: "Delegación Las Compañías", encargado: "Patricio Bacho González", zona: "Compañía Alta y Compañía Baja", funcionariosCount: 28 },
        { id: "DEL-PAM", nombre: "Delegación La Pampa", encargado: "Gonzalo Arceu Miranda", zona: "San Joaquín, La Florida Sur, Pampa Baja", funcionariosCount: 19 },
        { id: "DEL-ANT", nombre: "Delegación La Antena - La Florida", encargado: "Arturo Rivera Soto", zona: "La Antena, Coll, La Florida Norte", funcionariosCount: 22 },
        { id: "DEL-CEN", nombre: "Delegación Centro", encargado: "Lorena Casanova Díaz", zona: "Casco Histórico, Balmaceda, Almagro", funcionariosCount: 31 },
        { id: "DEL-MAR", nombre: "Delegación Avenida del Mar", encargado: "Felipe Morales Valenzuela", zona: "Borde Costero, Peñuelas Norte, Cuatro Esquinas", funcionariosCount: 12 }
    ],
    usuarios: [
        {
            id: "USR-001",
            nombre: "Carlos Miranda Vera",
            rut: "15.482.910-3",
            rol: "Funcionario_Territorial",
            rolNombre: "Funcionario Territorial",
            cargo: "Gestor Territorial Comunitario",
            delegacionId: "DEL-RUR",
            delegacionNombre: "Delegación Rural",
            email: "carlos.miranda@laserena.cl",
            avatar: "assets/logo_laserena.jpg",
            diasSinIngreso: 0,
            ultimoIngreso: "2026-08-14"
        },
        {
            id: "USR-002",
            nombre: "Marcela Gómez Pizarro",
            rut: "16.891.432-K",
            rol: "Gestor_Social",
            rolNombre: "Gestora de Asistencia Social",
            cargo: "Gestor Social y Familiar",
            delegacionId: "DEL-COM",
            delegacionNombre: "Delegación Las Compañías",
            email: "marcela.gomez@laserena.cl",
            avatar: "assets/logo_laserena.jpg",
            diasSinIngreso: 1,
            ultimoIngreso: "2026-08-13"
        },
        {
            id: "USR-003",
            nombre: "Roberto Henríquez Plaza",
            rut: "13.782.119-8",
            rol: "Verificador",
            rolNombre: "Supervisor DISERCO / Verificador",
            cargo: "Supervisor de Evidencias y Calidad",
            delegacionId: "DEL-RUR",
            delegacionNombre: "Delegación Rural",
            email: "roberto.henriquez@laserena.cl",
            avatar: "assets/logo_laserena.jpg",
            diasSinIngreso: 0,
            ultimoIngreso: "2026-08-14"
        },
        {
            id: "USR-004",
            nombre: "Ximena Alvarado Morales",
            rut: "12.981.654-2",
            rol: "Delegado",
            rolNombre: "Delegada Municipal",
            cargo: "Delegada Municipal Rural",
            delegacionId: "DEL-RUR",
            delegacionNombre: "Delegación Rural",
            email: "ximena.alvarado@laserena.cl",
            avatar: "assets/logo_laserena.jpg",
            diasSinIngreso: 2,
            ultimoIngreso: "2026-08-12"
        },
        {
            id: "USR-005",
            nombre: "Rodrigo Tapia Santander",
            rut: "11.234.890-1",
            rol: "Administrador",
            rolNombre: "Administrador Central SGR",
            cargo: "Jefe de Planificación y Control de Gestión",
            delegacionId: "DEL-CEN",
            delegacionNombre: "Delegación Centro",
            email: "rodrigo.tapia@laserena.cl",
            avatar: "assets/logo_laserena.jpg",
            diasSinIngreso: 0,
            ultimoIngreso: "2026-08-14"
        }
    ],
    itemsMedicion: [
        // Ítems para Gestor Territorial
        {
            id: "ITM-001",
            cargo: "Gestor Territorial Comunitario",
            nombre: "Reuniones con Juntas de Vecinos y Organizaciones",
            descripcion: "Asambleas vecinales, reuniones con directivas y organizaciones comunitarias",
            ponderacion: 30, // 30%
            metaTrimestral: 18,
            unidad: "Reuniones"
        },
        {
            id: "ITM-002",
            cargo: "Gestor Territorial Comunitario",
            nombre: "Inspecciones de Espacios Públicos y Alumbrado",
            descripcion: "Rondas de fiscalización de luminarias, baches, microbasurales y plazas",
            ponderacion: 25, // 25%
            metaTrimestral: 24,
            unidad: "Inspecciones"
        },
        {
            id: "ITM-003",
            cargo: "Gestor Territorial Comunitario",
            nombre: "Resolución de Solicitudes y Trámites Comunitarios",
            descripcion: "Gestión directa de requerimientos vecinales canalizados en terreno",
            ponderacion: 25, // 25%
            metaTrimestral: 30,
            unidad: "Solicitudes"
        },
        {
            id: "ITM-004",
            cargo: "Gestor Territorial Comunitario",
            nombre: "Compromisos Cumplidos en Agenda Colectiva",
            descripcion: "Tareas comprometidas con fecha límite finalizadas a tiempo (min 80%)",
            ponderacion: 20, // 20% -> Suma = 100%
            metaTrimestral: 15,
            unidad: "Compromisos"
        },
        // Ítems para Gestor Social
        {
            id: "ITM-005",
            cargo: "Gestor Social y Familiar",
            nombre: "Fichas de Asistencia Social Multietapa",
            descripcion: "Diagnósticos familiares y derivación social con seguimiento",
            ponderacion: 35, // 35%
            metaTrimestral: 40,
            unidad: "Atenciones"
        },
        {
            id: "ITM-006",
            cargo: "Gestor Social y Familiar",
            nombre: "Derivaciones a Redes y Programas Intersectoriales",
            descripcion: "Canalización a FOSIS, SENAMA, RSH, subsidios de agua o vivienda",
            ponderacion: 25, // 25%
            metaTrimestral: 25,
            unidad: "Derivaciones"
        },
        {
            id: "ITM-007",
            cargo: "Gestor Social y Familiar",
            nombre: "Entregas de Beneficios y Ayuda Social Paliativa",
            descripcion: "Cajas de alimentos, materiales de emergencia o vales de gas",
            ponderacion: 25, // 25%
            metaTrimestral: 20,
            unidad: "Entregas"
        },
        {
            id: "ITM-008",
            cargo: "Gestor Social y Familiar",
            nombre: "Compromisos Cumplidos en Agenda Colectiva",
            descripcion: "Casos críticos resueltos conforme al plazo acordado",
            ponderacion: 15, // 15% -> Suma = 100%
            metaTrimestral: 15,
            unidad: "Compromisos"
        }
    ],
    actividades: [
        {
            id: "ACT-2026-001",
            codigoEvidencia: "EVI-2026-0741",
            fecha: "2026-08-14",
            funcionarioId: "USR-001",
            funcionarioNombre: "Carlos Miranda Vera",
            delegacionId: "DEL-RUR",
            itemId: "ITM-002",
            itemNombre: "Inspecciones de Espacios Públicos y Alumbrado",
            descripcion: "Inspección técnica de luminarias LED dañadas y bacheo en Plaza Central de Algarrobito tras temporal costero.",
            accionEjecutada: "Levantamiento topográfico visual, catastro de 4 postes sin suministro y derivación directa a cuadrilla de alumbrado público.",
            contactoNombre: "Don Hernán Castillo Peña (Presidente JJ.VV Algarrobito)",
            contactoTelefono: "+56 9 8451 2239",
            ingresoAgenda: true,
            estadoValidacion: "APROBADA", // APROBADA, PENDIENTE, RECHAZADA
            verificadorId: "USR-003",
            verificadorNombre: "Roberto Henríquez Plaza",
            fechaValidacion: "2026-08-14 11:30",
            observacionVerificador: "Evidencia fotográfica nítida, poste rotulado e informe de derivación adjunto conforme a protocolo.",
            archivoEvidencia: "assets/evidencia_terreno.jpg",
            georreferencia: "Plaza Central Algarrobito, Ruta D-41, La Serena"
        },
        {
            id: "ACT-2026-002",
            codigoEvidencia: "EVI-2026-0742",
            fecha: "2026-08-14",
            funcionarioId: "USR-002",
            funcionarioNombre: "Marcela Gómez Pizarro",
            delegacionId: "DEL-COM",
            itemId: "ITM-005",
            itemNombre: "Fichas de Asistencia Social Multietapa",
            descripcion: "Atención y diagnóstico socioeconómico urgente a adulto mayor en situación de vulnerabilidad por corte de suministro de agua.",
            accionEjecutada: "Aplicación de ficha social RSH, solicitud de subsidio municipal provisorio y coordinación de visita domiciliaria.",
            contactoNombre: "Sra. Teresa Araya Godoy",
            contactoTelefono: "+56 9 9231 4455",
            ingresoAgenda: true,
            estadoValidacion: "PENDIENTE",
            verificadorId: null,
            verificadorNombre: null,
            fechaValidacion: null,
            observacionVerificador: null,
            archivoEvidencia: "assets/evidencia_social.jpg",
            georreferencia: "Delegación Las Compañías, Av. Viña del Mar #450"
        },
        {
            id: "ACT-2026-003",
            codigoEvidencia: "EVI-2026-0738",
            fecha: "2026-08-13",
            funcionarioId: "USR-001",
            funcionarioNombre: "Carlos Miranda Vera",
            delegacionId: "DEL-RUR",
            itemId: "ITM-001",
            itemNombre: "Reuniones con Juntas de Vecinos y Organizaciones",
            descripcion: "Mesa de trabajo y asamblea comunitaria sobre proyectos de agua potable rural en El Romero.",
            accionEjecutada: "Presentación del calendario de camiones aljibes y toma de compromisos para limpieza de fosas comunitarias.",
            contactoNombre: "Margarita Tapia Cortés (Tesorera JJ.VV El Romero)",
            contactoTelefono: "+56 9 7812 3341",
            ingresoAgenda: true,
            estadoValidacion: "APROBADA",
            verificadorId: "USR-003",
            verificadorNombre: "Roberto Henríquez Plaza",
            fechaValidacion: "2026-08-13 16:45",
            observacionVerificador: "Acta de asamblea firmada por 22 asistentes, fotografías de concurrencia validadas.",
            archivoEvidencia: "assets/evidencia_terreno.jpg",
            georreferencia: "Sede Social El Romero, Sector Los Aromos s/n"
        },
        {
            id: "ACT-2026-004",
            codigoEvidencia: "EVI-2026-0735",
            fecha: "2026-08-12",
            funcionarioId: "USR-001",
            funcionarioNombre: "Carlos Miranda Vera",
            delegacionId: "DEL-RUR",
            itemId: "ITM-003",
            itemNombre: "Resolución de Solicitudes y Trámites Comunitarios",
            descripcion: "Entrega de certificado de residencia para postulación a subsidio habitacional en Lambert.",
            accionEjecutada: "Verificación de documentación en terreno y timbre formal de delegación municipal.",
            contactoNombre: "Juan Carlos Pavez",
            contactoTelefono: "+56 9 6652 1190",
            ingresoAgenda: false,
            estadoValidacion: "APROBADA",
            verificadorId: "USR-003",
            verificadorNombre: "Roberto Henríquez Plaza",
            fechaValidacion: "2026-08-12 14:10",
            observacionVerificador: "Folio verificado en libro de partes.",
            archivoEvidencia: "assets/evidencia_terreno.jpg",
            georreferencia: "Oficina Enlace Lambert"
        },
        {
            id: "ACT-2026-005",
            codigoEvidencia: "EVI-2026-0731",
            fecha: "2026-08-11",
            funcionarioId: "USR-001",
            funcionarioNombre: "Carlos Miranda Vera",
            delegacionId: "DEL-RUR",
            itemId: "ITM-002",
            itemNombre: "Inspecciones de Espacios Públicos y Alumbrado",
            descripcion: "Revisión de despeje de ramas sobre tendido eléctrico en Quebrada de Talca.",
            accionEjecutada: "Toma de fotografía sin orden formal emitida.",
            contactoNombre: "Vecino no identificado",
            contactoTelefono: "Sin registro",
            ingresoAgenda: false,
            estadoValidacion: "RECHAZADA",
            verificadorId: "USR-003",
            verificadorNombre: "Roberto Henríquez Plaza",
            fechaValidacion: "2026-08-11 18:20",
            observacionVerificador: "Fotografía borrosa, no permite identificar ubicación ni poste. Falta contacto formal del solicitante.",
            archivoEvidencia: "assets/evidencia_terreno.jpg",
            georreferencia: "Quebrada de Talca s/n"
        }
    ],
    agendaColectiva: [
        {
            id: "TUB-2026-01",
            origen: "Inspección luminarias Algarrobito",
            solicitante: "Don Hernán Castillo Peña (JJ.VV Algarrobito)",
            territorio: "Algarrobito - Ruta D-41",
            responsableId: "USR-001",
            responsableNombre: "Carlos Miranda Vera",
            areaApoyo: "Cuadrilla Alumbrado DISERCO",
            fechaCompromiso: "2026-08-20",
            estado: "EN_PROCESO", // INGRESADO, PENDIENTE, EN_PROCESO, REALIZADO
            observaciones: "Cuadrilla programada para turno del jueves 20 a primera hora.",
            prioridad: "ALTA",
            fechaIngreso: "2026-08-14"
        },
        {
            id: "TUB-2026-02",
            origen: "Asamblea El Romero APR",
            solicitante: "JJ.VV El Romero",
            territorio: "El Romero",
            responsableId: "USR-001",
            responsableNombre: "Carlos Miranda Vera",
            areaApoyo: "Departamento de Recursos Hídricos",
            fechaCompromiso: "2026-08-10", // VENCIDO
            estado: "PENDIENTE",
            observaciones: "Retraso en proveedor de fosa móvil. Se debe reprogramar e informar a la directiva comunitaria.",
            prioridad: "CRITICA",
            fechaIngreso: "2026-08-01"
        },
        {
            id: "TUB-2026-03",
            origen: "Demanda de desmalezado",
            solicitante: "Club Adulto Mayor Las Rojas",
            territorio: "Las Rojas",
            responsableId: "USR-001",
            responsableNombre: "Carlos Miranda Vera",
            areaApoyo: "Medio Ambiente y Ornato",
            fechaCompromiso: "2026-08-25",
            estado: "INGRESADO",
            observaciones: "Ingresado en plataforma, pendiente asignación de maquinaria.",
            prioridad: "MEDIA",
            fechaIngreso: "2026-08-14"
        },
        {
            id: "TUB-2026-04",
            origen: "Reparación juego infantil Plaza Altovalsol",
            solicitante: "Centro de Madres Altovalsol",
            territorio: "Altovalsol",
            responsableId: "USR-001",
            responsableNombre: "Carlos Miranda Vera",
            areaApoyo: "Taller Municipal de Obras",
            fechaCompromiso: "2026-08-08",
            estado: "REALIZADO",
            observaciones: "Juegos soldados y pintados con pintura anticorrosiva. Acta de conformidad firmada.",
            prioridad: "ALTA",
            fechaIngreso: "2026-08-02"
        },
        {
            id: "TUB-2026-05",
            origen: "Subsidio de agua potable de emergencia",
            solicitante: "Sra. Teresa Araya Godoy",
            territorio: "Las Compañías",
            responsableId: "USR-002",
            responsableNombre: "Marcela Gómez Pizarro",
            areaApoyo: "DIDECO - Área Social",
            fechaCompromiso: "2026-08-18",
            estado: "EN_PROCESO",
            observaciones: "Carpeta en revisión de asistente social jefe para aprobación de decreto exento.",
            prioridad: "ALTA",
            fechaIngreso: "2026-08-14"
        }
    ],
    atencionesSociales: [
        {
            id: "SOC-2026-0089",
            rutBeneficiario: "5.892.311-2",
            nombreBeneficiario: "Teresa del Carmen Araya Godoy",
            edad: 74,
            direccion: "Pasaje Los Claveles #214, Las Compañías",
            telefono: "+56 9 9231 4455",
            tramoRSH: "40% Menor Ingreso",
            responsableId: "USR-002",
            responsableNombre: "Marcela Gómez Pizarro",
            gestiones: [
                {
                    etapa: 1,
                    nombreEtapa: "Diagnóstico y Apertura de Ficha",
                    fecha: "2026-08-05",
                    profesional: "Marcela Gómez Pizarro",
                    detalle: "Entrevista presencial en delegación. Se constata situación de abandono parcial y deuda de servicios básicos de $142.000.",
                    resultado: "Ficha social aperturada y calificada para subsidio municipal de urgencia."
                },
                {
                    etapa: 2,
                    nombreEtapa: "Derivación e Informe Socioeconómico",
                    fecha: "2026-08-10",
                    profesional: "Marcela Gómez Pizarro",
                    detalle: "Envío de informe social digital a Aguas del Valle y DIDECO central para convenio social preferente.",
                    resultado: "Convenio aprobado, subsidio del 70% de la cuenta concedido por 6 meses."
                },
                {
                    etapa: 3,
                    nombreEtapa: "Entrega de Ayuda Directa y Cierre",
                    fecha: "2026-08-14",
                    profesional: "Marcela Gómez Pizarro",
                    detalle: "Entrega de caja de alimentos para adulto mayor y vale de recarga de gas de 15kg.",
                    resultado: "Beneficio recibido conforme con firma de comprobante. Caso en seguimiento preventivo."
                }
            ]
        },
        {
            id: "SOC-2026-0092",
            rutBeneficiario: "12.445.890-4",
            nombreBeneficiario: "Manuel Segundo Rojas Pizarro",
            edad: 52,
            direccion: "Callejón El Arrayán #12, Lambert",
            telefono: "+56 9 8122 6601",
            tramoRSH: "60% Vulnerabilidad",
            responsableId: "USR-002",
            responsableNombre: "Marcela Gómez Pizarro",
            gestiones: [
                {
                    etapa: 1,
                    nombreEtapa: "Diagnóstico y Apertura de Ficha",
                    fecha: "2026-08-12",
                    profesional: "Marcela Gómez Pizarro",
                    detalle: "Ingreso por pérdida de empleo y filtraciones graves en techumbre tras lluvias.",
                    resultado: "Calificado para entrega de rollos de fieltro y planchas de zinc de emergencia."
                }
            ]
        }
    ],
    auditoria: [
        {
            id: "AUD-001",
            fecha: "2026-08-14 11:30:15",
            usuario: "Roberto Henríquez Plaza (Verificador)",
            accion: "APROBAR_EVIDENCIA",
            entidad: "Actividad EVI-2026-0741",
            valorAnterior: "Estado: PENDIENTE",
            valorNuevo: "Estado: APROBADA (Incrementa avance ITM-002 de Carlos Miranda)"
        },
        {
            id: "AUD-002",
            fecha: "2026-08-14 09:15:02",
            usuario: "Carlos Miranda Vera (Funcionario)",
            accion: "CREAR_ACTIVIDAD",
            entidad: "Actividad EVI-2026-0741",
            valorAnterior: "NULL",
            valorNuevo: "Registro actividad en Plaza Algarrobito"
        },
        {
            id: "AUD-003",
            fecha: "2026-08-11 18:20:44",
            usuario: "Roberto Henríquez Plaza (Verificador)",
            accion: "RECHAZAR_EVIDENCIA",
            entidad: "Actividad EVI-2026-0731",
            valorAnterior: "Estado: PENDIENTE",
            valorNuevo: "Estado: RECHAZADA (Motivo: Fotografía borrosa y falta contacto)"
        },
        {
            id: "AUD-004",
            fecha: "2026-07-01 08:00:00",
            usuario: "Rodrigo Tapia Santander (Admin)",
            accion: "APERTURA_PERIODO",
            entidad: "Periodo PER-2026-Q3",
            valorAnterior: "PER-2026-Q2 CERRADO",
            valorNuevo: "PER-2026-Q3 ACTIVO (91 días computables)"
        }
    ]
};

class SGRStorage {
    constructor() {
        this.STORAGE_KEY = "SGR_MUNICIPALIDAD_LASERENA_DB_V1";
        this.init();
    }

    init() {
        if (!localStorage.getItem(this.STORAGE_KEY)) {
            this.resetToDefaults();
        }
    }

    getData() {
        try {
            const raw = localStorage.getItem(this.STORAGE_KEY);
            return raw ? JSON.parse(raw) : SGR_DEFAULT_DATA;
        } catch (e) {
            console.error("Error leyendo localStorage, usando defaults", e);
            return SGR_DEFAULT_DATA;
        }
    }

    saveData(data) {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
        } catch (e) {
            console.error("Error guardando en localStorage", e);
        }
    }

    resetToDefaults() {
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(SGR_DEFAULT_DATA));
        return SGR_DEFAULT_DATA;
    }

    // Métodos para Actividades
    getActividades(funcionarioId = null) {
        const data = this.getData();
        if (funcionarioId) {
            return data.actividades.filter(a => a.funcionarioId === funcionarioId);
        }
        return data.actividades;
    }

    addActividad(actividad) {
        const data = this.getData();
        data.actividades.unshift(actividad);
        
        // Registrar en auditoria
        data.auditoria.unshift({
            id: "AUD-" + Date.now().toString().slice(-6),
            fecha: new Date().toISOString().replace("T", " ").slice(0, 19),
            usuario: actividad.funcionarioNombre,
            accion: "CREAR_ACTIVIDAD",
            entidad: `Actividad ${actividad.codigoEvidencia}`,
            valorAnterior: "NULL",
            valorNuevo: `Ingreso actividad: ${actividad.itemNombre}`
        });

        this.saveData(data);
        return actividad;
    }

    validarEvidencia(actividadId, decision, observacion, verificador) {
        const data = this.getData();
        const act = data.actividades.find(a => a.id === actividadId);
        if (!act) return null;

        const estadoAnterior = act.estadoValidacion;
        act.estadoValidacion = decision; // "APROBADA" o "RECHAZADA"
        act.verificadorId = verificador.id;
        act.verificadorNombre = verificador.nombre;
        act.observacionVerificador = observacion;
        act.fechaValidacion = new Date().toISOString().replace("T", " ").slice(0, 16);

        data.auditoria.unshift({
            id: "AUD-" + Date.now().toString().slice(-6),
            fecha: new Date().toISOString().replace("T", " ").slice(0, 19),
            usuario: verificador.nombre,
            accion: decision === "APROBADA" ? "APROBAR_EVIDENCIA" : "RECHAZAR_EVIDENCIA",
            entidad: `Actividad ${act.codigoEvidencia}`,
            valorAnterior: `Estado: ${estadoAnterior}`,
            valorNuevo: `Estado: ${decision} (${observacion})`
        });

        this.saveData(data);
        return act;
    }

    // Métodos para Agenda Colectiva
    getAgenda(delegacionId = null) {
        const data = this.getData();
        return data.agendaColectiva;
    }

    addCompromiso(compromiso) {
        const data = this.getData();
        data.agendaColectiva.unshift(compromiso);
        this.saveData(data);
        return compromiso;
    }

    updateEstadoCompromiso(compromisoId, nuevoEstado) {
        const data = this.getData();
        const comp = data.agendaColectiva.find(c => c.id === compromisoId);
        if (comp) {
            comp.estado = nuevoEstado;
            this.saveData(data);
        }
        return comp;
    }

    // Métodos para Atención Social
    getAtenciones() {
        return this.getData().atencionesSociales;
    }

    addGestionSocial(casoId, nuevaGestion) {
        const data = this.getData();
        const caso = data.atencionesSociales.find(c => c.id === casoId);
        if (caso) {
            if (caso.gestiones.length >= 3) {
                throw new Error("Regla RN-012: Un caso social admite un máximo de 3 gestiones relacionadas.");
            }
            caso.gestiones.push(nuevaGestion);
            this.saveData(data);
        }
        return caso;
    }
}

// Instancia global
window.sgrStorage = new SGRStorage();
