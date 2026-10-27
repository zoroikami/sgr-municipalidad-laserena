/** Syntax and modulo-11 validation. This does not query a civil or tax registry. */
(() => {
    const message = "Ingresa un RUT chileno válido con su dígito verificador (ej.: 12.345.678-5).";
    function normalize(value) {
        if (typeof value !== "string" || value.length > 20) throw new Error(message);
        const raw = value.trim().toUpperCase();
        if (!/^(?:[0-9]{1,8}|[0-9]{1,3}(?:\.[0-9]{3}){1,2})-?[0-9K]$/.test(raw)) throw new Error(message);
        const compact = raw.replace(/[.-]/g, "");
        const body = compact.slice(0, -1).replace(/^0+/, "");
        const dv = compact.slice(-1);
        if (!body || body.length > 8) throw new Error(message);
        const total = [...body].reverse().reduce((sum, digit, index) => sum + Number(digit) * (2 + index % 6), 0);
        const remainder = 11 - total % 11;
        const expected = remainder === 10 ? "K" : remainder === 11 ? "0" : String(remainder);
        if (dv !== expected) throw new Error(message);
        return `${body}-${dv}`;
    }
    function isValid(value) {
        try { normalize(value); return true; } catch { return false; }
    }
    function format(value) {
        const [body, dv] = normalize(value).split("-");
        return `${body.replace(/\B(?=(\d{3})+(?!\d))/g, ".")}-${dv}`;
    }
    function updateInput(input, show = true) {
        const valid = isValid(input.value);
        input.setCustomValidity?.(valid ? "" : message);
        if (show) {
            input.setAttribute?.("aria-invalid", String(!valid));
            const feedbackId = input.getAttribute?.("aria-describedby")?.split(" ")[0];
            const feedback = feedbackId && document.getElementById(feedbackId);
            if (feedback) feedback.textContent = valid ? "Formato y dígito verificador válidos." : message;
        }
        return valid;
    }
    function requireRut(input) {
        if (!input || !updateInput(input)) throw new Error(message);
        const normalized = normalize(input.value);
        input.value = format(normalized);
        return normalized;
    }
    window.ChileanRut = { normalize, isValid, format, require: requireRut, updateInput };
    document.addEventListener("input", event => {
        const input = event.target;
        if (input?.matches?.("[data-rut]")) updateInput(input, input.dataset.rutTouched === "true");
    });
    document.addEventListener("focusout", event => {
        const input = event.target;
        if (!input?.matches?.("[data-rut]")) return;
        input.dataset.rutTouched = "true";
        if (isValid(input.value)) input.value = format(input.value);
        updateInput(input);
    });
})();
