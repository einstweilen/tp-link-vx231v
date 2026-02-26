# Setup & Installation

## Einrichtung und Konfiguration

**Schnelle Installation:**
```bash
curl -sL https://raw.githubusercontent.com/einstweilen/tp-link-vx231v/main/install.sh | bash
```
<br>
<details markdown="1">
<summary>Beispiel: Installationsverlauf</summary>

```
curl -sL https://raw.githubusercontent.com/einstweilen/tp-link-vx231v/main/install.sh | bash

==== tp-link-vx231v Installation ====
[1/11] Klone das Repository...
Cloning into 'tp-link-vx231v'...
remote: Enumerating objects: 124, done.
remote: Counting objects: 100% (124/124), done.
Receiving objects: 100% (124/124), 2.45 MiB | 4.88 MiB/s, done.

[2/11] Wechsle in das Verzeichnis...

[3/11] Erstelle virtuelle Umgebung...
      Aktiviere virtuelle Umgebung...

[4/11] Installiere Abhängigkeiten...
Collecting playwright
  Downloading playwright-1.42.0-py3-none-macosx_11_0_arm64.whl
Successfully installed playwright-1.42.0 requests

[5/11] Installiere Chromium in Playwright...
Downloading Chromium 123.0.6312.4 (playwright build v1105)...
Playwright build of Chromium is installed.

[6/11] OPTIONAL: SNMP / TELNET verwenden
      Falls Sie mit dem superadmin Account Ihres Routers
      SNMP und Telnet aktiviert haben, können Sie
      Routerdaten auch per SNMP abrufen.
      Dafür benötigen Sie 'snmpget' und 'snmpwalk'.
      Möchten Sie SNMP-Tools jetzt installieren? (j/N) j
      Installiere net-snmp via Homebrew (macOS)...
      🍺  net-snmp wurde erfolgreich installiert!

[7/11] OPTIONAL: AI-Analyse Einrichtung (nur macOS)...
      Die Routerdatenanalyse wird über einen Apple Kurzbefehl 'ai-cloud' ausgeführt.
      Dieser Kurzbefehl muss manuell in der Kurzbefehle-App angelegt werden,
      wie in der Dokumentation beschrieben.
      Haben Sie den Kurzbefehl 'ai-cloud' bereits angelegt oder möchten Sie dies später tun? [Enter]

[8/11] Überprüfe Konfigurationsdatei...
      -> config.ini wurde aus der Vorlage (config.ini.sample) erstellt.

[9/11] Konfigurationsdatei anpassen
      Bitte passen Sie nun die Zugangsdaten in der config.ini an.
      Drücken Sie [Enter], um die Datei im Editor zu öffnen...

[10/11] Teste das Skript...

GUI Scraping
  ✓  Login in Routerweboberfläche erfolgreich
Telnet Konfiguration
  ✓  telnet Login erfolgreich
SNMP Konfiguration
  ✓  snmp Zugriff erfolgreich
eMail Konfiguration
  ✓  eMail erfolgreich versendet

==== Installation abgeschlossen! ====

[11/11] Skript in Cronjob eintragen
Vorschlag für Ihre crontab:
Einmal stündlich: Systemstatus, Clients, DSL-Werte, Log sichern
0 * * * * cd /Users/user/tp-link-vx231v && /Users/user/tp-link-vx231v/.venv/bin/python3 vx-info.py --update --log
Täglich um 06:10 Uhr: Statusbericht generieren und per E-Mail versenden
10 6 * * * cd /Users/user/tp-link-vx231v && /Users/user/tp-link-vx231v/.venv/bin/python3 vx-info.py --report-send

Möchten Sie jetzt 'crontab -e' öffnen? (j/N) n
Übersprungen. Sie können die Crontab später jederzeit mit 'crontab -e' bearbeiten.

Fertig!
```
</details>
<br>

1.  **Voraussetzungen installieren:**
    Neben Python 3 und den Modulen aus `requirements.txt` werden plattformabhängige Systemwerkzeuge benötigt:
    
    *   **Python-Umgebung & Pakete:** 
        Auf modernen Linux-Distributionen (z. B. Raspberry Pi OS, Debian) ist die Installation in eine virtuelle Umgebung (venv) notwendig:
        ```bash
        sudo apt install python3-venv  # falls nicht bereits installiert
        python3 -m venv .venv
        source .venv/bin/activate
        
        # Abhängigkeiten und Browser-Binaries in venv installieren
        pip install -r requirements.txt
        playwright install chromium
        ```
    *   **SNMP-Client:** Falls auf dem Router der superadmin Account aktiviert, müssen `snmpget` und `snmpwalk` verfügbar sein.
        *   _Debian/Raspberry Pi:_ `sudo apt install snmp`
        *   _macOS:_ `brew install net-snmp`
    *   **AI-Analyse (Optional):** Die Anomalie-Erkennung (`_run_ai_analysis`) setzt aktuell macOS voraus. Dazu ein Kurzbefehl `ai-cloud` wie auf dem folgenden Screenshot gezeigt anlegen.<br>
    Unter Linux/Debian wird die AI-Analyse aktuell noch übersprungen.<br>
    <details markdown="1">
    <summary>ai-cloud shortcut anlegen</summary>

    ![ai-cloud shortcut screenshot](images/ai-shortcut-anlegen.jpg)

    </details>

2.  **Konfigurationsdatei anlegen:**
    Die Vorlage `config.ini.sample` zu `config.ini` kopieren.
    Anschließend die Zugangsdaten für die Router Weboberfläche, SNMP, telnet sowie die E-Mail-Konfiguration an das eigene Netzwerk anpassen.

3.  **Testlauf durchführen (`--test`):**
    Überprüfen, ob die Kommunikation mit dem Router funktioniert und alle Abhängigkeiten korrekt installiert sind. Dies sollte als erster Schritt ausgeführt werden (Achtung: venv muss aktiv sein!):
    ```bash
    python3 vx-info.py --test
    ```
    Bei einer erfolgreichen Konfiguration sieht die Ausgabe folgendermaßen aus:
    ```text
    GUI Scraping
      ✓  Login in Routerweboberfläche erfolgreich
    
    Telnet Konfiguration
      ✓  telnet Login erfolgreich
    
    SNMP Konfiguration
      ✓  snmp Zugriff erfolgreich
    
    eMail Konfiguration
      ✓  eMail erfolgreich versendet
    ```
    
4.  **Erster Datenabruf:**
    Wenn der Testlauf erfolgreich war, kann das vollständige Logbuch manuell heruntergeladen und die Datenbank initialisiert werden:
    ```bash
    python3 vx-info.py --update --log
    ```
