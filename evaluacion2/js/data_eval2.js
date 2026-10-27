/**
 * SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - MUNICIPALIDAD DE LA SERENA
 * data_eval2.js - Capa de Datos, Sincronización REST / LocalStorage y Exportación Excel
 * Autores: Harold Concha, Keoni Vergara, Claudio Romo | INACAP
 */

if (window.Swal) {
    window.Swal = window.Swal.mixin({
        target: document.body,
        heightAuto: false,
        keydownListenerCapture: true,
        confirmButtonText: "Aceptar",
        cancelButtonText: "Cancelar",
        confirmButtonColor: "var(--primary)",
        customClass: {
            container: "sgr-alert-layer",
            popup: "sgr-swal",
            confirmButton: "sgr-swal-confirm",
            cancelButton: "sgr-swal-cancel"
        }
    });
}

// Todas las solicitudes de escritura usan la protección CSRF de Django.
const sgrNativeFetch = window.fetch.bind(window);
window.fetch = (input, options = {}) => {
    const url = new URL(typeof input === "string" ? input : input.url, window.location.href);
    const method = (options.method || "GET").toUpperCase();
    if (url.origin === window.location.origin && !["GET", "HEAD", "OPTIONS"].includes(method)) {
        const headers = new Headers(options.headers || {});
        const token = document.cookie.split("; ").find(row => row.startsWith("csrftoken="))?.split("=")[1];
        if (token) headers.set("X-CSRFToken", decodeURIComponent(token));
        options = { ...options, headers };
    }
    return sgrNativeFetch(input, options);
};

const SGR_ENDPOINTS = {
    delegaciones: "delegaciones", roles: "roles", usuarios: "usuarios",
    items_metas: "items-metas", tipos_atencion: "tipos-atencion",
    sub_atenciones: "sub-atenciones", atenciones: "atenciones"
};

class SGRDataManager {
    constructor() {
        this.hasBackend = true;
        this.data = Object.fromEntries(Object.keys(SGR_ENDPOINTS).map(key => [key, []]));
        // No recuperar registros ni sesiones del prototipo anterior.
        localStorage.removeItem("SGR_LA_SERENA_EVAL2_DATA");
        localStorage.removeItem("SGR_AUTH_SESSION_USER");
    }

    async init() {
        const response = await fetch("/api/health");
        if (!response.ok) throw new Error("No se pudo conectar con Django.");
    }

    async fetchCollection(endpoint) {
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error("No se pudo consultar el servidor. Inicie sesión nuevamente.");
        return response.json();
    }

    async syncFromBackend() {
        const keys = Object.keys(SGR_ENDPOINTS);
        const rows = await Promise.all(keys.map(key => this.fetchCollection(`/api/${SGR_ENDPOINTS[key]}`)));
        keys.forEach((key, index) => { this.data[key] = rows[index]; });
    }

    async getAll(collection) { return this.data[collection] || []; }

    generateCode(collection) {
        const formats = {delegaciones:["DEL",2], roles:["ROL",2], items_metas:["IT",3], tipos_atencion:["TA",3], sub_atenciones:["SA",3]};
        const [prefix, width] = formats[collection] || ["",3];
        const values = (this.data[collection] || []).map(row => Number((row.codigo || "").slice(prefix.length)) || 0);
        return prefix + String(Math.max(0, ...values) + 1).padStart(width, "0");
    }

    async mutate(collection, method, item, id) {
        const endpoint = SGR_ENDPOINTS[collection];
        if (!endpoint) throw new Error("Colección desconocida.");
        const response = await fetch(`/api/${endpoint}${id ? `/${id}` : ""}`, {
            method, headers: {"Content-Type":"application/json"},
            ...(item ? {body:JSON.stringify(item)} : {})
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.message || "No se pudo guardar la operación.");
        await this.syncFromBackend();
        return result;
    }
    async createItem(collection, item) { return this.mutate(collection, "POST", item); }
    async updateItem(collection, id, item) { return this.mutate(collection, "PUT", item, id); }
    async deleteItem(collection, id) { return this.mutate(collection, "DELETE", null, id); }
}
const sgrDb = new SGRDataManager();

// Exportación a Excel con SheetJS (xlsx)
function exportToExcel(records, filename, sheetTitle = "Datos") {
    if (!window.XLSX) {
        Swal.fire({
            title: "Librería no disponible",
            text: "Cargando motor de exportación a Excel...",
            icon: "info",
            confirmButtonColor: "var(--primary)"
        });
        return;
    }

    if (!records || records.length === 0) {
        Swal.fire({
            title: "Sin datos para exportar",
            text: "El filtro actual no contiene registros para generar el archivo Excel.",
            icon: "warning",
            confirmButtonColor: "var(--primary)"
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
        confirmButtonColor: "var(--primary)",
        timer: 3000
    });
}
