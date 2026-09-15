/**
 * SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - MUNICIPALIDAD DE LA SERENA
 * calculations.js - Motor matemático de reglas de negocio y semáforo diario
 * Conforme a las directrices de la Guía Oficial del Proyecto (Sección 7: RN-001 a RN-013)
 */

const SGRCalculations = {
    /**
     * RN-001: Valida que los ponderadores de un conjunto de ítems sumen exactamente 100%
     */
    validarPonderaciones(items) {
        const suma = items.reduce((acc, itm) => acc + (parseFloat(itm.ponderacion) || 0), 0);
        return {
            valido: Math.abs(suma - 100) < 0.01,
            sumaTotal: Math.round(suma * 100) / 100
        };
    },

    /**
     * RN-003 & RN-009: Calcula el avance real de un ítem para un funcionario
     * Solo las actividades con estadoValidacion === 'APROBADA' otorgan punto de avance
     */
    calcularAvanceItem(funcionarioId, itemId, actividades) {
        return actividades.filter(a => 
            a.funcionarioId === funcionarioId && 
            a.itemId === itemId && 
            a.estadoValidacion === "APROBADA"
        ).length;
    },

    /**
     * RN-004: % de cumplimiento = (avance actual / meta del período) * 100
     */
    calcularPctCumplimiento(avance, meta) {
        if (!meta || meta <= 0) return 0;
        const pct = (avance / meta) * 100;
        return Math.round(pct * 10) / 10;
    },

    /**
     * RN-005: Cumplimiento ponderado = ponderador * (% cumplimiento / 100)
     * Máximo computable tope: 150%
     */
    calcularCumplimientoPonderado(pctCumplimiento, ponderacion) {
        const ponderado = (pctCumplimiento * (ponderacion / 100));
        // Tope máximo 150% del ponderador original
        const maximoPermitido = ponderacion * 1.5;
        const ponderadoFinal = Math.min(ponderado, maximoPermitido);
        return Math.round(ponderadoFinal * 10) / 10;
    },

    /**
     * RN-007: Meta esperada al día = (días transcurridos / días totales del período) * 100
     */
    calcularMetaEsperadaAlDia(diasTranscurridos, diasTotales) {
        if (!diasTotales || diasTotales <= 0) return 0;
        const metaEsperada = (diasTranscurridos / diasTotales) * 100;
        return Math.round(metaEsperada * 100) / 100;
    },

    /**
     * RN-008 & 7.1: Interpretación visual del semáforo diario
     * - VERDE: Avance igual o superior a la meta acumulada esperada al día.
     * - ÁMBAR: Avance entre el 60% y menos del 100% de la meta esperada al día.
     * - ROJO: Avance inferior al 60% de la meta esperada al día.
     *
     * @param {number} cumplimientoPonderado - % de avance ponderado logrado por el funcionario
     * @param {number} metaEsperadaAlDia - % esperado según fecha del período
     */
    determinarSemaforo(cumplimientoPonderado, metaEsperadaAlDia) {
        if (metaEsperadaAlDia <= 0) {
            return {
                color: "VERDE",
                claseCss: "badge-semaforo-verde",
                texto: "Óptimo",
                descripcion: "Inicio de período de medición",
                icono: "check-circle"
            };
        }

        const umbralAmbar = metaEsperadaAlDia * 0.60;

        if (cumplimientoPonderado >= metaEsperadaAlDia) {
            return {
                color: "VERDE",
                claseCss: "badge-semaforo-verde",
                texto: "Cumplimiento Óptimo",
                descripcion: `Avance (${cumplimientoPonderado}%) ≥ Meta esperada al día (${metaEsperadaAlDia}%)`,
                icono: "check-circle"
            };
        } else if (cumplimientoPonderado >= umbralAmbar) {
            return {
                color: "AMBAR",
                claseCss: "badge-semaforo-ambar",
                texto: "Atención Requerida",
                descripcion: `Avance (${cumplimientoPonderado}%) entre 60% y 100% de la meta esperada (${metaEsperadaAlDia}%)`,
                icono: "alert-triangle"
            };
        } else {
            return {
                color: "ROJO",
                claseCss: "badge-semaforo-rojo",
                texto: "En Riesgo Crítico",
                descripcion: `Avance (${cumplimientoPonderado}%) inferior al 60% de la meta esperada (${metaEsperadaAlDia}%)`,
                icono: "alert-octagon"
            };
        }
    },

    /**
     * RN-006: Cálculo del desempeño colectivo de la Agenda / Tubo de Trabajo
     * Umbral mínimo exigido: 80% de compromisos realizados
     */
    calcularDesempenoAgenda(compromisos) {
        if (!compromisos || compromisos.length === 0) {
            return { total: 0, realizados: 0, pctRealizado: 0, cumpleUmbral80: false, vencidosCount: 0 };
        }

        const total = compromisos.length;
        const realizados = compromisos.filter(c => c.estado === "REALIZADO").length;
        const pct = Math.round((realizados / total) * 1000) / 10;
        
        // Detección de compromisos vencidos (no realizados y fecha < hoy)
        const hoy = new Date().toISOString().slice(0, 10);
        const vencidos = compromisos.filter(c => c.estado !== "REALIZADO" && c.fechaCompromiso < hoy);

        return {
            total,
            realizados,
            pendientes: total - realizados,
            pctRealizado: pct,
            cumpleUmbral80: pct >= 80,
            vencidosCount: vencidos.length,
            vencidos
        };
    },

    /**
     * RN-010: Generador de código de evidencia único, inmutable y correlativo
     */
    generarCodigoEvidencia(actividades) {
        const anio = new Date().getFullYear();
        let maxCorrelativo = 740;
        
        actividades.forEach(a => {
            if (a.codigoEvidencia && a.codigoEvidencia.startsWith(`EVI-${anio}-`)) {
                const num = parseInt(a.codigoEvidencia.replace(`EVI-${anio}-`, ""), 10);
                if (!isNaN(num) && num > maxCorrelativo) {
                    maxCorrelativo = num;
                }
            }
        });

        const nuevoNumero = (maxCorrelativo + 1).toString().padStart(4, "0");
        return `EVI-${anio}-${nuevoNumero}`;
    },

    /**
     * Cálculo consolidado para la Ficha Personal de un funcionario
     */
    calcularFichaFuncionario(funcionario, itemsMedicion, actividades, periodo) {
        const itemsFuncionario = itemsMedicion.filter(itm => itm.cargo === funcionario.cargo);
        let sumaPonderadaTotal = 0;

        const itemsCalculados = itemsFuncionario.map(itm => {
            const avance = this.calcularAvanceItem(funcionario.id, itm.id, actividades);
            const pct = this.calcularPctCumplimiento(avance, itm.metaTrimestral);
            const ponderado = this.calcularCumplimientoPonderado(pct, itm.ponderacion);
            sumaPonderadaTotal += ponderado;

            return {
                ...itm,
                avanceReal: avance,
                pctCumplimiento: pct,
                puntajePonderado: ponderado
            };
        });

        const metaEsperada = this.calcularMetaEsperadaAlDia(periodo.diasTranscurridos, periodo.diasTotales);
        const cumplimientoFinal = Math.round(sumaPonderadaTotal * 10) / 10;
        const semaforo = this.determinarSemaforo(cumplimientoFinal, metaEsperada);

        return {
            funcionario,
            periodo,
            items: itemsCalculados,
            cumplimientoPonderadoTotal: cumplimientoFinal,
            metaEsperadaAlDia: metaEsperada,
            semaforo
        };
    }
};

window.SGRCalculations = SGRCalculations;
