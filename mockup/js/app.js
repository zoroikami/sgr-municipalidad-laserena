/**
 * SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - MUNICIPALIDAD DE LA SERENA
 * app.js - Controlador Principal del Prototipo Funcional SPA
 */

class SGRApp {
    constructor() {
        this.currentView = "ficha";
        this.currentUser = null;
        this.currentCasoSocial = null;
        this.currentActividadValidando = null;
        this.filterValidacionEstado = "TODAS";
        this.chartFuncionarios = null;
        this.chartAgenda = null;
    }

    init() {
        // Cargar usuario inicial (Carlos Miranda - Funcionario Territorial)
        const data = window.sgrStorage.getData();
        this.currentUser = data.usuarios[0];

        // Configurar selector de usuario en navbar
        const userSwitcher = document.getElementById("select-user-switcher");
        if (userSwitcher) {
            userSwitcher.value = this.currentUser.id;
        }

        // Configurar tema guardado
        const savedTheme = localStorage.getItem("SGR_THEME") || "light";
        document.documentElement.setAttribute("data-theme", savedTheme);
        this.updateThemeIcon(savedTheme);

        // Atajo de teclado para búsqueda (Ctrl+K o Cmd+K)
        document.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
                e.preventDefault();
                this.openSearchModal();
            }
            if (e.key === "Escape") {
                this.closeAllModals();
            }
        });

        // Toggle sidebar en móvil
        const btnToggle = document.getElementById("btn-toggle-sidebar");
        if (btnToggle) {
            btnToggle.addEventListener("click", () => {
                document.getElementById("sidebar").classList.toggle("open");
            });
        }

        // Inicializar fecha actual en formulario
        const fechaInput = document.getElementById("form-act-fecha");
        if (fechaInput) {
            fechaInput.value = new Date().toISOString().slice(0, 10);
        }

        // Renderizar interfaz inicial
        this.updateUserContextUI();
        this.navigate("ficha");
        this.actualizarNotificaciones();
    }

    /**
     * Navegación entre vistas SPA
     */
    navigate(viewId) {
        this.currentView = viewId;

        // Ocultar todas las secciones
        document.querySelectorAll(".sgr-view").forEach(sec => sec.style.display = "none");
        
        // Quitar estado activo de los menús
        document.querySelectorAll(".menu-item").forEach(item => item.classList.remove("active"));

        // Mostrar la sección seleccionada
        const targetView = document.getElementById(`view-${viewId}`);
        if (targetView) {
            targetView.style.display = "block";
        }

        const targetNav = document.getElementById(`nav-item-${viewId}`);
        if (targetNav) {
            targetNav.classList.add("active");
        }

        // Cerrar sidebar en móvil si está abierto
        const sidebar = document.getElementById("sidebar");
        if (sidebar && sidebar.classList.contains("open")) {
            sidebar.classList.remove("open");
        }

        // Renderizar contenido dinámico según la vista
        switch (viewId) {
            case "ficha":
                this.renderFicha();
                break;
            case "actividades":
                this.renderActividades();
                break;
            case "validacion":
                this.renderValidacion();
                break;
            case "agenda":
                this.renderAgenda();
                break;
            case "resumen":
                this.renderResumen();
                break;
            case "social":
                this.renderSocial();
                break;
            case "semaforo":
                this.renderSemaforo();
                break;
            case "config":
                this.renderConfig();
                break;
            case "auditoria":
                this.renderAuditoria();
                break;
            case "trazabilidad":
                // Estática enriquecida
                break;
        }

        // Re-crear iconos de Lucide en caso de nuevos elementos
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    /**
     * Cambio de usuario / rol activo
     */
    changeUser(userId) {
        const data = window.sgrStorage.getData();
        const user = data.usuarios.find(u => u.id === userId);
        if (user) {
            this.currentUser = user;
            this.updateUserContextUI();
            this.showToast(`Cambiado a perfil: ${user.nombre} (${user.rolNombre})`, "info");
            this.navigate(this.currentView);
        }
    }

    updateUserContextUI() {
        const u = this.currentUser;
        // Actualizar sidebar
        document.getElementById("sidebar-user-name").textContent = u.nombre;
        document.getElementById("sidebar-user-role").textContent = `${u.rolNombre} - ${u.delegacionNombre}`;
        
        // Actualizar datos de período en top bar
        const data = window.sgrStorage.getData();
        const p = data.periodoActivo;
        document.getElementById("top-periodo-nombre").textContent = `${p.nombre}: Día ${p.diasTranscurridos}/${p.diasTotales} (${p.metaEsperadaPct}% esperado)`;
    }

    /**
     * VISTA 1: FICHA PERSONAL / MI DESEMPEÑO
     */
    renderFicha() {
        const data = window.sgrStorage.getData();
        const ficha = window.SGRCalculations.calcularFichaFuncionario(
            this.currentUser,
            data.itemsMedicion,
            data.actividades,
            data.periodoActivo
        );

        // Títulos
        document.getElementById("ficha-user-title").textContent = `Ficha de Desempeño: ${this.currentUser.nombre}`;
        document.getElementById("ficha-user-subtitle").textContent = `Cargo: ${this.currentUser.cargo} | ${this.currentUser.delegacionNombre} | Período: ${data.periodoActivo.nombre}`;

        // Banner del semáforo
        const badge = document.getElementById("ficha-semaforo-badge");
        badge.className = `badge-semaforo ${ficha.semaforo.claseCss}`;
        document.getElementById("ficha-semaforo-text").textContent = `${ficha.semaforo.texto} (${ficha.semaforo.color})`;
        
        document.getElementById("ficha-cumplimiento-headline").textContent = `${ficha.cumplimientoPonderadoTotal}% Ponderado Alcanzado`;
        document.getElementById("ficha-semaforo-explicacion").textContent = ficha.semaforo.descripcion;
        document.getElementById("ficha-meta-esperada-val").textContent = `${ficha.metaEsperadaAlDia}%`;

        // Badge en el menú lateral
        const badgeSidebar = document.getElementById("badge-mi-semaforo");
        badgeSidebar.textContent = ficha.semaforo.color;
        badgeSidebar.className = `badge-counter ${ficha.semaforo.color === "ROJO" ? "badge-alert" : ""}`;

        // Tabla de Ítems
        const tbody = document.getElementById("tbody-items-ficha");
        tbody.innerHTML = "";

        ficha.items.forEach(itm => {
            const tr = document.createElement("tr");
            
            let colorBarra = "bg-verde";
            if (itm.pctCumplimiento < 60) colorBarra = "bg-rojo";
            else if (itm.pctCumplimiento < 100) colorBarra = "bg-ambar";

            tr.innerHTML = `
                <td>
                    <div style="font-weight: 700;">${itm.nombre}</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">${itm.descripcion}</div>
                </td>
                <td><span style="font-size: 0.8rem; font-weight: 600;">${itm.unidad}</span></td>
                <td><strong style="color: var(--color-navy);">${itm.ponderacion}%</strong></td>
                <td><strong>${itm.metaTrimestral}</strong></td>
                <td><span class="badge-semaforo badge-semaforo-verde" style="font-size: 0.85rem;">${itm.avanceReal}</span></td>
                <td><strong>${itm.pctCumplimiento}%</strong></td>
                <td><strong style="color: #2563eb; font-size: 0.95rem;">${itm.puntajePonderado}%</strong></td>
                <td style="width: 140px;">
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill ${colorBarra}" style="width: ${Math.min(itm.pctCumplimiento, 100)}%;"></div>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Historial reciente del funcionario
        const tbodyActs = document.getElementById("tbody-ultimas-actividades-ficha");
        tbodyActs.innerHTML = "";
        const misActs = data.actividades.filter(a => a.funcionarioId === this.currentUser.id).slice(0, 5);

        if (misActs.length === 0) {
            tbodyActs.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">No ha registrado actividades en este período.</td></tr>`;
        } else {
            misActs.forEach(act => {
                let badgeEstado = '<span class="badge-semaforo badge-semaforo-verde">Aprobada</span>';
                if (act.estadoValidacion === "PENDIENTE") badgeEstado = '<span class="badge-semaforo badge-semaforo-ambar">Pendiente</span>';
                if (act.estadoValidacion === "RECHAZADA") badgeEstado = '<span class="badge-semaforo badge-semaforo-rojo">Rechazada</span>';

                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${act.codigoEvidencia}</strong></td>
                    <td>${act.fecha}</td>
                    <td>${act.itemNombre}</td>
                    <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${act.descripcion}</td>
                    <td>
                        <img src="${act.archivoEvidencia}" class="evidence-thumb" alt="Foto" onclick="sgrApp.openModalEvidencia('${act.id}')">
                    </td>
                    <td>${badgeEstado}</td>
                    <td style="font-size: 0.78rem; color: var(--text-secondary);">${act.observacionVerificador || "En espera de revisión DISERCO"}</td>
                `;
                tbodyActs.appendChild(tr);
            });
        }
    }

    /**
     * VISTA 2: REGISTRO DE ACTIVIDADES
     */
    renderActividades() {
        const data = window.sgrStorage.getData();
        
        // Generar código de evidencia
        const nuevoCodigo = window.SGRCalculations.generarCodigoEvidencia(data.actividades);
        document.getElementById("form-act-codigo").value = nuevoCodigo;
        document.getElementById("form-codigo-preview").textContent = nuevoCodigo;

        // Cargar ítems disponibles según el cargo del usuario
        const selectItem = document.getElementById("form-act-item");
        selectItem.innerHTML = "";
        
        const itemsCargo = data.itemsMedicion.filter(itm => itm.cargo === this.currentUser.cargo);
        itemsCargo.forEach(itm => {
            const opt = document.createElement("option");
            opt.value = itm.id;
            opt.textContent = `${itm.nombre} (Ponderación: ${itm.ponderacion}% | Meta: ${itm.metaTrimestral} ${itm.unidad})`;
            selectItem.appendChild(opt);
        });

        // Renderizar tabla completa de actividades
        this.renderTablaTodasActividades(data.actividades);
    }

    renderTablaTodasActividades(lista) {
        const tbody = document.getElementById("tbody-todas-actividades");
        tbody.innerHTML = "";

        lista.forEach(act => {
            let badgeEstado = '<span class="badge-semaforo badge-semaforo-verde">Aprobada</span>';
            if (act.estadoValidacion === "PENDIENTE") badgeEstado = '<span class="badge-semaforo badge-semaforo-ambar">Pendiente</span>';
            if (act.estadoValidacion === "RECHAZADA") badgeEstado = '<span class="badge-semaforo badge-semaforo-rojo">Rechazada</span>';

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${act.codigoEvidencia}</strong></td>
                <td>${act.fecha}</td>
                <td>${act.funcionarioNombre}</td>
                <td>${act.itemNombre}</td>
                <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${act.descripcion}</td>
                <td>
                    <img src="${act.archivoEvidencia}" class="evidence-thumb" alt="Foto" onclick="sgrApp.openModalEvidencia('${act.id}')">
                </td>
                <td>${badgeEstado}</td>
                <td>
                    <button class="btn btn-outline btn-sm" onclick="sgrApp.openModalEvidencia('${act.id}')">
                        <i data-lucide="eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        if (window.lucide) window.lucide.createIcons();
    }

    handleSubmitActividad(e) {
        e.preventDefault();

        const codigo = document.getElementById("form-act-codigo").value;
        const fecha = document.getElementById("form-act-fecha").value;
        const itemId = document.getElementById("form-act-item").value;
        const desc = document.getElementById("form-act-desc").value.trim();
        const accion = document.getElementById("form-act-accion").value.trim();
        const contacto = document.getElementById("form-act-contacto").value.trim();
        const telefono = document.getElementById("form-act-telefono").value.trim();
        const geo = document.getElementById("form-act-geo").value.trim();
        const ingresarAgenda = document.getElementById("form-act-agenda").checked;
        const imgSrc = document.getElementById("form-img-preview").src;

        // Validación de campos obligatorios (CU-08 / CU-09)
        if (!fecha || !itemId || !desc || !accion) {
            document.getElementById("modal-error-msg").textContent = "Todos los campos con asterisco rojo (*) son requeridos por el reglamento institucional.";
            this.openModal("modal-error-validacion");
            return;
        }

        const data = window.sgrStorage.getData();
        const itemObj = data.itemsMedicion.find(i => i.id === itemId);

        const nuevaActividad = {
            id: "ACT-2026-" + Date.now().toString().slice(-4),
            codigoEvidencia: codigo,
            fecha: fecha,
            funcionarioId: this.currentUser.id,
            funcionarioNombre: this.currentUser.nombre,
            delegacionId: this.currentUser.delegacionId,
            itemId: itemId,
            itemNombre: itemObj ? itemObj.nombre : "Actividad General",
            descripcion: desc,
            accionEjecutada: accion,
            contactoNombre: contacto || "No registrado",
            contactoTelefono: telefono || "Sin teléfono",
            ingresoAgenda: ingresarAgenda,
            estadoValidacion: "PENDIENTE",
            verificadorId: null,
            verificadorNombre: null,
            fechaValidacion: null,
            observacionVerificador: null,
            archivoEvidencia: imgSrc || "assets/evidencia_terreno.jpg",
            georreferencia: geo || "La Serena"
        };

        window.sgrStorage.addActividad(nuevaActividad);

        // Si se marcó ingresar a la agenda colectiva
        if (ingresarAgenda) {
            window.sgrStorage.addCompromiso({
                id: "TUB-2026-" + Date.now().toString().slice(-4),
                origen: desc.slice(0, 40),
                solicitante: contacto || "Comunidad Vecinal",
                territorio: geo || this.currentUser.delegacionNombre,
                responsableId: this.currentUser.id,
                responsableNombre: this.currentUser.nombre,
                areaApoyo: "Cuadrilla Municipal",
                fechaCompromiso: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
                estado: "INGRESADO",
                observaciones: `Originado por actividad ${codigo}: ${accion.slice(0, 80)}`,
                prioridad: "MEDIA",
                fechaIngreso: fecha
            });
        }

        this.showToast(`Actividad ${codigo} enviada exitosamente a la bandeja de verificación DISERCO.`, "success");
        this.resetFormActividad();
        this.renderActividades();
        this.actualizarNotificaciones();
    }

    resetFormActividad() {
        document.getElementById("form-act-desc").value = "";
        document.getElementById("form-act-accion").value = "";
        document.getElementById("form-act-contacto").value = "";
        document.getElementById("form-act-telefono").value = "";
        document.getElementById("form-act-agenda").checked = false;
        
        const data = window.sgrStorage.getData();
        const nuevoCodigo = window.SGRCalculations.generarCodigoEvidencia(data.actividades);
        document.getElementById("form-act-codigo").value = nuevoCodigo;
        document.getElementById("form-codigo-preview").textContent = nuevoCodigo;
    }

    handleImageUpload(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (evt) => {
                document.getElementById("form-img-preview").src = evt.target.result;
                document.getElementById("upload-box-text").textContent = `Fotografía cargada: ${file.name}`;
            };
            reader.readAsDataURL(file);
        }
    }

    triggerDuplicateModal() {
        this.openModal("modal-duplicado");
    }

    filterTablaActividades(texto) {
        const data = window.sgrStorage.getData();
        const q = texto.toLowerCase();
        const filtradas = data.actividades.filter(a => 
            a.codigoEvidencia.toLowerCase().includes(q) ||
            a.descripcion.toLowerCase().includes(q) ||
            a.funcionarioNombre.toLowerCase().includes(q) ||
            a.itemNombre.toLowerCase().includes(q)
        );
        this.renderTablaTodasActividades(filtradas);
    }

    /**
     * VISTA 3: BANDEJA DE VALIDACIÓN (ROL VERIFICADOR DISERCO)
     */
    renderValidacion() {
        const data = window.sgrStorage.getData();
        const tbody = document.getElementById("tbody-validacion");
        tbody.innerHTML = "";

        let lista = data.actividades;
        if (this.filterValidacionEstado !== "TODAS") {
            lista = lista.filter(a => a.estadoValidacion === this.filterValidacionEstado);
        }

        const pendientes = data.actividades.filter(a => a.estadoValidacion === "PENDIENTE").length;
        document.getElementById("badge-pendientes-validacion").textContent = pendientes;

        if (lista.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">No hay evidencias en este filtro.</td></tr>`;
            return;
        }

        lista.forEach(act => {
            let badgeEstado = '<span class="badge-semaforo badge-semaforo-verde">Aprobada</span>';
            if (act.estadoValidacion === "PENDIENTE") badgeEstado = '<span class="badge-semaforo badge-semaforo-ambar">Pendiente</span>';
            if (act.estadoValidacion === "RECHAZADA") badgeEstado = '<span class="badge-semaforo badge-semaforo-rojo">Rechazada</span>';

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${act.codigoEvidencia}</strong></td>
                <td>${act.fecha}</td>
                <td>${act.funcionarioNombre}</td>
                <td><span style="font-size: 0.78rem;">${act.delegacionId}</span></td>
                <td>${act.itemNombre}</td>
                <td>
                    <img src="${act.archivoEvidencia}" class="evidence-thumb" alt="Evidencia" onclick="sgrApp.openModalEvidencia('${act.id}')">
                </td>
                <td>${badgeEstado}</td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="sgrApp.openModalEvidencia('${act.id}')">
                        <i data-lucide="shield-check"></i>
                        <span>Evaluar</span>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        if (window.lucide) window.lucide.createIcons();
    }

    filtrarValidacion(estado) {
        this.filterValidacionEstado = estado;
        this.renderValidacion();
    }

    openModalEvidencia(actividadId) {
        const data = window.sgrStorage.getData();
        const act = data.actividades.find(a => a.id === actividadId);
        if (!act) return;

        this.currentActividadValidando = act;

        document.getElementById("modal-evi-titulo").textContent = `Revisión Técnica: ${act.codigoEvidencia}`;
        document.getElementById("modal-evi-subtitulo").textContent = `Funcionario: ${act.funcionarioNombre} | ${act.fecha}`;
        document.getElementById("modal-evi-img").src = act.archivoEvidencia;
        document.getElementById("modal-evi-geo").textContent = act.georreferencia || "La Serena";
        document.getElementById("modal-evi-item").textContent = act.itemNombre;
        document.getElementById("modal-evi-desc").textContent = `${act.descripcion} - Acción: ${act.accionEjecutada}`;
        document.getElementById("modal-evi-contacto").textContent = `${act.contactoNombre} (${act.contactoTelefono})`;
        document.getElementById("modal-evi-observacion").value = act.observacionVerificador || "";

        this.openModal("modal-evidencia");
    }

    dictaminarEvidencia(decision) {
        if (!this.currentActividadValidando) return;

        const obs = document.getElementById("modal-evi-observacion").value.trim();
        if (decision === "RECHAZADA" && !obs) {
            alert("Para rechazar una evidencia es obligatorio ingresar el fundamento u observación.");
            return;
        }

        // Obtener usuario verificador (Roberto Henríquez si el usuario activo no es verificador)
        const data = window.sgrStorage.getData();
        let verificador = this.currentUser;
        if (this.currentUser.rol !== "Verificador") {
            verificador = data.usuarios.find(u => u.rol === "Verificador") || this.currentUser;
        }

        window.sgrStorage.validarEvidencia(
            this.currentActividadValidando.id,
            decision,
            obs || "Evidencia fotográfica y datos conformes al protocolo institucional.",
            verificador
        );

        this.closeModal("modal-evidencia");
        this.showToast(`Evidencia ${this.currentActividadValidando.codigoEvidencia} dictaminada como ${decision}.`, decision === "APROBADA" ? "success" : "warning");

        // Refrescar vistas
        this.renderValidacion();
        this.renderFicha();
        this.actualizarNotificaciones();
    }

    /**
     * VISTA 4: AGENDA COLECTIVA / TUBO DE TRABAJO
     */
    renderAgenda() {
        const data = window.sgrStorage.getData();
        const compromisos = data.agendaColectiva;
        const desempeno = window.SGRCalculations.calcularDesempenoAgenda(compromisos);

        // Actualizar KPIs de cabecera
        document.getElementById("agenda-kpi-pct").textContent = `${desempeno.pctRealizado}%`;
        const subtext = document.getElementById("agenda-kpi-subtext");
        if (desempeno.cumpleUmbral80) {
            subtext.innerHTML = `<span style="color: var(--semaforo-verde); font-weight: 700;">Cumple umbral mínimo (≥ 80%)</span>`;
        } else {
            subtext.innerHTML = `<span style="color: var(--semaforo-rojo); font-weight: 700;">Bajo el 80% exigido (RN-006)</span>`;
        }

        document.getElementById("agenda-kpi-vencidos").textContent = desempeno.vencidosCount;
        document.getElementById("agenda-kpi-proceso").textContent = compromisos.filter(c => c.estado === "EN_PROCESO").length;
        document.getElementById("agenda-kpi-total").textContent = desempeno.total;

        // Badge en el menú lateral
        const badgeVencidos = document.getElementById("badge-vencidos");
        badgeVencidos.textContent = `${desempeno.vencidosCount} Vencido`;

        // Columnas
        const colIngresado = document.getElementById("kanban-col-ingresado");
        const colPendiente = document.getElementById("kanban-col-pendiente");
        const colEnProceso = document.getElementById("kanban-col-enproceso");
        const colRealizado = document.getElementById("kanban-col-realizado");

        colIngresado.innerHTML = "";
        colPendiente.innerHTML = "";
        colEnProceso.innerHTML = "";
        colRealizado.innerHTML = "";

        const counts = { INGRESADO: 0, PENDIENTE: 0, EN_PROCESO: 0, REALIZADO: 0 };
        const hoy = new Date().toISOString().slice(0, 10);

        compromisos.forEach(c => {
            counts[c.estado] = (counts[c.estado] || 0) + 1;
            const esVencido = c.estado !== "REALIZADO" && c.fechaCompromiso < hoy;

            const card = document.createElement("div");
            card.className = `kanban-card ${esVencido ? "vencido" : ""}`;
            card.innerHTML = `
                ${esVencido ? '<div style="color: var(--semaforo-rojo); font-size: 0.7rem; font-weight: 800; display: flex; align-items: center; gap: 4px; margin-bottom: 4px;"><i data-lucide="alarm-clock-off" style="width: 14px; height: 14px;"></i> ¡COMPROMISO VENCIDO (CA-03)!</div>' : ''}
                <div class="kanban-card-title">${c.origen}</div>
                <div class="kanban-card-meta">
                    <div><strong>Vecino:</strong> ${c.solicitante}</div>
                    <div><strong>Lugar:</strong> ${c.territorio}</div>
                    <div><strong>Responsable:</strong> ${c.responsableNombre}</div>
                    <div><strong>Fecha Límite:</strong> <span style="${esVencido ? 'color: var(--semaforo-rojo); font-weight: 700;' : ''}">${c.fechaCompromiso}</span></div>
                </div>
                <div style="font-size: 0.74rem; color: var(--text-secondary); background: var(--bg-app); padding: 6px; border-radius: 4px; margin-bottom: 8px;">
                    ${c.observaciones}
                </div>
                <div class="kanban-card-actions">
                    <select class="form-control" style="padding: 2px 6px; font-size: 0.74rem;" onchange="sgrApp.moverCompromiso('${c.id}', this.value)">
                        <option value="INGRESADO" ${c.estado === "INGRESADO" ? "selected" : ""}>1. Ingresado</option>
                        <option value="PENDIENTE" ${c.estado === "PENDIENTE" ? "selected" : ""}>2. Pendiente</option>
                        <option value="EN_PROCESO" ${c.estado === "EN_PROCESO" ? "selected" : ""}>3. En Proceso</option>
                        <option value="REALIZADO" ${c.estado === "REALIZADO" ? "selected" : ""}>4. Realizado</option>
                    </select>
                </div>
            `;

            if (c.estado === "INGRESADO") colIngresado.appendChild(card);
            else if (c.estado === "PENDIENTE") colPendiente.appendChild(card);
            else if (c.estado === "EN_PROCESO") colEnProceso.appendChild(card);
            else if (c.estado === "REALIZADO") colRealizado.appendChild(card);
        });

        // Actualizar contadores de cabecera de columna
        document.getElementById("badge-kanban-ingresado").textContent = counts.INGRESADO;
        document.getElementById("badge-kanban-pendiente").textContent = counts.PENDIENTE;
        document.getElementById("badge-kanban-enproceso").textContent = counts.EN_PROCESO;
        document.getElementById("badge-kanban-realizado").textContent = counts.REALIZADO;

        if (window.lucide) window.lucide.createIcons();
    }

    moverCompromiso(compromisoId, nuevoEstado) {
        window.sgrStorage.updateEstadoCompromiso(compromisoId, nuevoEstado);
        this.showToast(`Compromiso movido a estado: ${nuevoEstado}`, "info");
        this.renderAgenda();
    }

    openNuevoCompromisoModal() {
        document.getElementById("modal-comp-fecha").value = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
        this.openModal("modal-nuevo-compromiso");
    }

    handleSubmitCompromiso(e) {
        e.preventDefault();
        const origen = document.getElementById("modal-comp-origen").value;
        const solicitante = document.getElementById("modal-comp-solicitante").value;
        const territorio = document.getElementById("modal-comp-territorio").value;
        const fecha = document.getElementById("modal-comp-fecha").value;
        const area = document.getElementById("modal-comp-area").value;
        const obs = document.getElementById("modal-comp-obs").value;

        window.sgrStorage.addCompromiso({
            id: "TUB-2026-" + Date.now().toString().slice(-4),
            origen,
            solicitante,
            territorio,
            responsableId: this.currentUser.id,
            responsableNombre: this.currentUser.nombre,
            areaApoyo: area || "DISERCO Operaciones",
            fechaCompromiso: fecha,
            estado: "INGRESADO",
            observaciones: obs || "Compromiso ingresado a la agenda colectiva",
            prioridad: "MEDIA",
            fechaIngreso: new Date().toISOString().slice(0, 10)
        });

        this.closeModal("modal-nuevo-compromiso");
        this.showToast("Nuevo compromiso vecinal añadido al Tubo de Trabajo.", "success");
        this.renderAgenda();
    }

    openAlertaVencidoModal() {
        this.openModal("modal-alerta-vencido");
    }

    reprogramarCompromiso(compromisoId) {
        const data = window.sgrStorage.getData();
        const comp = data.agendaColectiva.find(c => c.id === compromisoId);
        if (comp) {
            comp.fechaCompromiso = new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10);
            comp.observaciones += " | Reprogramado con fecha nueva e informado a directiva vecinal.";
            comp.estado = "EN_PROCESO";
            window.sgrStorage.saveData(data);
            this.closeModal("modal-alerta-vencido");
            this.showToast("Compromiso reprogramado exitosamente. Se notificó a la directiva.", "success");
            this.renderAgenda();
        }
    }

    openReasignarModal() {
        alert("Función de reasignación masiva de compromisos por licencia o feriado del funcionario (RF-019). Permite traspasar la agenda a otro miembro del equipo territorial.");
    }

    /**
     * VISTA 5: TABLERO RESUMEN DELEGACIÓN (CONSOLIDADO)
     */
    renderResumen() {
        const data = window.sgrStorage.getData();
        const delegacionId = this.currentUser.delegacionId || "DEL-RUR";
        const delObj = data.delegaciones.find(d => d.id === delegacionId) || data.delegaciones[0];

        document.getElementById("resumen-del-title").textContent = `Tablero Resumen ${delObj.nombre}`;

        // Personal medido de la delegación
        const tbody = document.getElementById("tbody-resumen-personal");
        tbody.innerHTML = "";

        const funcionariosDel = data.usuarios.filter(u => u.delegacionId === delObj.id || u.rol.includes("Territorial") || u.rol.includes("Social"));

        const chartLabels = [];
        const chartData = [];

        funcionariosDel.forEach(f => {
            const ficha = window.SGRCalculations.calcularFichaFuncionario(f, data.itemsMedicion, data.actividades, data.periodoActivo);
            const actsFuncionario = data.actividades.filter(a => a.funcionarioId === f.id);

            chartLabels.push(f.nombre.split(" ")[0]);
            chartData.push(ficha.cumplimientoPonderadoTotal);

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>
                    <div style="font-weight: 700;">${f.nombre}</div>
                    <div style="font-size: 0.72rem; color: var(--text-secondary);">${f.email}</div>
                </td>
                <td>${f.cargo}</td>
                <td>${f.ultimoIngreso || "2026-08-14"}</td>
                <td><span class="badge-counter" style="background: var(--bg-app); color: var(--text-primary);">${f.diasSinIngreso} días</span></td>
                <td><strong>${actsFuncionario.length}</strong></td>
                <td>${(actsFuncionario.length / 45).toFixed(2)} / día</td>
                <td><strong style="color: #2563eb; font-size: 0.95rem;">${ficha.cumplimientoPonderadoTotal}%</strong></td>
                <td><span class="badge-semaforo ${ficha.semaforo.claseCss}">${ficha.semaforo.texto}</span></td>
            `;
            tbody.appendChild(tr);
        });

        // Renderizar gráficos de Chart.js
        this.renderChartsResumen(chartLabels, chartData);
    }

    renderChartsResumen(labels, dataValues) {
        // Gráfico 1: Cumplimiento de Funcionarios vs Meta Esperada
        const ctxFunc = document.getElementById("chart-resumen-funcionarios");
        if (ctxFunc) {
            if (this.chartFuncionarios) this.chartFuncionarios.destroy();

            this.chartFuncionarios = new Chart(ctxFunc, {
                type: "bar",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: "Cumplimiento Ponderado (%)",
                            data: dataValues,
                            backgroundColor: "#2563eb",
                            borderRadius: 6
                        },
                        {
                            label: "Meta Esperada al Día (49.5%)",
                            data: labels.map(() => 49.5),
                            type: "line",
                            borderColor: "#d69e2e",
                            borderWidth: 2,
                            borderDash: [5, 5],
                            pointRadius: 0,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, max: 100 }
                    }
                }
            });
        }

        // Gráfico 2: Estados de la Agenda Colectiva
        const ctxAgenda = document.getElementById("chart-resumen-agenda");
        if (ctxAgenda) {
            if (this.chartAgenda) this.chartAgenda.destroy();

            const data = window.sgrStorage.getData();
            const comp = data.agendaColectiva;
            const estados = {
                Ingresado: comp.filter(c => c.estado === "INGRESADO").length,
                Pendiente: comp.filter(c => c.estado === "PENDIENTE").length,
                EnProceso: comp.filter(c => c.estado === "EN_PROCESO").length,
                Realizado: comp.filter(c => c.estado === "REALIZADO").length
            };

            this.chartAgenda = new Chart(ctxAgenda, {
                type: "doughnut",
                data: {
                    labels: ["Ingresado", "Pendiente", "En Proceso", "Realizado"],
                    datasets: [{
                        data: [estados.Ingresado, estados.Pendiente, estados.EnProceso, estados.Realizado],
                        backgroundColor: ["#3b82f6", "#f59e0b", "#8b5cf6", "#10b981"]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
    }

    changeDelegacionFilter(delId) {
        this.currentUser.delegacionId = delId;
        this.renderResumen();
    }

    /**
     * VISTA 6: ATENCIÓN SOCIAL MULTIETAPA (RN-012)
     */
    renderSocial() {
        const atenciones = window.sgrStorage.getAtenciones();
        const tbody = document.getElementById("tbody-casos-sociales");
        tbody.innerHTML = "";

        atenciones.forEach(caso => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${caso.id}</strong></td>
                <td>${caso.rutBeneficiario}</td>
                <td>
                    <div style="font-weight: 700;">${caso.nombreBeneficiario}</div>
                    <div style="font-size: 0.72rem; color: var(--text-secondary);">${caso.direccion}</div>
                </td>
                <td><span class="badge-counter" style="background: rgba(37, 99, 235, 0.1); color: #2563eb;">${caso.tramoRSH}</span></td>
                <td><strong>Etapa ${caso.gestiones.length} de 3</strong></td>
                <td>${caso.gestiones[caso.gestiones.length - 1].fecha}</td>
                <td>${caso.responsableNombre}</td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="sgrApp.openModalCasoSocial('${caso.id}')">
                        <i data-lucide="folder-open"></i>
                        <span>Ver Ficha Multietapa</span>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        if (window.lucide) window.lucide.createIcons();
    }

    openModalCasoSocial(casoId) {
        const atenciones = window.sgrStorage.getAtenciones();
        const caso = atenciones.find(c => c.id === casoId);
        if (!caso) return;

        this.currentCasoSocial = caso;
        document.getElementById("modal-caso-titulo").textContent = `Ficha Social: ${caso.nombreBeneficiario}`;
        document.getElementById("modal-caso-subtitulo").textContent = `RUT: ${caso.rutBeneficiario} | Teléfono: ${caso.telefono} | ${caso.tramoRSH}`;

        const timeline = document.getElementById("modal-caso-timeline");
        timeline.innerHTML = "";

        caso.gestiones.forEach((g, idx) => {
            const item = document.createElement("div");
            item.style.background = "var(--bg-app)";
            item.style.padding = "14px";
            item.style.borderRadius = "8px";
            item.style.borderLeft = `4px solid ${idx === 2 ? "var(--semaforo-verde)" : "#2563eb"}`;
            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 0.88rem;">
                    <span>Gestión ${g.etapa}: ${g.nombreEtapa}</span>
                    <span style="color: var(--text-secondary); font-size: 0.78rem;">${g.fecha}</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 6px;">${g.detalle}</div>
                <div style="font-size: 0.8rem; color: #065f46; background: #d1fae5; padding: 4px 8px; border-radius: 4px; margin-top: 6px; font-weight: 600;">
                    Resultado: ${g.resultado}
                </div>
            `;
            timeline.appendChild(item);
        });

        const agregarWrapper = document.getElementById("modal-caso-agregar-wrapper");
        if (caso.gestiones.length >= 3) {
            agregarWrapper.innerHTML = `
                <div style="background: rgba(16, 185, 129, 0.1); color: #065f46; padding: 12px; border-radius: 6px; font-size: 0.82rem; font-weight: 600;">
                    <i data-lucide="check-check"></i> Este caso social ha completado sus 3 etapas reglamentarias (RN-012) y se encuentra formalmente cerrado.
                </div>
            `;
        } else {
            agregarWrapper.style.display = "block";
        }

        this.openModal("modal-caso-social");
    }

    agregarGestionActual() {
        if (!this.currentCasoSocial) return;

        const texto = document.getElementById("modal-nueva-gestion-texto").value.trim();
        if (!texto) {
            alert("Por favor ingrese el detalle de la nueva gestión.");
            return;
        }

        const nuevaEtapaNum = this.currentCasoSocial.gestiones.length + 1;
        const nombreEtapa = nuevaEtapaNum === 2 ? "Derivación e Informe Socioeconómico" : "Entrega de Ayuda Directa y Cierre";

        const nuevaGestion = {
            etapa: nuevaEtapaNum,
            nombreEtapa: nombreEtapa,
            fecha: new Date().toISOString().slice(0, 10),
            profesional: this.currentUser.nombre,
            detalle: texto,
            resultado: "Gestión incorporada exitosamente a la ficha única del beneficiario."
        };

        try {
            window.sgrStorage.addGestionSocial(this.currentCasoSocial.id, nuevaGestion);
            this.showToast(`Gestión ${nuevaEtapaNum} añadida a la ficha de ${this.currentCasoSocial.nombreBeneficiario}`, "success");
            this.openModalCasoSocial(this.currentCasoSocial.id);
            this.renderSocial();
        } catch (err) {
            alert(err.message);
        }
    }

    openNuevaAtencionModal() {
        alert("Apertura de nueva ficha social para persona usuaria. Registra RUT, Ficha RSH y primera gestión diagnóstica.");
    }

    filterCasosSociales(query) {
        const q = query.toLowerCase();
        const atenciones = window.sgrStorage.getAtenciones();
        const filtradas = atenciones.filter(c => 
            c.nombreBeneficiario.toLowerCase().includes(q) ||
            c.rutBeneficiario.toLowerCase().includes(q)
        );
        // Volver a renderizar sólo las filtradas
        const tbody = document.getElementById("tbody-casos-sociales");
        tbody.innerHTML = "";
        filtradas.forEach(caso => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${caso.id}</strong></td>
                <td>${caso.rutBeneficiario}</td>
                <td><div style="font-weight: 700;">${caso.nombreBeneficiario}</div></td>
                <td>${caso.tramoRSH}</td>
                <td>Etapa ${caso.gestiones.length} de 3</td>
                <td>${caso.gestiones[caso.gestiones.length - 1].fecha}</td>
                <td>${caso.responsableNombre}</td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="sgrApp.openModalCasoSocial('${caso.id}')">Ver Ficha</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    /**
     * VISTA 7: MONITOR SEMÁFORO DIARIO & SIMULADOR
     */
    renderSemaforo() {
        this.actualizarSimulador();
    }

    actualizarSimulador() {
        const diasTranscurridos = parseInt(document.getElementById("sim-dias-input").value, 10);
        const avancePonderado = parseFloat(document.getElementById("sim-avance-input").value);

        document.getElementById("sim-dias-val").textContent = `${diasTranscurridos} días`;
        document.getElementById("sim-avance-val").textContent = `${avancePonderado}%`;

        const metaEsperada = window.SGRCalculations.calcularMetaEsperadaAlDia(diasTranscurridos, 91);
        const semaforo = window.SGRCalculations.determinarSemaforo(avancePonderado, metaEsperada);

        document.getElementById("sim-meta-esperada-calc").textContent = `${metaEsperada}%`;
        
        const badge = document.getElementById("sim-semaforo-badge");
        badge.className = `badge-semaforo ${semaforo.claseCss}`;
        document.getElementById("sim-semaforo-text").textContent = `${semaforo.texto} (${semaforo.color})`;
        document.getElementById("sim-explicacion-calc").textContent = semaforo.descripcion;

        if (window.lucide) window.lucide.createIcons();
    }

    /**
     * VISTA 8: CONFIGURACIÓN DE METAS Y PONDERADORES (RN-001)
     */
    renderConfig() {
        const data = window.sgrStorage.getData();
        const tbody = document.getElementById("tbody-config-items");
        tbody.innerHTML = "";

        const itemsCargo = data.itemsMedicion.filter(itm => itm.cargo === this.currentUser.cargo);
        const validacionPond = window.SGRCalculations.validarPonderaciones(itemsCargo);

        const statusPond = document.getElementById("config-suma-status");
        if (validacionPond.valido) {
            statusPond.className = "badge-counter badge-semaforo-verde";
            statusPond.textContent = `Suma Ponderadores: ${validacionPond.sumaTotal}% (Conforme a RN-001)`;
        } else {
            statusPond.className = "badge-counter badge-semaforo-rojo";
            statusPond.textContent = `¡Error! Suma Ponderadores: ${validacionPond.sumaTotal}% (Debe ser exactamente 100%)`;
        }

        itemsCargo.forEach(itm => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><span style="font-size: 0.8rem; font-weight: 600;">${itm.cargo}</span></td>
                <td><strong>${itm.nombre}</strong></td>
                <td>${itm.unidad}</td>
                <td><strong style="color: #2563eb;">${itm.ponderacion}%</strong></td>
                <td><strong>${itm.metaTrimestral}</strong></td>
                <td>
                    <button class="btn btn-outline btn-sm" onclick="alert('Edición parametrizable de metas e ítems del período (RF-006 / RF-007)')">
                        <i data-lucide="edit-3"></i>
                        <span>Editar</span>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        if (window.lucide) window.lucide.createIcons();
    }

    /**
     * VISTA 9: LOG DE AUDITORÍA
     */
    renderAuditoria() {
        const data = window.sgrStorage.getData();
        const tbody = document.getElementById("tbody-auditoria");
        tbody.innerHTML = "";

        data.auditoria.forEach(log => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><code>${log.id}</code></td>
                <td><span style="font-size: 0.78rem;">${log.fecha}</span></td>
                <td><strong>${log.usuario}</strong></td>
                <td><span class="badge-counter" style="background: var(--bg-app); color: var(--color-navy);">${log.accion}</span></td>
                <td>${log.entidad}</td>
                <td><code style="font-size: 0.75rem;">${log.valorAnterior}</code></td>
                <td><strong style="font-size: 0.78rem; color: #065f46;">${log.valorNuevo}</strong></td>
            `;
            tbody.appendChild(tr);
        });
    }

    /**
     * BÚSQUEDA GLOBAL RÁPIDA (CTRL + K)
     */
    openSearchModal() {
        this.openModal("modal-search");
        setTimeout(() => {
            document.getElementById("modal-search-input").focus();
        }, 100);
    }

    executeGlobalSearch(query) {
        const resultsList = document.getElementById("search-results-list");
        if (!query || query.length < 2) {
            resultsList.innerHTML = `<div style="color: var(--text-muted); font-size: 0.82rem; text-align: center; padding: 20px;">Escriba al menos 2 letras para buscar en toda la plataforma...</div>`;
            return;
        }

        const data = window.sgrStorage.getData();
        const q = query.toLowerCase();

        const acts = data.actividades.filter(a => 
            a.codigoEvidencia.toLowerCase().includes(q) ||
            a.descripcion.toLowerCase().includes(q) ||
            a.funcionarioNombre.toLowerCase().includes(q)
        );

        const comps = data.agendaColectiva.filter(c =>
            c.origen.toLowerCase().includes(q) ||
            c.solicitante.toLowerCase().includes(q) ||
            c.territorio.toLowerCase().includes(q)
        );

        resultsList.innerHTML = "";

        if (acts.length === 0 && comps.length === 0) {
            resultsList.innerHTML = `<div style="color: var(--text-muted); font-size: 0.82rem; text-align: center; padding: 20px;">No se encontraron resultados para "${query}".</div>`;
            return;
        }

        acts.forEach(a => {
            const item = document.createElement("div");
            item.style.padding = "8px 12px";
            item.style.borderRadius = "6px";
            item.style.background = "var(--bg-app)";
            item.style.cursor = "pointer";
            item.innerHTML = `
                <div style="font-weight: 700; font-size: 0.85rem; color: #2563eb;">Actividad: ${a.codigoEvidencia} - ${a.itemNombre}</div>
                <div style="font-size: 0.78rem; color: var(--text-secondary);">${a.descripcion} (${a.funcionarioNombre})</div>
            `;
            item.onclick = () => {
                this.closeModal("modal-search");
                this.openModalEvidencia(a.id);
            };
            resultsList.appendChild(item);
        });

        comps.forEach(c => {
            const item = document.createElement("div");
            item.style.padding = "8px 12px";
            item.style.borderRadius = "6px";
            item.style.background = "var(--bg-app)";
            item.style.cursor = "pointer";
            item.innerHTML = `
                <div style="font-weight: 700; font-size: 0.85rem; color: var(--color-gold);">Agenda: ${c.origen}</div>
                <div style="font-size: 0.78rem; color: var(--text-secondary);">${c.solicitante} - ${c.territorio} (${c.fechaCompromiso})</div>
            `;
            item.onclick = () => {
                this.closeModal("modal-search");
                this.navigate("agenda");
            };
            resultsList.appendChild(item);
        });
    }

    /**
     * GESTIÓN DE NOTIFICACIONES Y MENÚS FLOTANTES
     */
    toggleNotifications() {
        const dropdown = document.getElementById("dropdown-notifications");
        dropdown.classList.toggle("show");
    }

    actualizarNotificaciones() {
        const notiList = document.getElementById("dropdown-noti-list");
        if (!notiList) return;

        notiList.innerHTML = `
            <li class="dropdown-item unread" onclick="sgrApp.openAlertaVencidoModal()">
                <i data-lucide="alert-octagon" style="color: var(--semaforo-rojo);"></i>
                <div>
                    <div style="font-weight: 700;">Compromiso Vencido (CA-03)</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">Asamblea El Romero APR expiró el 10-08-2026</div>
                </div>
            </li>
            <li class="dropdown-item unread" onclick="sgrApp.navigate('validacion')">
                <i data-lucide="camera" style="color: var(--color-gold);"></i>
                <div>
                    <div style="font-weight: 700;">Nueva Evidencia para Validación</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">EVI-2026-0742 remitida por Las Compañías</div>
                </div>
            </li>
            <li class="dropdown-item">
                <i data-lucide="check-circle" style="color: var(--semaforo-verde);"></i>
                <div>
                    <div style="font-weight: 700;">Evidencia EVI-2026-0741 Aprobada</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">Semáforo individual en estado Óptimo</div>
                </div>
            </li>
        `;

        if (window.lucide) window.lucide.createIcons();
    }

    /**
     * TEMA OSCURO / CLARO
     */
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
        const nextTheme = currentTheme === "light" ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", nextTheme);
        localStorage.setItem("SGR_THEME", nextTheme);
        this.updateThemeIcon(nextTheme);
        this.showToast(`Modo ${nextTheme === "dark" ? "Oscuro" : "Claro"} activado`, "info");
    }

    updateThemeIcon(theme) {
        const icon = document.getElementById("theme-icon");
        if (icon) {
            icon.setAttribute("data-lucide", theme === "dark" ? "sun" : "moon");
            if (window.lucide) window.lucide.createIcons();
        }
    }

    /**
     * MODALES
     */
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add("show");
        }
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove("show");
        }
    }

    closeAllModals() {
        document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("show"));
        const noti = document.getElementById("dropdown-notifications");
        if (noti) noti.classList.remove("show");
    }

    /**
     * TOASTS
     */
    showToast(message, type = "info") {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = "toast";

        let iconName = "info";
        let color = "#2563eb";
        if (type === "success") { iconName = "check-circle"; color = "#10b981"; }
        if (type === "warning") { iconName = "alert-triangle"; color = "#f59e0b"; }
        if (type === "error") { iconName = "alert-octagon"; color = "#ef4444"; }

        toast.innerHTML = `
            <i data-lucide="${iconName}" style="color: ${color}; width: 20px; height: 20px; flex-shrink: 0;"></i>
            <span>${message}</span>
        `;

        container.appendChild(toast);
        if (window.lucide) window.lucide.createIcons();

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    /**
     * RESETEO DE BASE DE DATOS
     */
    resetDatabase() {
        if (confirm("¿Desea restaurar todos los datos semilla originales del SGR de La Serena? Se restablecerán las actividades y estados.")) {
            window.sgrStorage.resetToDefaults();
            this.showToast("Datos semilla restablecidos correctamente.", "success");
            this.init();
        }
    }
}

// Inicializar la aplicación cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", () => {
    window.sgrApp = new SGRApp();
    window.sgrApp.init();
});
