#!/usr/bin/env bash
#
# Installationsskript für tp-link-vx231v
# Dieses Skript führt die Schritte zur lokalen Installation und Einrichtung aus.
#

# Bei Fehler abbrechen
set -e

# Farben
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# Hilfsfunktionen
info() { echo -e "  ${BLUE}ℹ${NC} $1"; }
success() { echo -e "  ${GREEN}✓${NC} $1"; }
error() { echo -e "  ${RED}✗${NC} $1"; }
step() { echo -e "\n${BOLD}==> $1${NC}"; }
prompt_text() { echo -ne "  ${YELLOW}?${NC} $1"; }

main() {
    echo -e "${BOLD}==== tp-link-vx231v Installation ====${NC}"

    # Pre-flight Checks
    if ! command -v python3 &> /dev/null; then
        error "Python 3 ist nicht installiert. Bitte zuerst installieren."
        exit 1
    fi

    if [ ! -d "tp-link-vx231v" ] && [ ! -f "requirements.txt" ]; then
        step "[1/12] Klone das Repository..."
        info "Lade Repository-Daten herunter (Details: .install.log)..."
        git clone https://github.com/einstweilen/tp-link-vx231v.git > .install.log 2>&1
        success "Repository geklont."
        step "[2/12] Wechsle in das Verzeichnis..."
        cd tp-link-vx231v
    elif [ -d "tp-link-vx231v" ]; then
        step "[1/12] Klone das Repository..."
        info "Verzeichnis 'tp-link-vx231v' existiert bereits."
        step "[2/12] Wechsle in das Verzeichnis..."
        cd tp-link-vx231v
    else
        step "[1/12] Klone das Repository..."
        info "Befinde mich bereits im Repository."
        step "[2/12] Wechsle in das Verzeichnis..."
        info "Verzeichniswechsel übersprungen."
    fi

    step "[3/12] Erstelle virtuelle Umgebung..."
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    info "Aktiviere virtuelle Umgebung..."
    source .venv/bin/activate
    success "Virtuelle Umgebung bereit."

    step "[4/12] Installiere Abhängigkeiten..."
    info "pip install (Details: .install.log)..."
    pip install --upgrade pip >> .install.log 2>&1
    pip install -r requirements.txt >> .install.log 2>&1
    success "Abhängigkeiten installiert."

    step "[5/12] Installiere Chromium in Playwright..."
    info "Lade Chromium herunter (Dies dauert einen Moment...)"
    playwright install chromium >> .install.log 2>&1
    success "Chromium installiert."

    step "[6/12] OPTIONAL: SNMP / TELNET verwenden"
    info "Falls mit dem superadmin Account des Routers SNMP und"
    info "Telnet aktiviert wurden, können Routerdaten darüber"
    info "abgerufen werden (--update läuft dann schneller)."
    prompt_text "Sollen SNMP-Tools jetzt installiert werden? (j/N) "
    read -r SNMP_ANSWER
    if [[ "$SNMP_ANSWER" =~ ^[jJ] ]]; then
        if [[ "$(uname)" == "Darwin" ]]; then
            info "Installiere net-snmp via Homebrew (macOS)..."
            if command -v brew &> /dev/null; then
                brew install net-snmp >> .install.log 2>&1
                success "net-snmp wurde erfolgreich installiert!"
            else
                error "Homebrew nicht gefunden. Bitte manuell installieren: brew install net-snmp"
            fi
        elif [[ -f "/etc/debian_version" ]]; then
            info "Installiere snmp via apt (Debian/Ubuntu/Raspberry Pi)..."
            sudo apt update >> .install.log 2>&1 && sudo apt install -y snmp >> .install.log 2>&1
            success "snmp wurde erfolgreich installiert!"
        else
            info "Betriebssystem nicht automatisch erkannt."
            info "Bitte SNMP-Tools manuell installieren (z.B. sudo apt install snmp / brew install net-snmp)."
        fi
    else
        info "SNMP-Installation übersprungen."
    fi

    step "[7/12] Überprüfe Konfigurationsdatei..."
    if [ ! -f "config.ini" ]; then
        cp config.ini.sample config.ini
        success "config.ini wurde aus der Vorlage (config.ini.sample) erstellt."
    else
        success "config.ini existiert bereits."
    fi

    step "[8/12] Interaktive Router-Konfiguration"
    while true; do
        prompt_text "Wie lautet die IP-Adresse des Routers? [192.168.1.1]: "
        read -r ROUTER_IP
        ROUTER_IP=${ROUTER_IP:-192.168.1.1}
        
        prompt_text "Bitte das Passwort für das Web-Interface (GUI) eingeben: "
        read -rs GUI_PASS
        echo ""

        info "Trage Daten in config.ini ein..."
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s/routerip = .*/routerip = $ROUTER_IP/g" config.ini
            sed -i '' "s/password = .*/password = $GUI_PASS/g" config.ini
        else
            sed -i "s/routerip = .*/routerip = $ROUTER_IP/g" config.ini
            sed -i "s/password = .*/password = $GUI_PASS/g" config.ini
        fi

        info "Teste Login mit den angegebenen Daten..."
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
             success "Login am Router erfolgreich!"
             break
        else
             error "Login fehlgeschlagen."
             prompt_text "Soll die Eingabe wiederholt werden? (J/n - n = manuell konfigurieren) " 
             read -r retry
             if [[ "$retry" =~ ^[nN] ]]; then
                  info "Überspringe Konfiguration. config.ini später manuell anpassen!"
                  break
             fi
             GUI_PASS="" # Reset password
        fi
    done

    step "[9/12] Globalen Befehl (Alias) einrichten..."
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
            info "Pfad wurde zu $DETECTED_RC hinzugefügt."
       fi
       success "Befehl 'vx-info' (z.B. vx-info --dashboard) ist jetzt global verfügbar."
       info "(Wirksam nach einem Neustart des Terminals oder nach: source $DETECTED_RC)"
    else
       info "Konnte Shell-Profil nicht automatisch erkennen."
       info "Bitte sicherstellen, dass ~/.local/bin im \$PATH liegt,"
       info "um den Befehl 'vx-info' global ausführen zu können."
    fi

    step "[10/12] KI Analyse Einrichtung"
    info "Falls im Tagesreport eine KI Analyse der aktuellen Routerdaten erfolgen soll,"
    info "wird ein kostenloser API Key von Google Gemini benötigt."
    prompt_text "Soll eine KI Datenanalyse durchgeführt werden [J/N]: "
    read -r AI_SETUP
    if [[ "$AI_SETUP" =~ ^[jJ] ]]; then
        if [ -f "setup_ai_key.sh" ]; then
            chmod +x setup_ai_key.sh
            ./setup_ai_key.sh
        else
            error "setup_ai_key.sh nicht gefunden!"
        fi
    else
        info "Übersprungen: Keine KI-Analyse gewünscht."
    fi

    step "[11/12] Cronjobs automatisch einrichten"
    prompt_text "Sollen die periodischen Abfrage-Jobs für cron eingerichtet werden? (j/N) " 
    read -r CRON_SETUP
    
    if [[ "$CRON_SETUP" =~ ^[jJ] ]]; then
        TMP_CRON=$(mktemp)
        crontab -l > "$TMP_CRON" 2>/dev/null || true
        
        # Determine schedule based on SNMP usage earlier
        if [[ "$SNMP_ANSWER" =~ ^[jJ] ]]; then
            info "Es wurde angegeben, SNMP/Telnet zu nutzen."
            info "Hinzugefügt: Alle 15 Min '--update', 5 Min nach der vollen Stunde '--log'"
            echo "*/15 * * * * cd \"$(pwd)\" && \"$(pwd)/.venv/bin/python3\" vx-info.py --update" >> "$TMP_CRON"
            echo "5 * * * * cd \"$(pwd)\" && \"$(pwd)/.venv/bin/python3\" vx-info.py --log" >> "$TMP_CRON"
        else
            info "Kein SNMP/Telnet. Nutze Fallback-Rhythmus mit GUI-Scraping."
            info "Hinzugefügt: Zu jeder vollen Stunde '--update --log --gui'"
            echo "0 * * * * cd \"$(pwd)\" && \"$(pwd)/.venv/bin/python3\" vx-info.py --update --log --gui" >> "$TMP_CRON"
        fi

        prompt_text "Soll täglich um 06:10 Uhr ein Statusbericht per Mail versandt werden? (j/N) " 
        read -r MAIL_SETUP
        if [[ "$MAIL_SETUP" =~ ^[jJ] ]]; then
            info "Hinzugefügt: Täglich 06:10 Uhr '--report-send'"
            echo "10 6 * * * cd \"$(pwd)\" && \"$(pwd)/.venv/bin/python3\" vx-info.py --report-send" >> "$TMP_CRON"
        fi

        crontab "$TMP_CRON"
        rm -f "$TMP_CRON"
        success "Cronjobs erfolgreich eingerichtet!"
    else
        info "Übersprungen. Die Crontab kann später jederzeit mit 'crontab -e' bearbeitet werden."
    fi

    step "[12/12] Installation testen..."
    info "Es wird nun ein kurzer Verbindungstest ausgeführt..."
    cd "$(pwd)" && .venv/bin/python3 vx-info.py --test

    echo -e "\n${BOLD}==== Installation abgeschlossen! ====${NC}\n"
    info "Tipp: Da der Alias angelegt wurde, kann das Script ab sofort direkt aufgerufen werden:"
    info "vx-info --dashboard"
    echo ""
    info "Wenn rsyslog verwendet werden soll, kann es mit folgendem Script eingerichtet werden:"
    info "./pi_rsyslog_setup.sh"
    echo ""
}

main "$@"
