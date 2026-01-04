# SNMP Findings: TP-Link VX231v

**Version:** 1.0  
**Device:** TP-Link VX231v (FW 231.0.19)  
**Protocol:** SNMP v2c  

---

## 1. Introduction
This manual provides OIDs for monitoring systems (Zabbix, PRTG, Grafana). It is based on a standard MIB-II walk, as enterprise-specific MIBs are restricted by the firmware.

---

## 2. Interface Mapping (ifIndex)
Use the **ifIndex** for granular traffic analysis:

| Index | Interface Name | Description |
| :--- | :--- | :--- |
| **55** | `ppp0` | **WAN / Internet (PPPoE)**<br>Logical internet interface. |
| **52** | `nas9` | **VDSL Bridge**<br>Physical DSLAM connection. |
| **23** | `ra2` | **WiFi 2.4 GHz**<br>Radio module for 2.4 GHz. |
| **31** | `rai3` | **WiFi 5 GHz**<br>Radio module for 5 GHz. |
| **19** | `br0` | **LAN Bridge**<br>Combined LAN and WiFi network. |

---

## 3. Monitoring Parameters

### 3.1 Bandwidth & Traffic
*Type: Counter32 (Requires differential calculation).*

| Metric | OID (X = Index) | Example (Internet Download) |
| :--- | :--- | :--- |
| **Download (Bytes)** | `.1.3.6.1.2.1.2.2.1.10.X` | `.1.3.6.1.2.1.2.2.1.10.55` |
| **Upload (Bytes)** | `.1.3.6.1.2.1.2.2.1.16.X` | `.1.3.6.1.2.1.2.2.1.16.55` |

### 3.2 System Health & Errors
| OID | Name | Description |
| :--- | :--- | :--- |
| `.1.3.6.1.2.1.2.2.1.14.55` | `ifInErrors` | Corrupted packets (CRC/Framing). |
| `.1.3.6.1.2.1.2.2.1.13.55` | `ifInDiscards`| Dropped packets (Buffer full). |

### 3.3 Connection Status (Layer 4)
Monitoring of session load and potential attacks.

| OID | Name | Description |
| :--- | :--- | :--- |
| `.1.3.6.1.2.1.6.9.0` | `tcpCurrEstab` | Number of active TCP connections. |
| `.1.3.6.1.2.1.7.1.0` | `udpInDatagrams`| Total received UDP datagrams. |
| `.1.3.6.1.2.1.7.3.0` | `udpInErrors` | Faulty UDP packets. |

---

## 4. Network Analysis

### 4.1 Active IP Interfaces
* `192.168.1.1` (Internal Gateway)
* `127.0.0.1` (Localhost)

### 4.2 ARP Table
Accessible via `.1.3.6.1.2.1.4.22.1.2`. This OID maps IP addresses to physical MAC addresses for all devices in the ARP cache.

### 4.3 Listening Ports
* **UDP 161:** SNMP (Poll interface).
* **UDP 67:** DHCP Server.
* **TCP/UDP 53:** DNS Proxy.

---

## 5. Access the information form the terminal
```
> snmpget -v2c -c 'public' 192.168.1.1 1.3.6.1.2.1.1.1.0
SNMPv2-MIB::sysDescr.0 = STRING: 231.0.19

> snmpget -v2c -c 'public' 192.168.1.1 1.3.6.1.2.1.1.3.0
DISMAN-EVENT-MIB::sysUpTimeInstance = Timeticks: (2228800) 6:11:28.00

> snmpget -v2c -c 'public' 192.168.1.1 1.3.6.1.2.1.1.5.0
SNMPv2-MIB::sysName.0 = STRING: VX231v
```

## 6. Known Limitations
1. **DSL Parameters:** Sync rates and SNR margin return `No Such Instance`.
2. **Resource Monitoring:** CPU and RAM OIDs are unavailable.
3. **Counter Rollover:** 32-bit counters reset at ~4.29 GB (4294967295 bytes).
