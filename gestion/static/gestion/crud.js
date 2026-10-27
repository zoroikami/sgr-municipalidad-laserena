"use strict";

// Django entrega el formulario (vacío, cargado o con errores); Bootstrap lo presenta.
const formModal = document.getElementById("crudModal");
if (formModal?.dataset.openModal === "true") {
    formModal.addEventListener("shown.bs.modal", () => {
        formModal.querySelector('[aria-invalid="true"], input:not([type="hidden"]), select, textarea')?.focus();
    });
    formModal.addEventListener("hidden.bs.modal", () => {
        window.location.assign(formModal.dataset.returnUrl);
    });
    bootstrap.Modal.getOrCreateInstance(formModal).show();
    formModal.querySelector("form").addEventListener("submit", () => {
        const button = formModal.querySelector("[data-save-button]");
        button.disabled = true;
        button.textContent = "Guardando…";
    });
}

// SweetAlert2 confirma; el formulario POST con CSRF llega a DeleteView.
document.querySelectorAll("[data-confirm-delete]").forEach(form => {
    form.addEventListener("submit", async event => {
        if (!window.Swal) {
            event.preventDefault();
            window.alert("No se pudo cargar la confirmación. Recarga la página.");
            return;
        }
        event.preventDefault();
        const result = await Swal.fire({
            title: "¿Eliminar registro?",
            text: form.dataset.recordName,
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Sí, eliminar",
            cancelButtonText: "Cancelar",
            focusCancel: true,
            confirmButtonColor: "#C41230"
        });
        if (result.isConfirmed) HTMLFormElement.prototype.submit.call(form);
    });
});

const message = document.querySelector("[data-sgr-message]");
if (message && window.Swal) {
    Swal.fire({title: message.dataset.icon === "error" ? "No se pudo completar" : "Operación realizada", text: message.textContent.trim(), icon: message.dataset.icon, confirmButtonText: "Aceptar", confirmButtonColor: "#C41230"});
}
