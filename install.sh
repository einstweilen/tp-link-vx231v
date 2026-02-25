#!/usr/bin/env bash
#
# Installationsskript für tp-link-vx231v
# Dieses Skript führt die Schritte zur lokalen Installation und Einrichtung aus.
#

# Bei Fehler abbrechen
set -e

main() {
    echo "==== tp-link-vx231v Installation ===="

    if [ ! -d "tp-link-vx231v" ] && [ ! -f "requirements.txt" ]; then
        echo "[1/11] Klone das Repository..."
    git clone https://github.com/einstweilen/tp-link-vx231v.git
    echo "[2/1] Wechsle in das Verzeichnis..."
    cd tp-link-vx231v
elif [ -d "tp-link-vx231v" ]; then
    echo "[1/1] Verzeichnis 'tp-link-vx231v' existiert bereits."
    echo "[2/1] Wechsle in das Verzeichnis..."
    cd tp-link-vx231v
else
    echo "[1/1] Befinde mich bereits im Repository."
    echo "[2/1] Verzeichniswechsel übersprungen."
fi

echo "[3/11] Erstelle virtuelle Umgebung..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
echo "      Aktiviere virtuelle Umgebung..."
source .venv/bin/activate

echo "[4/11] Installiere Abhängigkeiten..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[5/11] Installiere Chromium in Playwright..."
playwright install chromium

    echo ""
    echo "[6/11] OPTIONAL: SNMP / TELNET verwenden"
    echo "      Falls Sie mit dem superadmin Account Ihres Routers"
    echo "      SNMP und Telnet aktiviert haben, können Sie"
    echo "      Routerdaten auch per SNMP abrufen."
    echo "      Dafür benötigen Sie 'snmpget' und 'snmpwalk'."
    read -p "      Möchten Sie SNMP-Tools jetzt installieren? (j/N) " SNMP_ANSWER
    if [[ "$SNMP_ANSWER" =~ ^[jJ] ]]; then
        if [[ "$(uname)" == "Darwin" ]]; then
            echo "      Installiere net-snmp via Homebrew (macOS)..."
            if command -v brew &> /dev/null; then
                brew install net-snmp
            else
                echo "      FEHLER: Homebrew nicht gefunden. Bitte manuell installieren: brew install net-snmp"
            fi
        elif [[ -f "/etc/debian_version" ]]; then
            echo "      Installiere snmp via apt (Debian/Ubuntu/Raspberry Pi)..."
            sudo apt update && sudo apt install -y snmp
        else
            echo "      Betriebssystem nicht automatisch erkannt."
            echo "      Bitte installieren Sie SNMP-Tools manuell (z.B. sudo apt install snmp / brew install net-snmp)."
        fi
    else
        echo "      SNMP-Installation übersprungen."
    fi

    echo ""
    echo "[7/11] OPTIONAL: AI-Analyse Einrichtung (nur macOS)..."
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "      Die Routerdatenanalyse wird über einen Apple Kurzbefehl 'ai-cloud' ausgeführt."
        echo "      Dieser Kurzbefehl muss manuell in der Kurzbefehle-App angelegt werden,"
        echo "      wie in der Dokumentation beschrieben."
        read -p "      Haben Sie den Kurzbefehl 'ai-cloud' bereits angelegt oder möchten Sie dies später tun? [Enter]"
    else
        echo "      Übersprungen: Die AI-Analyse wird derzeit unter Linux/Debian nicht unterstützt."
    fi

    echo ""
    echo "[8/11] Überprüfe Konfigurationsdatei..."
    if [ ! -f "config.ini" ]; then
        cp config.ini.sample config.ini
        echo "      -> config.ini wurde aus der Vorlage (config.ini.sample) erstellt."
    else
        echo "      -> config.ini existiert bereits."
    fi

    echo ""
    echo "[9/11] Konfigurationsdatei anpassen"
    echo "      Bitte passen Sie nun die Zugangsdaten in der config.ini an."
    read -p "      Drücken Sie [Enter], um die Datei im Editor zu öffnen..."
    ${EDITOR:-nano} config.ini

    echo ""
    echo "[10/11] Teste das Skript..."
    python3 vx-info.py --test

    echo ""
    echo "==== Installation abgeschlossen! ===="
    echo ""

    echo "[11/11] Skript in Cronjob eintragen"
    echo "Vorschlag für Ihre crontab:"
    echo ""
    echo "Einmal stündlich: Systemstatus, Clients, DSL-Werte, Log sichern"
    echo "0 * * * * cd \"$(pwd)\" && \"$(pwd)/.venv/bin/python3\" vx-info.py --update --log"
    echo ""
    echo "Täglich um 06:10 Uhr: Statusbericht generieren und per E-Mail versenden"
    echo "10 6 * * * cd \"$(pwd)\" && \"$(pwd)/.venv/bin/python3\" vx-info.py --report-send"
    echo ""
    read -p "Möchten Sie jetzt 'crontab -e' öffnen? (j/N) " CRON_ANSWER
    if [[ "$CRON_ANSWER" =~ ^[jJ] ]]; then
        crontab -e
    else
        echo "Übersprungen. Sie können die Crontab später jederzeit mit 'crontab -e' bearbeiten."
    fi

    echo "Fertig!"
}

main "$@"
