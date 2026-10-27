/** Crop geometry in a 512 × 512 viewport. Offsets always cover the entire viewport. */
window.SGRPhotoCropGeometry = class SGRPhotoCropGeometry {
    constructor(width, height) {
        this.width = width;
        this.height = height;
        this.baseScale = 512 / Math.min(width, height);
        this.reset();
    }

    reset() { this.zoom = 1; this.x = 0; this.y = 0; }

    setZoom(value) {
        const previous = this.zoom;
        this.zoom = Math.max(1, Math.min(4, Number(value) || 1));
        this.x *= this.zoom / previous;
        this.y *= this.zoom / previous;
        this.move(0, 0);
    }

    move(dx, dy) {
        const scale = this.baseScale * this.zoom;
        const limitX = Math.max(0, (this.width * scale - 512) / 2);
        const limitY = Math.max(0, (this.height * scale - 512) / 2);
        this.x = Math.max(-limitX, Math.min(limitX, this.x + dx));
        this.y = Math.max(-limitY, Math.min(limitY, this.y + dy));
    }

    sourceRect() {
        const scale = this.baseScale * this.zoom;
        const side = 512 / scale;
        return { x: (this.width - side) / 2 - this.x / scale,
            y: (this.height - side) / 2 - this.y / scale, side };
    }
};

/** Shared, temporary photo editor; only the confirmed JPEG reaches the save flow. */
window.SGRPhotoCropper = class SGRPhotoCropper {
    static get active() { return Boolean(this.instance?.opened); }
    static edit(file, isCurrent = () => true) {
        this.instance ||= new this();
        return this.instance.edit(file, isCurrent);
    }

    constructor() {
        this.generation = 0;
        this.modal = document.getElementById("sgr-photo-crop-modal");
        this.canvas = document.getElementById("photo-crop-canvas");
        this.zoom = document.getElementById("photo-crop-zoom");
        this.zoom.addEventListener("input", () => { this.model.setZoom(this.zoom.value); this.render(); });
        for (const id of ["photo-crop-close", "photo-crop-cancel"]) {
            document.getElementById(id).addEventListener("click", () => this.finish(null));
        }
        document.getElementById("photo-crop-use").addEventListener("click", () => this.confirm());
        document.getElementById("photo-crop-reset").addEventListener("click", () => {
            this.model.reset(); this.render(); this.canvas.focus();
        });
        this.canvas.addEventListener("pointerdown", event => {
            if (!this.opened || event.button !== 0 || this.pointer) return;
            this.canvas.setPointerCapture(event.pointerId);
            this.pointer = { id: event.pointerId, x: event.clientX, y: event.clientY };
            this.canvas.classList.add("dragging");
            this.canvas.focus();
        });
        this.canvas.addEventListener("pointermove", event => {
            if (!this.pointer || event.pointerId !== this.pointer.id) return;
            const factor = 512 / this.canvas.getBoundingClientRect().width;
            this.model.move((event.clientX - this.pointer.x) * factor, (event.clientY - this.pointer.y) * factor);
            this.pointer.x = event.clientX;
            this.pointer.y = event.clientY;
            this.render();
        });
        for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) {
            this.canvas.addEventListener(type, () => this.endDrag());
        }
        document.addEventListener("keydown", event => this.handleKeydown(event));
    }

    async edit(file, isCurrent = () => true) {
        this.finish(null);
        const generation = ++this.generation;
        const url = URL.createObjectURL(file);
        try {
            const image = await new Promise((resolve, reject) => {
                const image = new Image();
                image.onload = () => resolve(image);
                image.onerror = () => reject(new Error("No se pudo leer la imagen. Prueba con otro archivo."));
                image.src = url;
            });
            if (generation !== this.generation || !isCurrent()) return null;
            if (!image.naturalWidth || !image.naturalHeight) throw new Error("La imagen no tiene un tamaño válido.");
            this.image = image;
            this.model = new window.SGRPhotoCropGeometry(image.naturalWidth, image.naturalHeight);
            this.previousFocus = document.activeElement;
            this.previousOverflow = document.body.style.overflow;
            document.body.style.overflow = "hidden";
            this.opened = true;
            this.modal.hidden = false;
            this.modal.classList.add("active");
            this.render();
            this.canvas.focus();
            return await new Promise(resolve => { this.resolve = resolve; });
        } catch (error) {
            if (generation === this.generation) this.finish(null);
            throw error;
        } finally {
            URL.revokeObjectURL(url);
        }
    }

    render() {
        const context = this.canvas.getContext("2d");
        if (!context) throw new Error("Tu navegador no pudo preparar la foto.");
        const rect = this.model.sourceRect();
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, 512, 512);
        context.drawImage(this.image, rect.x, rect.y, rect.side, rect.side, 0, 0, 512, 512);
        this.zoom.value = String(this.model.zoom);
        document.getElementById("photo-crop-zoom-value").textContent = `${Math.round(this.model.zoom * 100)} %`;
    }

    async confirm() {
        if (!this.opened) return;
        try {
            const photo = this.canvas.toDataURL("image/jpeg", 0.85);
            if (!photo.startsWith("data:image/jpeg;base64,") || photo.length > 700000) {
                throw new Error("No se pudo reducir la foto. Prueba con otra imagen.");
            }
            this.finish(photo);
        } catch (error) {
            await Swal.fire({ title: "No se pudo usar el recorte", text: error.message, icon: "error" });
        }
    }

    endDrag() {
        const pointer = this.pointer;
        this.pointer = null;
        if (pointer && this.canvas.hasPointerCapture(pointer.id)) this.canvas.releasePointerCapture(pointer.id);
        this.canvas.classList.remove("dragging");
    }

    finish(photo) {
        this.generation++;
        if (!this.opened) return;
        this.opened = false;
        this.endDrag();
        this.modal.hidden = true;
        this.modal.classList.remove("active");
        document.body.style.overflow = this.previousOverflow || "";
        this.previousFocus?.focus();
        this.image = null;
        const resolve = this.resolve;
        this.resolve = null;
        resolve?.(photo);
    }

    handleKeydown(event) {
        if (!this.opened || Swal.isVisible?.()) return;
        if (event.key === "Escape") {
            event.preventDefault();
            event.stopImmediatePropagation();
            this.finish(null);
            return;
        }
        const directions = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
        if (document.activeElement === this.canvas && directions[event.key]) {
            event.preventDefault();
            const [x, y] = directions[event.key];
            const step = event.shiftKey ? 32 : 8;
            this.model.move(x * step, y * step);
            this.render();
        }
        if (event.key !== "Tab") return;
        const controls = [...this.modal.querySelectorAll('button:not(:disabled), input:not(:disabled), canvas[tabindex]')];
        const first = controls[0], last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
};
