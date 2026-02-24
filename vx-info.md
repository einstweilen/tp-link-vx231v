# TP-Link VX231v Tracker

Ein Set aus Python-Skripten zum automatisierten Auslesen, Speichern und Darstellen von Router-Daten des TP-Link VX231v.

## Funktionen

### 1. Abfrage der Routerdaten via Telnet, SNMP und Web-Scraping
Das Skript nutzt Telnet und SNMP für den primären Abruf von Systemzuständen und DSL-Werten. Für detaillierte Ereignisprotokolle, die über diese Schnittstellen nicht zugänglich sind, erfolgt ein automatisierter Login in die Weboberfläche mithilfe von Playwright.

### 2. Routerclients
Verbundene Geräte im Heim- und Gastnetzwerk werden registriert und deren Verbindungsdauer anhand von DHCP- und Mesh-Ereignissen aus dem Router-Log ermittelt.
Dies ermöglicht die Generierung eines Anwesenheitscharts.

### 3. Report-Generierung (HTML und E-Mail)
Die aufgezeichneten DSL-Werte, Systemzustände und Client-Aktivitäten werden in einem Bericht zusammengefasst.
Dieser Bericht kann im Standard-Browser geöffnet oder zeitgesteuert via SMTP versendet werden.

### 4. Lokales Web-Dashboard
Mit Flask werden die historischen Datenbankwerte als interaktive Diagramme zur Verfügung gestellt. Der Zugriff erfolgt über ein lokales Web-Interface, in dem spezifische Datenpunkte detailliert betrachtet werden können.

### 5. Datenspeicherung in SQLite
Sämtliche ausgelesenen Werte und Logs werden in eine SQLite-Datenbank geschrieben.
Standardmäßig werden DHCP und MESH Einträge nach drei Tagen gelöscht, in der `config.ini` (unter `[Events]`) kann die Anzahl der Tage konfiguriert werden

### 6. Lokalisierung und eigene Feldbeschriftungen
Die Datenbank `router_lang.db` dient als Übersetzungsmatrix. Sie wandelt technische Spaltennamen (z. B. `downstream_curr_rate`) für das Web-Dashboard und den HTML-Bericht in menschenlesbare Bezeichner (z. B. "Download-Rate") um. 
Eigene Übersetzungen können direkt im Quellcode des beiliegenden Hilfsskripts `lang_editor.py` (innerhalb der Liste `translations`) angepasst und erweitert werden. Ein anschließendes Ausführen des Skripts generiert die Übersetzungsdatenbank neu.

## Einrichtung und Konfiguration

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
    *   **AI-Analyse (Optional):** Die Anomalie-Erkennung (`_run_ai_analysis`) setzt auf macOS voraus, dass ein funktionierender Kurzbefehl namens `ai-cloud` existiert, der über das Terminal (`shortcuts run ai-cloud`) aufgerufen wird.<br>
    Unter Linux/Debian wird die AI-Analyse aktuellübersprungen.

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

## Ausführungsoptionen (CLI)

Hauptskript `vx-info.py` mit folgenden Aufrufparametern:

*   `--update`: Fragt grundlegende Daten (Systemstatus, DSL-Werte, Client-Liste) primär über Telnet/SNMP ab und speichert sie in der Datenbank. Sind Telnet/SNMP nicht verfügbar, wird das Web-Scraping-Interface genutzt.
*   `--log`: Lädt das vollständige Systemprotokoll ("Logbuch") des Routers via Playwright-(Web-Scraping) herunter und importiert neue Ereignisse (wie DHCP/Mesh). Häufig in Kombination mit `--update` genutzt.

*   `--gui`: Erzwingt den Datenabruf (Systemstatus, DSL, Clients) ausschließlich über das Web-Scraping-Interface anstelle von Telnet/SNMP.

*   `--report-show`: Generiert den HTML-Statusbericht basierend auf den aktuellen Datenbankwerten und öffnet diesen direkt im Standard-Browser.
*   `--report-send`: Generiert den HTML-Statusbericht und versendet diesen über die in der `config.ini` hinterlegte E-Mail-Adresse.

*   `--output [DATEI]`: Schreibt die ausgelesenen Basisdaten zusätzlich als Rohdaten in eine JSON-Datei.
*   `--json-only`: Unterdrückt die standardmäßigen tabellarischen Konsolenausgaben während eines Abrufs.

*   `--test`: Testet alle installierten Technologien (Telnet, SNMP, Playwright) und verifiziert die in der `config.ini` hinterlegten Zugangsdaten sowie die E-Mail-Konfiguration. Idealerweise nach der Ersteinrichtung aufzurufen.
*   `--debug`: Aktiviert eine ausführlichere Konsolenausgabe zur Fehlerdiagnose.

*   `--dashboard`: Startet einen lokalen Webserver (Standard: Port 31311) zur interaktiven Anzeige historischer Metriken.

## Automatisierung (Cronjobs)

Für ein kontinuierliches Monitoring wird die periodische Ausführung über `cron` empfohlen. 

Typisches Ausführungsszenario:
*   **Datenerfassung:** Alle 15 Minuten werden aktuelle Statuswerte, verbundene Clients und DSL-Metriken abgefragt.
*   **Log-Sicherung:** Einmal pro Stunde wird das vollständige Router-Logbuch archiviert, um Netzwerk-Events zu protokollieren.
*   **Report-Versand:** Einmal täglich um 06:00 Uhr wird ein HTML-Report generiert und per E-Mail versendet.

Die Crontab mit `crontab -e` öffnen und folgende Vorgaben einfügen (Pfade müssen an die lokale Umgebung angepasst werden):

```cron
# 1. Alle 15 Minuten: Systemstatus, Clients und DSL-Werte aktualisieren
*/15 * * * * cd /pfad/zum/script && /pfad/zum/script/.venv/bin/python3 vx-info.py --update

# 2. Einmal stündlich: Zusätzlich das komplette Router-Logbuch (Web-Scraping) sichern
50 * * * * cd /pfad/zum/script && /pfad/zum/script/.venv/bin/python3 vx-info.py --update --log

# 3. Täglich um 06:10 Uhr: HTML-Statusbericht generieren und per E-Mail versenden
10 6 * * * cd /pfad/zum/script && /pfad/zum/script/.venv/bin/python3 vx-info.py --report-send
```
_Hinweis: Das Skript initiiert vor dem Statusbericht (06:10 Uhr) bei Bedarf automatisch einen Log-Download, falls der letzte länger als 15 Minuten zurückliegt._
