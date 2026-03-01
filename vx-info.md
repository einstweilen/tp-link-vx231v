# TP-Link VX231v Tracker

Ein Set aus Python-Skripten zum automatisierten Auslesen, Speichern und Darstellen von Router-Daten des TP-Link VX231v.

## Entstehungsgeschichte

Ausgangspunkt war der Wunsch, die DSL-Leitungswerte und die aktuell verbundenen Clients im Heimnetzwerk regelmäßig zu erfassen und darzustellen.

Eine Zusammenfassung der wichtigsten in den letzten 24 Stunden erfassten Daten sollte visuell aufbereitet und als täglicher Report automatisch per E-Mail versendet werden.

Zusätzlich sollte auf Auffälligkeiten in den erfassten Daten, wie z.B. Verbindungsabbrüche oder hohe Fehlerraten, hingewiesen werden.

Da der Router keine allgemein zugängliche API bietet, wurden die Daten zuerst nur über Web-Scraping ausgelesen. 
Im nächsten Schritt wurden Telnet und SNMP hinzugefügt, um die Daten schneller und zuverlässiger auszulesen.

Hierbei ist zu beachten, dass Telnet und SNMP zwar in der Firmware des Routers vorhanden sind, aber der superadmin Account auf dem Router aktiviert sein muss, um Telnet und SNMP nutzen zu können. Die Aktivierung des Accounts wird in der Anleitung **[Aktivierung superadmin, Telnet, SNMP und iPerf3](superadmin_telnet_snmp_iperf.md)** beschrieben.

**Alle Funktionen** des Skripts können **auch ohne aktivierten superadmin Account** genutzt werden, allerdings ist dann das Web-Scraping die einzige Methode der Datenabfrage, was die langsamste und unsicherste Methode der Datenabfrage ist, so dass auch schonmal eine Abfrage fehlschlagen kann. Im Verzeichnis `logs/` finden sich dann entsprechende Fehlermeldungen.<br>
Ohne superadmin Account wechselt das Skript **automatisch** zurück zum Webscraping Modus, alternativ kann man diesen Modus **trotz** aktiviertem superadmin Account mit `--gui` erzwingen.



## Funktionen

### 1. Abfrage der Routerdaten via Telnet, SNMP und Web-Scraping
Das Skript nutzt bei aktiviertem **superadmin Account** Telnet und SNMP für den primären Abruf von Systemzuständen und DSL-Werten.
Für Daten, die über diese Schnittstellen nicht zugänglich sind, erfolgt ein automatisierter Login in die Weboberfläche mithilfe von Playwright.
Ist der **superadmin Account** nicht aktiviert, erfolgt der Datenabruf automatisch ausschließlich über das Web-Scraping-Interface.

Das Webscraping ist die langsamste Methode der Datenabfrage, daher sollte wenn möglich Telnet und SNMP genutzt werden.


### 2. Routerclients
Verbundene Geräte im Heim- und Gastnetzwerk werden registriert und deren Verbindungsdauer anhand von DHCP- und Mesh-Ereignissen aus dem Router-Log ermittelt.
Dies ermöglicht die Generierung eines Anwesenheitscharts.


### 3. Report-Generierung
Die aufgezeichneten Daten werden in einem Bericht zusammengefasst.<br>
Der Bericht kann im Browser geöffnet oder zeitgesteuert als eMail versendet werden.

  <details>
      <summary>Beispiel: Statusreport</summary>
      <br>
      <img src="images/beispiel-statusreport.jpg" alt="Beispiel Statusreport">
  </details>

### 4. Lokales Web-Dashboard
Für den schnellen Überblick der aufgezeichneten Daten können diese als interaktive Diagramme dargestellt werden. Der Zugriff erfolgt über ein lokales Web-Interface, in dem die anzuzeigen Daten und der Zeitraum ausgewählt werden können.

  <details>
      <summary>Beispiel: Web-Dashboard</summary>
      <br>
      <img src="images/beispiel-dashboard.jpg" alt="Beispiel Web-Dashboard">
  </details>

### 5. Lokale Datenspeicherung
Sämtliche ausgelesenen Werte und Logs werden in eine SQLite-Datenbank geschrieben.<br>
Standardmäßig werden DHCP und MESH Einträge nach drei Tagen aus der DB gelöscht; in der `config.ini` (unter `[Events]`) kann die Anzahl der Tage konfiguriert werden

### 6. Lokalisierung und eigene Feldbeschriftungen
Die Datenbank `router_lang.db` dient als Übersetzungsmatrix. Sie wandelt technische Spaltennamen (z. B. `downstream_curr_rate`) für das Web-Dashboard und den HTML-Bericht in menschenlesbare Bezeichner (z. B. "Aktuelle Download-Rate") um.<br>
Eigene Übersetzungen können direkt in der router_lang.db oder auch  im Quellcode des beiliegenden Hilfsskripts `lang_editor.py` (innerhalb der Liste `translations`) angepasst und erweitert werden. Ein anschließendes Ausführen des Skripts generiert die Übersetzungsdatenbank neu.

## Einrichtung und Konfiguration

**Schnelle Installation:**
```bash
curl -sL https://raw.githubusercontent.com/einstweilen/tp-link-vx231v/main/install.sh | bash
```
<br>

## Ausführungsoptionen (CLI)

Hauptskript `vx-info.py` mit folgenden Aufrufparametern:

*   `--update`: Fragt grundlegende Daten (Systemstatus, DSL-Werte, Client-Liste) primär über Telnet/SNMP ab und speichert sie in der Datenbank. Sind Telnet/SNMP nicht verfügbar, wird das Web-Scraping-Interface genutzt.
<br>
*   `--log`: Lädt das vollständige Systemprotokoll ("Logbuch") des Routers via Playwright-(Web-Scraping) herunter und importiert neue Ereignisse (wie DHCP/Mesh). Häufig in Kombination mit `--update` genutzt.
<br>
*   `--gui`: Erzwingt den Datenabruf (Systemstatus, DSL, Clients) ausschließlich über das Web-Scraping-Interface anstelle von Telnet/SNMP.
<br><br>
*   `--report-show`: Generiert den HTML-Statusreport basierend auf den aktuellen Datenbankwerten und öffnet diesen direkt im Standard-Browser.
<br><br>
*   `--report-send`: Generiert den HTML-Statusreport und versendet diesen über die in der `config.ini` hinterlegte E-Mail-Adresse.
<br><br>
*   `--output [DATEI]`: Schreibt die ausgelesenen Basisdaten zusätzlich als Rohdaten in eine JSON-Datei.
<br>
*   `--json-only`: Unterdrückt die standardmäßigen tabellarischen Konsolenausgaben während eines Abrufs.
<br><br>
*   `--dashboard`: Startet einen lokalen Webserver (Standard: Port 31311) zur interaktiven Anzeige historischer Metriken.
<br><br>
*   `--test`: Testet alle installierten Technologien (Telnet, SNMP, Playwright) und verifiziert die in der `config.ini` hinterlegten Zugangsdaten sowie die E-Mail-Konfiguration. Idealerweise nach der Ersteinrichtung aufzurufen.
<br>
*   `--debug`: Aktiviert eine ausführlichere Konsolenausgabe zur Fehlerdiagnose.

### Release Notes / letzte Updates

* [Release Notes](release-notes.md)

## Vertiefende Dokumentation

Für detaillierte Informationen zu Einrichtung, Konfiguration und Nutzung lesen Sie bitte die weiterführenden Dokumentationen:

*   [**Setup & Installation**](docs/setup.md)
    Voraussetzungen, virtuelle Umgebung, Systemwerkzeuge (SNMP, Telnet, Playwright) und AI-Analyse.
*   [**Konfiguration & Automatisierung**](docs/konfiguration.md)
    Anpassung der `config.ini`, Testläufe, Ausführungsoptionen (CLI) und Einrichtung von Cronjobs.
*   [**Report**](docs/report.md)
    Details zur Berichtgenerierung und dem Versand per E-Mail.
*   [**Web-Dashboard**](docs/dashboard.md)
    Hinweise zur Nutzung des lokalen Dashboards und der Diagramme.
*   [**Lokalisierung**](docs/lokalisierung.md)
    Anleitung zur Übersetzung und Anpassung der Feldbeschriftungen über die `router_lang.db`.

<br>


*Getestet unter MacOS und Debian/DietPi auf einem Raspberry Pi Zero 2W*