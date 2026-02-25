# TP-Link VX231v Tools

Skripte und Anleitungen für den TP-Link VX231v Router

---

### 1. [Aktivierung Superadmin, Telnet, SNMP und iPerf3](superadmin_telnet_snmp_iperf.md)
Zusätzliche Funktionen des Router aktivieren und nutzen.
**Inhalte:**
* Aktivierung des `superadmin`-Accounts
* Aktivierung von **Telnet** und **SNMP** für den Netzwerkzugriff
* Aktivierung des **iPerf3**-Servers zur Bandbreitenmessung

[Zur Aktivierungsanleitung:](superadmin_telnet_snmp_iperf.md)

---

### 2. [Router Monitoring: VX-Info Tracker](vx-info.md)
Ein Set aus Python-Skripten (`vx-info.py`) zur automatisierten Erfassung und Darstellung der Routerdaten.
**Inhalte:**
* Datenabruf von DSL-Werten und der verbundenen Clients via SNMP, Telnet und Web-Scraping
* Speicherung der Daten in einer Datenbank
* Automatisierte Generierung von HTML-Statusberichten
* Lokales Web-Dashboard zur Visualisierung

[Zur Installationsanleitung: VX-Info Tracker](vx-info.md)

---

**Hinweis:** Die Python-Monitoring-Tools setzen für einen effizienten Datenabruf die Freischaltung von Telnet und SNMP voraus. Es wird empfohlen, zunächst die Schritte zur Systemfreischaltung auszuführen.

**Getestet unter MacOS und Debian/DietPi auf einem Raspberry Pi Zero 2W**