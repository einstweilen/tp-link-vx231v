#!/bin/bash
# Router Syslog Empfang einrichten

set -e

# Farben
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

info() { echo -e "  ${BLUE}ℹ${NC} $1"; }
success() { echo -e "  ${GREEN}✓${NC} $1"; }
error() { echo -e "  ${RED}✗${NC} $1"; }
step() { echo -e "\n${BOLD}==> $1${NC}"; }

echo -e "${BOLD}==== Router Syslog Einrichtung ====${NC}"

ROUTER_IP=$(ip route | grep default | awk '{print $3}')
RSYSLOG_CONF="/etc/rsyslog.conf"
CURRENT_USER="${USER}"
CURRENT_GROUP="$(id -gn)"

# Bestimme das Verzeichnis, in dem dieses Skript liegt
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
LOG_FILE="${SCRIPT_DIR}/router.log"

info "Log-Datei wird in ${LOG_FILE} gespeichert."
info "Router-IP ermittelt: ${ROUTER_IP}"

step "Prüfe rsyslog Installation..."
if ! command -v rsyslogd &> /dev/null && [ ! -x "/usr/sbin/rsyslogd" ]; then
    info "rsyslog nicht gefunden - wird installiert..."
    if command -v dietpi-software &> /dev/null; then
        info "DietPi erkannt - installiere via dietpi-software..."
        sudo dietpi-software install 102 > /dev/null 2>&1
    else
        info "Installiere via apt..."
        sudo apt update > /dev/null 2>&1 && sudo apt install rsyslog -y > /dev/null 2>&1
    fi
    success "rsyslog installiert."
else
    success "rsyslog bereits installiert."
fi

step "Prüfe rsyslog.conf..."

if ! grep -q "SpaceLFOnReceive" "${RSYSLOG_CONF}"; then
    info "SpaceLFOnReceive fehlt - wird eingefuegt..."
    sudo sed -i '/module(load="imudp")/i $SpaceLFOnReceive on' "${RSYSLOG_CONF}"
else
    success "SpaceLFOnReceive bereits vorhanden."
fi

if grep -q '#module(load="imudp")' "${RSYSLOG_CONF}"; then
    info "imudp ist auskommentiert - wird aktiviert..."
    sudo sed -i 's/#module(load="imudp")/module(load="imudp")/' "${RSYSLOG_CONF}"
elif grep -q 'module(load="imudp")' "${RSYSLOG_CONF}"; then
    success "imudp bereits aktiv."
else
    info "imudp fehlt komplett - wird eingefuegt..."
    echo '$SpaceLFOnReceive on
module(load="imudp")
input(type="imudp" port="514")' | sudo tee -a "${RSYSLOG_CONF}" > /dev/null
fi

if grep -q '#input(type="imudp" port="514")' "${RSYSLOG_CONF}"; then
    info "imudp input ist auskommentiert - wird aktiviert..."
    sudo sed -i 's/#input(type="imudp" port="514")/input(type="imudp" port="514")/' "${RSYSLOG_CONF}"
elif grep -q 'input(type="imudp" port="514")' "${RSYSLOG_CONF}"; then
    success "imudp input bereits aktiv."
fi

step "Prüfe auf doppelte Filterregeln..."
if [ -f /etc/rsyslog.d/router.conf ] && [ -f /etc/rsyslog.d/10-router.conf ]; then
    info "Doppelte Regel gefunden - router.conf wird entfernt..."
    sudo rm /etc/rsyslog.d/router.conf
elif [ -f /etc/rsyslog.d/router.conf ]; then
    info "Alte router.conf gefunden - wird zu 10-router.conf umbenannt..."
    sudo mv /etc/rsyslog.d/router.conf /etc/rsyslog.d/10-router.conf
else
    success "Keine doppelten Regeln."
fi

step "Router-Filterregel anlegen..."
if [ -f /etc/rsyslog.d/10-router.conf ]; then
    info "10-router.conf bereits vorhanden - wird aktualisiert..."
fi

sudo tee /etc/rsyslog.d/10-router.conf > /dev/null <<EOF
# Template: Original-Timestamp des Routers verwenden
template(name="RouterTimestamp" type="list") {
    property(name="timereported" dateFormat="rfc3339")
    constant(value=" ")
    property(name="hostname")
    constant(value=" ")
    property(name="syslogtag")
    property(name="msg" spifno1stsp="on")
    constant(value="\n")
}

if (\$fromhost-ip == '${ROUTER_IP}') then {
    action(type="omfile" file="${LOG_FILE}" template="RouterTimestamp")
    stop
}
EOF
success "Filterregel geschrieben."

step "Rsyslog Systemd-Berechtigungen anpassen..."
sudo mkdir -p /etc/systemd/system/rsyslog.service.d
sudo tee /etc/systemd/system/rsyslog.service.d/override.conf > /dev/null <<EOF
[Service]
ProtectHome=read-only
ReadWritePaths=${SCRIPT_DIR}
EOF
sudo systemctl daemon-reload > /dev/null 2>&1
success "Systemd-Override eingerichtet."

step "Log-Datei anlegen..."
if [ -f "${LOG_FILE}" ]; then
    success "${LOG_FILE} bereits vorhanden."
else
    sudo touch "${LOG_FILE}"
    sudo chown root:${CURRENT_GROUP} "${LOG_FILE}"
    sudo chmod 644 "${LOG_FILE}"
    success "${LOG_FILE} angelegt (Owner: root:${CURRENT_GROUP})."
fi

step "Log-Rotation einrichten..."
if [ -f /etc/logrotate.d/router ]; then
    success "logrotate-Regel bereits vorhanden."
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
    success "logrotate-Regel angelegt."
fi

step "Rsyslog neu starten..."
sudo systemctl restart rsyslog > /dev/null 2>&1
success "Rsyslog erfolgreich neu gestartet."

echo -e "\n${BOLD}==== Fertig ====${NC}"
info "Log überwachen mit: tail -f ${LOG_FILE}\n"
