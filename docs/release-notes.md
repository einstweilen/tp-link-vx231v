## Changelog / Updates

### 17.03.2026
* **Neue Option / Feature**
  * Der Parameter `--reconnect` akzeptiert nun optional eine Wartezeit in Sekunden vor dem Wiederverbinden (z. B. `--reconnect 15`).

* **Log-Verarbeitung & Rsyslog**
  * Konfiguration von `rsyslog` geändert, sodass nun direkt die Zeitstempel des Routers statt der lokalen Empfangszeit verwendet werden.

### 11.03.2026

* **Log-Verarbeitung & Rsyslog**
  * Router-Logs können alternativ und performanter ohne GUI-Scraping über einen lokalen Syslog-Server (rsyslog) eingelesen werden.
  * Loglevel-Anpassung: Das Level für rsyslog-Events ist nun `8`, während für interne Statistik-Events das virtuelle Level `9` eingeführt wurde.

* **Statusreport**
  * Das Eventlog im Report zeigt die gewählte Filterstufe an.

### 08.03.2026

* **Statusreport**
  * Zusätzliche Analyse der Verbindungsdaten auf Leitungsprobleme

### 07.03.2026

* **Installation & Setup**
  * Installationsskript `install.sh` interaktiver gestaltet.

* **Neue Option**
  * Router Reconnect: Mit `--reconnect` lässt sich die Internetverbindung trennen und neu aufbauen.

### 05.03.2026

* **Statusreport** 
  * Eventlogausgabe nach Loglevel oder Typ filterbar
  * Einführung virtueller Loglevel '8' (alle Events außer exclude_types)
  * Alte Statusreports automatisch löschbar (`cleanup_reports = 7`)

* **Sonstiges**
  * `main()` aufgeräumt, Funktionen in Klassen verschoben

### 03.03.2026

* **Diverses** 
  * Browsersession sauber beenden und Timeout für langsame Geräte erhöht
  * Falsche DSL Werte vor dem Schreiben in DB abgefangen
  * Formatierung des Statusreport Headers

### 01.03.2026

* **Statusreport** 
  * aktuelle IPv6-Adresse
  * Verbindungsdauer 
  * Router Uptime in Tagen & Stunden (nur wenn SNMP aktiviert ist)

* **Firmware-Prüfung:**
  * Online Erkennung neuer Firmware robuster
  * Firmware-Hinweis nur noch bis 48 Stunden nach einer erfolgreichen Aktualisierung

* **Geräte-Erkennung & Anwesenheitsgrafik (Gantt-Chart):**
  * Das Erkennungs-Skript führt ein Web-Update durch, wenn es in der Datenbank noch unaufgelöste "Unknown"-Geräte gibt
  * Verbleibende unbekannte Geräte erhalten im Namen nun ein Suffix aus ihrer MAC-Adresse (z. B. `Unknown:C4:30`)
  * Anwesenheitsgrafik zeigt die Clients alphabetisch sortiert
  * Tageswechsel besser in der Anwesenheitsgrafik erkennbar

* **Performance-Dashboard:**
  * Direkte Auswahl und Anzeige von bis zu 2 DSL-Parametern
  * Nur noch Parameter mit numerischen Werten sind auswählbar