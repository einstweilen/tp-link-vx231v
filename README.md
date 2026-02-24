# TP-Link VX231v Tools

Skripte und Anleitungen für den TP-Link VX231v Router

---

### 1. [Systemfreischaltung: Superadmin, Telnet, SNMP und iPerf3](superadmin_telnet_snmp_iperf.md)
Dieser Leitfaden beschreibt die Aktivierung administrativer Funktionen auf dem Router.
**Inhalte:**
* Aktivierung des `superadmin`-Accounts
* Aktivierung von Telnet und SNMP für den Netzwerkzugriff
* Aktivierung des iPerf3-Servers zur Bandbreitenmessung

[Zur Anleitung: Systemfreischaltung](superadmin_telnet_snmp_iperf.md)

---

### 2. [Router Monitoring: VX-Info Tracker](vx-info.md)
Ein Set aus Python-Skripten (`vx-info.py`) zur automatisierten Erfassung und Darstellung von Routerdaten.
**Inhalte:**
* Datenabruf von DSL-Werten, Systemauslastung und verbundenen Clients via SNMP, Telnet und Web-Scraping
* Speicherung der historischen Daten in einer lokalen Datenbank
* Automatisierte Generierung von HTML-Statusberichten
* Lokales Web-Dashboard zur Visualisierung

[Zur Anleitung: VX-Info Tracker](vx-info.md)

---

**Hinweis:** Die Python-Monitoring-Tools setzen für einen effizienten Datenabruf die Freischaltung von Telnet und SNMP voraus. Es wird empfohlen, zunächst die Schritte zur Systemfreischaltung auszuführen.
