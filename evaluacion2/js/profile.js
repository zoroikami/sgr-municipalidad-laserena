/** Personal profile and photo preview. Photo persistence always goes through SQLite. */
window.SGRProfileController = class SGRProfileController {
    static DEFAULT_PHOTO = "/assets/municipal/avatar-default.svg";

    constructor(app) {
        this.app = app;
        this.pendingPhoto = undefined;
        this.busy = false;
        this.previousFocus = null;
        this.opened = false;
        this.previewGeneration = 0;
        document.addEventListener("keydown", event => this.handleKeydown(event));
    }

    element(id) { return document.getElementById(id); }

    renderHeader() {
        const image = this.element("header-user-avatar");
        if (image) image.src = this.app.currentUser?.foto_perfil || SGRProfileController.DEFAULT_PHOTO;
    }

    setBusy(busy, message = "", saving = false) {
        this.busy = busy;
        this.saving = saving;
        for (const id of ["profile-choose-photo", "profile-remove-photo", "profile-save-photo", "profile-photo-file"]) {
            const control = this.element(id);
            if (control) control.disabled = busy;
        }
        const save = this.element("profile-save-photo");
        save.textContent = saving ? "Guardando…" : "Guardar foto";
        save.disabled = busy || this.pendingPhoto === undefined;
        this.element("profile-remove-photo").disabled = busy || this.previewPhoto() === SGRProfileController.DEFAULT_PHOTO;
        this.element("profile-status").textContent = message;
        this.element("sgr-profile-modal").setAttribute("aria-busy", String(busy));
    }

    previewPhoto() {
        return this.pendingPhoto === undefined
            ? this.app.currentUser?.foto_perfil || SGRProfileController.DEFAULT_PHOTO
            : this.pendingPhoto || SGRProfileController.DEFAULT_PHOTO;
    }

    render() {
        const user = this.app.currentUser;
        for (const [id, text] of Object.entries({
            "profile-user-name": user.nombre,
            "profile-user-email": user.email,
            "profile-user-role": user.rol_nombre || user.rol_codigo,
            "profile-user-delegation": user.delegacion_nombre || user.delegacion_codigo
        })) this.element(id).textContent = text || "—";
        this.element("profile-photo-preview").src = this.previewPhoto();
        this.element("profile-photo-file").value = "";
        this.setBusy(false, this.pendingPhoto === undefined ? "" : "Vista previa. Guarda para aplicar el cambio.");
    }

    async open() {
        if (this.opened || !this.app.currentUser) return;
        this.opened = true;
        const generation = ++this.previewGeneration;
        const ownerId = this.app.currentUser.id;
        this.previousFocus = document.activeElement;
        this.pendingPhoto = undefined;
        const modal = this.element("sgr-profile-modal");
        modal.hidden = false;
        modal.classList.add("active");
        this.previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        this.element("profile-photo-preview").src = this.previewPhoto();
        this.setBusy(true, "Cargando tu perfil…");
        this.element("profile-close").focus();
        try {
            const user = await sgrDb.getProfile();
            if (!this.opened || generation !== this.previewGeneration || this.app.currentUser?.id !== ownerId) return;
            if (user.id !== this.app.currentUser?.id) throw new Error("La sesión no corresponde al usuario actual. Vuelve a iniciar sesión.");
            this.app.currentUser = { ...this.app.currentUser, ...user };
            this.app.updateHeaderUserInfo();
            this.render();
            this.element("profile-choose-photo").focus();
        } catch (error) {
            if (!this.opened || generation !== this.previewGeneration || this.app.currentUser?.id !== ownerId) return;
            this.dismiss();
            if (error.status === 401) {
                localStorage.removeItem("SGR_AUTH_SESSION_USER");
                localStorage.removeItem("SGR_AUTH_SESSION_TOKEN");
                this.app.currentUser = null;
                this.app.showAuthView("login");
            }
            await Swal.fire({ title: "No se pudo abrir tu perfil", text: error.message, icon: "error" });
        }
    }

    choosePhoto() { this.element("profile-photo-file").click(); }

    async selectPhoto(input) {
        const file = input.files?.[0];
        if (!file || this.busy) return;
        const generation = ++this.previewGeneration;
        this.editingPhoto = true;
        this.setBusy(true, "Preparando la foto…");
        try {
            const photo = await SGRProfileController.preparePhoto(file,
                () => generation === this.previewGeneration && this.opened);
            if (generation !== this.previewGeneration || !this.opened) return;
            if (photo !== null) this.pendingPhoto = photo;
            this.render();
            this.element("profile-choose-photo").focus();
        } catch (error) {
            if (generation === this.previewGeneration && this.opened) {
                this.render();
                this.element("profile-status").textContent = error.message;
                await Swal.fire({ title: "No se pudo usar la foto", text: error.message, icon: "error" });
            }
        } finally {
            if (generation === this.previewGeneration) this.editingPhoto = false;
        }
    }

    async removePhoto() {
        if (this.busy) return;
        const result = await Swal.fire({ title: "¿Quitar tu foto?", text: "Se usará el avatar predeterminado al guardar.", icon: "question", showCancelButton: true, confirmButtonText: "Quitar foto" });
        if (!result.isConfirmed || !this.opened) return;
        this.pendingPhoto = null;
        this.render();
    }

    async save() {
        if (this.busy || this.pendingPhoto === undefined) return;
        this.setBusy(true, "Guardando tu foto…", true);
        try {
            const user = await sgrDb.saveProfilePhoto(this.pendingPhoto);
            if (user.id !== this.app.currentUser?.id) throw new Error("No se pudo verificar el usuario de la foto.");
            this.app.currentUser = { ...this.app.currentUser, ...user };
            this.pendingPhoto = undefined;
            this.app.updateHeaderUserInfo();
            this.setBusy(false);
            this.dismiss();
            await Swal.fire({ title: "Foto actualizada", text: "Tu foto de perfil quedó guardada.", icon: "success" });
        } catch (error) {
            this.setBusy(false, error.message);
            await Swal.fire({ title: "No se pudo guardar la foto", text: error.message, icon: "error" });
        }
    }

    async close() {
        if (this.saving) return;
        if (this.pendingPhoto !== undefined) {
            const result = await Swal.fire({ title: "¿Descartar la foto sin guardar?", icon: "question", showCancelButton: true, confirmButtonText: "Descartar", cancelButtonText: "Seguir editando" });
            if (!result.isConfirmed) return;
        }
        this.dismiss();
    }

    dismiss() {
        if (!this.opened) return;
        this.opened = false;
        if (this.editingPhoto) window.SGRPhotoCropper?.instance?.finish(null);
        this.editingPhoto = false;
        this.previewGeneration++;
        this.pendingPhoto = undefined;
        const modal = this.element("sgr-profile-modal");
        modal.hidden = true;
        modal.classList.remove("active");
        document.body.style.overflow = this.previousOverflow || "";
        this.previousFocus?.focus();
    }

    handleKeydown(event) {
        if (!this.opened || window.SGRPhotoCropper?.active || Swal.isVisible?.()) return;
        if (event.key === "Escape") { event.preventDefault(); this.close(); }
        if (event.key !== "Tab") return;
        const controls = [...this.element("sgr-profile-modal").querySelectorAll('button:not(:disabled), input:not(:disabled):not([hidden])')];
        const first = controls[0], last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }

    static async preparePhoto(file, isCurrent) {
        if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) throw new Error("Selecciona una imagen JPG, PNG o WebP.");
        if (file.size > 5 * 1024 * 1024) throw new Error("La imagen debe pesar como máximo 5 MB.");
        return window.SGRPhotoCropper.edit(file, isCurrent);
    }
};
