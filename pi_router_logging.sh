#!/bin/bash
# Router Syslog Empfang einrichten

set -e

ROUTER_IP=$(ip route | grep default | awk '{print $3}')
RSYSLOG_CONF="/etc/rsyslog.conf"
CURRENT_USER="${USER}"
CURRENT_GROUP="$(id -gn)"

# Bestimme das Verzeichnis, in dem dieses Skript liegt
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
LOG_FILE="${SCRIPT_DIR}/router.log"

echo "==> Log-Datei wird in ${LOG_FILE} gespeichert."
echo "==> Router-IP ermittelt: ${ROUTER_IP}"

echo "==> Prüfe rsyslog Installation..."
if ! command -v rsyslogd &> /dev/null; then
    echo "    rsyslog nicht gefunden - wird installiert..."
    if command -v dietpi-software &> /dev/null; then
        echo "    DietPi erkannt - installiere via dietpi-software..."
        sudo dietpi-software install 102
    else
        echo "    Installiere via apt..."
        sudo apt install rsyslog -y
    fi
else
    echo "    rsyslog bereits installiert - übersprungen."
fi

echo "==> Prüfe rsyslog.conf..."

if ! grep -q "SpaceLFOnReceive" "${RSYSLOG_CONF}"; then
    echo "    SpaceLFOnReceive fehlt - wird eingefuegt..."
    sudo sed -i '/module(load="imudp")/i $SpaceLFOnReceive on' "${RSYSLOG_CONF}"
else
    echo "    SpaceLFOnReceive bereits vorhanden - übersprungen."
fi

if grep -q '#module(load="imudp")' "${RSYSLOG_CONF}"; then
    echo "    imudp ist auskommentiert - wird aktiviert..."
    sudo sed -i 's/#module(load="imudp")/module(load="imudp")/' "${RSYSLOG_CONF}"
elif grep -q 'module(load="imudp")' "${RSYSLOG_CONF}"; then
    echo "    imudp bereits aktiv - übersprungen."
else
    echo "    imudp fehlt komplett - wird eingefuegt..."
    echo '$SpaceLFOnReceive on
module(load="imudp")
input(type="imudp" port="514")' | sudo tee -a "${RSYSLOG_CONF}" > /dev/null
fi

if grep -q '#input(type="imudp" port="514")' "${RSYSLOG_CONF}"; then
    echo "    imudp input ist auskommentiert - wird aktiviert..."
    sudo sed -i 's/#input(type="imudp" port="514")/input(type="imudp" port="514")/' "${RSYSLOG_CONF}"
elif grep -q 'input(type="imudp" port="514")' "${RSYSLOG_CONF}"; then
    echo "    imudp input bereits aktiv - übersprungen."
fi

echo "==> Prüfe auf doppelte Filterregeln..."
if [ -f /etc/rsyslog.d/router.conf ] && [ -f /etc/rsyslog.d/10-router.conf ]; then
    echo "    Doppelte Regel gefunden - router.conf wird entfernt..."
    sudo rm /etc/rsyslog.d/router.conf
elif [ -f /etc/rsyslog.d/router.conf ]; then
    echo "    Alte router.conf gefunden - wird zu 10-router.conf umbenannt..."
    sudo mv /etc/rsyslog.d/router.conf /etc/rsyslog.d/10-router.conf
fi

echo "==> Router-Filterregel anlegen..."
if [ -f /etc/rsyslog.d/10-router.conf ]; then
    echo "    10-router.conf bereits vorhanden - wird überschrieben um korrekte Syntax sicherzustellen..."
fi

sudo tee /etc/rsyslog.d/10-router.conf > /dev/null <<EOF
if (\$fromhost-ip == '${ROUTER_IP}') then {
    action(type="omfile" file="${LOG_FILE}")
    stop
}
EOF
echo "==> Rsyslog Systemd-Berechtigungen anpassen..."
# Moderne Linux-Systeme schuetzen /home vor Diensten wie rsyslog
sudo mkdir -p /etc/systemd/system/rsyslog.service.d
sudo tee /etc/systemd/system/rsyslog.service.d/override.conf > /dev/null <<EOF
[Service]
ProtectHome=read-only
ReadWritePaths=${SCRIPT_DIR}
EOF
sudo systemctl daemon-reload
echo "    Systemd-Override fuer Rsyslog eingerichtet."

echo "==> Log-Datei anlegen..."
if [ -f "${LOG_FILE}" ]; then
    echo "    ${LOG_FILE} bereits vorhanden - übersprungen."
else
    sudo touch "${LOG_FILE}"
    sudo chown root:${CURRENT_GROUP} "${LOG_FILE}"
    sudo chmod 644 "${LOG_FILE}"
    echo "    ${LOG_FILE} angelegt (Owner: root:${CURRENT_GROUP}"
    echo "                                 lesbar für Standarduser)"
fi

echo "==> Log-Rotation einrichten..."
if [ -f /etc/logrotate.d/router ]; then
    echo "    logrotate-Regel bereits vorhanden - übersprungen."
else
    sudo tee /etc/logrotate.d/router > /dev/null <<EOF
${LOG_FILE} {
    daily
    rotate 14
    compress
    missingok
    notifempty
    create 644 root ${CURRENT_GROUP}
    postrotate
        systemctl is-active rsyslog && systemctl kill -s HUP rsyslog || true
    endscript
}
EOF
    echo "    logrotate-Regel angelegt."
fi

echo "==> Rsyslog neu starten..."
sudo systemctl restart rsyslog

echo ""
echo "==> Fertig. Log überwachen mit:"
echo "    tail -f ${LOG_FILE}"
