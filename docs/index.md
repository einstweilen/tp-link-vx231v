# TP-Link VX231v Tracker

Eine Sammlung von Python-Skripten zur Erfassung, Speicherung und Visualisierung der Router-Daten.

Ausgangspunkt war der Wunsch, die DSL-Leitungswerte und die aktuell verbundenen Clients im Heimnetzwerk regelmäßig zu erfassen und darzustellen.

Eine Zusammenfassung der wichtigsten in den letzten 24 Stunden erfassten Daten sollte visuell aufbereitet und als täglicher Report automatisch per E-Mail versendet werden.

Zusätzlich sollte auf Auffälligkeiten in den erfassten Daten, wie z.B. Verbindungsabbrüche oder hohe Fehlerraten, hingewiesen werden. Hierfür werden im Skript zwei Mechanismen genutzt: einmal eine **optionale** Analyse der DSL-Werte und des Router-Logs durch **Google Gemini KI** (kostenlos, Link wird angeboten) und zum anderen eine rein lokale regelbasierte Analyse der Routerdaten, die primär auf Probleme beim Verbinungsaufbau hinweist.<br>
Details siehe [Dokumentation zum Statusreport](report.md).

Da der Router keine offizielle Daten-API bietet, wurden die Daten zuerst nur über Web-Scraping ausgelesen. 
Im nächsten Schritt wurden Telnet und SNMP hinzugefügt, um die Daten schneller und zuverlässiger auszulesen.<br>
Durch die Verwendung einer [Third-Party-Router API von Alexandr Erohin](https://github.com/AlexandrErohin/TP-Link-Archer-C6U) wurde die Datenabfrage soweit beschleunigt, dass auf die Aktivierung und Verwendung von Telnet und SNMP zur reinen Datenerfassung verzichtet werden kann.

OPTIONAL: Telnet und SNMP sind zwar in der Firmware des Routers vorhanden, aber der superadmin Account auf dem Router muss aktiviert sein, um Telnet und SNMP aktivieren und nutzen zu können. Die Aktivierung des Accounts wird in der Anleitung **[Aktivierung superadmin, Telnet, SNMP und iPerf3](superadmin_telnet_snmp_iperf.md)** beschrieben.

**Alle Funktionen** des Skripts können **auch ohne aktivierten superadmin Account** genutzt werden. 

??? info "Beispiel für einen Statusreport"
    ![Beispiel Statusreport](images/beispiel-statusreport.jpg)

??? info "Beispiel für das Browser-Dashboard"
    ![Beispiel Browser-Dashboard](images/beispiel-dashboard.jpg)

## Funktionsumfang

*   **Datenerfassung:** Automatisierter Abruf von Systemzuständen, DSL-Werten und Client-Listen primär per Telnet und SNMP. Für Daten, die darüber nicht zugänglich sind, erfolgt ein Auslesen der Weboberfläche des Routers.
*   **Datenspeicherung:** Alle erfassten Messwerte, verbundenen Geräte und System-Logs werden fortlaufend in einer SQLite-Datenbank gespeichert.
*   **Reporting:** Die gesammelten Daten der letzten 24 Stunden können als HTML-Statusbericht aufbereitet werden. Der Bericht enthält unter anderem aktuelle Verbindungsparameter, Auszüge aus dem Event-Log und ein Anwesenheitsdiagramm der Clients. Der Versand kann automatisiert per E-Mail erfolgen.
*   **Lokales Browser-Dashboard:** Ein integrierter lokaler Webserver ermöglicht die interaktive grafische Visualisierung der historisierten DSL-Parameter über frei wählbare Zeiträume.

([Release Notes anzeigen](release-notes.md))

## Dokumentationsübersicht

*   [**Setup & Installation**](setup.md) - Systemvoraussetzungen (inkl. Aktivierung des Superadmin-Zugangs) und Installation.
*   [**Konfiguration**](konfiguration.md) - Syntax der `config.ini`, Startparameter und Einrichtung der automatisierten Ausführung.
*   [**Auswertungen - Statusreport**](report.md) - Erläuterung der Inhalte und Parameter des generierten HTML-Berichts.
*   [**Auswertungen - Browser-Dashboard**](dashboard.md) - Nutzung der lokalen, interaktiven Ansicht für historische Daten.
*   [**Lokalisierung**](lokalisierung.md) - Anleitung zur Anpassung der Tabellenansicht auf andere Sprachen.

---
*Weitere Informationen unter [vx-info.md](https://github.com/einstweilen/tp-link-vx231v/blob/main/vx-info.md).*
