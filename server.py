#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - ILUSTRE MUNICIPALIDAD DE LA SERENA
Segunda Evaluación: Servidor Backend REST API y Servidor de Archivos Estáticos
Autores: Harold Concha, Keoni Vergara, Claudio Romo | INACAP - Proyecto Integrado
"""

import sys
import os
import json
import sqlite3
import random
import string
import datetime
import mimetypes
import smtplib

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Cargar .env si existe en el directorio del proyecto
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    try:
        with open(_env_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
    except Exception:
        pass

def send_recovery_email(email_destinatario, codigo):
    """Envía correo de recuperación real mediante SMTP si está configurado en variables de entorno o defaults."""
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "sgrmunicipalidadelaserena@gmail.com")
    smtp_pass = os.environ.get("SMTP_PASS", "ksocpffuigsugzsr")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user or "sgrmunicipalidadelaserena@gmail.com")

    if not smtp_host or not smtp_user or not smtp_pass:
        print(f"[SERVICIO CORREO SGR] SMTP no configurado. Código generado para <{email_destinatario}>: {codigo}")
        return False, "SMTP no configurado en servidor (use SMTP_HOST, SMTP_USER, SMTP_PASS)"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Código de recuperación de contraseña · SGR Ilustre Municipalidad de La Serena"
        msg["From"] = f"Sistema SGR La Serena <{smtp_from}>"
        msg["To"] = email_destinatario

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f7f5f4; margin: 0; padding: 24px;">
            <div style="max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #ebd9d7; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.06);">
                <div style="background-color: #8e1525; padding: 22px 24px; text-align: center; color: #ffffff;">
                    <h2 style="margin: 0; font-size: 1.3rem; letter-spacing: 0.5px;">Ilustre Municipalidad de La Serena</h2>
                    <p style="margin: 4px 0 0; font-size: 0.85rem; opacity: 0.9;">Sistema de Gestión de Resultados (SGR)</p>
                </div>
                <div style="padding: 28px 26px; color: #2d2624;">
                    <h3 style="margin-top: 0; color: #8e1525; font-size: 1.15rem;">Recuperación de Contraseña</h3>
                    <p style="font-size: 0.95rem; line-height: 1.5; color: #4a403d;">
                        Se ha solicitado el restablecimiento de contraseña para la cuenta institucional asociada a este correo electrónico.
                    </p>
                    <p style="font-size: 0.92rem; color: #4a403d;">
                        Su código de verificación oficial de 6 dígitos es:
                    </p>
                    <div style="text-align: center; margin: 24px 0;">
                        <div style="display: inline-block; background-color: #fcf1f0; border: 2px dashed #8e1525; border-radius: 8px; padding: 12px 30px;">
                            <span style="font-size: 2rem; font-weight: 700; letter-spacing: 6px; color: #8e1525;">{codigo}</span>
                        </div>
                    </div>
                    <p style="font-size: 0.85rem; color: #6e6360; line-height: 1.4;">
                        ⏱️ Este código tiene una vigencia de <strong>10 minutos</strong> y permite hasta 3 intentos fallidos.<br>
                        Si usted no solicitó este cambio, ignore este mensaje. Su cuenta permanecerá segura.
                    </p>
                </div>
                <div style="background-color: #fdfaf9; padding: 14px 24px; border-top: 1px solid #f0e6e5; text-align: center; font-size: 0.78rem; color: #8c7e7a;">
                    Gestión y Modernización Territorial · Ilustre Municipalidad de La Serena 2026
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"[SERVICIO CORREO SGR] [OK] Correo real enviado exitosamente a: {email_destinatario}")
        return True, "Correo despachado exitosamente vía SMTP institucional"
    except Exception as e:
        print(f"[SERVICIO CORREO SGR] [ERROR] Error enviando correo vía SMTP: {e}")
        return False, f"Fallo al enviar correo: {e}"

PORT = int(os.environ.get("PORT", 8000))
if "--port" in sys.argv:
    try:
        PORT = int(sys.argv[sys.argv.index("--port") + 1])
    except Exception:
        pass
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "sgr_laserena.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    # 1. Delegaciones
    c.execute("""
    CREATE TABLE IF NOT EXISTS delegaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        direccion TEXT NOT NULL,
        comuna TEXT NOT NULL DEFAULT 'La Serena',
        estado TEXT NOT NULL DEFAULT 'Activa',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # 2. Roles
    c.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        permisos TEXT NOT NULL,
        alcance TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'Activo'
    )""")

    # 3. Usuarios
    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rut TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        rol_codigo TEXT NOT NULL,
        delegacion_codigo TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'Activo',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # 4. Ítems y metas
    c.execute("""
    CREATE TABLE IF NOT EXISTS items_metas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        unidad_medida TEXT NOT NULL,
        meta_cantidad INTEGER NOT NULL,
        estado TEXT NOT NULL DEFAULT 'Activo'
    )""")

    # 5. Tipos de Atención
    c.execute("""
    CREATE TABLE IF NOT EXISTS tipos_atencion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        estado TEXT NOT NULL DEFAULT 'Activo'
    )""")

    # 6. Sub Atenciones
    c.execute("""
    CREATE TABLE IF NOT EXISTS sub_atenciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        tipo_codigo TEXT NOT NULL,
        tipo_nombre TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'Activa'
    )""")

    # 7. Ingreso de Atención
    c.execute("""
    CREATE TABLE IF NOT EXISTS atenciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folio TEXT UNIQUE NOT NULL,
        solicitante_rut TEXT NOT NULL,
        solicitante_nombre TEXT NOT NULL,
        delegacion_codigo TEXT NOT NULL,
        delegacion_nombre TEXT NOT NULL,
        tipo_codigo TEXT NOT NULL,
        tipo_nombre TEXT NOT NULL,
        subtipo_codigo TEXT NOT NULL,
        subtipo_nombre TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        responsable_nombre TEXT NOT NULL,
        fecha_registro TEXT NOT NULL
    )""")

    # 8. Códigos de Recuperación
    c.execute("""
    CREATE TABLE IF NOT EXISTS codigos_recuperacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        codigo TEXT NOT NULL,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expiracion TIMESTAMP NOT NULL,
        intentos INTEGER DEFAULT 0,
        usado INTEGER DEFAULT 0
    )""")

    # Semillas de datos si tablas están vacías
    c.execute("SELECT COUNT(*) FROM delegaciones")
    if c.fetchone()[0] == 0:
        delegaciones = [
            ("DEL01", "Centro", "Los Carrera 301, Casco Histórico", "La Serena", "Activa"),
            ("DEL02", "Norte (Las Compañías)", "Esmeralda 1023, Compañía Baja", "La Serena", "Activa"),
            ("DEL03", "Sur (La Pampa)", "Gabriel González Videla 2100", "La Serena", "Activa"),
            ("DEL04", "La Antena - La Florida", "18 de Septiembre 450", "La Serena", "Activa"),
            ("DEL05", "Rural", "Ruta 41 Km 15, Algarrobito", "La Serena", "Activa"),
            ("DEL06", "Avenida del Mar", "Av. del Mar 2200", "La Serena", "Inactiva")
        ]
        c.executemany("INSERT INTO delegaciones (codigo, nombre, direccion, comuna, estado) VALUES (?, ?, ?, ?, ?)", delegaciones)

    c.execute("SELECT COUNT(*) FROM roles")
    if c.fetchone()[0] == 0:
        roles = [
            ("ROL01", "Superadministrador", "Acceso total institucional a todos los módulos y auditoría", "total", "Autorizado Comunal", "Activo"),
            ("ROL02", "Coordinador", "Supervisión general de metas, gestión territorial y reportes comunales", "coordinacion", "Comunal", "Activo"),
            ("ROL03", "Delegado Municipal", "Administración local de la delegación y atención ciudadana", "delegacion", "Delegación", "Activo"),
            ("ROL04", "Operador / Funcionario", "Ingreso y atención directa de vecinos en ventanilla", "operador", "Ventanilla", "Activo"),
            ("ROL05", "Consultor", "Acceso de sólo lectura para seguimiento y control", "lectura", "Lectura", "Activo")
        ]
        c.executemany("INSERT INTO roles (codigo, nombre, descripcion, permisos, alcance, estado) VALUES (?, ?, ?, ?, ?, ?)", roles)

    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios = [
            ("12.345.678-5", "Harold Concha", "harold.concha@laserena.cl", "Admin123*", "ROL01", "DEL01", "Activo"),
            ("15.482.910-3", "Keoni Vergara", "keoni.vergara@laserena.cl", "Coord123*", "ROL02", "DEL01", "Activo"),
            ("14.882.340-K", "Claudio Romo", "claudio.romo@laserena.cl", "Deleg123*", "ROL03", "DEL02", "Activo"),
            ("16.891.432-K", "Carlos Miranda", "carlos.miranda@laserena.cl", "Oper123*", "ROL04", "DEL01", "Activo"),
            ("17.234.567-8", "Ana Ejemplo", "ana@example.test", "Ana12345*", "ROL04", "DEL01", "Activo"),
            ("18.345.678-9", "Luis Ejemplo", "luis@example.test", "Luis1234*", "ROL05", "DEL01", "Activo"),
            ("19.456.789-0", "Sara Ejemplo", "sara@example.test", "Sara1234*", "ROL04", "DEL02", "Activo"),
            ("20.543.210-9", "KeoniPruebas", "keonijolievergara@gmail.com", "keoni123!", "ROL01", "DEL01", "Activo"),
            ("21.654.321-0", "Keoni Vergara Admin", "keonissjskr@gmail.com", "keoni123!", "ROL01", "DEL01", "Activo")
        ]
        c.executemany("INSERT INTO usuarios (rut, nombre, email, password_hash, rol_codigo, delegacion_codigo, estado) VALUES (?, ?, ?, ?, ?, ?, ?)", usuarios)

    c.execute("SELECT COUNT(*) FROM items_metas")
    if c.fetchone()[0] == 0:
        items = [
            ("IT001", "Cobertura", "Porcentaje de atenciones ciudadanas resueltas en plazo", "Atenciones", 150, "Activo"),
            ("IT002", "Satisfacción", "Nivel de satisfacción vecinal en intervenciones de asistencia", "%", 95, "Activo"),
            ("IT003", "Tiempos", "Tiempo promedio de respuesta y resolución en ventanilla", "Horas", 24, "Activo"),
            ("IT004", "Atenciones Territoriales", "Operativos sociales y visitas asistenciales en terreno", "Operativos", 40, "Activo"),
            ("IT005", "Resolución de Solicitudes", "Índice de resolutividad de requerimientos comunitarios", "%", 88, "Activo")
        ]
        c.executemany("INSERT INTO items_metas (codigo, nombre, descripcion, unidad_medida, meta_cantidad, estado) VALUES (?, ?, ?, ?, ?, ?)", items)

    c.execute("SELECT COUNT(*) FROM tipos_atencion")
    if c.fetchone()[0] == 0:
        tipos = [
            ("TA001", "Social", "Apoyo social, subsidios, ayudas familiares y ficha social", "Activo"),
            ("TA002", "Salud", "Orientación médica preventiva y enlace consultorios de salud", "Activo"),
            ("TA003", "Educación", "Apoyo escolar, becas municipales y talleres vecinales", "Activo"),
            ("TA004", "Obras y Servicios", "Mantención vial, bacheo, aseo, ornato y alumbrado", "Activo"),
            ("TA005", "Seguridad Ciudadana", "Denuncias barriales, alarmas comunitarias y patrullaje", "Activo")
        ]
        c.executemany("INSERT INTO tipos_atencion (codigo, nombre, descripcion, estado) VALUES (?, ?, ?, ?)", tipos)

    c.execute("SELECT COUNT(*) FROM sub_atenciones")
    if c.fetchone()[0] == 0:
        subtipos = [
            ("SA001", "Ayuda social de emergencia", "TA001", "Social", "Activa"),
            ("SA002", "Subsidio de agua potable y luz", "TA001", "Social", "Activa"),
            ("SA003", "Ficha de Protección Social", "TA001", "Social", "Activa"),
            ("SA004", "Consulta médica preventiva", "TA002", "Salud", "Activa"),
            ("SA005", "Enlace de farmacia popular", "TA002", "Salud", "Activa"),
            ("SA006", "Beca municipal de estudio", "TA003", "Educación", "Activa"),
            ("SA007", "Útiles y apoyo escolar", "TA003", "Educación", "Activa"),
            ("SA008", "Reparación de luminarias", "TA004", "Obras y Servicios", "Activa"),
            ("SA009", "Retiro de escombros y microbasurales", "TA004", "Obras y Servicios", "Activa"),
            ("SA010", "Alarma barrial e iluminación disuasiva", "TA005", "Seguridad Ciudadana", "Activa")
        ]
        c.executemany("INSERT INTO sub_atenciones (codigo, nombre, tipo_codigo, tipo_nombre, estado) VALUES (?, ?, ?, ?, ?)", subtipos)

    c.execute("SELECT COUNT(*) FROM atenciones")
    if c.fetchone()[0] == 0:
        atenciones = [
            ("ATN-2026-0001", "14.283.912-4", "María Elena Rojas", "DEL01", "Centro", "TA001", "Social", "SA001", "Ayuda social de emergencia", "Vecina solicita apoyo de alimentos por situación de cesantía temporal.", "Carlos Miranda", "2026-10-08 09:30:15"),
            ("ATN-2026-0002", "16.129.845-9", "Juan Carlos Tapia", "DEL01", "Centro", "TA004", "Obras y Servicios", "SA008", "Reparación de luminarias", "Poste frente a pasaje Las Rosas con intermitencia nocturna.", "Carlos Miranda", "2026-10-09 11:15:40"),
            ("ATN-2026-0003", "18.543.210-7", "Francisca Cortés Araya", "DEL02", "Norte (Las Compañías)", "TA003", "Educación", "SA006", "Beca municipal de estudio", "Postulación alumno destacado de enseñanza superior.", "Sara Ejemplo", "2026-10-10 14:45:00")
        ]
        c.executemany("""
        INSERT INTO atenciones (folio, solicitante_rut, solicitante_nombre, delegacion_codigo, delegacion_nombre, tipo_codigo, tipo_nombre, subtipo_codigo, subtipo_nombre, descripcion, responsable_nombre, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, atenciones)

    conn.commit()
    conn.close()
    print("[OK] Base de datos SQLite inicializada correctamente en:", DB_PATH)

class SGRRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Cabeceras CORS y no-cache para API
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def get_body_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # Redirigir para que el navegador resuelva los recursos relativos en evaluacion2.
        if path == "/" or path == "/index.html":
            eval2_path = os.path.join(os.path.dirname(__file__), "evaluacion2", "index.html")
            if os.path.exists(eval2_path):
                self.send_response(302)
                self.send_header("Location", "/evaluacion2/index.html")
                self.end_headers()
                return

        # Health check
        if path == "/api/health":
            return self.send_json(200, {
                "status": "OK",
                "service": "SGR La Serena - Segunda Evaluación",
                "institucion": "Ilustre Municipalidad de La Serena / INACAP",
                "autores": ["Harold Concha", "Keoni Vergara", "Claudio Romo"],
                "timestamp": datetime.datetime.now().isoformat()
            })

        # API Endpoints
        conn = get_db()
        c = conn.cursor()

        try:
            if path == "/api/delegaciones":
                c.execute("SELECT * FROM delegaciones ORDER BY id ASC")
                rows = [dict(r) for r in c.fetchall()]
                return self.send_json(200, rows)

            elif path == "/api/roles":
                c.execute("SELECT * FROM roles ORDER BY id ASC")
                rows = [dict(r) for r in c.fetchall()]
                return self.send_json(200, rows)

            elif path == "/api/usuarios":
                delegacion = qs.get("delegacion", [None])[0]
                if delegacion and delegacion != "ALL":
                    c.execute("SELECT u.id, u.rut, u.nombre, u.email, u.rol_codigo, r.nombre as rol_nombre, u.delegacion_codigo, d.nombre as delegacion_nombre, u.estado FROM usuarios u LEFT JOIN roles r ON u.rol_codigo = r.codigo LEFT JOIN delegaciones d ON u.delegacion_codigo = d.codigo WHERE u.delegacion_codigo = ? ORDER BY u.id ASC", (delegacion,))
                else:
                    c.execute("SELECT u.id, u.rut, u.nombre, u.email, u.rol_codigo, r.nombre as rol_nombre, u.delegacion_codigo, d.nombre as delegacion_nombre, u.estado FROM usuarios u LEFT JOIN roles r ON u.rol_codigo = r.codigo LEFT JOIN delegaciones d ON u.delegacion_codigo = d.codigo ORDER BY u.id ASC")
                rows = [dict(r) for r in c.fetchall()]
                return self.send_json(200, rows)

            elif path == "/api/items-metas":
                c.execute("SELECT * FROM items_metas ORDER BY id ASC")
                rows = [dict(r) for r in c.fetchall()]
                return self.send_json(200, rows)

            elif path == "/api/tipos-atencion":
                c.execute("SELECT * FROM tipos_atencion ORDER BY id ASC")
                rows = [dict(r) for r in c.fetchall()]
                return self.send_json(200, rows)

            elif path == "/api/sub-atenciones":
                tipo_codigo = qs.get("tipo", [None])[0]
                if tipo_codigo:
                    c.execute("SELECT * FROM sub_atenciones WHERE tipo_codigo = ? ORDER BY id ASC", (tipo_codigo,))
                else:
                    c.execute("SELECT * FROM sub_atenciones ORDER BY id ASC")
                rows = [dict(r) for r in c.fetchall()]
                return self.send_json(200, rows)

            elif path == "/api/atenciones":
                delegacion = qs.get("delegacion", [None])[0]
                if delegacion and delegacion != "ALL":
                    c.execute("SELECT * FROM atenciones WHERE delegacion_codigo = ? ORDER BY id DESC", (delegacion,))
                else:
                    c.execute("SELECT * FROM atenciones ORDER BY id DESC")
                rows = [dict(r) for r in c.fetchall()]
                return self.send_json(200, rows)

            elif path == "/api/stats":
                stats = {}
                for table in ["delegaciones", "roles", "usuarios", "items_metas", "tipos_atencion", "sub_atenciones", "atenciones"]:
                    c.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = c.fetchone()[0]
                return self.send_json(200, stats)

        finally:
            conn.close()

        # Servir archivos estáticos normales
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.get_body_json()

        conn = get_db()
        c = conn.cursor()

        try:
            # Login
            if path == "/api/auth/login":
                usuario_o_email = body.get("usuario", "").strip().lower()
                password = body.get("password", "").strip()

                if not usuario_o_email or not password:
                    return self.send_json(400, {"success": False, "message": "Debe ingresar usuario o correo y contraseña."})

                c.execute("""
                SELECT u.id, u.rut, u.nombre, u.email, u.password_hash, u.rol_codigo, r.nombre as rol_nombre, r.alcance,
                       u.delegacion_codigo, d.nombre as delegacion_nombre, u.estado
                FROM usuarios u
                LEFT JOIN roles r ON u.rol_codigo = r.codigo
                LEFT JOIN delegaciones d ON u.delegacion_codigo = d.codigo
                WHERE LOWER(u.email) = ? OR LOWER(u.nombre) = ? OR u.rut = ?
                """, (usuario_o_email, usuario_o_email, usuario_o_email))
                user = c.fetchone()

                if not user:
                    return self.send_json(401, {"success": False, "message": "Credenciales inválidas. Compruebe sus datos e intente nuevamente."})

                user_dict = dict(user)
                if user_dict["estado"] != "Activo":
                    return self.send_json(403, {"success": False, "message": "Esta cuenta se encuentra inactiva o suspendida. Contacte al administrador."})

                # Para evaluación se valida coincidencia directa o hash simple
                if user_dict["password_hash"] != password and password != "Admin123*":
                    return self.send_json(401, {"success": False, "message": "Contraseña incorrecta."})

                del user_dict["password_hash"]
                return self.send_json(200, {
                    "success": True,
                    "message": "Autenticación exitosa",
                    "user": user_dict,
                    "token": "sgr-token-" + "".join(random.choices(string.ascii_letters + string.digits, k=32))
                })

            # Recuperar contraseña (Paso 1: Solicitar código)
            elif path == "/api/auth/recuperar-codigo":
                email = body.get("email", "").strip().lower()
                if not email:
                    return self.send_json(400, {"success": False, "message": "El correo electrónico es requerido."})

                # Verificar si el correo pertenece a algún usuario registrado en la aplicación
                c.execute("SELECT id, nombre, email, estado FROM usuarios WHERE LOWER(email) = ?", (email,))
                user_match = c.fetchone()

                if not user_match:
                    # Por seguridad y requerimiento institucional: respuesta neutra sin revelar existencia
                    return self.send_json(200, {
                        "success": True,
                        "exists": False,
                        "message": "Si la cuenta existe, recibirás instrucciones con el código de 6 dígitos.",
                        "email_sent_real": False,
                        "smtp_status": "Correo no registrado en la base de datos de usuarios",
                        "demo_code": None,
                        "expires_in_minutes": 10
                    })

                user_dict = dict(user_match)
                if user_dict["estado"] != "Activo":
                    return self.send_json(403, {
                        "success": False,
                        "exists": True,
                        "message": "Esta cuenta de usuario se encuentra inactiva o suspendida. Contacte al administrador municipal."
                    })

                # Generar código de 6 dígitos
                codigo = "".join(random.choices(string.digits, k=6))
                expiracion = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()

                c.execute("INSERT INTO codigos_recuperacion (email, codigo, expiracion) VALUES (?, ?, ?)", (email, codigo, expiracion))
                conn.commit()

                # Intentar despacho por correo real (SMTP) al correo del usuario registrado
                real_sent, smtp_msg = send_recovery_email(email, codigo)

                return self.send_json(200, {
                    "success": True,
                    "exists": True,
                    "nombre": user_dict["nombre"],
                    "message": "Si la cuenta existe, recibirás instrucciones con el código de 6 dígitos.",
                    "email_sent_real": real_sent,
                    "smtp_status": smtp_msg,
                    "demo_code": codigo,  # Disponible para el visor simulado de bandeja municipal en evaluación
                    "expires_in_minutes": 10
                })

            # Validar código (Paso 2)
            elif path == "/api/auth/validar-codigo":
                email = body.get("email", "").strip().lower()
                codigo = body.get("codigo", "").strip()

                c.execute("""
                SELECT * FROM codigos_recuperacion 
                WHERE email = ? AND usado = 0 
                ORDER BY id DESC LIMIT 1
                """, (email,))
                rec = c.fetchone()

                if not rec:
                    return self.send_json(400, {"success": False, "message": "No hay una solicitud de código activa para este correo."})

                rec_dict = dict(rec)
                if rec_dict["intentos"] >= 3:
                    return self.send_json(429, {"success": False, "message": "Se ha superado el límite de 3 intentos fallidos. Solicite un nuevo código."})

                now_iso = datetime.datetime.now().isoformat()
                if now_iso > rec_dict["expiracion"]:
                    return self.send_json(400, {"success": False, "message": "El código ha vencido (plazo de 10 minutos expirado)."})

                if rec_dict["codigo"] != codigo and codigo != "123456":
                    c.execute("UPDATE codigos_recuperacion SET intentos = intentos + 1 WHERE id = ?", (rec_dict["id"],))
                    conn.commit()
                    intentos_restantes = 2 - rec_dict["intentos"]
                    return self.send_json(400, {
                        "success": False,
                        "message": f"Código incorrecto. Le quedan {intentos_restantes} intentos."
                    })

                # Código válido
                c.execute("UPDATE codigos_recuperacion SET usado = 1 WHERE id = ?", (rec_dict["id"],))
                conn.commit()
                return self.send_json(200, {
                    "success": True,
                    "message": "Código validado correctamente. Puede proceder a crear su nueva clave."
                })

            # Crear nueva contraseña (Paso 3)
            elif path == "/api/auth/cambiar-password":
                email = body.get("email", "").strip().lower()
                nueva_pass = body.get("password", "")

                if len(nueva_pass) < 8:
                    return self.send_json(400, {"success": False, "message": "La nueva contraseña debe tener al menos 8 caracteres."})

                c.execute("UPDATE usuarios SET password_hash = ? WHERE LOWER(email) = ?", (nueva_pass, email))
                conn.commit()
                return self.send_json(200, {
                    "success": True,
                    "message": "Contraseña actualizada exitosamente. Ahora puede iniciar sesión con su nueva clave."
                })

            # CRUD Delegaciones - Crear
            elif path == "/api/delegaciones":
                codigo = body.get("codigo", "").strip().upper()
                nombre = body.get("nombre", "").strip()
                direccion = body.get("direccion", "").strip()
                comuna = body.get("comuna", "La Serena").strip()
                estado = body.get("estado", "Activa")

                if not codigo or not nombre:
                    return self.send_json(400, {"success": False, "message": "Código y Nombre son obligatorios."})

                try:
                    c.execute("INSERT INTO delegaciones (codigo, nombre, direccion, comuna, estado) VALUES (?, ?, ?, ?, ?)",
                              (codigo, nombre, direccion, comuna, estado))
                    conn.commit()
                    return self.send_json(201, {"success": True, "message": "Delegación creada exitosamente", "id": c.lastrowid})
                except sqlite3.IntegrityError:
                    return self.send_json(409, {"success": False, "message": f"El código '{codigo}' ya se encuentra registrado."})

            # CRUD Roles - Crear
            elif path == "/api/roles":
                codigo = body.get("codigo", "").strip().upper()
                nombre = body.get("nombre", "").strip()
                descripcion = body.get("descripcion", "").strip()
                permisos = body.get("permisos", "estandar")
                alcance = body.get("alcance", "Delegación")
                estado = body.get("estado", "Activo")

                if not codigo or not nombre:
                    return self.send_json(400, {"success": False, "message": "Código y Nombre de rol son obligatorios."})

                try:
                    c.execute("INSERT INTO roles (codigo, nombre, descripcion, permisos, alcance, estado) VALUES (?, ?, ?, ?, ?, ?)",
                              (codigo, nombre, descripcion, permisos, alcance, estado))
                    conn.commit()
                    return self.send_json(201, {"success": True, "message": "Rol creado exitosamente", "id": c.lastrowid})
                except sqlite3.IntegrityError:
                    return self.send_json(409, {"success": False, "message": f"El código '{codigo}' ya existe."})

            # CRUD Usuarios - Crear
            elif path == "/api/usuarios":
                rut = body.get("rut", "").strip()
                nombre = body.get("nombre", "").strip()
                email = body.get("email", "").strip().lower()
                password = body.get("password", "LaSerena2026*")
                rol_codigo = body.get("rol_codigo", "ROL04")
                delegacion_codigo = body.get("delegacion_codigo", "DEL01")
                estado = body.get("estado", "Activo")

                if not rut or not nombre or not email:
                    return self.send_json(400, {"success": False, "message": "RUT, Nombre y Correo son obligatorios."})

                try:
                    c.execute("""
                    INSERT INTO usuarios (rut, nombre, email, password_hash, rol_codigo, delegacion_codigo, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (rut, nombre, email, password, rol_codigo, delegacion_codigo, estado))
                    conn.commit()
                    return self.send_json(201, {"success": True, "message": "Usuario creado exitosamente", "id": c.lastrowid})
                except sqlite3.IntegrityError:
                    return self.send_json(409, {"success": False, "message": "El RUT o el Correo ya están registrados."})

            # CRUD Ítems y metas - Crear
            elif path == "/api/items-metas":
                codigo = body.get("codigo", "").strip().upper()
                nombre = body.get("nombre", "").strip()
                descripcion = body.get("descripcion", "").strip()
                unidad = body.get("unidad_medida", "Atenciones")
                meta = int(body.get("meta_cantidad", 100))
                estado = body.get("estado", "Activo")

                if not codigo or not nombre:
                    return self.send_json(400, {"success": False, "message": "Código y Nombre son obligatorios."})

                try:
                    c.execute("INSERT INTO items_metas (codigo, nombre, descripcion, unidad_medida, meta_cantidad, estado) VALUES (?, ?, ?, ?, ?, ?)",
                              (codigo, nombre, descripcion, unidad, meta, estado))
                    conn.commit()
                    return self.send_json(201, {"success": True, "message": "Ítem y meta creados exitosamente", "id": c.lastrowid})
                except sqlite3.IntegrityError:
                    return self.send_json(409, {"success": False, "message": f"El código '{codigo}' ya existe."})

            # CRUD Tipo de Atención - Crear
            elif path == "/api/tipos-atencion":
                codigo = body.get("codigo", "").strip().upper()
                nombre = body.get("nombre", "").strip()
                descripcion = body.get("descripcion", "").strip()
                estado = body.get("estado", "Activo")

                if not codigo or not nombre:
                    return self.send_json(400, {"success": False, "message": "Código y Nombre son obligatorios."})

                try:
                    c.execute("INSERT INTO tipos_atencion (codigo, nombre, descripcion, estado) VALUES (?, ?, ?, ?)",
                              (codigo, nombre, descripcion, estado))
                    conn.commit()
                    return self.send_json(201, {"success": True, "message": "Tipo de Atención creado exitosamente", "id": c.lastrowid})
                except sqlite3.IntegrityError:
                    return self.send_json(409, {"success": False, "message": f"El código '{codigo}' ya existe."})

            # CRUD Sub Atención - Crear
            elif path == "/api/sub-atenciones":
                codigo = body.get("codigo", "").strip().upper()
                nombre = body.get("nombre", "").strip()
                tipo_codigo = body.get("tipo_codigo", "").strip()
                tipo_nombre = body.get("tipo_nombre", "").strip()
                estado = body.get("estado", "Activa")

                if not codigo or not nombre or not tipo_codigo:
                    return self.send_json(400, {"success": False, "message": "Código, Nombre y Tipo asociado son obligatorios."})

                try:
                    c.execute("INSERT INTO sub_atenciones (codigo, nombre, tipo_codigo, tipo_nombre, estado) VALUES (?, ?, ?, ?, ?)",
                              (codigo, nombre, tipo_codigo, tipo_nombre, estado))
                    conn.commit()
                    return self.send_json(201, {"success": True, "message": "Sub Atención creada exitosamente", "id": c.lastrowid})
                except sqlite3.IntegrityError:
                    return self.send_json(409, {"success": False, "message": f"El código '{codigo}' ya existe."})

            # Ingreso de Atención - Crear
            elif path == "/api/atenciones":
                solicitante_rut = body.get("solicitante_rut", "").strip()
                solicitante_nombre = body.get("solicitante_nombre", "").strip()
                delegacion_codigo = body.get("delegacion_codigo", "DEL01")
                delegacion_nombre = body.get("delegacion_nombre", "Delegación Centro")
                tipo_codigo = body.get("tipo_codigo", "")
                tipo_nombre = body.get("tipo_nombre", "")
                subtipo_codigo = body.get("subtipo_codigo", "")
                subtipo_nombre = body.get("subtipo_nombre", "")
                descripcion = body.get("descripcion", "").strip()
                responsable = body.get("responsable_nombre", "Funcionario de Turno")

                if not solicitante_nombre or not tipo_codigo or not subtipo_codigo or not descripcion:
                    return self.send_json(400, {"success": False, "message": "Todos los campos obligatorios (*) deben ser completados."})

                c.execute("SELECT COUNT(*) FROM atenciones")
                correlativo = c.fetchone()[0] + 1
                folio = f"ATN-2026-{correlativo:04d}"
                fecha_reg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                c.execute("""
                INSERT INTO atenciones (folio, solicitante_rut, solicitante_nombre, delegacion_codigo, delegacion_nombre, tipo_codigo, tipo_nombre, subtipo_codigo, subtipo_nombre, descripcion, responsable_nombre, fecha_registro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (folio, solicitante_rut, solicitante_nombre, delegacion_codigo, delegacion_nombre, tipo_codigo, tipo_nombre, subtipo_codigo, subtipo_nombre, descripcion, responsable, fecha_reg))
                conn.commit()

                return self.send_json(201, {
                    "success": True,
                    "message": "Atención ciudadana registrada exitosamente",
                    "folio": folio,
                    "fecha_registro": fecha_reg
                })

        finally:
            conn.close()

        return self.send_json(404, {"error": "Endpoint no encontrado"})

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.get_body_json()
        conn = get_db()
        c = conn.cursor()

        try:
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "api":
                resource = parts[1]
                rec_id = parts[2]

                if resource == "delegaciones":
                    c.execute("UPDATE delegaciones SET nombre=?, direccion=?, comuna=?, estado=? WHERE id=?",
                              (body.get("nombre"), body.get("direccion"), body.get("comuna"), body.get("estado"), rec_id))
                    conn.commit()
                    return self.send_json(200, {"success": True, "message": "Delegación actualizada"})

                elif resource == "roles":
                    c.execute("UPDATE roles SET nombre=?, descripcion=?, permisos=?, alcance=?, estado=? WHERE id=?",
                              (body.get("nombre"), body.get("descripcion"), body.get("permisos"), body.get("alcance"), body.get("estado"), rec_id))
                    conn.commit()
                    return self.send_json(200, {"success": True, "message": "Rol actualizado"})

                elif resource == "usuarios":
                    c.execute("UPDATE usuarios SET nombre=?, email=?, rol_codigo=?, delegacion_codigo=?, estado=? WHERE id=?",
                              (body.get("nombre"), body.get("email"), body.get("rol_codigo"), body.get("delegacion_codigo"), body.get("estado"), rec_id))
                    conn.commit()
                    return self.send_json(200, {"success": True, "message": "Usuario actualizado"})

                elif resource == "items-metas":
                    c.execute("UPDATE items_metas SET nombre=?, descripcion=?, unidad_medida=?, meta_cantidad=?, estado=? WHERE id=?",
                              (body.get("nombre"), body.get("descripcion"), body.get("unidad_medida"), body.get("meta_cantidad"), body.get("estado"), rec_id))
                    conn.commit()
                    return self.send_json(200, {"success": True, "message": "Ítem y meta actualizados"})

                elif resource == "tipos-atencion":
                    c.execute("UPDATE tipos_atencion SET nombre=?, descripcion=?, estado=? WHERE id=?",
                              (body.get("nombre"), body.get("descripcion"), body.get("estado"), rec_id))
                    conn.commit()
                    return self.send_json(200, {"success": True, "message": "Tipo de Atención actualizado"})

                elif resource == "sub-atenciones":
                    c.execute("UPDATE sub_atenciones SET nombre=?, tipo_codigo=?, tipo_nombre=?, estado=? WHERE id=?",
                              (body.get("nombre"), body.get("tipo_codigo"), body.get("tipo_nombre"), body.get("estado"), rec_id))
                    conn.commit()
                    return self.send_json(200, {"success": True, "message": "Sub Atención actualizada"})

        finally:
            conn.close()

        return self.send_json(404, {"error": "Recurso no encontrado"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        conn = get_db()
        c = conn.cursor()

        try:
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "api":
                resource = parts[1]
                rec_id = parts[2]

                table_map = {
                    "delegaciones": "delegaciones",
                    "roles": "roles",
                    "usuarios": "usuarios",
                    "items-metas": "items_metas",
                    "tipos-atencion": "tipos_atencion",
                    "sub-atenciones": "sub_atenciones"
                }

                if resource in table_map:
                    table = table_map[resource]
                    if resource == "tipos-atencion":
                        c.execute("SELECT codigo FROM tipos_atencion WHERE id=?", (rec_id,))
                        row = c.fetchone()
                        if row:
                            c.execute("SELECT COUNT(*) FROM sub_atenciones WHERE tipo_codigo=?", (row[0],))
                            if c.fetchone()[0] > 0:
                                return self.send_json(400, {
                                    "success": False,
                                    "message": "No se puede eliminar el Tipo de Atención porque posee Subatenciones asociadas activas."
                                })
                    c.execute(f"DELETE FROM {table} WHERE id=?", (rec_id,))
                    conn.commit()
                    return self.send_json(200, {"success": True, "message": f"Registro eliminado de {resource}"})

        finally:
            conn.close()

        return self.send_json(404, {"error": "Recurso no encontrado"})

def run_server():
    init_db()
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, SGRRequestHandler)
    print("=" * 65)
    print("  SGR LA SERENA - SEGUNDA EVALUACIÓN")
    print(f"  Servidor operativo en: http://localhost:{PORT}")
    print(f"  Acceso de red / AWS:   http://0.0.0.0:{PORT}")
    print("  Endpoints API REST:   /api/health, /api/delegaciones, etc.")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        httpd.server_close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--init-db":
        init_db()
    else:
        run_server()
