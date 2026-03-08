### Changelog / Updates

## 08.03.2026

* **Statusreport**
  * Zusätzliche Analyse der Verbíndungsdaten auf Leitungsprobleme

## 07.03.2026

* **Installation & Setup**
  * Installationsskript `install.sh` interaktiver gestaltet.

* **Neue Option**
  * Router Reconnect: Mit --reconnect lässt sich die Internetverbindung trennen und neu aufbauen.


## 05.03.2026

* **Statusbericht** 
  * Eventlogausgabe nach Loglevel oder Typ filterbar
  * Einführung virtueller Loglevel '8' (alle Events außer exclude_types)
  * Alte Statusreports automatisch löschbar (cleanup_reports = 7)

* **Sonstiges**
  * `main()` aufgeräumt, Funktionen in Klassen verschoben

## 03.03.2026

* **Diverses** 
  * Browsersession sauber beenden und Timeout für langsame Geräte erhöht
  * Falsche DSL Werte vor dem Schreiben in DB abgefangen
  * Formatierung des Statusreport Headers

## 01.03.2026

* **Statusbericht** 
  * aktuelle IPv6-Adresse
  * Verbindungsdauer 
  * Router Uptime in Tagen & Stunden (nur wenn SNMP aktiviert ist)

* **Firmware-Prüfung:**
  * Online Erkennung neuer Firmware robuster (anhand der Dateinamen des Download-Links)
  * Firmware-Hinweis nur noch bis 48 Stunden nach einer erfolgreichen Aktualisierung

* **Geräte-Erkennung & Anwesenheitsgrafik (Gantt-Chart):**
  * Das Erkennungs-Skript führt ein Web-Update durch, wenn es in der Datenbank noch unaufgelöste "Unknown"-Geräte gibt
  * Verbleibende unbekannte Geräte erhalten im Namen nun ein Suffix aus ihrer MAC-Adresse (z. B. `Unknown:C4:30`)
  * Anwesenheitsgrafik zeigt die Clients alphabetisch sortiert (vorher nach MAC-Adresse)
  * Tageswechsel besser in der Anwesenheitsgrafik erkennbar

* **Performance-Dashboard:**
  * Direkte Auswahl und Anzeige von bis zu 2 DSL-Parametern
  * Nur noch Parameter mit numerischen Werten sind auswählbar