### Changelog / Updates

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