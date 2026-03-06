# Statusreport

Die aufgezeichneten Daten können in einem Statusreport zusammengefasst werden.<br>
Dieser Bericht kann direkt mit dem lokalen Browser geöffnet oder zeitgesteuert als eMail versendet werden.

<details markdown="1">
<summary>Beispiel: Statusreport</summary>

![Beispiel Statusreport](images/beispiel-statusreport.jpg)

</details>

## Header

![Header](images/report-header.jpg)

Der Header zeigt
* Datum der Generierung
* Datum und Uhrzeit seit der letzten Routereinwahl
* die aktuelle IP-Adresse des Routers
* die aktuelle Download- und Upload-Geschwindigkeit

## Firmware

![Firmware](images/report-firmware.jpg)

Falls eine neue Firmware verfügbar ist, werden die dazugehörigen Releasenotes angezeigt. 
Die Releasenotes werden von der TP-Link Seite geladen und 1:1 ausgegeben.

Hinweis: TP-Link stellt diese Informationen nicht in strukturierter Form zur Verfügung, weshalb die Gestaltung sich von Note zu Note ändern kann.

## OPTIONAL: AI Analyse der Routerdaten der letzten 24/48 Stunden

![AI Analyse](images/report-ai.jpg)

Wenn auf dem Mac der AI Shortcut installiert ist, werden die Routerdaten der letzten 24/48 Stunden analysiert und ein kurzer Bericht erstellt.
Sollten die erfassten Routerdaten zu umfangreich für die Nutzung der kostenlosen Apple/GPT Schnittstelle sein, wird der Analyseprompt als Textdatei ai_prompt_debug.txt im Skriptordner abgelegt und der Bericht nicht erstellt.
Man kann bei Bedarf diese Datei durch eine andere KI auswerten lassen.

## Eventübersicht

![Eventübersicht](images/report-events.jpg)

Die Eventübersicht zeigt Leitungstrennungen und Neuverbindungen der letzten 48 Stunden.

## Anwesenheit

![Anwesenheit](images/report-clients.jpg)

Die Anwesenheitsübersicht zeigt die LAN und WLANVerbindungen der Clients der letzten 48 Stunden.
Durch unterschiedliche Farbgebung wird zwischen den verschiedenen Verbindungsarten unterschieden:
* Türkis: Heimnetz-Verbindung
* Orange: Gastnetz-Verbindung

Die Anwesenheit der Clients wird anhand der Routerlogdaten über die Zuteilung der IP durch den DHCP-Server ermittelt.

Clientnamen
Wenn im Router unter "WLAN-Teilnehmer" oder "Kabelgebundene Teilnehmer" ein Clientname hinterlegt ist, wird dieser im Statusreport angezeigt.
Der hinterlegte Name entspricht dem Namen, den der Client bei der Verbindung dem Router mitgeteilt hat. Hat man diesen in Webinterface überschrieben, wird der manuell überschriebene Name angezeigt.

Damit auch bei der schnellen Datenerfassung via Telnet/SNMP die Namen neuer Clients ermittelt werden können, prüft das Skript vor der Reporterstellung automatisch, ob noch unbekannte ("Unknown") Geräte in der Datenbank vorhanden sind. Ist dies der Fall, wird kurzzeitig auf das Web-Scraping-Interface zurückgegriffen, um die Namen auszulesen und in der Datenbank dauerhaft zu verknüpfen. Schlägt auch diese Zuordnung fehl, erhält der Client in der Grafik die Bezeichnung "unknown" gefolgt von seiner MAC-Adresse.



## Heimnetzübersicht aktuell aktiver Clients

![Heimnetzübersicht](images/report-aktive.jpg)

Zeigt die zum Zeitpunkt der Berichtserstellung im Heimnetz aktiven Clients an.

## Downstream Störabstand (dB)

![Downstream Störabstand](images/report-einparameter.jpg)

Zeigt einen über die config.ini konfigurierbaren DSL-Parameter, für den man sich besonders interessiert, an.
Im Beispiel wird der Verlauf über die letzten 48 Stunden des "Störabstands im Downstream" angezeigt.

## Statistiken

**Anzahl der Reconnects im Zeitraum (48h):** 2<br>
**Anzahl der Reconnects in den letzten 24h:** 1<br>
**Anzahl der PADO_timeouts im Zeitraum (48h):** 2<br>
**Anzahl der PADO_timeouts in den letzten 24h:** 0<br>

Beispiel für typische Debuginformationen bei Verbindungsproblemen.<br>
Abschaltbar im [Statistics] Bereich der config.ini durch setzen der Werte auf False.

## Ereignislog der letzten 24 Stunden

![Ereignislog](images/report-eventlog.jpg)

### Konfiguration der Ereignisloganzeige
Was in dem Statusreport angezeigt wird, läßt sich über zwei Parameter steuern, den Loglevel und den Typ des Events.

#### Der Loglevel
Der Router unterteilt aufgetretene Events in Loglevel von "0 Notfall" bis "7 Debug". Über den Parameter "show_level" in der config.ini wird festgelegt, bis zu welchem Loglevel Events im Statusreport angezeigt werden.<br>

Die vom Router verwendeten Loglevel lauten:<br>
```
0 Notfall   1 Alarm    2 Kritisch  3 Fehler 
4 Vorsicht  5 Hinweis  6 Info      7 Debug
```

Ist in der config.ini "show_level = 4" gesetzt, werden alle Events bis einschließlich Level "4 Vorsicht" angezeigt, also 0 Notfall, 1 Alarm, 2 Kritisch, 3 Fehler, 4 Vorsicht.

Beispielausgabe für einen Event:
```
Datum             Level Typ Event
05.03.26 03:50:25	3   PPP ppp0 LCP down
```

Wird "show_level = 7" in der config.ini gesetzt, werden alle Events der letzten 24 Stunden im Statusreport angezeigt, was sehr umfangreich werden kann.


#### Die Eventtypen
Jeder Event ist einem Eventtyp zugeordnet. Die vom Router verwendeten Eventtypen lauten: "DHCPD", "HTTPD", "MESH", "PPP", "VOIP".

Besonders die Events der Typen "DHCPD" und "MESH" treten sehr häufig auf, da sie durch das "ständige" An- und Abmelden der Clients entstehen, wie oben bereits bei "show_level = 7" geschrieben.
<br>
Um hier eine bessere Übersicht zu schaffen, wurden die bestehenden Eventlevel des Routers um einen weiteren virtuellen Level "8" ergänzt. Level "8" dient dazu, sich zwar alle Logeinträge anzeigen zu lassen, aber gleichzeitig bestimmte Eventtypen, die einen aktuell nicht interessieren, ausblenden zu lassen.

Zur Verwendung dieses Levels trägt man bei **show_level = 8** und bei **exclude_types** die zu ignorierenden Eventtypen ein. 

Die Eventtypen "DHCPD" und "MESH" sind in der Standardkonfiguration bereits eingetragen und werden somit bei gewähltem Level 8 nicht im Statusreport angezeigt.<br>Weitere oder andere Eventtypen können in der config.ini im Bereich [Events] unter "exclude_types" konfiguriert werden. Speziell "VOIP" könnte dort ergänzt werden, da dazu viele reine Info-Meldungen geschrieben werden.
