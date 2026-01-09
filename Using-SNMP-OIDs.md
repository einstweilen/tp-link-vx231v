# SNMP Basics: TP-Link VX231v

**Version:** 1.1  
**Device:** TP-Link VX231v (FW 231.0.19)  
**Protocol:** SNMP v2c  

---

## 1. Introduction
This is a very basic introduction to [SNMP](https://www.wikipedia.org/wiki/Simple_Network_Management_Protocol) and a collection of some useful [OIDs](https://www.rfc-editor.org/rfc/rfc4293.html).<br>It is mainly based on a standard SNMPwalk, some OIDs are missing as enterprise-specific MIBs are restricted by the firmware.

### Used variables in this document
**$COMMUNITY** your read-only password (default 'public')

**$IP** the IP auf your router (default '192.168.1.1')

**snmpwalk** lists 363 OIDs for the VX231v<br>
`snmpwalk -v2c -c "$COMMUNITY" "$IP" .1`
<br>

### How to access a specfic OID<br>

Either symbolic OID e.g. 'SNMPv2-MIB::sysName.0'<br>
snmpget -v2c -c "$COMMUNITY" "$IP" SNMPv2-MIB::sysName.0<br>
or numeric OID e.g. '.1.3.6.1.2.1.1.5.0'<br>
snmpget -v2c -c "$COMMUNITY" "$IP" .1.3.6.1.2.1.1.5.0<br>


Use SNMP flags to format command output<br>
**-Ov**	output values only (hides OID)<br>
**-Oq**	output quick format (removes "=" and data type)


| OID (numeric) | OID (symbolic)
| :--- | :--- |
1.3.6.1.2.1.1.5.0 | SNMPv2-MIB::sysName.0
<br>

snmpget -v2c -c "$COMMUNITY" "$IP" 1.3.6.1.2.1.1.5.0<br>
OUTPUT: SNMPv2-MIB::sysName.0 = STRING: VX231v

snmpget -v2c -c "$COMMUNITY" **-Ov** "$IP" 1.3.6.1.2.1.1.5.0<br>
OUTPUT: STRING: VX231v

snmpget -v2c -c "$COMMUNITY" **-Ovq** "$IP" 1.3.6.1.2.1.1.5.0<br>
OUTPUT: VX231v

---

## 2. Interface Mapping (ifIndex)
Use the **ifIndex** for granular traffic analysis:

snmpwalk -v2c -c "$COMMUNITY" "$IP" .1.3.6.1.2.1.2.2.1.2

| Index | Interface Name | Description |
| :--- | :--- | :--- |
| **52** | `nas9` | **VDSL Bridge**<br>Physical DSLAM connection|
| **55** | `ppp0` | **WAN / Internet (PPPoE)**<br>Logical internet interface|
| **19** | `br0` | **LAN Bridge**<br>Combined LAN and WiFi network|
| **23** | `ra2` | **WiFi 2.4 GHz**<br>Radio module for 2.4 GHz|
| **24** | `ra3` | **WiFi 5 GHz**<br>Radio module for 5 GHz|
| **31** | `rai3` | **LAN**<br>Sum of all LAN ports (?)|


---

## 3. Monitoring Parameters
### 3.1 Bandwidth & Traffic

ip4 ipAdEntIfIndex<br>
snmpwalk -v2c -c "$COMMUNITY" "$IP" .1.3.6.1.2.1.4.20.1.2

| OID (numeric) | OID (symbolic)
| :--- | :--- |
| IP-MIB::ipAdEntIfIndex.84.140.153.11 = INTEGER: 67 | **external IP4 IP** |
| IP-MIB::ipAdEntIfIndex.127.0.0.1 = INTEGER: 1 | ??? |
| IP-MIB::ipAdEntIfIndex.169.254.63.206 = INTEGER: 65 | ??? |
| IP-MIB::ipAdEntIfIndex.192.168.1.1 = INTEGER: 19 | **main** |
| IP-MIB::ipAdEntIfIndex.192.168.210.1 = INTEGER: 37 | **guest** |

### 3.2 Bandwidth & Traffic
*Type: Counter32 (Requires differential calculation).*

| Metric | OID (X = Index) | Example (Internet Download) |
| :--- | :--- | :--- |
| **Download (Bytes)** | `.1.3.6.1.2.1.2.2.1.10.X` | `.1.3.6.1.2.1.2.2.1.10.55` |
| **Upload (Bytes)** | `.1.3.6.1.2.1.2.2.1.16.X` | `.1.3.6.1.2.1.2.2.1.16.55` |

### 3.3 System Health & Errors
| OID | Name | Description |
| :--- | :--- | :--- |
| `.1.3.6.1.2.1.2.2.1.14.55` | `ifInErrors` | Corrupted packets (CRC/Framing). |
| `.1.3.6.1.2.1.2.2.1.13.55` | `ifInDiscards` | Dropped packets (Buffer full). |

### 3.4 Connection Status

| OID | Name | Description |
| :--- | :--- | :--- |
| `.1.3.6.1.2.1.6.9.0` | `tcpCurrEstab` | Number of active TCP connections. |
| `.1.3.6.1.2.1.7.1.0` | `udpInDatagrams`| Total received UDP datagrams. |
| `.1.3.6.1.2.1.7.3.0` | `udpInErrors` | Faulty UDP packets. |

<br>

 ```
 oid=".1.3.6.1.2.1.7.3.0" # Faulty UDP packets
 a=$(snmpget -v2c -c "$COMMUNITY" -Ovq "$IP" "$oid")
 sleep 60
 b=$(snmpget -v2c -c "$COMMUNITY" -Ovq "$IP" "$oid")
 echo "Faulty UDP packets $((b-a))/min"
 ```
 
---

## 4. Network Analysis

### 4.1 Active IP Interfaces
* `192.168.1.1` (Internal Gateway)
* `127.0.0.1` (Localhost)

### 4.2 ARP Table / Connected Clients
This OID maps IP addresses to physical MAC addresses for all devices in the ARP cache.

oid='.1.3.6.1.2.1.4.22.1.2' # ipNetToMediaPhysAddress<br>
snmpwalk -v2c -c "$COMMUNITY" "$IP" "$oid"

 ```
IP-MIB::ipNetToMediaPhysAddress.19.192.168.178.152 = STRING: b8:27:eb:8e:7f:39
IP-MIB::ipNetToMediaPhysAddress.19.192.168.178.153 = STRING: e4:5f:1:58:7:fd
IP-MIB::ipNetToMediaPhysAddress.19.192.168.178.176 = STRING: 70:4f:57:51:c4:30
IP-MIB::ipNetToMediaPhysAddress.19.192.168.178.190 = STRING: ee:90:2:43:ad:36
 ```

### 4.3 Listening Ports
Nmap scan report for 192.168.178.1

 ```
PORT    STATE         SERVICE
22/tcp  open          ssh
53/tcp  open          domain
80/tcp  open          http
443/tcp open          https
53/udp  open          domain
67/udp  open|filtered dhcps
161/udp open|filtered snmp
500/udp open|filtered isakmp
MAC Address: 3C:64:CF:ED:CA:FE (TP-Link PTE.)
 ```

---

## 5. Misc. information
```
Firware Version
> snmpget -v2c -c 'public' 192.168.1.1 1.3.6.1.2.1.1.1.0
SNMPv2-MIB::sysDescr.0 = STRING: 231.0.19

Uptime
> snmpget -v2c -c 'public' 192.168.1.1 1.3.6.1.2.1.1.3.0
DISMAN-EVENT-MIB::sysUpTimeInstance = Timeticks: (2228800) 6:11:28.00
```

## 6. Known Limitations
1. **DSL Parameters:** Sync rates and SNR margin return `No Such Instance`.
2. **Resource Monitoring:** CPU and RAM OIDs are unavailable.
3. **Counter Rollover:** 32-bit counters reset at ~4.29 GB (4294967295 bytes).
