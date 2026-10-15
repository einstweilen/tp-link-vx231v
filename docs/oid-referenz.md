# OID-Referenz: Router-Datenmodell `DEV2_*` und SNMP

Diese Referenz sammelt, **welche Daten der VX231v hergibt und wie man sie abfragt**. Sie entstand bei der
Umstellung auf SNMP v3 / Firmware 0.26.0 (Oktober 2026), als für die Client-Liste systematisch alle OIDs der
Firmware durchprobiert wurden.

**Wichtig zum Verständnis:** `DEV2_*` sind **keine SNMP-OIDs**, sondern das interne Datenmodell des Routers
(TR-069-nah). Sie werden über die Weboberfläche/HTTP-API abgefragt (`POST /cgi_gdpr`, AES-GCM-verschlüsselt) -
die SNMP-OIDs (Abschnitt 4) sind davon getrennt.

**Stand:** Firmware `231.0.26` (0.26.0, Build 260908, 13.10.2026). Die Feldnamen können sich mit Firmware-
Updates ändern.

---

## 1) Überblick: 22 von 776 OIDs liefern Daten

Die Firmware kennt **776** `DEV2_*`-Namen (Quelle: `/js/oid_str.js` der Router-Oberfläche). Über die API
liefern davon nur die folgenden **22** Daten (Abfrage über `req_act` der Bibliothek `tplinkrouterc6u`):

| OID | Operation | Einträge | Felder | Inhalt / wichtige Felder | Im Projekt genutzt |
|---|---|---|---|---|---|
| `DEV2_DEV_INFO` | `go` | – | ~57 | System/Gerät: `modelName`, `softwareVersion`, `hardwareVersion`, `serialNumber`, `upTime` (Sekunden), `X_TP_BuildDate`, `X_TP_MACAddress` | ✔ System/Report |
| `DEV2_DSL_LINE` | `go` + Stack `1,0,0,0,0,0` | 1 | 59 | Leitungswerte (Abschnitt 3.2) | ✔ DSL |
| `DEV2_DSL_CHANNEL` | `go` + Stack `1,0,0,0,0,0` | 2 | 14 | Kanalwerte (Abschnitt 3.2) | ✔ DSL |
| `DEV2_ADT_WAN` | `gl` | 3 | 118 | WAN-Verbindungen inkl. öffentlicher IP, Byte-/Paketzähler (Abschnitt 3.4) | ✔ IP/Report |
| `DEV2_WIFI_APDEV_ASSOCDEV` | `gl` | 5 | 19 | **WLAN-Clients** (Abschnitt 3.1) | ✔ Clients |
| `DEV2_WIFI_APDEV_ETHASSOCDEV` | `gl` | 1 | 25 | **LAN-Clients** inkl. Byte-Zähler (Abschnitt 3.1) | ✔ Clients |
| `DEV2_WIFI_DE_STA` | `gl` | 5 | 39 | WLAN-Stationen inkl. Paket-/Retry-Zähler (Abschnitt 3.1) | ergänzend |
| `DEV2_WIFI_APDEV` | `gl` | 1 | 57 | Mesh-Controller/WLAN-Gerät (Abschnitt 3.5) | – |
| `DEV2_WIFI_APDEV_AP` | `gl` | 4 | 10 | Funkzellen/SSIDs (BSSID, SSID) | – |
| `DEV2_WIFI_APDEV_RADIO` | `gl` | 2 | 21 | Funkparameter je Band | – |
| `DEV2_WIFI_RADIO` | `gl` | 2 | 45 | Funkparameter (Detail) | – |
| `DEV2_WIFI_APDEV_COMPONENT` | `gl` | 43 | 5 | Mesh-Komponenten (`protocol`, `type`, `version`, `capability`) | – |
| `DEV2_ADT_WIFI_COMMON` | `gl` | 2 | 129 | WLAN-Konfiguration (umfangreich) | – |
| `DEV2_WIFI_WDSBRIDGE` | `gl` | 2 | 14 | WDS-Bridge-Partner | – |
| `DEV2_ETH_INTF` | `gl` | 5 | 14 | Ethernet-Interfaces (`name`, `status`, `MACAddress`, `X_TP_IfNameAlias` z. B. `LAN`) | – |
| `DEV2_IP_INTF` | `gl` | 4 | 44 | IP-Interfaces | – |
| `DEV2_ROUTER_V4FWD` | `gl` | 3 | 15 | IPv4-Portweiterleitungen | – |
| `DEV2_ROUTER_V6FWD` | `gl` | 1 | 11 | IPv6-Freigaben | – |
| `DEV2_FW_CHAIN` / `DEV2_FW_CHAIN_RULE` | `gl` | 4 / 1 | 6 / 47 | Firewall-Ketten und -Regeln | – |
| `DEV2_USB_INTF` | `gl` | 1 | 30 | USB-Interface | – |
| `DEV2_DSLITE_INTFSET` | `gl` | 1 | 13 | DS-Lite-Einstellungen | – |
| `DEV2_PAGE_ACCESS_PERMISSION` | `gl` | 40 | 6 | Berechtigungen je Oberflächenseite | – |

`DEV2_X_TP_EASYMESH` liefert über `go` ein Dictionary mit **Mesh-Einstellungen** (`workMode`,
`controllerMACAddress`, Schwellwerte …) - **keine** Client-Liste.

Für die in dieser Tabelle **nicht** im Detail geprüften OIDs (Feldnamen) gilt: Anzahl Einträge/Felder wie
oben, Inhalt ergibt sich aus dem Namen.

---

## 2) OIDs ohne Daten (geprüft) - wichtig für die Fehlersuche

Diese OIDs liefern auf Firmware 231.0.26 **nur `null`** (getestet mit `gl` und `go`, mit und ohne
`stack`-Parameter). Sie stammen aus älteren Firmware-Ständen bzw. sind für dieses Modell nicht gefüllt:

| OID | Vermuteter Zweck | Befund |
|---|---|---|
| `DEV2_HOST_ENTRY`, `DEV2_HOSTS`, `DEV2_STORED_HOST_ENTRY` | Geräteliste des Routers | `null` - **nicht** für Clients nutzbar |
| `DEV2_ADT_LAN`, `DEV2_ADT_WIFI_CLIENT`, `DEV2_WIFI_APDEV_MACTABLE` | LAN-/WLAN-Clientlisten | `null` |
| `DEV2_CLIENT_INFO`, `DEV2_DHCPV4_CLIENT`, `DEV2_ONLINESTATUS` | Client-/Lease-Infos | `null` |
| `DEV2_WIFI_APDEV_STATS`, `DEV2_ETH_INTF_STATS`, `DEV2_HOST_WANSTATS` | Verkehrsstatistiken | `null` |
| `DEV2_DSL_LINE_STATS(_TOT)`, `DEV2_DSL_CHANNEL_STATS(_TOT)`, `DEV2_FAST_LINE_STATS(_TOTAL)` | DSL-Zähler (CRC/FEC/ES) | `null` |
| `DEV2_DSL_DIAG`, `DEV2_DSL_DIAGNOSTIC`, `DEV2_DSL_*_QUART_HOUR`, `DEV2_DSL_*_CURR_DAY` | DSL-Diagnose/Verlauf | `null` |

**Folge:** DSL-**Fehlerzähler (CRC/FEC)** sind über die API **nicht** erhältlich - sie stehen ausschließlich in
der Weboberfläche (Elemente `UCRC`/`DCRC`, siehe [config.ini im Detail](config-details.md), Option
`crc_source`). Ebenso liefert `DEV2_ADT_LAN` keine Daten mehr, weshalb die Client-Liste über
`DEV2_WIFI_APDEV_ASSOCDEV` / `…_ETHASSOCDEV` (bzw. SNMP-ARP) geholt wird.

---

## 3) Wichtige OIDs im Detail

### 3.1 Clients

**`DEV2_WIFI_APDEV_ASSOCDEV`** (`gl`) - WLAN-Clients, je Eintrag 19 Felder:
`MACAddress`, `X_TP_HostName`, `X_TP_IPAddress`, `X_TP_RadioMac`, `X_TP_ApDeviceMac`, `X_TP_BssMac`,
`operatingStandard` (`g` = 2,4 GHz, `a` = 5 GHz), `signalStrength` (roh, z. B. `164`),
`X_TP_SignalStrengthLevel`, `noise`, `X_TP_MaxLinkRate`, `lastDataDownlinkRate` / `lastDataUplinkRate`
(kbit/s, z. B. `72000`), `active` (`1`/`0`), `associationTime`, `X_TP_DisassociationTime`,
`steeringHistoryNumberOfEntries`, `X_TP_Remove`, `stack`

**`DEV2_WIFI_APDEV_ETHASSOCDEV`** (`gl`) - LAN-Clients, je Eintrag 25 Felder:
`MACAddress`, `X_TP_HostName`, **`IPAddress`** (Achtung: nicht `X_TP_IPAddress`), `IPv6Address`,
`APDeviceID`, `APDeviceMACAddress`, `active`, `linkSpeed` (Mbit/s, z. B. `1000`), `duplexMode`,
`interfaceType`, `bytesReceived` / `bytesSent`, `packetReceived` / `packetsSent`, `errorsReceived` /
`errorsSent`, `retransCount`, `downSpeed` / `upSpeed`, `lastConnectTime`, `associationTime`,
`X_TP_DisassociationTime`, `timeStamp`, `X_TP_Remove`, `stack`

**`DEV2_WIFI_DE_STA`** (`gl`) - WLAN-Stationen, je Eintrag 39 Felder. Wichtig: **`bytesReceived`/`bytesSent`
sind `0`** (die Firmware füllt sie hier nicht), gefüllt sind die **Paket-/Retry-Zähler**:
`packetsReceived`, `packetsSent`, `retransCount`, `X_TP_FailNum`, `X_TP_FailedRetransCount`,
`X_TP_RetryCount`, `X_TP_MultipleRetryCount`, `X_TP_RxRate`, `X_TP_TxRate`, `X_TP_DownSpeed`,
`X_TP_UpSpeed`, `X_TP_Noise`, `X_TP_OperatingStandard`, `X_TP_MaxLinkRate`, `lastDataDownlinkRate`,
`lastDataUplinkRate`, `estMACDataRateDownlink`/`Uplink`, `signalStrength`, `utilizationReceive`/
`utilizationTransmit`, `measurementReport`, `numberOfMeasureReports`, `X_TP_HostName`, `X_TP_IPAddress`,
`IPV4Address`, `IPV6Address`, `hostname`, `lastConnectTime`, `HTCapabilities`, `VHTCapabilities`,
`HECapabilities`, `stack`, `timeStamp`

> **Zähler sind 32-Bit** (wie SNMP `Counter32`) - bei Stundenläufen sind nur Momentaufnahmen sinnvoll,
> keine Differenzen (Überlauf > 4 GB zwischen zwei Läufen).

### 3.2 DSL

**`DEV2_DSL_LINE`** (`go`, Stack `1,0,0,0,0,0`) - 59 Felder, u. a.:
`upstreamMaxBitRate`, `downstreamMaxBitRate`, `upstreamCurrRate`\*, `downstreamCurrRate`\*,
`upstreamNoiseMargin`, `downstreamNoiseMargin` (Zehntel-dB, z. B. `64` = 6,4 dB),
`upstreamAttenuation`, `downstreamAttenuation`, `upstreamPower`/`downstreamPower` (Zehntel-dBm),
`X_TP_UpstreamDelay`, `X_TP_DownstreamDelay`, `linkStatus`, `status`, `enable`, `standardUsed`,
`standardsSupported`, `allowedProfiles`, `currentProfile`, `XTSE`, `XTSUsed`, `X_TP_AnnexType`,
`X_TP_BitswapEnable`, `X_TP_DataPath`, `X_TP_DownstreamGinp`, `X_TP_DownstreamGvector`,
`X_TP_DownstreamInp`, `X_TP_DownstreamGinpReinVal`, `X_TP_DownstreamGinpShineVal`, `X_TP_UpstreamGinp`,
`X_TP_UpstreamGvector`, `X_TP_UpstreamInp`, `X_TP_LoopLength`, `X_TP_ModulationType`,
`X_TP_ModulationTypeUsed`, `X_TP_Profile`, `X_TP_SRAEnable`, `X_TP_SRAState`, `X_TP_SupportedDslMode`,
`X_TP_UPBO`, `X_TP_VDSLProfiles_8a` … `_35b`, `X_TP_VDSLProfiles_US0_8a`, `X_TP_VendorID`,
`X_TP_Version`, `X_TP_35bCompat`, `X_TP_DownstreamGinpReinVal`, `alias`, `name`, `lastChange`,
`lowerLayers`, `upstream`, `stack`

\* `upstreamCurrRate`/`downstreamCurrRate` kamen auf dieser Firmware über den Line-OID als `0` zurück; die
„aktuellen" Raten liefert `DEV2_DSL_CHANNEL`, sonst wird auf die Maximalrate zurückgefallen.

**`DEV2_DSL_CHANNEL`** (`go`, Stack `1,0,0,0,0,0`) - 14 Felder:
`upstreamCurrRate`, `downstreamCurrRate` (kbit/s), `status`, `enable`, `linkEncapsulationUsed`,
`linkEncapsulationSupported`, `INTLVDEPTH`, `LPATH`, `X_TP_Qos_intf_enable`, `alias`, `name`,
`lastChange`, `lowerLayers`, `stack`
**Keine Fehlerzähler** - CRC/FEC gibt es nur in der Weboberfläche.

### 3.3 System / Gerät

**`DEV2_DEV_INFO`** (`go`) - ~57 Felder, u. a.: `modelName` (`VX231v`), `description`
(`Wi-Fi 6 Internet box 4`), `manufacturer`, `manufacturerOUI`, `serialNumber`, `hardwareVersion`,
`softwareVersion` (`231.0.26`), `X_TP_CloudSoftwareVersion` (`0.26.0 3.2.2 v606c.0 Build 260908`),
`X_TP_BuildDate` (`260908`), `X_TP_BuildTime`, `X_TP_BuildSpec` (`DE`), `X_TP_DeviceModel` (`VX231v(DE)`),
`X_TP_DeviceType` (`ISP.XDSLMODEMROUTER`), `X_TP_MACAddress`, `X_TP_SerialNumber`,
`X_TP_HardwareID`/`X_TP_FirmwareID`/`X_TP_OemID`, `upTime` (Sekunden), `provisioningCode`, `stack`

### 3.4 WAN / Interfaces

**`DEV2_ADT_WAN`** (`gl`) - 118 Felder je Eintrag, typischerweise 3 Einträge (`usb_ppp3g`, `usb_dhcp4g`,
`pppoe_ptm_7_0`). Wichtige Felder: `enable`, `name`, `accessMode` (`PPPoE`/`USB`/…), `serviceType`,
`connStatusV4` / `connStatusV6` (`Connected`), `connIPv4Address`, `connIPv6Address`, `connIPv4Gateway`,
`connIPv4SubnetMask`, `connIPv4DnsServer`, `X_TP_IfName`, `X_TP_BytesReceived` / `X_TP_BytesSent`,
`X_TP_PacketsReceived` / `X_TP_PacketsSent`, `PPPLastConnError`, `DHCPLastConnectionError`,
`secondConnDHCPLastConnectionError`, `IPIntfIndex`, `_IPIntfInstanceId`, `stack`

Weitere Interfaces: `DEV2_ETH_INTF` (Ethernet, `X_TP_IfNameAlias` = `LAN`), `DEV2_IP_INTF` (IP/PPPoE),
`DEV2_DSLITE_INTFSET`, `DEV2_USB_INTF`, `DEV2_ROUTER_V4FWD`/`_V6FWD` (Portweiterleitungen),
`DEV2_FW_CHAIN`/`DEV2_FW_CHAIN_RULE` (Firewall).

### 3.5 WLAN / Mesh

`DEV2_WIFI_APDEV` (`gl`, 1 Eintrag, 57 Felder) = das WLAN-Gerät selbst: `X_TP_HostName` (`VX231v`),
`X_TP_IPAddress`, `X_TP_ModelName`, `X_TP_IsController`, `X_TP_Active`, `X_TP_InetStatus`, `X_TP_Band`,
`X_TP_LinkRate`, `X_TP_CPUUsage`, `X_TP_MemoryUsage`, `X_TP_DownSpeed`/`UpSpeed`, `X_TP_DeviceId`,
`X_TP_HardwareID`, `X_TP_CloudSoftwareVersion`, `X_TP_ADDBYSCANNING`, `X_TP_AlMac`, `X_TP_Location`,
`X_TP_Action`, `X_TP_DeviceType`, `X_TP_DeviceSubType`, `X_TP_IMEI`, `X_TP_IsSupportThread`, …
`DEV2_WIFI_APDEV_AP` (4 Einträge, 10 Felder) = Funkzellen: `BSSID`, `SSID`, `X_TP_Type` (`Primary`),
`X_TP_LinkRate`, `X_TP_SignalStrength`, `BTMAttempts`, `BTMQueryResponses`, `blacklistAttempts`, …
Dazu `DEV2_WIFI_RADIO`, `DEV2_WIFI_APDEV_RADIO`, `DEV2_WIFI_APDEV_COMPONENT`, `DEV2_ADT_WIFI_COMMON`,
`DEV2_WIFI_WDSBRIDGE`, `DEV2_X_TP_EASYMESH`.

---

## 4) SNMP-OIDs (net-snmp) - 32-Bit-Zähler

Diese OIDs werden per Kommandozeile abgefragt (SNMP v3, siehe
[SNMP-Beispiele](https://github.com/einstweilen/tp-link-vx231v/blob/main/Using-SNMP-OIDs.md) bzw. [superadmin/Telnet/SNMP](https://github.com/einstweilen/tp-link-vx231v/blob/main/superadmin_telnet_snmp_iperf.md)):

```bash
SNMP_OPTS=(-v3 -l authNoPriv -u "$SNMP_USER" -a MD5 -A "$SNMP_PASS")
snmpget "${SNMP_OPTS[@]}" -Ovq "$IP" 1.3.6.1.2.1.1.5.0     # sysName
```

| OID | Bedeutung | Genutzt für |
|---|---|---|
| `.1.3.6.1.2.1.1.1.0` | `sysDescr` (Firmware/Kernel-String) | Verfügbarkeitsprüfung |
| `.1.3.6.1.2.1.1.3.0` | `sysUpTime` (`d:hh:mm:ss`) | Router-Uptime im Report |
| `.1.3.6.1.2.1.1.5.0` | `sysName` | Gegenprobe |
| `.1.3.6.1.2.1.2.2.1.2` | `ifDescr` (Interfacenamen: `eth0.4`, `nas9`, `ppp0`) | Interface-Index-Suche |
| `.1.3.6.1.2.1.2.2.1.10/16.<idx>` | `ifInOctets`/`ifOutOctets` (**Counter32**) | Traffic-Zähler (Wrapper-Logik nötig) |
| `.1.3.6.1.2.1.31.1.1.1.6/10.<idx>` | `ifHCInOctets`/`ifHCOutOctets` | liefert **denselben** Wert → es gibt keinen 64-Bit-Zähler |
| `.1.3.6.1.2.1.2.2.1.8.<idx>` | `ifOperStatus` | DSL-Link up/down |
| `.1.3.6.1.2.1.4.20.1.2` | `ipAdEntIfIndex` | LAN-/Gastnetz-Interfaces finden |
| `.1.3.6.1.2.1.4.22.1.2` | `ipNetToMediaPhysAddress` (ARP) | **Client-Liste** (MAC/zu IP aus Index) |

Hinweis: `.1.3.6.1.2.1.2.2.1.10/16` sind **32-Bit** (`Counter32`, Überlauf bei 4 GB). Das Skript behandelt
den Überlauf in `vx_status_snmp.8s.sh`, im Python-Teil werden die Werte nur als Momentaufnahme gespeichert.

---

## 5) Praktische Fallstricke

1. **Ein OID pro Abfrage:** `tplinkrouterc6u` entfernt OIDs ohne Daten aus der Ergebnisliste einer
   Sammelabfrage - dadurch verschieben sich die Positionen der übrigen Werte. Im Projekt deshalb `_act()`
   (einzelne Abfrage je OID).
2. **Operation beachten:** `go` (`GET`) für Einzelobjekte, `gl` (`GL`) für Listen (Clients, WAN, Funk).
   Die Clients-OIDs liefern nur mit `gl`.
3. **`stack`-Parameter:** DSL-OIDs brauchen `1,0,0,0,0,0`, LAN-/WLAN-Listen kommen ohne Stack.
4. **Tabellen erst nach einem Besuch der Weboberfläche gefüllt** (DSL und Clients). Über die API kommt
   vorher dauerhaft leer - das Projekt „weckt" sie daher einmal per Browser (`warmup`).
5. **Werte sind Strings**, teils skaliert: SNR/Dämpfung in Zehntel-dB, `lastData*Rate` in kbit/s,
   `linkSpeed` in Mbit/s, `upTime` in Sekunden.
6. **IP-Adressen heißen unterschiedlich:** LAN-Clients `IPAddress`, WLAN-Clients `X_TP_IPAddress`,
   WAN `connIPv4Address`.
7. **Fehlerzähler nur in der Oberfläche** (Abschnitt 2).

---

## 6) Selbst nachschauen

```python
# OID-Namen der Firmware:  https://<router>/js/oid_str.js   (im angemeldeten Browser abrufen, 776 Namen)
import logging
from tplinkrouterc6u.client.ex import TPLinkEXClientGCM

r = TPLinkEXClientGCM("https://192.168.178.1", "<ROUTER-PASSWORT>", "user", logging.getLogger("t"), verify_ssl=False)
r.authorize()
code, values = r.req_act([r.ActItem(r.ActItem.GL, "DEV2_WIFI_APDEV_ASSOCDEV")])
print(values[0])          # Liste der WLAN-Clients; None = keine Daten
r.logout()
```

Nützliche Helfer im Projekt: `core/api_client.py` (`_act()`, `get_clients()`, `get_dsl_data()`),
`core/arp_scan.py` (Client-Suche ohne SNMP/API) und das lokale Debug-Skript `nogit/nogit_vx-info.py`
(nicht Teil des Repos).
