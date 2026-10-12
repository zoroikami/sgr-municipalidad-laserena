#!/bin/bash
# =============================================================================
# SISTEMA DE GESTIÓN DE RESULTADOS (SGR) - ILUSTRE MUNICIPALIDAD DE LA SERENA
# Script de Despliegue Automatizado en AWS EC2 (Ubuntu / Amazon Linux 2023)
# Autores: Harold Concha, Keoni Vergara, Claudio Romo | INACAP - Proyecto Integrado
# =============================================================================

set -e

echo "=========================================================="
echo " INICIANDO DESPLIEGUE SGR LA SERENA EN AWS EC2"
echo "=========================================================="

APP_DIR="/opt/sgr-municipalidad-laserena"
SERVICE_NAME="sgr-laserena"

# 1. Actualizar repositorios e instalar paquetes base
if command -v apt-get &> /dev/null; then
    echo "[1/5] Actualizando paquetes en Ubuntu/Debian..."
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip git curl
elif command -v dnf &> /dev/null; then
    echo "[1/5] Actualizando paquetes en Amazon Linux 2023..."
    sudo dnf install -y git python3
fi

# 2. Clonar o actualizar repositorio
if [ ! -d "$APP_DIR" ]; then
    echo "[2/5] Clonando repositorio institucional..."
    sudo git clone -b feature/SGR-23-segunda-evaluacion-mantenedores-acceso https://github.com/zoroikami/sgr-municipalidad-laserena.git "$APP_DIR"
else
    echo "[2/5] Actualizando repositorio existente..."
    cd "$APP_DIR"
    sudo git fetch origin
    sudo git checkout feature/SGR-23-segunda-evaluacion-mantenedores-acceso
    sudo git pull origin feature/SGR-23-segunda-evaluacion-mantenedores-acceso
fi

cd "$APP_DIR"
sudo git checkout feature/SGR-23-segunda-evaluacion-mantenedores-acceso

# 3. Inicializar base de datos SQLite y datos semilla
echo "[3/5] Inicializando base de datos relacional y semillas..."
sudo python3 server.py --init-db

# 4. Configurar servicio systemd para ejecución continua en puerto 80
echo "[4/5] Configurando servicio systemd para alta disponibilidad..."
cat << 'EOF' | sudo tee /etc/systemd/system/sgr-laserena.service > /dev/null
[Unit]
Description=SGR La Serena - Sistema de Gestion de Resultados (INACAP Eval 2)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sgr-municipalidad-laserena
Environment="PORT=80"
ExecStart=/usr/bin/python3 /opt/sgr-municipalidad-laserena/server.py --port 80
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sgr-laserena.service
sudo systemctl restart sgr-laserena.service

# 5. Verificación
echo "[5/5] Comprobando disponibilidad del servicio..."
sleep 2

STATUS=$(curl -s http://127.0.0.1/api/health || echo "FAIL")
echo "Respuesta del servicio: $STATUS"

PUBLIC_IP=$(curl -s http://checkip.amazonaws.com || echo "IP_PUBLICA_EC2")

echo "=========================================================="
echo " DESPLIEGUE FINALIZADO EXITOSAMENTE"
echo " Acceso Web: http://${PUBLIC_IP}/"
echo " Evaluacion 2: http://${PUBLIC_IP}/evaluacion2/index.html"
echo " API Health: http://${PUBLIC_IP}/api/health"
echo "=========================================================="
