#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"

SERVICES=(
    "llm.service"
    "singender-interface.service"
    "singender-main.service"
)

echo "========================================"
echo " Singender Aufzug – Service Installation"
echo "========================================"
echo
echo "Projekt: $PROJECT_DIR"
echo

# --------------------------------------------------
# Voraussetzungen prüfen
# --------------------------------------------------

echo "Prüfe Voraussetzungen..."

ERRORS=0

check_file() {
    if [ -e "$1" ]; then
        echo "  [OK] $1"
    else
        echo "  [FEHLT] $1"
        ERRORS=$((ERRORS + 1))
    fi
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "  [OK] $1"
    else
        echo "  [FEHLT] $1"
        ERRORS=$((ERRORS + 1))
    fi
}

check_file "$PROJECT_DIR/.venv/bin/python"
check_file "$PROJECT_DIR/main.py"
check_file "$PROJECT_DIR/interface/interface.py"
check_file "$PROJECT_DIR/models/llm/run_server.sh"
check_file "$PROJECT_DIR/models/llm/Qwen3-4B-Q4_K_M.gguf"
check_file "/home/pi/llama.cpp/build/bin/llama-server"

check_command curl

echo

if [ "$ERRORS" -ne 0 ]; then
    echo "ABBRUCH: $ERRORS Voraussetzung(en) fehlen."
    echo "Es wurden keine systemd-Services installiert."
    exit 1
fi

echo "Alle Voraussetzungen vorhanden."
echo

# --------------------------------------------------
# Service-Dateien prüfen
# --------------------------------------------------

for SERVICE in "${SERVICES[@]}"; do
    check_file "$PROJECT_DIR/systemd/$SERVICE"
done

if [ "$ERRORS" -ne 0 ]; then
    echo
    echo "ABBRUCH: Service-Dateien fehlen."
    exit 1
fi

# --------------------------------------------------
# Services installieren
# --------------------------------------------------

echo
echo "Installiere systemd-Services..."

for SERVICE in "${SERVICES[@]}"; do
    echo "  -> $SERVICE"
    sudo cp "$PROJECT_DIR/systemd/$SERVICE" "$SYSTEMD_DIR/$SERVICE"
done

echo
echo "Lade systemd-Konfiguration neu..."
sudo systemctl daemon-reload

echo
echo "Aktiviere Autostart..."

for SERVICE in "${SERVICES[@]}"; do
    sudo systemctl enable "$SERVICE"
done

echo
echo "========================================"
echo " Installation abgeschlossen"
echo "========================================"
echo

for SERVICE in "${SERVICES[@]}"; do
    printf "%-32s " "$SERVICE"
    systemctl is-enabled "$SERVICE"
done

echo
echo "Die Services wurden NICHT gestartet."
echo "Für den ersten Test:"
echo
echo "  sudo reboot"
echo
echo "Danach prüfen mit:"
echo
echo "  systemctl status llm singender-main singender-interface --no-pager -l"
