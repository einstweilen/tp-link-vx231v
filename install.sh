#!/usr/bin/env bash
#
# Installationsskript für tp-link-vx231v
# Dieses Skript führt die Schritte zur lokalen Installation und Einrichtung aus.
#

# Bei Fehler abbrechen
set -e

main() {
    echo "==== tp-link-vx231v Installation ===="

    # Pre-flight Checks
    if ! command -v python3 &> /dev/null; then
        echo "FEHLER: Python 3 ist nicht installiert. Bitte zuerst installieren."
        exit 1
    fi

    if [ ! -d "tp-link-vx231v" ] && [ ! -f "requirements.txt" ]; then
        echo "[1/11] Klone das Repository..."
        git clone https://github.com/einstweilen/tp-link-vx231v.git
        echo "[2/11] Wechsle in das Verzeichnis..."
        cd tp-link-vx231v
    elif [ -d "tp-link-vx231v" ]; then
        echo "[1/11] Verzeichnis 'tp-link-vx231v' existiert bereits."
        echo "[2/11] Wechsle in das Verzeichnis..."
        cd tp-link-vx231v
    else
        echo "[1/11] Befinde mich bereits im Repository."
        echo "[2/11] Verzeichniswechsel übersprungen."
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
    echo "      Falls mit dem superadmin Account des Routers"
    echo "      SNMP und Telnet aktiviert wurden, können"
    echo "      Routerdaten auch darüber abgerufen werden."
    echo "      Hinweis: Werden SNMP/Telnet genutzt, läuft"
    echo "      --update im schnellen SNMP/Telnet-Modus."
    echo "      Andernfalls wird das langsamere GUI-Scraping genutzt."
    read -p "      Sollen SNMP-Tools jetzt installiert werden? (j/N) " SNMP_ANSWER
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
            echo "      Bitte SNMP-Tools manuell installieren (z.B. sudo apt install snmp / brew install net-snmp)."
        fi
    else
        echo "      SNMP-Installation übersprungen."
    fi

    echo ""
    echo "[7/11] Überprüfe Konfigurationsdatei..."
    if [ ! -f "config.ini" ]; then
        cp config.ini.sample config.ini
        echo "      -> config.ini wurde aus der Vorlage (config.ini.sample) erstellt."
    else
        echo "      -> config.ini existiert bereits."
    fi

    echo ""
    echo "[8/11] Interaktive Router-Konfiguration"
    while true; do
        read -p "      Wie lautet die IP-Adresse des Routers? [192.168.1.1]: " ROUTER_IP
        ROUTER_IP=${ROUTER_IP:-192.168.1.1}
        
        prompt="      Bitte das Passwort für das Web-Interface (GUI) eingeben: "
        while IFS= read -p "$prompt" -r -s -n 1 char; do
            if [[ $char == $'\0' ]]; then
                break
            fi
            prompt='*'
            GUI_PASS+="$char"
        done
        echo ""

        echo "      Trage Daten in config.ini ein..."
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s/routerip = .*/routerip = $ROUTER_IP/g" config.ini
            sed -i '' "s/password = .*/password = $GUI_PASS/g" config.ini
        else
            sed -i "s/routerip = .*/routerip = $ROUTER_IP/g" config.ini
            sed -i "s/password = .*/password = $GUI_PASS/g" config.ini
        fi

        echo "      Teste Login mit den angegebenen Daten..."
        python_test_code="
import sys, configparser
from core.playwright_client import TPLinkVX231vPlaywright

config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
config.read('config.ini')

try:
    client = TPLinkVX231vPlaywright(
        config['Router']['routerip'],
        config['GUI']['username'],
        config['GUI']['password'],
        debug=False
    )
    if client.login():
        sys.exit(0)
    else:
        sys.exit(1)
except Exception as e:
    sys.exit(1)
"
        if python3 -c "$python_test_code"; then
             echo "      ✓ Login am Router erfolgreich!"
             break
        else
             echo "      ✗ FEHLER: Login fehlgeschlagen."
             read -p "      Soll die Eingabe wiederholt werden? (J/n - n = manuell konfigurieren) " retry
             if [[ "$retry" =~ ^[nN] ]]; then
                  echo "      Überspringe Konfiguration. config.ini später manuell anpassen!"
                  break
             fi
             GUI_PASS="" # Reset password
        fi
    done

    echo ""
    echo "[9/11] Globalen Befehl (Alias) einrichten..."
    mkdir -p "$HOME/.local/bin"
    WRAPPER_SCRIPT="$HOME/.local/bin/vx-info"
    
    cat << 'WRAPPER_EOF' > "$WRAPPER_SCRIPT"
#!/usr/bin/env bash
cd "$(dirname "$0")" # Placeholder, will be replaced
source .venv/bin/activate
python3 vx-info.py "$@"
WRAPPER_EOF

    # Fix the cd path dynamically
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "s|cd \".*|cd \"$(pwd)\"|g" "$WRAPPER_SCRIPT"
    else
        sed -i "s|cd \".*|cd \"$(pwd)\"|g" "$WRAPPER_SCRIPT"
    fi
    
    chmod +x "$WRAPPER_SCRIPT"

    # Add ~/.local/bin to PATH if not already there
    DETECTED_RC=""
    if [[ "$SHELL" == *"zsh"* ]]; then
        DETECTED_RC="$HOME/.zshrc"
    elif [[ "$SHELL" == *"bash"* ]]; then
        DETECTED_RC="$HOME/.bashrc"
    fi

    if [[ -n "$DETECTED_RC" ]]; then
       if ! grep -q "$HOME/.local/bin" "$DETECTED_RC" 2>/dev/null; then
            echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$DETECTED_RC"
            echo "      Pfad wurde zu $DETECTED_RC hinzugefügt."
       fi
       echo "      Befehl 'vx-info' (z.B. vx-info --dashboard) ist jetzt global verfügbar."
       echo "      (Wirksam nach einem Neustart des Terminals oder nach: source $DETECTED_RC)"
    else
       echo "      Konnte Shell-Profil nicht automatisch erkennen."
       echo "      Bitte sicherstellen, dass ~/.local/bin im \$PATH liegt,"
       echo "      um den Befehl 'vx-info' global ausführen zu können."
    fi

    echo ""
    echo "[10/11] OPTIONAL: AI-Analyse Einrichtung (nur macOS)..."
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "      Die Routerdatenanalyse wird über einen Apple Kurzbefehl 'ai-cloud' ausgeführt."
        echo "      Dieser Kurzbefehl muss manuell in der Kurzbefehle-App angelegt werden,"
        echo "      wie in der Dokumentation beschrieben."
        read -p "      Wurde der Kurzbefehl 'ai-cloud' bereits angelegt oder soll dies später erfolgen? [Enter]"
    else
        echo "      Übersprungen: Die AI-Analyse wird derzeit unter Linux/Debian nicht unterstützt."
    fi

    echo ""
    echo "[11/11] Cronjobs automatisch einrichten"
    read -p "      Sollen die periodischen Abfrage-Jobs für cron eingerichtet werden? (j/N) " CRON_SETUP
    
    if [[ "$CRON_SETUP" =~ ^[jJ] ]]; then
        TMP_CRON=$(mktemp)
        crontab -l > "$TMP_CRON" 2>/dev/null || true
        
        # Determine schedule based on SNMP usage earlier
        if [[ "$SNMP_ANSWER" =~ ^[jJ] ]]; then
            echo "      Es wurde angegeben, SNMP/Telnet zu nutzen."
            echo "      Hinzugefügt: Alle 15 Min '--update', 5 Min nach der vollen Stunde '--log'"
            echo "*/15 * * * * cd \"$(pwd)\" && \"$(pwd)/.venv/bin/python3\" vx-info.py --update" >> "$TMP_CRON"
            echo "5 * * * * cd \"$(pwd)\" && \"$(pwd)/.venv/bin/python3\" vx-info.py --log" >> "$TMP_CRON"
        else
            echo "      Kein SNMP/Telnet. Nutze Fallback-Rhythmus mit GUI-Scraping."
            echo "      Hinzugefügt: Zu jeder vollen Stunde '--update --log --gui'"
            echo "0 * * * * cd \"$(pwd)\" && \"$(pwd)/.venv/bin/python3\" vx-info.py --update --log --gui" >> "$TMP_CRON"
        fi

        read -p "      Soll täglich um 06:10 Uhr ein Statusbericht per Mail versandt werden? (j/N) " MAIL_SETUP
        if [[ "$MAIL_SETUP" =~ ^[jJ] ]]; then
            echo "      Hinzugefügt: Täglich 06:10 Uhr '--report-send'"
            echo "10 6 * * * cd \"$(pwd)\" && \"$(pwd)/.venv/bin/python3\" vx-info.py --report-send" >> "$TMP_CRON"
        fi

        crontab "$TMP_CRON"
        rm -f "$TMP_CRON"
        echo "      ✓ Cronjobs erfolgreich eingerichtet!"
    else
        echo "      Übersprungen. Die Crontab kann später jederzeit mit 'crontab -e' bearbeitet werden."
    fi

    echo ""
    echo "[12/12] Installation testen..."
    echo "      Es wird nun ein kurzer Verbindungstest ausgeführt..."
    cd "$(pwd)" && .venv/bin/python3 vx-info.py --test

    echo ""
    echo "==== Installation abgeschlossen! ===="
    echo ""
    echo "Tipp: Da der Alias angelegt wurde, kann das Script ab sofort direktmit aufgerufen werden:"
    echo "vx-info --$OPTION
    echo ""
}

main "$@"
