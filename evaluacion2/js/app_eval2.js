/**
 * SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - MUNICIPALIDAD DE LA SERENA
 * app_eval2.js - Controlador Principal, Lógica de Vistas, 6 Mantenedores,
 *               Control de Roles y Flujo de Recuperación de Contraseña
 * Autores: Harold Concha, Keoni Vergara, Claudio Romo | INACAP
 */

class SGRApplication {
    constructor() {
        this.currentUser = null;
        this.profileController = null;
        this.newUserPhoto = null;
        this.newUserPhotoPending = null;
        this.activeDelegacion = "DEL01";
        this.nativeCrud = document.body?.dataset?.nativeCrud || null;
        const requestedView = new URL(window.location.href).searchParams.get("view");
        this.currentView = this.nativeCrud ? this.nativeCrud.replaceAll("-", "_") :
            (["atenciones", "tablero", "evidencias", "agenda", "auditoria"].includes(requestedView) ? requestedView : "atenciones");
        this.pagination = {
            delegaciones: { page: 1, limit: 5, search: "", filter: "TODOS" },
            roles: { page: 1, limit: 5, search: "", filter: "TODOS" },
            usuarios: { page: 1, limit: 5, search: "", filter: "TODOS" },
            items_metas: { page: 1, limit: 5, search: "", filter: "TODOS" },
            tipos_atencion: { page: 1, limit: 5, search: "", filter: "TODOS" },
            sub_atenciones: { page: 1, limit: 5, search: "", filter: "TODOS" },
            atenciones: { page: 1, limit: 5, search: "", filter: "TODOS" }
        };

        // Estado del flujo de recuperación de clave
        this.recoveryState = {
            step: 1,
            email: "",
            demoCode: "",
            timerInterval: null,
            timerSeconds: 600, // 10 minutos
            resendCooldown: 45,
            attempts: 0
        };
    }

    async init() {
        this.setupEventListeners();
        if (!this.nativeCrud) this.showAuthView("login");
        try {
            await sgrDb.init();
        } catch (err) {
            Swal.fire({ title: "Error de conexión", text: err.message, icon: "error" });
            return;
        }

        localStorage.removeItem("SGR_SESSION_USER");
        const response = await fetch("/api/profile");
        if (response.ok) {
            const { user } = await response.json();
            this.currentUser = user;
            this.activeDelegacion = user.delegacion_codigo || "ALL";
            if (this.redirectAfterLogin()) return;
            if (this.nativeCrud) {
                sgrDb.data.delegaciones = await sgrDb.fetchCollection("/api/delegaciones");
            } else {
                await sgrDb.syncFromBackend();
            }
            this.showAppView();
        }

        // Inicializar iconos de Lucide
        if (window.lucide) {
            lucide.createIcons();
        }
    }

    // =========================================================================
    // GESTIÓN DE USUARIOS Y ROLES (REQUISITO FUNDAMENTAL DE LA ENTREGA)
    // =========================================================================
    applyRolePermissions() {
        if (!this.currentUser) return;
        const rol = this.currentUser.rol_codigo; // ROL01: Superadmin, ROL02: Coord, ROL03: Delegado, ROL04: Operador, ROL05: Consultor

        // Definición estricta de módulos visibles por rol
        const menuPermissions = {
            "ROL01": ["inicio", "delegaciones", "roles", "usuarios", "items_metas", "tipos_atencion", "sub_atenciones", "atenciones", "tablero", "evidencias", "agenda", "auditoria"],
            "ROL02": ["inicio", "delegaciones", "items_metas", "tipos_atencion", "sub_atenciones", "atenciones", "tablero", "agenda"],
            "ROL03": ["inicio", "usuarios", "items_metas", "atenciones", "tablero"],
            "ROL04": ["inicio", "atenciones"],
            "ROL05": ["inicio", "delegaciones", "items_metas", "tipos_atencion", "sub_atenciones", "atenciones", "tablero"]
        };

        let allowed = menuPermissions[rol] || ["atenciones"];
        if (this.nativeCrud) {
            const catalogs = JSON.parse(document.getElementById("sgr-native-navigation").textContent);
            const operational = allowed.filter(name => ["inicio", "atenciones", "tablero", "evidencias", "agenda", "auditoria"].includes(name));
            allowed = [...operational, ...catalogs.map(([slug]) => slug.replaceAll("-", "_"))];
        }

        // Actualizar visibilidad de elementos del menú lateral
        document.querySelectorAll("[data-module]").forEach(el => {
            const mod = el.getAttribute("data-module");
            if (allowed.includes(mod)) {
                el.style.display = "";
            } else {
                el.style.display = "none";
            }
        });

        // Si la vista actual no está permitida, redirigir a una válida
        if (!this.nativeCrud && !allowed.includes(this.currentView)) {
            this.navigateTo(allowed.includes("atenciones") ? "atenciones" : allowed[0]);
        }
    }

    setupHeaderDelegacion() {
        const select = document.getElementById("header-delegacion-select");
        if (!select) return;

        select.innerHTML = "";
        const allDelegaciones = sgrDb.data.delegaciones;

        // Si el usuario es Superadmin o Coordinador, puede cambiar entre todas las delegaciones
        const esComunal = ["ROL01", "ROL02"].includes(this.currentUser?.rol_codigo);

        allDelegaciones.forEach(del => {
            const opt = document.createElement("option");
            opt.value = del.codigo;
            opt.textContent = `Delegación ${del.nombre} · ${del.codigo}`;
            if (del.codigo === this.activeDelegacion) {
                opt.selected = true;
            }
            // Si el perfil no tiene alcance comunal, deshabilitar delegaciones ajenas
            if (!esComunal && del.codigo !== this.currentUser?.delegacion_codigo) {
                opt.disabled = true;
            }
            select.appendChild(opt);
        });

        // Deshabilitar el select si el usuario solo tiene una delegación autorizada
        select.disabled = !esComunal;

        // El select nativo conserva teclado y permisos; la etiqueta muestra la jerarquía visual.
        const actual = allDelegaciones.find(d => d.codigo === this.activeDelegacion);
        const descEl = document.getElementById("header-delegacion-name");
        if (descEl) {
            descEl.textContent = actual ? `Delegación ${actual.nombre}` : "Delegación La Serena";
        }
        const codeEl = document.getElementById("header-delegacion-code");
        if (codeEl) codeEl.textContent = actual ? actual.codigo : this.activeDelegacion;
        select.closest(".topbar-delegacion-pill")?.classList.toggle("is-disabled", select.disabled);
    }

    onHeaderDelegacionChange(newCodigo) {
        const delActual = sgrDb.data.delegaciones.find(d => d.codigo === newCodigo);
        this.activeDelegacion = newCodigo;
        this.setupHeaderDelegacion();

        Swal.fire({
            title: "Contexto Actualizado",
            text: `Has cambiado a la ${delActual ? delActual.nombre : newCodigo}. Todos los listados y registros reflejan este ámbito.`,
            icon: "info",
            confirmButtonColor: "var(--primary)",
            timer: 2500
        });

        this.renderCurrentView();
    }

    updateHeaderUserInfo() {
        const nameEl = document.getElementById("header-user-name");
        const roleEl = document.getElementById("header-user-role");
        if (nameEl && this.currentUser) nameEl.textContent = this.currentUser.nombre;
        if (roleEl && this.currentUser) roleEl.textContent = this.currentUser.rol_nombre || "Funcionario";
        if (window.SGRProfileController && this.currentUser) {
            this.profileController ||= new window.SGRProfileController(this);
            this.profileController.renderHeader();
        }
    }

    openProfile() {
        if (!this.currentUser || !window.SGRProfileController) return;
        this.profileController ||= new window.SGRProfileController(this);
        return this.profileController.open();
    }

    async selectNewUserPhoto(input) {
        const file = input.files?.[0];
        if (!file) return;
        const button = document.getElementById("btn-modal-save");
        button.disabled = true;
        const pending = window.SGRProfileController.preparePhoto(file,
            () => this.newUserPhotoPending === pending && document.getElementById("m-usr-foto") === input);
        this.newUserPhotoPending = pending;
        try {
            const photo = await pending;
            if (photo !== null && this.newUserPhotoPending === pending && document.getElementById("m-usr-foto") === input) {
                this.newUserPhoto = photo;
                document.getElementById("m-usr-foto-preview").src = photo;
            }
        } catch (error) {
            if (this.newUserPhotoPending === pending && document.getElementById("m-usr-foto") === input) {
                input.value = "";
                Swal.fire({ title: "No se pudo usar la foto", text: error.message, icon: "error" });
            }
        } finally {
            if (this.newUserPhotoPending === pending) {
                input.value = "";
                this.newUserPhotoPending = null;
                button.disabled = false;
            }
        }
    }

    // =========================================================================
    // NAVEGACIÓN Y ENRUTAMIENTO DE VISTAS
    // =========================================================================
    navigateTo(viewName) {
        const crudRoutes = {
            delegaciones: "delegaciones", roles: "roles", usuarios: "usuarios",
            items_metas: "items-metas", tipos_atencion: "tipos-atencion",
            sub_atenciones: "sub-atenciones"
        };
        if (crudRoutes[viewName]) {
            window.location.assign(`/gestion/${crudRoutes[viewName]}/`);
            return;
        }
        if (this.nativeCrud) {
            window.location.assign(`/?view=${encodeURIComponent(viewName)}`);
            return;
        }
        this.currentView = viewName;

        // Actualizar clase activa en sidebar
        document.querySelectorAll(".nav-link-btn").forEach(btn => {
            if (btn.getAttribute("data-target") === viewName) {
                btn.classList.add("active");
                btn.setAttribute("aria-current", "page");
            } else {
                btn.classList.remove("active");
                btn.removeAttribute("aria-current");
            }
        });

        // Ocultar todas las secciones y mostrar la activa
        document.querySelectorAll(".sgr-view-section").forEach(sec => {
            sec.style.display = "none";
        });

        const activeSec = document.getElementById(`view-${viewName}`);
        if (activeSec) {
            activeSec.style.display = "block";
        }

        this.renderCurrentView();

        if (window.lucide) {
            lucide.createIcons();
        }
    }

    renderCurrentView() {
        if (this.nativeCrud) return; // Django ya entregó el listado y su formulario.
        switch (this.currentView) {
            case "delegaciones":
                this.renderDelegaciones();
                break;
            case "roles":
                this.renderRoles();
                break;
            case "usuarios":
                this.renderUsuarios();
                break;
            case "items_metas":
                this.renderItemsMetas();
                break;
            case "tipos_atencion":
                this.renderTiposAtencion();
                break;
            case "sub_atenciones":
                this.renderSubAtenciones();
                break;
            case "atenciones":
                this.renderAtencionesView();
                break;
            default:
                break;
        }
    }

    filterByVisibleColumns(moduleName, records) {
        const query = (this.pagination[moduleName]?.search || "").toLowerCase().trim();
        if (!query) return records;

        const columns = {
            delegaciones: ["codigo", "nombre", "comuna", "estado"],
            roles: ["codigo", "nombre", "alcance", "estado"],
            usuarios: ["nombre", "email", ["rol_nombre", "rol_codigo"], ["delegacion_nombre", "delegacion_codigo"]],
            items_metas: ["codigo", "nombre", "descripcion", "estado"],
            tipos_atencion: ["codigo", "nombre", "descripcion", "estado"],
            sub_atenciones: ["codigo", "nombre", "tipo_nombre", "estado"],
            atenciones: ["folio", "solicitante_nombre", "delegacion_nombre", "tipo_nombre", "subtipo_nombre", "responsable_nombre", "fecha_registro"]
        };

        return records.filter(record => (columns[moduleName] || []).some(column => {
            const value = Array.isArray(column) ? record[column[0]] || record[column[1]] : record[column];
            return String(value ?? "").toLowerCase().includes(query);
        }));
    }

    // =========================================================================
    // MANTENEDOR 1: DELEGACIONES MUNICIPALES (DISEÑO C3)
    // =========================================================================
    renderDelegaciones() {
        const conf = this.pagination.delegaciones;
        let list = sgrDb.data.delegaciones;

        // Filtro por estado
        if (conf.filter !== "TODOS") {
            list = list.filter(d => d.estado.toUpperCase() === conf.filter);
        }

        // Búsqueda inteligente insensible a mayúsculas/minúsculas
        list = this.filterByVisibleColumns("delegaciones", list);

        const total = list.length;
        const totalPages = Math.ceil(total / conf.limit) || 1;
        if (conf.page > totalPages) conf.page = totalPages;

        const startIdx = (conf.page - 1) * conf.limit;
        const paged = list.slice(startIdx, startIdx + conf.limit);

        const tbody = document.getElementById("tbody-delegaciones");
        if (!tbody) return;

        if (paged.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-table-state">
                        <i data-lucide="building-2"></i>
                        <p>No se encontraron delegaciones que coincidan con la búsqueda o filtro.</p>
                    </td>
                </tr>`;
        } else {
            tbody.innerHTML = paged.map(del => `
                <tr>
                    <td class="record-code">${del.codigo}</td>
                    <td class="record-name">${del.nombre}</td>
                    <td>${del.comuna}</td>
                    <td><span class="badge-status ${del.estado.toLowerCase()}">${del.estado}</span></td>
                    <td>
                        <div class="table-actions" role="group" aria-label="Acciones del registro">
                            <button type="button" class="action-link view" onclick="sgrApp.openModalView('delegaciones', ${del.id})"><svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg><span>Ver</span></button>
                            <button type="button" class="action-link edit" onclick="sgrApp.openModalEdit('delegaciones', ${del.id})">Editar</button>
                            <button type="button" class="action-link delete" onclick="sgrApp.confirmDelete('delegaciones', ${del.id})">Eliminar</button>
                        </div>
                    </td>
                </tr>
            `).join("");
        }

        this.renderPaginationControls("delegaciones", total, conf.page, totalPages, startIdx, paged.length);
        if (window.lucide) lucide.createIcons();
    }

    // =========================================================================
    // MANTENEDOR 2: ROLES Y PERMISOS (DISEÑO C3)
    // =========================================================================
    renderRoles() {
        const conf = this.pagination.roles;
        let list = sgrDb.data.roles;

        if (conf.filter !== "TODOS") {
            list = list.filter(r => r.estado.toUpperCase() === conf.filter);
        }

        list = this.filterByVisibleColumns("roles", list);

        const total = list.length;
        const totalPages = Math.ceil(total / conf.limit) || 1;
        if (conf.page > totalPages) conf.page = totalPages;

        const startIdx = (conf.page - 1) * conf.limit;
        const paged = list.slice(startIdx, startIdx + conf.limit);

        const tbody = document.getElementById("tbody-roles");
        if (!tbody) return;

        if (paged.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-table-state"><p>No se encontraron roles.</p></td></tr>`;
        } else {
            tbody.innerHTML = paged.map(r => `
                <tr>
                    <td class="record-code">${r.codigo}</td>
                    <td class="record-name">${r.nombre}</td>
                    <td>${r.alcance}</td>
                    <td><span class="badge-status ${r.estado.toLowerCase()}">${r.estado}</span></td>
                    <td>
                        <div class="table-actions" role="group" aria-label="Acciones del registro">
                            <button type="button" class="action-link view" onclick="sgrApp.openModalView('roles', ${r.id})"><svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg><span>Ver</span></button>
                            <button type="button" class="action-link edit" onclick="sgrApp.openModalEdit('roles', ${r.id})">Editar</button>
                            <button type="button" class="action-link delete" onclick="sgrApp.confirmDelete('roles', ${r.id})">Eliminar</button>
                        </div>
                    </td>
                </tr>
            `).join("");
        }

        this.renderPaginationControls("roles", total, conf.page, totalPages, startIdx, paged.length);
    }

    // =========================================================================
    // MANTENEDOR 3: USUARIOS DEL SISTEMA (DISEÑO C4)
    // =========================================================================
    renderUsuarios() {
        const conf = this.pagination.usuarios;
        let list = sgrDb.data.usuarios;

        // Si es Delegado Municipal, sólo puede consultar usuarios de su delegación asignada
        if (this.currentUser?.rol_codigo === "ROL03") {
            list = list.filter(u => u.delegacion_codigo === this.currentUser.delegacion_codigo);
        }

        if (conf.filter !== "TODOS") {
            list = list.filter(u => u.estado.toUpperCase() === conf.filter);
        }

        list = this.filterByVisibleColumns("usuarios", list);

        const total = list.length;
        const totalPages = Math.ceil(total / conf.limit) || 1;
        if (conf.page > totalPages) conf.page = totalPages;

        const startIdx = (conf.page - 1) * conf.limit;
        const paged = list.slice(startIdx, startIdx + conf.limit);

        const tbody = document.getElementById("tbody-usuarios");
        if (!tbody) return;

        if (paged.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-table-state"><p>No se encontraron usuarios.</p></td></tr>`;
        } else {
            tbody.innerHTML = paged.map(u => `
                <tr>
                    <td class="record-name">${u.nombre}</td>
                    <td>${u.email}</td>
                    <td>${u.rol_nombre || u.rol_codigo}</td>
                    <td>${u.delegacion_nombre || u.delegacion_codigo}</td>
                    <td>
                        <div class="table-actions" role="group" aria-label="Acciones del registro">
                            <button type="button" class="action-link view" onclick="sgrApp.openModalView('usuarios', ${u.id})"><svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg><span>Ver</span></button>
                            <button type="button" class="action-link edit" onclick="sgrApp.openModalEdit('usuarios', ${u.id})">Editar</button>
                            <button type="button" class="action-link delete" onclick="sgrApp.confirmDelete('usuarios', ${u.id})">Eliminar</button>
                        </div>
                    </td>
                </tr>
            `).join("");
        }

        this.renderPaginationControls("usuarios", total, conf.page, totalPages, startIdx, paged.length);
    }

    // =========================================================================
    // MANTENEDOR 4: ÍTEMS Y METAS (DISEÑO C4)
    // =========================================================================
    renderItemsMetas() {
        const conf = this.pagination.items_metas;
        let list = sgrDb.data.items_metas;

        if (conf.filter !== "TODOS") {
            list = list.filter(i => i.estado.toUpperCase() === conf.filter);
        }

        list = this.filterByVisibleColumns("items_metas", list);

        const total = list.length;
        const totalPages = Math.ceil(total / conf.limit) || 1;
        if (conf.page > totalPages) conf.page = totalPages;

        const startIdx = (conf.page - 1) * conf.limit;
        const paged = list.slice(startIdx, startIdx + conf.limit);

        const tbody = document.getElementById("tbody-items-metas");
        if (!tbody) return;

        if (paged.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-table-state"><p>No se encontraron ítems.</p></td></tr>`;
        } else {
            tbody.innerHTML = paged.map(i => `
                <tr>
                    <td class="record-code">${i.codigo}</td>
                    <td class="record-name">${i.nombre}</td>
                    <td>${i.descripcion}</td>
                    <td><span class="badge-status ${i.estado.toLowerCase()}">${i.estado}</span></td>
                    <td>
                        <div class="table-actions" role="group" aria-label="Acciones del registro">
                            <button type="button" class="action-link view" onclick="sgrApp.openModalView('items_metas', ${i.id})"><svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg><span>Ver</span></button>
                            <button type="button" class="action-link edit" onclick="sgrApp.openModalEdit('items_metas', ${i.id})">Editar</button>
                            <button type="button" class="action-link delete" onclick="sgrApp.confirmDelete('items_metas', ${i.id})">Eliminar</button>
                        </div>
                    </td>
                </tr>
            `).join("");
        }

        this.renderPaginationControls("items_metas", total, conf.page, totalPages, startIdx, paged.length);
    }

    // =========================================================================
    // MANTENEDOR 5: TIPOS DE ATENCIÓN (DISEÑO C5)
    // =========================================================================
    renderTiposAtencion() {
        const conf = this.pagination.tipos_atencion;
        let list = sgrDb.data.tipos_atencion;

        if (conf.filter !== "TODOS") {
            list = list.filter(t => t.estado.toUpperCase() === conf.filter);
        }

        list = this.filterByVisibleColumns("tipos_atencion", list);

        const total = list.length;
        const totalPages = Math.ceil(total / conf.limit) || 1;
        if (conf.page > totalPages) conf.page = totalPages;

        const startIdx = (conf.page - 1) * conf.limit;
        const paged = list.slice(startIdx, startIdx + conf.limit);

        const tbody = document.getElementById("tbody-tipos-atencion");
        if (!tbody) return;

        if (paged.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-table-state"><p>No se encontraron tipos de atención.</p></td></tr>`;
        } else {
            tbody.innerHTML = paged.map(t => `
                <tr>
                    <td class="record-code">${t.codigo}</td>
                    <td class="record-name">${t.nombre}</td>
                    <td>${t.descripcion}</td>
                    <td><span class="badge-status ${t.estado.toLowerCase()}">${t.estado}</span></td>
                    <td>
                        <div class="table-actions" role="group" aria-label="Acciones del registro">
                            <button type="button" class="action-link view" onclick="sgrApp.openModalView('tipos_atencion', ${t.id})"><svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg><span>Ver</span></button>
                            <button type="button" class="action-link edit" onclick="sgrApp.openModalEdit('tipos_atencion', ${t.id})">Editar</button>
                            <button type="button" class="action-link delete" onclick="sgrApp.confirmDelete('tipos_atencion', ${t.id})">Eliminar</button>
                        </div>
                    </td>
                </tr>
            `).join("");
        }

        this.renderPaginationControls("tipos_atencion", total, conf.page, totalPages, startIdx, paged.length);
    }

    // =========================================================================
    // MANTENEDOR 6: SUB ATENCIÓN (DISEÑO C5)
    // =========================================================================
    renderSubAtenciones() {
        const conf = this.pagination.sub_atenciones;
        let list = sgrDb.data.sub_atenciones;

        if (conf.filter !== "TODOS") {
            list = list.filter(s => s.estado.toUpperCase() === conf.filter);
        }

        list = this.filterByVisibleColumns("sub_atenciones", list);

        const total = list.length;
        const totalPages = Math.ceil(total / conf.limit) || 1;
        if (conf.page > totalPages) conf.page = totalPages;

        const startIdx = (conf.page - 1) * conf.limit;
        const paged = list.slice(startIdx, startIdx + conf.limit);

        const tbody = document.getElementById("tbody-sub-atenciones");
        if (!tbody) return;

        if (paged.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-table-state"><p>No se encontraron subatenciones.</p></td></tr>`;
        } else {
            tbody.innerHTML = paged.map(s => `
                <tr>
                    <td class="record-code">${s.codigo}</td>
                    <td class="record-name">${s.nombre}</td>
                    <td>${s.tipo_nombre}</td>
                    <td><span class="badge-status ${s.estado.toLowerCase()}">${s.estado}</span></td>
                    <td>
                        <div class="table-actions" role="group" aria-label="Acciones del registro">
                            <button type="button" class="action-link view" onclick="sgrApp.openModalView('sub_atenciones', ${s.id})"><svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg><span>Ver</span></button>
                            <button type="button" class="action-link edit" onclick="sgrApp.openModalEdit('sub_atenciones', ${s.id})">Editar</button>
                            <button type="button" class="action-link delete" onclick="sgrApp.confirmDelete('sub_atenciones', ${s.id})">Eliminar</button>
                        </div>
                    </td>
                </tr>
            `).join("");
        }

        this.renderPaginationControls("sub_atenciones", total, conf.page, totalPages, startIdx, paged.length);
    }

    // =========================================================================
    // VISTA: INGRESO DE ATENCIÓN CIUDADANA (DISEÑO C6)
    // =========================================================================
    renderAtencionesView() {
        // Cargar delegación del contexto del usuario en el campo readonly
        const delField = document.getElementById("atn-delegacion-display");
        const activeDelObj = sgrDb.data.delegaciones.find(d => d.codigo === this.activeDelegacion);
        if (delField) {
            delField.value = `${this.activeDelegacion} - ${activeDelObj ? activeDelObj.nombre : 'Centro'} [Asignada por perfil]`;
        }

        // Cargar tipos de atención activos en el dropdown
        const tipoSelect = document.getElementById("atn-tipo-select");
        if (tipoSelect && tipoSelect.options.length <= 1) {
            tipoSelect.innerHTML = `<option value="">Seleccione Tipo de Atención *</option>`;
            sgrDb.data.tipos_atencion.filter(t => t.estado === "Activo").forEach(t => {
                const opt = document.createElement("option");
                opt.value = t.codigo;
                opt.textContent = `${t.nombre} (${t.descripcion})`;
                tipoSelect.appendChild(opt);
            });
        }

        // Actualizar responsable y fecha en nota
        const noteResp = document.getElementById("atn-meta-info");
        if (noteResp) {
            const fechaHoy = new Date().toLocaleDateString("es-CL", { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
            noteResp.textContent = `Responsable: ${this.currentUser?.nombre || 'Usuario en sesión'} | Fecha y hora: ${fechaHoy} (automática)`;
        }

        // Renderizar tabla de atenciones recientes
        this.renderAtencionesTable();
    }

    onTipoAtencionChange() {
        const tipoSelect = document.getElementById("atn-tipo-select");
        const subSelect = document.getElementById("atn-subtipo-select");
        if (!tipoSelect || !subSelect) return;

        const selectedTipo = tipoSelect.value;
        subSelect.innerHTML = `<option value="">Seleccione Sub Atención *</option>`;

        if (!selectedTipo) {
            subSelect.disabled = true;
            return;
        }

        // Filtrar subatenciones dependientes activas
        const subs = sgrDb.data.sub_atenciones.filter(s => s.tipo_codigo === selectedTipo && s.estado === "Activa");
        subs.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.codigo;
            opt.textContent = s.nombre;
            subSelect.appendChild(opt);
        });

        subSelect.disabled = subs.length === 0;
    }

    async submitIngresoAtencion(e) {
        if (e) e.preventDefault();

        const solicitanteInput = document.getElementById("atn-solicitante");
        const tipoSelect = document.getElementById("atn-tipo-select");
        const subSelect = document.getElementById("atn-subtipo-select");
        const descInput = document.getElementById("atn-descripcion");

        const solicitante = solicitanteInput.value.trim();
        const tipoCodigo = tipoSelect.value;
        const subCodigo = subSelect.value;
        const descripcion = descInput.value.trim();

        if (!solicitante || !tipoCodigo || !subCodigo || !descripcion) {
            Swal.fire({
                title: "Campos Incompletos",
                text: "Por favor complete todos los campos obligatorios (*) antes de guardar.",
                icon: "warning",
                confirmButtonColor: "var(--primary)"
            });
            return;
        }

        let solicitanteRut;
        try {
            solicitanteRut = window.ChileanRut.require(document.getElementById("atn-solicitante-rut"));
        } catch (error) {
            document.getElementById("atn-solicitante-rut")?.focus();
            Swal.fire({ title: "Revisa el RUT", text: error.message, icon: "warning" });
            return;
        }

        const tipoObj = sgrDb.data.tipos_atencion.find(t => t.codigo === tipoCodigo);
        const subObj = sgrDb.data.sub_atenciones.find(s => s.codigo === subCodigo);
        const delObj = sgrDb.data.delegaciones.find(d => d.codigo === this.activeDelegacion);

        const nuevaAtencion = {
            solicitante_rut: solicitanteRut,
            solicitante_nombre: solicitante,
            delegacion_codigo: this.activeDelegacion,
            delegacion_nombre: delObj ? delObj.nombre : "Centro",
            tipo_codigo: tipoCodigo,
            tipo_nombre: tipoObj ? tipoObj.nombre : "Social",
            subtipo_codigo: subCodigo,
            subtipo_nombre: subObj ? subObj.nombre : "General",
            descripcion: descripcion,
            responsable_nombre: this.currentUser?.nombre || "Funcionario de Ventanilla",
            fecha_registro: new Date().toISOString().replace("T", " ").slice(0, 19)
        };

        const submitBtn = document.querySelector(".btn-save-attention");
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = "Guardando...";
        }

        try {
            const result = await sgrDb.createItem("atenciones", nuevaAtencion);
            const folioGenerado = result.folio || `ATN-2026-${String(sgrDb.data.atenciones.length).padStart(4, "0")}`;

            Swal.fire({
                title: "¡Atención Registrada!",
                html: `
                    <div style="text-align: left; font-size: 0.92rem; line-height: 1.6;">
                        <p><strong>Folio Único:</strong> <span style="color:var(--primary); font-size:1.1rem; font-weight:700;">${folioGenerado}</span></p>
                        <p><strong>Solicitante:</strong> ${solicitante}</p>
                        <p><strong>Delegación:</strong> ${delObj ? delObj.nombre : 'Centro'}</p>
                        <p><strong>Clasificación:</strong> ${tipoObj?.nombre} &rarr; ${subObj?.nombre}</p>
                        <p><strong>Responsable:</strong> ${this.currentUser?.nombre}</p>
                    </div>
                `,
                icon: "success",
                confirmButtonColor: "var(--primary)"
            });

            // Limpiar formulario
            solicitanteInput.value = "";
            this.resetAttentionRut();
            tipoSelect.value = "";
            subSelect.innerHTML = `<option value="">Seleccione Sub Atención *</option>`;
            subSelect.disabled = true;
            descInput.value = "";

            this.renderAtencionesTable();
        } catch (err) {
            Swal.fire({
                title: "Error al registrar",
                text: err.message,
                icon: "error",
                confirmButtonColor: "var(--primary)"
            });
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = "Guardar atención";
            }
        }
    }

    cancelarIngresoAtencion() {
        Swal.fire({
            title: "¿Descartar atención?",
            text: "Los datos ingresados no se guardarán en el sistema.",
            icon: "question",
            showCancelButton: true,
            confirmButtonText: "Sí, descartar",
            cancelButtonText: "Continuar editando",
            confirmButtonColor: "var(--primary)"
        }).then(res => {
            if (res.isConfirmed) {
                document.getElementById("atn-solicitante").value = "";
                this.resetAttentionRut();
                document.getElementById("atn-tipo-select").value = "";
                const sub = document.getElementById("atn-subtipo-select");
                sub.innerHTML = `<option value="">Seleccione Sub Atención *</option>`;
                sub.disabled = true;
                document.getElementById("atn-descripcion").value = "";
            }
        });
    }

    resetAttentionRut() {
        const input = document.getElementById("atn-solicitante-rut");
        if (!input) return;
        input.value = "";
        input.setCustomValidity?.("");
        input.removeAttribute?.("aria-invalid");
        if (input.dataset) delete input.dataset.rutTouched;
        const feedback = document.getElementById("atn-rut-help");
        if (feedback) feedback.textContent = "";
    }

    renderAtencionesTable() {
        const conf = this.pagination.atenciones;
        let list = sgrDb.data.atenciones;

        // Filtrar por delegación activa si el rol es territorial
        if (["ROL03", "ROL04"].includes(this.currentUser?.rol_codigo)) {
            list = list.filter(a => a.delegacion_codigo === this.activeDelegacion);
        }

        list = this.filterByVisibleColumns("atenciones", list);

        const total = list.length;
        const totalPages = Math.ceil(total / conf.limit) || 1;
        if (conf.page > totalPages) conf.page = totalPages;

        const startIdx = (conf.page - 1) * conf.limit;
        const paged = list.slice(startIdx, startIdx + conf.limit);

        const tbody = document.getElementById("tbody-atenciones-historial");
        if (!tbody) return;

        if (paged.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="empty-table-state"><p>No hay atenciones registradas en este contexto.</p></td></tr>`;
        } else {
            tbody.innerHTML = paged.map(a => `
                <tr>
                    <td class="record-code">${a.folio}</td>
                    <td class="record-name">${a.solicitante_nombre}</td>
                    <td>${a.delegacion_nombre}</td>
                    <td><span class="record-name">${a.tipo_nombre}</span><span class="record-secondary">${a.subtipo_nombre}</span></td>
                    <td>${a.responsable_nombre}</td>
                    <td class="record-date">${a.fecha_registro}</td>
                </tr>
            `).join("");
        }

        this.renderPaginationControls("atenciones", total, conf.page, totalPages, startIdx, paged.length);
    }

    // =========================================================================
    // CONTROLES DE PAGINACIÓN GENÉRICOS (DISEÑOS C3 - C5)
    // =========================================================================
    renderPaginationControls(moduleName, total, currentPage, totalPages, startIdx, pagedCount) {
        const footer = document.getElementById(`pagination-${moduleName}`);
        if (!footer) return;

        const endIdx = total === 0 ? 0 : startIdx + pagedCount;
        const showingText = total === 0 ? "Mostrando 0 de 0 registros" : `Mostrando ${startIdx + 1} a ${endIdx} de ${total} registros`;

        let pagesHtml = "";
        const pages = new Set([1, totalPages]);
        const windowStart = Math.max(2, Math.min(currentPage - 1, totalPages - 3));
        const windowEnd = Math.min(totalPages - 1, windowStart + 2);
        for (let page = windowStart; page <= windowEnd; page++) pages.add(page);
        let previousPage = 0;
        for (const page of [...pages].sort((first, second) => first - second)) {
            if (previousPage && page - previousPage > 1) {
                pagesHtml += '<span class="pagination-ellipsis" aria-hidden="true">…</span>';
            }
            pagesHtml += `<button type="button" class="btn-page ${page === currentPage ? 'active' : ''}" ${page === currentPage ? 'aria-current="page"' : ''} aria-label="Página ${page}" onclick="sgrApp.goToPage('${moduleName}', ${page})">${page}</button>`;
            previousPage = page;
        }

        footer.innerHTML = `
            <span>${showingText}</span>
            <nav class="pagination-controls" aria-label="Paginación de registros">
                <button type="button" class="btn-page" ${currentPage <= 1 ? 'disabled' : ''} onclick="sgrApp.goToPage('${moduleName}', ${currentPage - 1})">Anterior</button>
                ${pagesHtml}
                <button type="button" class="btn-page" ${currentPage >= totalPages ? 'disabled' : ''} onclick="sgrApp.goToPage('${moduleName}', ${currentPage + 1})">Siguiente</button>
            </nav>
        `;
    }

    goToPage(moduleName, pageNum) {
        if (this.pagination[moduleName]) {
            this.pagination[moduleName].page = pageNum;
            this.renderCurrentView();
        }
    }

    onSearchInput(moduleName, value) {
        if (this.pagination[moduleName]) {
            this.pagination[moduleName].search = value;
            this.pagination[moduleName].page = 1;
            this.renderCurrentView();
        }
    }

    onFilterChange(moduleName, filterValue) {
        if (this.pagination[moduleName]) {
            this.pagination[moduleName].filter = filterValue;
            this.pagination[moduleName].page = 1;
            this.renderCurrentView();
        }
    }

    exportModuleToExcel(moduleName) {
        let list = sgrDb.data[moduleName] || [];
        const conf = this.pagination[moduleName];

        if (conf) {
            // Si el usuario es delegado municipal, restringir usuarios a su delegación
            if (moduleName === "usuarios" && this.currentUser?.rol_codigo === "ROL03") {
                list = list.filter(u => u.delegacion_codigo === this.currentUser.delegacion_codigo);
            }
            // En atenciones, filtrar por delegación activa si está definida
            if (moduleName === "atenciones" && this.activeDelegacion) {
                list = list.filter(a => a.delegacion_codigo === this.activeDelegacion);
            }
            // Filtro por estado
            if (conf.filter && conf.filter !== "TODOS") {
                list = list.filter(item => (item.estado || "").toUpperCase() === conf.filter);
            }
            // Filtro de búsqueda por texto
            list = this.filterByVisibleColumns(moduleName, list);
        }

        const titles = {
            "delegaciones": "SGR_Delegaciones_LaSerena",
            "roles": "SGR_Roles_Permisos_LaSerena",
            "usuarios": "SGR_Usuarios_LaSerena",
            "items_metas": "SGR_Items_Metas_LaSerena",
            "tipos_atencion": "SGR_Tipos_Atencion_LaSerena",
            "sub_atenciones": "SGR_Sub_Atenciones_LaSerena",
            "atenciones": "SGR_Atenciones_Ciudadanas_LaSerena"
        };
        exportToExcel(list, titles[moduleName] || "SGR_Reporte");
    }

    // =========================================================================
    // MODALES GENÉRICOS (CREAR, EDITAR, VER DETALLE)
    // =========================================================================
    openModalNew(moduleName) {
        this.newUserPhoto = null;
        this.newUserPhotoPending = null;
        const modal = document.getElementById("sgr-crud-modal");
        const titleEl = document.getElementById("modal-crud-title");
        const bodyEl = document.getElementById("modal-crud-body");
        const saveBtn = document.getElementById("btn-modal-save");

        saveBtn.style.display = "";
        saveBtn.disabled = false;
        saveBtn.onclick = () => this.handleSaveModal(moduleName, null);

        switch (moduleName) {
            case "delegaciones":
                titleEl.textContent = "Nueva Delegación Municipal";
                bodyEl.innerHTML = `
                    <p class="form-meta-note">El código de la delegación se genera automáticamente al guardar.</p>
                    <div class="form-group"><label class="form-label">Nombre *</label><input type="text" id="m-del-nombre" class="form-control" placeholder="Ej: Delegación Tierras Blancas"></div>
                    <div class="form-group"><label class="form-label">Dirección *</label><input type="text" id="m-del-direccion" class="form-control" placeholder="Ej: Av. Balmaceda 1200"></div>
                    <div class="form-group"><label class="form-label">Comuna</label><input type="text" id="m-del-comuna" class="form-control" value="La Serena" readonly></div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-del-estado" class="form-control">
                            <option value="Activa">Activa</option>
                            <option value="Inactiva">Inactiva</option>
                        </select>
                    </div>
                `;
                break;
            case "roles":
                titleEl.textContent = "Nuevo Rol del Sistema";
                bodyEl.innerHTML = `
                    <p class="form-meta-note">El código del rol se genera automáticamente al guardar.</p>
                    <div class="form-group"><label class="form-label">Nombre de Rol *</label><input type="text" id="m-rol-nombre" class="form-control" placeholder="Ej: Inspector Territorial"></div>
                    <div class="form-group"><label class="form-label">Descripción</label><input type="text" id="m-rol-desc" class="form-control" placeholder="Alcance operativo"></div>
                    <div class="form-group"><label class="form-label">Alcance</label><input type="text" id="m-rol-alcance" class="form-control" value="Delegación"></div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-rol-estado" class="form-control">
                            <option value="Activo">Activo</option>
                            <option value="Inactivo">Inactivo</option>
                        </select>
                    </div>
                `;
                break;
            case "usuarios":
                titleEl.textContent = "Nuevo Usuario";
                bodyEl.innerHTML = `
                    <div class="new-user-photo">
                        <img id="m-usr-foto-preview" class="profile-avatar" src="/assets/municipal/avatar-default.svg" alt="Foto de perfil del nuevo usuario">
                        <div>
                            <label class="form-label" for="m-usr-foto">Foto de perfil</label>
                            <input type="file" id="m-usr-foto" class="profile-file-input" accept="image/jpeg,image/png,image/webp" aria-describedby="m-usr-foto-help" onchange="sgrApp.selectNewUserPhoto(this)">
                            <p id="m-usr-foto-help" class="profile-help">Opcional. JPG, PNG o WebP, hasta 5 MB. Si no eliges una foto, se asignará el avatar predeterminado.</p>
                        </div>
                    </div>
                    <div class="form-group"><label class="form-label" for="m-usr-rut">RUT *</label><input type="text" id="m-usr-rut" class="form-control" placeholder="12.345.678-5" data-rut required maxlength="12" aria-describedby="m-usr-rut-help m-usr-rut-format"><p id="m-usr-rut-format" class="rut-hint">* Ejemplo: 12.345.678-5. Incluye siempre el dígito verificador (número o K).</p><p id="m-usr-rut-help" class="rut-feedback" aria-live="polite"></p></div>
                    <div class="form-group"><label class="form-label">Nombre Completo *</label><input type="text" id="m-usr-nombre" class="form-control" placeholder="Nombre y apellidos"></div>
                    <div class="form-group"><label class="form-label">Correo Institucional *</label><input type="email" id="m-usr-email" class="form-control" placeholder="usuario@laserena.cl"></div>
                    <div class="form-group"><label class="form-label">Rol *</label>
                        <select id="m-usr-rol" class="form-control">
                            ${sgrDb.data.roles.map(r => `<option value="${r.codigo}">${r.nombre}</option>`).join("")}
                        </select>
                    </div>
                    <div class="form-group"><label class="form-label">Delegación Asignada *</label>
                        <select id="m-usr-delegacion" class="form-control">
                            ${sgrDb.data.delegaciones.map(d => `<option value="${d.codigo}">${d.nombre}</option>`).join("")}
                        </select>
                    </div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-usr-estado" class="form-control">
                            <option value="Activo">Activo</option>
                            <option value="Inactivo">Inactivo</option>
                        </select>
                    </div>
                `;
                break;
            case "items_metas":
                titleEl.textContent = "Nuevo Ítem y Meta";
                bodyEl.innerHTML = `
                    <p class="form-meta-note">El código del ítem y meta se genera automáticamente al guardar.</p>
                    <div class="form-group"><label class="form-label">Nombre *</label><input type="text" id="m-itm-nombre" class="form-control" placeholder="Nombre del ítem"></div>
                    <div class="form-group"><label class="form-label">Descripción</label><input type="text" id="m-itm-desc" class="form-control" placeholder="Descripción de la meta"></div>
                    <div class="form-group"><label class="form-label">Unidad de Medida</label><input type="text" id="m-itm-unidad" class="form-control" value="Atenciones"></div>
                    <div class="form-group"><label class="form-label">Meta Cantidad</label><input type="text" id="m-itm-meta" class="form-control" value="100" readonly aria-describedby="m-itm-meta-help"><small id="m-itm-meta-help" class="profile-help">Cantidad asignada automáticamente por el sistema.</small></div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-itm-estado" class="form-control">
                            <option value="Activo">Activo</option>
                            <option value="Inactivo">Inactivo</option>
                        </select>
                    </div>
                `;
                break;
            case "tipos_atencion":
                titleEl.textContent = "Nuevo Tipo de Atención";
                bodyEl.innerHTML = `
                    <p class="form-meta-note">El código del tipo de atención se genera automáticamente al guardar.</p>
                    <div class="form-group"><label class="form-label">Nombre *</label><input type="text" id="m-ta-nombre" class="form-control" placeholder="Ej: Medio Ambiente"></div>
                    <div class="form-group"><label class="form-label">Descripción</label><input type="text" id="m-ta-desc" class="form-control" placeholder="Descripción general"></div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-ta-estado" class="form-control">
                            <option value="Activo">Activo</option>
                            <option value="Inactivo">Inactivo</option>
                        </select>
                    </div>
                `;
                break;
            case "sub_atenciones":
                titleEl.textContent = "Nueva Sub Atención";
                bodyEl.innerHTML = `
                    <p class="form-meta-note">El código de la subatención se genera automáticamente al guardar.</p>
                    <div class="form-group"><label class="form-label">Nombre *</label><input type="text" id="m-sa-nombre" class="form-control" placeholder="Nombre de la subatención"></div>
                    <div class="form-group"><label class="form-label">Tipo Asociado *</label>
                        <select id="m-sa-tipo" class="form-control">
                            ${sgrDb.data.tipos_atencion.map(t => `<option value="${t.codigo}">${t.nombre}</option>`).join("")}
                        </select>
                    </div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-sa-estado" class="form-control">
                            <option value="Activa">Activa</option>
                            <option value="Inactiva">Inactiva</option>
                        </select>
                    </div>
                `;
                break;
        }

        modal.classList.add("active");
    }

    openModalEdit(moduleName, id) {
        const item = sgrDb.data[moduleName].find(x => x.id == id);
        if (!item) return;

        const modal = document.getElementById("sgr-crud-modal");
        const titleEl = document.getElementById("modal-crud-title");
        const bodyEl = document.getElementById("modal-crud-body");
        const saveBtn = document.getElementById("btn-modal-save");

        saveBtn.style.display = "";
        saveBtn.disabled = false;
        saveBtn.onclick = () => this.handleSaveModal(moduleName, id);

        switch (moduleName) {
            case "delegaciones":
                titleEl.textContent = `Editar Delegación: ${item.codigo}`;
                bodyEl.innerHTML = `
                    <div class="form-group"><label class="form-label">Código</label><input type="text" class="form-control" value="${item.codigo}" readonly></div>
                    <div class="form-group"><label class="form-label">Nombre *</label><input type="text" id="m-del-nombre" class="form-control" value="${item.nombre}"></div>
                    <div class="form-group"><label class="form-label">Dirección *</label><input type="text" id="m-del-direccion" class="form-control" value="${item.direccion}"></div>
                    <div class="form-group"><label class="form-label">Comuna</label><input type="text" id="m-del-comuna" class="form-control" value="${item.comuna}"></div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-del-estado" class="form-control">
                            <option value="Activa" ${item.estado === "Activa" ? 'selected' : ''}>Activa</option>
                            <option value="Inactiva" ${item.estado === "Inactiva" ? 'selected' : ''}>Inactiva</option>
                        </select>
                    </div>
                `;
                break;
            case "roles":
                titleEl.textContent = `Editar Rol: ${item.nombre}`;
                bodyEl.innerHTML = `
                    <div class="form-group"><label class="form-label">Código</label><input type="text" class="form-control" value="${item.codigo}" readonly></div>
                    <div class="form-group"><label class="form-label">Nombre *</label><input type="text" id="m-rol-nombre" class="form-control" value="${item.nombre}"></div>
                    <div class="form-group"><label class="form-label">Descripción</label><input type="text" id="m-rol-desc" class="form-control" value="${item.descripcion || ''}"></div>
                    <div class="form-group"><label class="form-label">Alcance</label><input type="text" id="m-rol-alcance" class="form-control" value="${item.alcance}"></div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-rol-estado" class="form-control">
                            <option value="Activo" ${item.estado === "Activo" ? 'selected' : ''}>Activo</option>
                            <option value="Inactivo" ${item.estado === "Inactivo" ? 'selected' : ''}>Inactivo</option>
                        </select>
                    </div>
                `;
                break;
            case "usuarios":
                titleEl.textContent = `Editar Usuario: ${item.nombre}`;
                bodyEl.innerHTML = `
                    <div class="form-group"><label class="form-label">RUT</label><input type="text" class="form-control" value="${item.rut}" readonly></div>
                    <div class="form-group"><label class="form-label">Nombre *</label><input type="text" id="m-usr-nombre" class="form-control" value="${item.nombre}"></div>
                    <div class="form-group"><label class="form-label">Correo *</label><input type="email" id="m-usr-email" class="form-control" value="${item.email}"></div>
                    <div class="form-group"><label class="form-label">Rol</label>
                        <select id="m-usr-rol" class="form-control">
                            ${sgrDb.data.roles.map(r => `<option value="${r.codigo}" ${r.codigo === item.rol_codigo ? 'selected' : ''}>${r.nombre}</option>`).join("")}
                        </select>
                    </div>
                    <div class="form-group"><label class="form-label">Delegación Asignada</label>
                        <select id="m-usr-delegacion" class="form-control">
                            ${sgrDb.data.delegaciones.map(d => `<option value="${d.codigo}" ${d.codigo === item.delegacion_codigo ? 'selected' : ''}>${d.nombre}</option>`).join("")}
                        </select>
                    </div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-usr-estado" class="form-control">
                            <option value="Activo" ${item.estado === "Activo" ? 'selected' : ''}>Activo</option>
                            <option value="Inactivo" ${item.estado === "Inactivo" ? 'selected' : ''}>Inactivo</option>
                        </select>
                    </div>
                `;
                break;
            case "items_metas":
                titleEl.textContent = `Editar Ítem: ${item.nombre}`;
                bodyEl.innerHTML = `
                    <div class="form-group"><label class="form-label">Código</label><input type="text" class="form-control" value="${item.codigo}" readonly></div>
                    <div class="form-group"><label class="form-label">Nombre *</label><input type="text" id="m-itm-nombre" class="form-control" value="${item.nombre}"></div>
                    <div class="form-group"><label class="form-label">Descripción</label><input type="text" id="m-itm-desc" class="form-control" value="${item.descripcion}"></div>
                    <div class="form-group"><label class="form-label">Unidad de Medida</label><input type="text" id="m-itm-unidad" class="form-control" value="${item.unidad_medida}"></div>
                    <div class="form-group"><label class="form-label">Meta Cantidad</label><input type="text" id="m-itm-meta" class="form-control" value="${item.meta_cantidad}" readonly aria-describedby="m-itm-meta-help"><small id="m-itm-meta-help" class="profile-help">Cantidad asignada automáticamente por el sistema.</small></div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-itm-estado" class="form-control">
                            <option value="Activo" ${item.estado === "Activo" ? 'selected' : ''}>Activo</option>
                            <option value="Inactivo" ${item.estado === "Inactivo" ? 'selected' : ''}>Inactivo</option>
                        </select>
                    </div>
                `;
                break;
            case "tipos_atencion":
                titleEl.textContent = `Editar Tipo: ${item.nombre}`;
                bodyEl.innerHTML = `
                    <div class="form-group"><label class="form-label">Código</label><input type="text" class="form-control" value="${item.codigo}" readonly></div>
                    <div class="form-group"><label class="form-label">Nombre *</label><input type="text" id="m-ta-nombre" class="form-control" value="${item.nombre}"></div>
                    <div class="form-group"><label class="form-label">Descripción</label><input type="text" id="m-ta-desc" class="form-control" value="${item.descripcion}"></div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-ta-estado" class="form-control">
                            <option value="Activo" ${item.estado === "Activo" ? 'selected' : ''}>Activo</option>
                            <option value="Inactivo" ${item.estado === "Inactivo" ? 'selected' : ''}>Inactivo</option>
                        </select>
                    </div>
                `;
                break;
            case "sub_atenciones":
                titleEl.textContent = `Editar Sub Atención: ${item.nombre}`;
                bodyEl.innerHTML = `
                    <div class="form-group"><label class="form-label">Código</label><input type="text" class="form-control" value="${item.codigo}" readonly></div>
                    <div class="form-group"><label class="form-label">Nombre *</label><input type="text" id="m-sa-nombre" class="form-control" value="${item.nombre}"></div>
                    <div class="form-group"><label class="form-label">Tipo Asociado</label>
                        <select id="m-sa-tipo" class="form-control">
                            ${sgrDb.data.tipos_atencion.map(t => `<option value="${t.codigo}" ${t.codigo === item.tipo_codigo ? 'selected' : ''}>${t.nombre}</option>`).join("")}
                        </select>
                    </div>
                    <div class="form-group"><label class="form-label">Estado</label>
                        <select id="m-sa-estado" class="form-control">
                            <option value="Activa" ${item.estado === "Activa" ? 'selected' : ''}>Activa</option>
                            <option value="Inactiva" ${item.estado === "Inactiva" ? 'selected' : ''}>Inactiva</option>
                        </select>
                    </div>
                `;
                break;
        }

        modal.classList.add("active");
    }

    openModalView(moduleName, id) {
        if (this.nativeCrud) {
            const detail = document.getElementById(`record-detail-${id}`);
            if (!detail) return;
            document.getElementById("modal-crud-title").textContent = `Detalle de registro (${detail.dataset.recordName})`;
            document.getElementById("modal-crud-body").replaceChildren(detail.content.cloneNode(true));
            document.getElementById("btn-modal-save").style.display = "none";
            document.getElementById("sgr-crud-modal").classList.add("active");
            return;
        }
        const item = sgrDb.data[moduleName].find(x => x.id == id);
        if (!item) return;

        const modal = document.getElementById("sgr-crud-modal");
        const titleEl = document.getElementById("modal-crud-title");
        const bodyEl = document.getElementById("modal-crud-body");
        const saveBtn = document.getElementById("btn-modal-save");

        saveBtn.style.display = "none"; // Sólo lectura
        titleEl.textContent = `Detalle de Registro (${item.codigo || item.nombre})`;

        let rowsHtml = "";
        for (const [k, v] of Object.entries(item)) {
            if (["id", "password_hash"].includes(k)) continue;
            rowsHtml += `
                <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #f0e6e4;">
                    <span style="font-weight:600; color:#6e6360; text-transform:capitalize;">${k.replace(/_/g, ' ')}:</span>
                    <span style="color:#2b2525; font-weight:500;">${v || '-'}</span>
                </div>
            `;
        }

        bodyEl.innerHTML = `<div style="font-size:0.92rem;">${rowsHtml}</div>`;
        modal.classList.add("active");
    }

    closeCrudModal() {
        if (this.newUserPhotoPending) {
            this.newUserPhotoPending = null;
            window.SGRPhotoCropper?.instance?.finish(null);
            document.getElementById("btn-modal-save").disabled = false;
        }
        const modal = document.getElementById("sgr-crud-modal");
        if (modal) modal.classList.remove("active");
    }

    async handleSaveModal(moduleName, id) {
        let payload = {};
        const saveButton = document.getElementById("btn-modal-save");
        if (saveButton.disabled) return;
        saveButton.disabled = true;

        try {
            if (moduleName === "delegaciones") {
                const nombre = document.getElementById("m-del-nombre").value.trim();
                const direccion = document.getElementById("m-del-direccion").value.trim();
                const comuna = document.getElementById("m-del-comuna").value.trim();
                const estado = document.getElementById("m-del-estado").value;
                if (!nombre || !direccion) throw new Error("Complete Nombre y Dirección.");
                payload = { nombre, direccion, comuna, estado };

            } else if (moduleName === "roles") {
                const nombre = document.getElementById("m-rol-nombre").value.trim();
                const descripcion = document.getElementById("m-rol-desc").value.trim();
                const alcance = document.getElementById("m-rol-alcance").value.trim();
                const estado = document.getElementById("m-rol-estado").value;
                if (!nombre) throw new Error("El nombre de rol es requerido.");
                payload = { nombre, descripcion, alcance, estado, permisos: "estandar" };

            } else if (moduleName === "usuarios") {
                const nombre = document.getElementById("m-usr-nombre").value.trim();
                const email = document.getElementById("m-usr-email").value.trim().toLowerCase();
                const rolCodigo = document.getElementById("m-usr-rol").value;
                const delCodigo = document.getElementById("m-usr-delegacion").value;
                const estado = document.getElementById("m-usr-estado").value;
                if (!nombre || !email) throw new Error("Nombre y correo son requeridos.");
                const rolObj = sgrDb.data.roles.find(r => r.codigo === rolCodigo);
                const delObj = sgrDb.data.delegaciones.find(d => d.codigo === delCodigo);
                payload = {
                    nombre, email, rol_codigo: rolCodigo,
                    rol_nombre: rolObj ? rolObj.nombre : rolCodigo,
                    delegacion_codigo: delCodigo,
                    delegacion_nombre: delObj ? delObj.nombre : delCodigo,
                    estado
                };
                if (!id) {
                    payload.rut = window.ChileanRut.require(document.getElementById("m-usr-rut"));
                    payload.password = "LaSerena2026*";
                    if (this.newUserPhotoPending) await this.newUserPhotoPending;
                    if (this.newUserPhoto) payload.foto_perfil = this.newUserPhoto;
                }

            } else if (moduleName === "items_metas") {
                const nombre = document.getElementById("m-itm-nombre").value.trim();
                const descripcion = document.getElementById("m-itm-desc").value.trim();
                const unidad = document.getElementById("m-itm-unidad").value.trim();
                const estado = document.getElementById("m-itm-estado").value;
                if (!nombre) throw new Error("El nombre es requerido.");
                payload = { nombre, descripcion, unidad_medida: unidad, estado };

            } else if (moduleName === "tipos_atencion") {
                const nombre = document.getElementById("m-ta-nombre").value.trim();
                const descripcion = document.getElementById("m-ta-desc").value.trim();
                const estado = document.getElementById("m-ta-estado").value;
                if (!nombre) throw new Error("El nombre es requerido.");
                payload = { nombre, descripcion, estado };

            } else if (moduleName === "sub_atenciones") {
                const nombre = document.getElementById("m-sa-nombre").value.trim();
                const tipoCodigo = document.getElementById("m-sa-tipo").value;
                const estado = document.getElementById("m-sa-estado").value;
                if (!nombre) throw new Error("El nombre es requerido.");
                const tipoObj = sgrDb.data.tipos_atencion.find(t => t.codigo === tipoCodigo);
                payload = {
                    nombre, tipo_codigo: tipoCodigo,
                    tipo_nombre: tipoObj ? tipoObj.nombre : tipoCodigo,
                    estado
                };
            }

            if (id) {
                await sgrDb.updateItem(moduleName, id, payload);
            } else {
                await sgrDb.createItem(moduleName, payload);
            }

            this.closeCrudModal();
            Swal.fire({
                title: "¡Guardado exitoso!",
                text: "Los datos han sido persistidos correctamente.",
                icon: "success",
                confirmButtonColor: "var(--primary)",
                timer: 2000
            });
            this.renderCurrentView();

        } catch (err) {
            Swal.fire({
                title: "No se pudo guardar",
                text: err.message,
                icon: "error",
                confirmButtonColor: "var(--primary)"
            });
        } finally {
            saveButton.disabled = false;
        }
    }

    confirmDelete(moduleName, id) {
        const item = sgrDb.data[moduleName].find(x => x.id == id);
        const nombre = item ? (item.nombre || item.codigo) : "el registro";

        // Regla de Integridad de Negocio (PDF): Subatenciones dependen de Tipos de Atención
        if (moduleName === "tipos_atencion") {
            const vinculados = sgrDb.data.sub_atenciones.filter(s => s.tipo_codigo === item.codigo);
            if (vinculados.length > 0) {
                Swal.fire({
                    title: "Restricción de Integridad",
                    text: `No es posible eliminar '${nombre}' porque existen ${vinculados.length} subatenciones vinculadas a él. Debe reasignar o desactivar primero.`,
                    icon: "error",
                    confirmButtonColor: "var(--primary)"
                });
                return;
            }
        }

        Swal.fire({
            title: "¿Confirmar eliminación?",
            text: `Se eliminará '${nombre}' del sistema. Esta acción no se puede deshacer.`,
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Sí, eliminar",
            cancelButtonText: "Cancelar",
            confirmButtonColor: "var(--primary)",
            cancelButtonColor: "#6e6360"
        }).then(async res => {
            if (res.isConfirmed) {
                try {
                    await sgrDb.deleteItem(moduleName, id);
                    Swal.fire({
                        title: "Registro eliminado",
                        text: `'${nombre}' ha sido eliminado exitosamente.`,
                        icon: "success",
                        confirmButtonColor: "var(--primary)",
                        timer: 2000
                    });
                    this.renderCurrentView();
                } catch (err) {
                    Swal.fire({
                        title: "Error al eliminar",
                        text: err.message,
                        icon: "error",
                        confirmButtonColor: "var(--primary)"
                    });
                }
            }
        });
    }

    // =========================================================================
    // FLUJO DE RECUPERACIÓN DE CONTRASEÑA EN 3 PASOS (DISEÑOS C1 & C2)
    // =========================================================================
    showAuthView(mode = "login") {
        document.getElementById("sgr-app-container").style.display = "none";
        document.getElementById("sgr-auth-container").style.display = "flex";

        const views = ["login", "recuperar-paso1", "recuperar-paso2", "recuperar-paso3"];
        views.forEach(v => {
            const el = document.getElementById(`auth-card-${v}`);
            if (el) el.style.display = (v === mode) ? "block" : "none";
        });

        if (mode === "recuperar-paso2") {
            this.startRecoveryTimer();
        }
    }

    showAppView() {
        document.getElementById("sgr-auth-container").style.display = "none";
        document.getElementById("sgr-app-container").style.display = "block";
        this.updateHeaderUserInfo();
        this.setupHeaderDelegacion();
        this.applyRolePermissions();
        if (this.nativeCrud) {
            document.querySelectorAll(".nav-link-btn").forEach(button => {
                const active = button.getAttribute("data-target") === this.currentView;
                button.classList.toggle("active", active);
                if (active) button.setAttribute("aria-current", "page");
                else button.removeAttribute("aria-current");
            });
        }
        this.renderCurrentView();
    }

    // Paso 1: Solicitar código
    async submitRecuperarPaso1(e) {
        if (e) e.preventDefault();
        const emailInput = document.getElementById("rec-email-input");
        const email = emailInput.value.trim().toLowerCase();

        if (!email || !email.includes("@")) {
            Swal.fire({
                title: "Correo Requerido",
                text: "Por favor ingrese un correo electrónico válido.",
                icon: "warning",
                confirmButtonColor: "var(--primary)"
            });
            return;
        }

        this.recoveryState.email = email;

        try {
            const response = await fetch("/api/auth/recuperar-codigo", {
                method: "POST", headers: {"Content-Type":"application/json"},
                body: JSON.stringify({email})
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.message);
        } catch (err) {
            Swal.fire({title:"No se pudo solicitar el código", text:err.message, icon:"error"});
            return;
        }
        this.recoveryState.attempts = 0;
        const emailSentReal = true;

        // Mensaje formal neutro: por seguridad el código NO se muestra en pantalla
        Swal.fire({
            title: "Instrucciones Enviadas",
            html: `
                <div style="font-size:0.95rem; line-height: 1.5; color: var(--text-main); text-align: left;">
                    <p style="margin-top:0;">Si la cuenta institucional se encuentra registrada en el sistema, hemos enviado las instrucciones y el <strong>código de verificación de 6 dígitos</strong> a su correo electrónico.</p>
                    <div style="background: #fdfaf9; border-left: 4px solid var(--primary); padding: 10px 14px; border-radius: 4px; margin-top: 12px; font-size: 0.85rem; color: #5a4f4c;">
                        ${emailSentReal 
                            ? '✅ <strong>Correo despachado vía SMTP:</strong> Revise su bandeja de entrada o carpeta de spam.' 
                            : 'ℹ️ <strong>Bandeja institucional:</strong> El código ha sido despachado a su casilla de correo municipal.'}
                    </div>
                </div>
            `,
            icon: "success",
            confirmButtonColor: "var(--primary)",
            confirmButtonText: "Ingresar Código"
        }).then(() => {
            const emailMask = email.replace(/(.{2})(.*)(?=@)/, (gp1, gp2, gp3) => gp2 + "*".repeat(Math.max(gp3.length, 3)));
            const targetEl = document.getElementById("rec-masked-email");
            if (targetEl) targetEl.textContent = `Código enviado a ${emailMask}`;

            this.showAuthView("recuperar-paso2");
            setTimeout(() => {
                const firstDigit = document.querySelector(".digit-input[data-idx='0']");
                if (firstDigit) firstDigit.focus();
            }, 100);
        });
    }

    openEmailSimulatorModal() {
        Swal.fire({title:"Código de recuperación", text:"Revise el correo asociado a su cuenta. En desarrollo, el código se imprime en la consola del servidor.", icon:"info"});
    }

    setupDigitInputs() {
        const inputs = document.querySelectorAll(".digit-input");
        inputs.forEach((input, idx) => {
            input.addEventListener("input", (e) => {
                const val = e.target.value.replace(/[^0-9]/g, "");
                e.target.value = val ? val[0] : "";
                if (val && idx < inputs.length - 1) {
                    inputs[idx + 1].focus();
                }
            });

            input.addEventListener("keydown", (e) => {
                if (e.key === "Backspace" && !e.target.value && idx > 0) {
                    inputs[idx - 1].focus();
                }
            });

            input.addEventListener("paste", (e) => {
                e.preventDefault();
                const pasteData = (e.clipboardData || window.clipboardData).getData("text").replace(/[^0-9]/g, "");
                if (pasteData) {
                    pasteData.split("").slice(0, 6).forEach((char, i) => {
                        if (inputs[i]) inputs[i].value = char;
                    });
                    if (inputs[Math.min(pasteData.length, 5)]) {
                        inputs[Math.min(pasteData.length, 5)].focus();
                    }
                }
            });
        });
    }

    async submitValidarCodigo(e) {
        if (e) e.preventDefault();
        const inputs = document.querySelectorAll(".digit-input");
        const entered = Array.from(inputs).map(i => i.value).join("");

        if (entered.length < 6) {
            Swal.fire({
                title: "Código Incompleto",
                text: "Debe ingresar las 6 casillas numéricas del código.",
                icon: "warning",
                confirmButtonColor: "var(--primary)"
            });
            return;
        }

        if (this.recoveryState.timerSeconds <= 0) {
            Swal.fire({
                title: "Código Expirado",
                text: "El tiempo de vigencia de 10 minutos ha vencido. Por favor solicite un nuevo código.",
                icon: "error",
                confirmButtonColor: "var(--primary)"
            });
            return;
        }

        this.recoveryState.attempts++;
        if (this.recoveryState.attempts > 3) {
            Swal.fire({
                title: "Límite Superado",
                text: "Ha superado el límite de 3 intentos fallidos. Debe iniciar una nueva solicitud.",
                icon: "error",
                confirmButtonColor: "var(--primary)"
            });
            this.showAuthView("recuperar-paso1");
            return;
        }

        // Validación con backend o local
        let isValid = false;
        try {
            const response = await fetch("/api/auth/validar-codigo", {
                method:"POST", headers:{"Content-Type":"application/json"},
                body:JSON.stringify({email:this.recoveryState.email, codigo:entered})
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.message);
            isValid = result.success;
        } catch (err) {
            Swal.fire({title:"No se pudo verificar el código", text:err.message, icon:"error"});
            return;
        }

        if (!isValid) {
            const intentosRestantes = 3 - this.recoveryState.attempts;
            Swal.fire({
                title: "Código Incorrecto",
                text: `El código ingresado no es válido. Le quedan ${intentosRestantes} intentos.`,
                icon: "error",
                confirmButtonColor: "var(--primary)"
            });
            return;
        }

        clearInterval(this.recoveryState.timerInterval);
        Swal.fire({
            title: "Código Verificado",
            text: "Identidad confirmada exitosamente. Proceda a crear su nueva contraseña.",
            icon: "success",
            confirmButtonColor: "var(--primary)",
            timer: 1800
        }).then(() => {
            this.showAuthView("recuperar-paso3");
        });
    }

    // Paso 3: Crear nueva clave
    setupPasswordStrengthChecker() {
        const passInput = document.getElementById("new-password-input");
        const confirmInput = document.getElementById("confirm-password-input");
        if (!passInput || !confirmInput) return;

        const checkRules = () => {
            const val = passInput.value;
            const conf = confirmInput.value;

            const rLen = val.length >= 8;
            const rMay = /[A-Z]/.test(val);
            const rNum = /[0-9]/.test(val);
            const rSpec = /[^A-Za-z0-9]/.test(val);
            const rMatch = val.length > 0 && val === conf;

            this.updateReqItem("req-len", rLen);
            this.updateReqItem("req-may", rMay);
            this.updateReqItem("req-num", rNum);
            this.updateReqItem("req-spec", rSpec);
            this.updateReqItem("req-match", rMatch);
        };

        passInput.addEventListener("input", checkRules);
        confirmInput.addEventListener("input", checkRules);
    }

    updateReqItem(id, isValid) {
        const el = document.getElementById(id);
        if (!el) return;
        if (isValid) {
            el.classList.add("valid");
            el.querySelector("i")?.setAttribute("data-lucide", "check");
        } else {
            el.classList.remove("valid");
            el.querySelector("i")?.setAttribute("data-lucide", "circle");
        }
        if (window.lucide) lucide.createIcons();
    }

    async submitCrearNuevaPassword(e) {
        if (e) e.preventDefault();
        const pass = document.getElementById("new-password-input").value;
        const confirm = document.getElementById("confirm-password-input").value;

        if (pass.length < 8 || !/[A-Z]/.test(pass) || !/[0-9]/.test(pass) || !/[^A-Za-z0-9]/.test(pass)) {
            Swal.fire({
                title: "Requisitos no cumplidos",
                text: "La contraseña no cumple con todas las políticas de seguridad institucionales.",
                icon: "warning",
                confirmButtonColor: "var(--primary)"
            });
            return;
        }

        if (pass !== confirm) {
            Swal.fire({
                title: "Las contraseñas no coinciden",
                text: "Por favor confirme la misma contraseña en ambos campos.",
                icon: "error",
                confirmButtonColor: "var(--primary)"
            });
            return;
        }

        try {
            if (sgrDb.hasBackend) {
                const response = await fetch("/api/auth/cambiar-password", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: this.recoveryState.email, password: pass })
                });
                const result = await response.json();
                if (!response.ok || !result.success) {
                    throw new Error(result.message || "No se pudo actualizar la contraseña.");
                }
            }

            Swal.fire({
                title: "¡Contraseña Actualizada!",
                text: "Su contraseña ha sido cambiada exitosamente. Ahora puede iniciar sesión con su nueva clave.",
                icon: "success",
                confirmButtonColor: "var(--primary)"
            }).then(() => {
                this.showAuthView("login");
            });
        } catch (err) {
            Swal.fire({ title: "Error", text: err.message, icon: "error", confirmButtonColor: "var(--primary)" });
        }
    }

    redirectAfterLogin() {
        const next = document.getElementById("login-next")?.value;
        if (!next) return false;
        try {
            const destination = new URL(next, window.location.origin);
            if (destination.origin === window.location.origin && destination.pathname !== "/acceso/") {
                window.location.assign(destination.pathname + destination.search + destination.hash);
                return true;
            }
        } catch (_) { /* Un destino inválido mantiene la pantalla original. */ }
        return false;
    }

    // Login Tradicional
    async submitLogin(e) {
        if (e) e.preventDefault();
        const usrInput = document.getElementById("login-username").value.trim();
        const passInput = document.getElementById("login-password").value;

        if (!usrInput || !passInput) {
            Swal.fire({
                title: "Campos requeridos",
                text: "Debe ingresar su usuario o correo y contraseña.",
                icon: "warning",
                confirmButtonColor: "var(--primary)"
            });
            return;
        }

        let user = null;

        // Intentar autenticación formal en Backend API
        if (sgrDb.hasBackend) {
            try {
                const res = await fetch("/api/auth/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ usuario: usrInput, password: passInput })
                });
                const data = await res.json();
                if (res.ok && data.success && data.user) {
                    user = data.user;
                } else {
                    Swal.fire({
                        title: res.status >= 500 ? "Error del servidor" : "Error de autenticación",
                        text: data.message || (res.status >= 500 ? "No se pudo iniciar sesión. Intente nuevamente." : "Usuario o contraseña no válidos."),
                        icon: "error",
                        confirmButtonColor: "var(--primary)"
                    });
                    return;
                }
            } catch (err) {
                console.warn("Backend auth fetch error:", err);
                Swal.fire({ title: "Error de conexión", text: "No se pudo conectar con el servidor. Intente nuevamente.", icon: "error" });
                return;
            }
        }


        if (!user) {
            Swal.fire({
                title: "Credenciales Incorrectas",
                text: "Usuario o contraseña no válidos. Verifique sus credenciales institucionales.",
                icon: "error",
                confirmButtonColor: "var(--primary)"
            });
            return;
        }

        if (user.estado !== "Activo") {
            Swal.fire({
                title: "Cuenta Inactiva",
                text: "Su usuario se encuentra inactivo. Contacte al administrador municipal.",
                icon: "error",
                confirmButtonColor: "var(--primary)"
            });
            return;
        }

        this.currentUser = { ...user };
        this.activeDelegacion = user.delegacion_codigo || "DEL01";
        if (this.redirectAfterLogin()) return;
        await sgrDb.syncFromBackend();

        Swal.fire({
            title: `¡Bienvenido, ${user.nombre}!`,
            text: `Sesión iniciada como ${user.rol_nombre || 'Funcionario'} en ${user.delegacion_nombre || 'Centro'}.`,
            icon: "success",
            confirmButtonColor: "var(--primary)",
            timer: 2000
        }).then(() => {
            this.showAppView();
        });
    }

    logout() {
        Swal.fire({
            title: "¿Cerrar sesión?",
            text: "¿Está seguro que desea salir del Sistema Municipal SGR?",
            icon: "question",
            showCancelButton: true,
            confirmButtonText: "Sí, salir",
            cancelButtonText: "Cancelar",
            confirmButtonColor: "var(--primary)"
        }).then(async res => {
            if (res.isConfirmed) {
                const response = await fetch("/api/profile", {method:"DELETE"});
                if (!response.ok) {
                    Swal.fire({title:"Error", text:"No se pudo cerrar la sesión.", icon:"error"});
                    return;
                }
                this.profileController?.dismiss();
                this.currentUser = null;
                localStorage.removeItem("SGR_SESSION_USER");
                localStorage.removeItem("SGR_AUTH_SESSION_USER");
                document.getElementById("login-password").value = "";
                this.showAuthView("login");
            }
        });
    }

    setupEventListeners() {
        this.setupDigitInputs();
        this.setupPasswordStrengthChecker();
    }
}

// Inicializador global
let sgrApp;
document.addEventListener("DOMContentLoaded", () => {
    sgrApp = new SGRApplication();
    sgrApp.init();
});
