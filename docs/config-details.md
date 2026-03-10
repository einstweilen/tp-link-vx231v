# Die config.ini im Detail

Die zentrale Steuerung des TP-Link VX231v Trackers erfolgt über die Datei `config.ini`. Sie wird vor dem ersten Start aus der beigelegten `config.ini.sample` erstellt.

Die Parameter und ihre Funktion:

---

## [Router]

*   `routerip`: Die IP-Adresse (z. B. `192.168.0.1`) oder der Hostname des Routers.
    *   **Nutzung:** Wird beim Login in die Web-Oberfläche sowie bei den Telnet- und SNMP-Verbindungen als Zieladresse verwendet.

## [Database]

Konfiguration der lokalen SQLite-Datenbanken.

*   `db_name`: Der Dateiname (Standard: `router_data.db`) für sämtliche vom Skript ausgelesenen Router-Werte (DSL-Historie, Client-Logs, Event-Logs).
*   `lang_db_name`: Der Dateiname (Standard: `router_lang.db`) der sprachspezifischen Übersetzungsmatrix für das Dashboard und Berichtswesen.

## [Telnet]

Zugangsdaten für die schnelle Router-Abfrage, sofern der superadmin-Account aktiviert wurde.

*   `username` / `password`: Login-Daten für Telnet.
    *   **Nutzung:** Ermöglicht dem Skript (`vx-info.py --update`) in Sekunden den Status und alle DSL-Werte des Routers abzurufen, ohne den langsamen Browser starten zu müssen.

## [Analyse]

Zentrale Steuerung für den KI/Leitungs-Analyseblock im Statusreport.

*   `report_disconnects_level`: Bestimmt, ab welchem Schweregrad ein Verbindungsabbruch in der Leitungsanalyse aufgelistet wird. (Standard: `1`)
    *   `0`: Zeigt alle Trennungen, auch vom Nutzer geplante Reboots, saubere Neuverbindungen oder die regelmäßige Zwangstrennung des Providers.
    *   `1`: Zeigt ausschließlich ungeplante Abbrüche und echte technische Fehler.
    *   `2`: Zeigt ausschließlich Abbrüche, bei denen es messbare Probleme gab (z.B. Reconnect dauerte >45s, DNS-Fehler, massiver Bandbreitenverlust).
    *   `3`: Meldet nur schwere, sicherheitskritische Störungen (SNR-Absturz < 6dB, starker CRC-Fehler-Burst, PPPoE-Timeouts).

## [SNMP]

Optionale Zugangsparameter für SNMP (Simple Network Management Protocol).

*   `community`: Das SNMP-Passwort bzw. der "Community String" (oft `public`).

## [GUI]

Login-Daten für das reguläre TP-Link Web-Interface.

*   `username` / `password`: Die Zugangsdaten, mit denen auch der Login im Router im Browser erfolgt.
    *   **Nutzung:** Das Skript nutzt einen headless Browser, um das vollständige Eventlog des Routers (`--log`) herunterzuladen und Client-Hostnames auszulesen.<br>Ohne aktiviertes Telnet/SNMP werden auch die DSL-Parameter (`--update`) automatisch auf diesem Weg ermittelt.

## [Email]

Einstellungen für den automatisierten E-Mail-Versand des HTML-Statusreports (`vx-info.py --report-send`).

*   `smtp_server` / `smtp_port`: Postausgangsserver (z. B. `smtp.gmail.com` oder `mail.gmx.net`) und der zugehörige Port (oft `587` mit TLS).
*   `sender_email` / `sender_password`: Die E-Mail-Adresse und das Passwort, von der aus der Bericht gesendet wird. (Bei GMail oder Apple ist hier evtl. ein gerätespezifisches App-Passwort nötig!).
*   `recipient_email`: Die Ziel-Adresse, die den täglichen Report empfangen soll.
Wer Sicherheitsbedenken hat, kann einen gesonderten E-Mail Account dafür anlegen und diesen ausschließlich für den Reportversand und -empfang nutzen, dann gibt keine Gefahr, dass darüber andere Daten leaken.

## [Events]

Regelt, wie die vielen Event-Logs ("Logbuch") des Routers in der Datenbank und im Statusreport behandelt werden.

*   `exclude_types`: (z. B. `DHCPD, Mesh`). Bestimmt, welche Art von Systemereignissen als zu detailliert/unwichtig betrachtet werden.
*   `cleanup_excludes`: (z. B. `3`). Löscht alle in `exclude_types` genannten Events automatisch nach dieser Anzahl an Tagen (hier: nach 3 Tagen) unwiderruflich aus der lokalen Datenbank `.db`, um Speicherplatz zu sparen.
<br>
*   `show_level`: Steuert direkt, welche Ereignisse im generierten HTML-Report des Tages auftauchen:
    *   `0` bis `7`: Nimmt die Standard-Warnstufen des Routers (von Notfall bis Debug). Ein Wert von `4` (Vorsicht) zeigt also alle Ereignisse zwischen Notfall (0) und Vorsicht (4) an.
    *   `8`: Reserviert für rsyslog importierte Logeinträge.
    *   `9`: Ein vom Skript zusätzlicher scriptspezifischer Level.<br>Es zeigt alle Ereignisse der letzten 24 Stunden (entspricht dem Level Debug 7), verbirgt aber explizit die bei `exclude_types` (z. B. den ständigen MESH Handshake der Repeater) herausgefilterten Typen.

## [Charts]

Konfiguration der historischen DSL-Balkendiagramme, vorwiegend für den täglichen HTML-Report (`--report-show`).

*   `table_1` / `field_1`: Bestimmt die auszuwertende Spalte aus der Datenbank. `table_1 = dsl` und `field_1 = downstream_noise_margin` greift auf die historische Rauschtoleranz im Download zu.
*   `label_1`: Die Überschrift des Diagramms im Report (z.B. "Downstream Störabstand (dB)").
*   `hours_back`: Bestimmt die zeitliche Breite (X-Achse) des Diagramms im generierten Statusreport (Standard: z.B. `48` Stunden).
*   `start_hour`: Wenn auf `0` gesetzt, zwingt es das System, den betrachteten Zeitraum eines Tages immer um 00:00 Uhr und nicht "genau heute vor 24 Stunden" beginnen zu lassen.

## [Reports]

Verwaltung der lokal gespeicherten Berichte

*   `cleanup_reports`: Jedes Mal, wenn ein Report (`--report-show` oder `--report-send`) generiert wird, speichert das Skript eine `.html` Datei im Ordner `reports/`.<br>
Entspricht dieser Wert z. B. `7`, so werden alle Berichte, die älter als 7 Tage sind, bei der Skriptausführung automatisch gelöscht, um das Verzeichnis nicht unendlich wachsen zu lassen. `0` deaktiviert die Löschfunktion.

## [Statistics]

Kleine Indikatoren, die im Statusreport im Bereich "Statistiken" auftauchen können, um beim Debugging zu unterstützen

*   `reconnects`: Wenn `True`, berechnet das Skript aus den Logs der letzten 24 Stunden, wie oft der Router die DSL-Verbindung ("PPP down / up") verloren hat.
*   `PADO_timeouts`: Wenn `True`, wird gezielt nach Einwahl-Fehlern gesucht (Provider-Störungen beim Zuteilen der IP) und deren Anzahl ausgeworfen.
