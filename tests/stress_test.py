#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - MUNICIPALIDAD DE LA SERENA
Script Automatizado de Pruebas de Estrés y Concurrencia (Requisito A3)
Evalúa Concurrencia Progresiva, Latencia Promedio, Percentil 95 (P95), RPS y Tasa de Error.
"""

import sys
import time
import json
import statistics
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_BASE_URL = "http://127.0.0.1:8000"

def make_request(url, method="GET", payload=None):
    start = time.perf_counter()
    status_code = 0
    success = False
    try:
        data = json.dumps(payload).encode("utf-8") if payload else None
        headers = {"Content-Type": "application/json"} if payload else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.status
            success = (200 <= status_code < 300)
    except urllib.error.HTTPError as e:
        status_code = e.code
        success = (200 <= status_code < 300)
    except Exception:
        status_code = 500
        success = False

    latency_ms = (time.perf_counter() - start) * 1000.0
    return success, latency_ms, status_code

def run_stress_scenario(base_url, name, method, path, payload, concurrency, total_requests):
    target_url = f"{base_url.rstrip('/')}{path}"
    latencies = []
    successes = 0
    failures = 0

    t_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request, target_url, method, payload) for _ in range(total_requests)]
        for f in as_completed(futures):
            ok, lat, _ = f.result()
            latencies.append(lat)
            if ok:
                successes += 1
            else:
                failures += 1

    t_total = time.perf_counter() - t_start
    rps = total_requests / t_total if t_total > 0 else 0
    avg_lat = statistics.mean(latencies) if latencies else 0
    p50_lat = statistics.median(latencies) if latencies else 0
    p95_lat = statistics.quantiles(latencies, n=100)[94] if len(latencies) >= 100 else (max(latencies) if latencies else 0)
    err_rate = (failures / total_requests) * 100.0

    return {
        "scenario": name,
        "concurrency": concurrency,
        "total_requests": total_requests,
        "duration_sec": round(t_total, 2),
        "rps": round(rps, 2),
        "avg_lat_ms": round(avg_lat, 2),
        "p50_ms": round(p50_lat, 2),
        "p95_ms": round(p95_lat, 2),
        "errors": failures,
        "err_rate": round(err_rate, 2)
    }

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else DEFAULT_BASE_URL
    print("=" * 75)
    print("  SGR LA SERENA - PLAN DE PRUEBAS DE ESTRÉS Y RENDIMIENTO (A3)")
    print(f"  Target URL: {base_url}")
    print("  Institución: Ilustre Municipalidad de La Serena | INACAP")
    print("  Evaluadores: Docente Jorge Cortés")
    print("=" * 75)

    scenarios = [
        ("Health & Disponibilidad", "GET", "/api/health", None, [10, 25, 50]),
        ("Consulta Mantenedores (Delegaciones)", "GET", "/api/delegaciones", None, [10, 25, 50]),
        ("Login y Validación de Credenciales", "POST", "/api/auth/login", {"usuario": "harold.concha@laserena.cl", "password": "Admin123*"}, [10, 25, 50]),
        ("Ingreso Concurrente de Atención", "POST", "/api/atenciones", {
            "solicitante_rut": "15.482.910-3",
            "solicitante_nombre": "Test Estrés Carga",
            "delegacion_codigo": "DEL01",
            "delegacion_nombre": "Centro",
            "tipo_codigo": "TA001",
            "tipo_nombre": "Social",
            "subtipo_codigo": "SA001",
            "subtipo_nombre": "Ayuda social",
            "descripcion": "Solicitud generada durante prueba de estrés de concurrencia.",
            "responsable_nombre": "Bot Benchmark"
        }, [10, 25, 50])
    ]

    all_results = []

    for name, method, path, payload, concurrency_levels in scenarios:
        print(f"\n[Ejecutando Escenario] {name} ({method} {path})")
        for conc in concurrency_levels:
            total_reqs = conc * 10
            res = run_stress_scenario(base_url, name, method, path, payload, conc, total_reqs)
            all_results.append(res)
            print(f"  -> Concurrencia: {conc:2d} | Solicitudes: {total_reqs:3d} | RPS: {res['rps']:6.1f} | Latencia Prom: {res['avg_lat_ms']:5.1f} ms | P95: {res['p95_ms']:5.1f} ms | Errores: {res['errors']}")

    # Imprimir Tabla Markdown Consolidada
    print("\n" + "=" * 75)
    print("TABLA CONSOLIDADA PARA INFORME DE SEGUNDA EVALUACIÓN:")
    print("=" * 75)
    print("| Escenario | Concurrencia | Solicitudes | Duración (s) | RPS | Latencia Prom. | P95 | Error % |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in all_results:
        print(f"| {r['scenario']} | {r['concurrency']} | {r['total_requests']} | {r['duration_sec']}s | {r['rps']} | {r['avg_lat_ms']} ms | {r['p95_ms']} ms | {r['err_rate']}% |")
    print("=" * 75)

if __name__ == "__main__":
    main()
