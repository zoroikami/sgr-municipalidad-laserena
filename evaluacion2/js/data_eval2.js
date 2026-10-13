/**
 * SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - MUNICIPALIDAD DE LA SERENA
 * data_eval2.js - Capa de Datos, Sincronización REST / LocalStorage y Exportación Excel
 * Autores: Harold Concha, Keoni Vergara, Claudio Romo | INACAP
 */

const SGR_INITIAL_DATA = {
    delegaciones: [
        { id: 1, codigo: "DEL01", nombre: "Centro", direccion: "Los Carrera 301, Casco Histórico", comuna: "La Serena", estado: "Activa" },
        { id: 2, codigo: "DEL02", nombre: "Norte (Las Compañías)", direccion: "Esmeralda 1023, Compañía Baja", comuna: "La Serena", estado: "Activa" },
        { id: 3, codigo: "DEL03", nombre: "Sur (La Pampa)", direccion: "Gabriel González Videla 2100", comuna: "La Serena", estado: "Activa" },
        { id: 4, codigo: "DEL04", nombre: "La Antena - La Florida", direccion: "18 de Septiembre 450", comuna: "La Serena", estado: "Activa" },
        { id: 5, codigo: "DEL05", nombre: "Rural", direccion: "Ruta 41 Km 15, Algarrobito", comuna: "La Serena", estado: "Activa" },
        { id: 6, codigo: "DEL06", nombre: "Avenida del Mar", direccion: "Av. del Mar 2200", comuna: "La Serena", estado: "Inactiva" }
    ],

    roles: [
        { id: 1, codigo: "ROL01", nombre: "Superadministrador", descripcion: "Acceso total institucional a todos los módulos y auditoría general", permisos: "total", alcance: "Autorizado Comunal", estado: "Activo" },
        { id: 2, codigo: "ROL02", nombre: "Coordinador", descripcion: "Supervisión general de metas, gestión territorial y reportes comunales", permisos: "coordinacion", alcance: "Comunal", estado: "Activo" },
        { id: 3, codigo: "ROL03", nombre: "Delegado Municipal", descripcion: "Administración local de la delegación asignada y atención ciudadana", permisos: "delegacion", alcance: "Delegación", estado: "Activo" },
        { id: 4, codigo: "ROL04", nombre: "Operador / Funcionario", descripcion: "Ingreso y atención directa de vecinos en ventanilla territorial", permisos: "operador", alcance: "Ventanilla", estado: "Activo" },
        { id: 5, codigo: "ROL05", nombre: "Consultor", descripcion: "Acceso de sólo lectura para seguimiento, auditoría y control", permisos: "lectura", alcance: "Lectura", estado: "Activo" }
    ],

    usuarios: [
        { id: 1, rut: "12.345.678-5", nombre: "Harold Concha", email: "harold.concha@laserena.cl", rol_codigo: "ROL01", rol_nombre: "Superadministrador", delegacion_codigo: "DEL01", delegacion_nombre: "Centro", estado: "Activo", delegaciones_autorizadas: ["DEL01", "DEL02", "DEL03", "DEL04", "DEL05", "DEL06"] },
        { id: 2, rut: "15.482.910-3", nombre: "Keoni Vergara", email: "keoni.vergara@laserena.cl", rol_codigo: "ROL02", rol_nombre: "Coordinador", delegacion_codigo: "DEL01", delegacion_nombre: "Centro", estado: "Activo", delegaciones_autorizadas: ["DEL01", "DEL02", "DEL03", "DEL04", "DEL05", "DEL06"] },
        { id: 3, rut: "14.882.340-K", nombre: "Claudio Romo", email: "claudio.romo@laserena.cl", rol_codigo: "ROL03", rol_nombre: "Delegado Municipal", delegacion_codigo: "DEL02", delegacion_nombre: "Norte (Las Compañías)", estado: "Activo", delegaciones_autorizadas: ["DEL02"] },
        { id: 4, rut: "16.891.432-K", nombre: "Carlos Miranda", email: "carlos.miranda@laserena.cl", rol_codigo: "ROL04", rol_nombre: "Operador / Funcionario", delegacion_codigo: "DEL01", delegacion_nombre: "Centro", estado: "Activo", delegaciones_autorizadas: ["DEL01"] },
        { id: 5, rut: "17.234.567-8", nombre: "Ana Ejemplo", email: "ana@example.test", rol_codigo: "ROL04", rol_nombre: "Operador / Funcionario", delegacion_codigo: "DEL01", delegacion_nombre: "Centro", estado: "Activo", delegaciones_autorizadas: ["DEL01"] },
        { id: 6, rut: "18.345.678-9", nombre: "Luis Ejemplo", email: "luis@example.test", rol_codigo: "ROL05", rol_nombre: "Consultor", delegacion_codigo: "DEL01", delegacion_nombre: "Centro", estado: "Activo", delegaciones_autorizadas: ["DEL01"] },
        { id: 7, rut: "19.456.789-0", nombre: "Sara Ejemplo", email: "sara@example.test", rol_codigo: "ROL04", rol_nombre: "Operador / Funcionario", delegacion_codigo: "DEL02", delegacion_nombre: "Norte (Las Compañías)", estado: "Activo", delegaciones_autorizadas: ["DEL02"] },
        { id: 8, rut: "20.543.210-9", nombre: "KeoniPruebas", email: "keonijolievergara@gmail.com", password: "keoni123!", password_hash: "keoni123!", rol_codigo: "ROL01", rol_nombre: "Superadministrador", delegacion_codigo: "DEL01", delegacion_nombre: "Centro", estado: "Activo", delegaciones_autorizadas: ["DEL01", "DEL02", "DEL03", "DEL04", "DEL05", "DEL06"] },
        { id: 9, rut: "21.654.321-0", nombre: "Keoni Vergara Admin", email: "keonissjskr@gmail.com", password: "keoni123!", password_hash: "keoni123!", rol_codigo: "ROL01", rol_nombre: "Superadministrador", delegacion_codigo: "DEL01", delegacion_nombre: "Centro", estado: "Activo", delegaciones_autorizadas: ["DEL01", "DEL02", "DEL03", "DEL04", "DEL05", "DEL06"] }
    ],

    items_metas: [
        { id: 1, codigo: "IT001", nombre: "Cobertura", descripcion: "Porcentaje de atenciones ciudadanas resueltas en plazo", unidad_medida: "Atenciones", meta_cantidad: 150, estado: "Activo" },
        { id: 2, codigo: "IT002", nombre: "Satisfacción", descripcion: "Nivel de satisfacción vecinal en intervenciones de asistencia", unidad_medida: "%", meta_cantidad: 95, estado: "Activo" },
        { id: 3, codigo: "IT003", nombre: "Tiempos", descripcion: "Tiempo promedio de respuesta y resolución en ventanilla", unidad_medida: "Horas", meta_cantidad: 24, estado: "Activo" },
        { id: 4, codigo: "IT004", nombre: "Atenciones Territoriales", descripcion: "Operativos sociales y visitas asistenciales en terreno", unidad_medida: "Operativos", meta_cantidad: 40, estado: "Activo" },
        { id: 5, codigo: "IT005", nombre: "Resolución de Solicitudes", descripcion: "Índice de resolutividad de requerimientos comunitarios", unidad_medida: "%", meta_cantidad: 88, estado: "Activo" }
    ],

    tipos_atencion: [
        { id: 1, codigo: "TA001", nombre: "Social", descripcion: "Apoyo social, subsidios, ayudas familiares y ficha social", estado: "Activo" },
        { id: 2, codigo: "TA002", nombre: "Salud", descripcion: "Orientación médica preventiva y enlace consultorios de salud", estado: "Activo" },
        { id: 3, codigo: "TA003", nombre: "Educación", descripcion: "Apoyo escolar, becas municipales y talleres vecinales", estado: "Activo" },
        { id: 4, codigo: "TA004", nombre: "Obras y Servicios", descripcion: "Mantención vial, bacheo, aseo, ornato y alumbrado", estado: "Activo" },
        { id: 5, codigo: "TA005", nombre: "Seguridad Ciudadana", descripcion: "Denuncias barriales, alarmas comunitarias y patrullaje", estado: "Activo" }
    ],

    sub_atenciones: [
        { id: 1, codigo: "SA001", nombre: "Ayuda social de emergencia", tipo_codigo: "TA001", tipo_nombre: "Social", estado: "Activa" },
        { id: 2, codigo: "SA002", nombre: "Subsidio de agua potable y luz", tipo_codigo: "TA001", tipo_nombre: "Social", estado: "Activa" },
        { id: 3, codigo: "SA003", nombre: "Ficha de Protección Social", tipo_codigo: "TA001", tipo_nombre: "Social", estado: "Activa" },
        { id: 4, codigo: "SA004", nombre: "Consulta médica preventiva", tipo_codigo: "TA002", tipo_nombre: "Salud", estado: "Activa" },
        { id: 5, codigo: "SA005", nombre: "Enlace de farmacia popular", tipo_codigo: "TA002", tipo_nombre: "Salud", estado: "Activa" },
        { id: 6, codigo: "SA006", nombre: "Beca municipal de estudio", tipo_codigo: "TA003", tipo_nombre: "Educación", estado: "Activa" },
        { id: 7, codigo: "SA007", nombre: "Útiles y apoyo escolar", tipo_codigo: "TA003", tipo_nombre: "Educación", estado: "Activa" },
        { id: 8, codigo: "SA008", nombre: "Reparación de luminarias", tipo_codigo: "TA004", tipo_nombre: "Obras y Servicios", estado: "Activa" },
        { id: 9, codigo: "SA009", nombre: "Retiro de escombros y microbasurales", tipo_codigo: "TA004", tipo_nombre: "Obras y Servicios", estado: "Activa" },
        { id: 10, codigo: "SA010", nombre: "Alarma barrial e iluminación disuasiva", tipo_codigo: "TA005", tipo_nombre: "Seguridad Ciudadana", estado: "Activa" }
    ],

    atenciones: [
        { id: 1, folio: "ATN-2026-0001", solicitante_rut: "14.283.912-4", solicitante_nombre: "María Elena Rojas", delegacion_codigo: "DEL01", delegacion_nombre: "Centro", tipo_codigo: "TA001", tipo_nombre: "Social", subtipo_codigo: "SA001", subtipo_nombre: "Ayuda social de emergencia", descripcion: "Vecina solicita apoyo de alimentos por situación de cesantía temporal.", responsable_nombre: "Carlos Miranda", fecha_registro: "2026-10-08 09:30:15" },
        { id: 2, folio: "ATN-2026-0002", solicitante_rut: "16.129.845-9", solicitante_nombre: "Juan Carlos Tapia", delegacion_codigo: "DEL01", delegacion_nombre: "Centro", tipo_codigo: "TA004", tipo_nombre: "Obras y Servicios", subtipo_codigo: "SA008", subtipo_nombre: "Reparación de luminarias", descripcion: "Poste frente a pasaje Las Rosas con intermitencia nocturna.", responsable_nombre: "Carlos Miranda", fecha_registro: "2026-10-09 11:15:40" },
        { id: 3, folio: "ATN-2026-0003", solicitante_rut: "18.543.210-7", solicitante_nombre: "Francisca Cortés Araya", delegacion_codigo: "DEL02", delegacion_nombre: "Norte (Las Compañías)", tipo_codigo: "TA003", tipo_nombre: "Educación", subtipo_codigo: "SA006", subtipo_nombre: "Beca municipal de estudio", descripcion: "Postulación alumno destacado de enseñanza superior.", responsable_nombre: "Sara Ejemplo", fecha_registro: "2026-10-10 14:45:00" }
    ]
};

class SGRDataManager {
    constructor() {
        this.apiBase = window.location.origin.includes("http") ? "" : null;
        this.storageKey = "SGR_LA_SERENA_EVAL2_DATA";
        this.hasBackend = false;
        this.loadLocalData();
    }

    async init() {
        // Verificar si backend está respondiendo
        try {
            const resp = await fetch("/api/health");
            if (resp.ok) {
                this.hasBackend = true;
                console.log("[SGR Data] Backend REST API activo en AWS/Localhost.");
                await this.syncFromBackend();
                return;
            }
        } catch (e) {
            console.log("[SGR Data] Modo Local / GitHub Pages activo (persistencia localStorage).");
        }
        this.hasBackend = false;
    }

    loadLocalData() {
        const stored = localStorage.getItem(this.storageKey);
        if (stored) {
            try {
                this.data = JSON.parse(stored);
            } catch (e) {
                this.data = JSON.parse(JSON.stringify(SGR_INITIAL_DATA));
            }
        } else {
            this.data = JSON.parse(JSON.stringify(SGR_INITIAL_DATA));
            this.saveLocalData();
        }
    }

    saveLocalData() {
        localStorage.setItem(this.storageKey, JSON.stringify(this.data));
    }

    async syncFromBackend() {
        if (!this.hasBackend) return;
        try {
            const [del, rol, usr, itm, tip, sub, atn] = await Promise.all([
                fetch("/api/delegaciones").then(r => r.json()),
                fetch("/api/roles").then(r => r.json()),
                fetch("/api/usuarios").then(r => r.json()),
                fetch("/api/items-metas").then(r => r.json()),
                fetch("/api/tipos-atencion").then(r => r.json()),
                fetch("/api/sub-atenciones").then(r => r.json()),
                fetch("/api/atenciones").then(r => r.json())
            ]);
            this.data.delegaciones = del;
            this.data.roles = rol;
            this.data.usuarios = usr;
            this.data.items_metas = itm;
            this.data.tipos_atencion = tip;
            this.data.sub_atenciones = sub;
            this.data.atenciones = atn;
            this.saveLocalData();
        } catch (err) {
            console.warn("[SGR Data] Error sincronizando con backend:", err);
        }
    }

    // CRUD Genérico (soporta backend y localStorage transparente)
    async getAll(collection) {
        return this.data[collection] || [];
    }

    async createItem(collection, item) {
        if (this.hasBackend) {
            const endpointMap = {
                "delegaciones": "/api/delegaciones",
                "roles": "/api/roles",
                "usuarios": "/api/usuarios",
                "items_metas": "/api/items-metas",
                "tipos_atencion": "/api/tipos-atencion",
                "sub_atenciones": "/api/sub-atenciones",
                "atenciones": "/api/atenciones"
            };
            const ep = endpointMap[collection];
            if (ep) {
                try {
                    const res = await fetch(ep, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(item)
                    });
                    const result = await res.json();
                    if (!res.ok) throw new Error(result.message || "Error al crear en servidor");
                    await this.syncFromBackend();
                    return result;
                } catch (e) {
                    throw e;
                }
            }
        }

        // Fallback LocalStorage
        const list = this.data[collection];
        item.id = list.length ? Math.max(...list.map(x => x.id || 0)) + 1 : 1;
        list.push(item);
        this.saveLocalData();
        return { success: true, message: "Registro creado exitosamente", id: item.id };
    }

    async updateItem(collection, id, updatedData) {
        if (this.hasBackend) {
            const endpointMap = {
                "delegaciones": `/api/delegaciones/${id}`,
                "roles": `/api/roles/${id}`,
                "usuarios": `/api/usuarios/${id}`,
                "items_metas": `/api/items-metas/${id}`,
                "tipos_atencion": `/api/tipos-atencion/${id}`,
                "sub_atenciones": `/api/sub-atenciones/${id}`
            };
            const ep = endpointMap[collection];
            if (ep) {
                const res = await fetch(ep, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(updatedData)
                });
                const result = await res.json();
                if (!res.ok) throw new Error(result.message || "Error al actualizar");
                await this.syncFromBackend();
                return result;
            }
        }

        // Fallback LocalStorage
        const list = this.data[collection];
        const idx = list.findIndex(x => x.id == id);
        if (idx !== -1) {
            list[idx] = { ...list[idx], ...updatedData };
            this.saveLocalData();
            return { success: true, message: "Registro actualizado exitosamente" };
        }
        throw new Error("Registro no encontrado");
    }

    async deleteItem(collection, id) {
        if (this.hasBackend) {
            const endpointMap = {
                "delegaciones": `/api/delegaciones/${id}`,
                "roles": `/api/roles/${id}`,
                "usuarios": `/api/usuarios/${id}`,
                "items_metas": `/api/items-metas/${id}`,
                "tipos_atencion": `/api/tipos-atencion/${id}`,
                "sub_atenciones": `/api/sub-atenciones/${id}`
            };
            const ep = endpointMap[collection];
            if (ep) {
                const res = await fetch(ep, { method: "DELETE" });
                const result = await res.json();
                if (!res.ok) throw new Error(result.message || "Error al eliminar");
                await this.syncFromBackend();
                return result;
            }
        }

        // Fallback LocalStorage
        const list = this.data[collection];
        const idx = list.findIndex(x => x.id == id);
        if (idx !== -1) {
            list.splice(idx, 1);
            this.saveLocalData();
            return { success: true, message: "Registro eliminado exitosamente" };
        }
        throw new Error("Registro no encontrado");
    }
}

// Instancia global
const sgrDb = new SGRDataManager();

// Exportación a Excel con SheetJS (xlsx)
function exportToExcel(records, filename, sheetTitle = "Datos") {
    if (!window.XLSX) {
        Swal.fire({
            title: "Librería no disponible",
            text: "Cargando motor de exportación a Excel...",
            icon: "info",
            confirmButtonColor: "#8e1525"
        });
        return;
    }

    if (!records || records.length === 0) {
        Swal.fire({
            title: "Sin datos para exportar",
            text: "El filtro actual no contiene registros para generar el archivo Excel.",
            icon: "warning",
            confirmButtonColor: "#8e1525"
        });
        return;
    }

    // Filtrar campos sensibles de seguridad (contraseñas, tokens, etc.)
    const cleanRecords = records.map(item => {
        const copy = { ...item };
        delete copy.password_hash;
        delete copy.password;
        delete copy.token;
        delete copy.id;
        return copy;
    });

    const worksheet = XLSX.utils.json_to_sheet(cleanRecords);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, sheetTitle);

    // Guardar archivo Excel .xlsx
    XLSX.writeFile(workbook, `${filename}_${new Date().toISOString().slice(0, 10)}.xlsx`);

    Swal.fire({
        title: "¡Exportación Exitosa!",
        text: `Se ha descargado el archivo ${filename}.xlsx con ${cleanRecords.length} registros.`,
        icon: "success",
        confirmButtonColor: "#8e1525",
        timer: 3000
    });
}
