# verwendet die tplinkrouterc6u Library von Alexandr Erohin
# https://github.com/AlexandrErohin/TP-Link-Archer-C6U

import time
import sys
import re
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from macaddress import EUI48
from ipaddress import IPv4Address

try:
    from tplinkrouterc6u.client.ex import TPLinkEXClientGCM
    from tplinkrouterc6u.common.exception import ClientException
except ImportError:
    # Fallback if not installed (though it should be)
    TPLinkEXClientGCM = None
    ClientException = Exception

from core.database import DatabaseManager

class TPLinkVX231vAPI:
    def __init__(self, ip, username, password, debug=False, verify_ssl=False):
        # Die Router-Firmware (Stand Sep 2026) erzwingt HTTPS: über http:// liefert
        # der Router nur die GDPR-/Willkommensseite und der Login scheitert mit
        # "Unknown error rsa_key!". Deshalb hier https:// als Standard
        # (Zertifikat ist selbst signiert, daher verify_ssl standardmäßig False).
        self.host = ip if str(ip).startswith(('http://', 'https://')) else f"https://{ip}"
        self.username = username
        self.password = password
        self.debug = debug
        self.verify_ssl = verify_ssl
        self.router = None
        
        # Logging Setup
        self.logger = logging.getLogger("tplink_api")
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.ERROR)

    def _log(self, msg, force=False):
        if self.debug or force:
            print(msg)

    def login(self):
        self._log(f"\nLogin (API) {self.host}...")
        try:
            if not TPLinkEXClientGCM:
                raise Exception("tplinkrouterc6u library not found.")
            
            # Die API (AES-GCM) verlangt oft 'user' statt 'admin'
            usernames = [self.username]
            if self.username != "user":
                usernames.append("user")
            
            last_err = None
            for test_user in usernames:
                self._log(f"Versuche Login mit Benutzername: '{test_user}' ...")
                try:
                    self.router = TPLinkEXClientGCM(self.host, self.password, test_user, self.logger, verify_ssl=self.verify_ssl)
                    self.router.authorize()
                    self._log(f"✔ Login-Vorgang (API) erfolgreich abgeschlossen (User: '{test_user}').")
                    return True
                except Exception as e:
                    last_err = e
                    self._log(f"  ✘ Fehlgeschlagen für '{test_user}': {e}")
            
            raise last_err
        except Exception as e:
            self._log(f"Login-Fehler (API): {str(e)}", force=True)
            return False

    def downloadrouterlog_to_memory(self):
        if not self.router:
            return None
        try:
            self._log("Starte Log-Download über API...")
            url = self.router._get_url('cgi/log')
            code, response = self.router._request(url, data_str="", encrypt=True)
            
            if code != 200:
                self._log(f"HTTP-Fehler beim Log-Download: {code}", force=True)
                return self._downloadrouterlog_http_fallback()
                
            # Formatierung sicherstellen (wie in playwright_client)
            return re.sub(r"(202\d-)", r"\n\1", response, count=1)
        except Exception as e:
            self._log(f"Verschlüsselter Log-Download fehlgeschlagen ({e}), versuche HTTP-Fallback...", force=True)
            return self._downloadrouterlog_http_fallback()

    def _downloadrouterlog_http_fallback(self):
        """Fallback: Log als Dateidownload über cgi/log?down (wie Playwright, ohne AES-GCM)."""
        try:
            import ssl
            import urllib.request

            base_url = self.router.host  # z.B. https://192.168.1.1
            logurl = f"{base_url}/cgi/log?down"
            self._log(f"HTTP-Fallback: {logurl}")

            # Session-Cookie und Token aus der Library-Session übernehmen
            cookie_str = "; ".join([f"{c.name}={c.value}" for c in self.router.req.cookies])
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/plain,*/*;q=0.8',
                'Referer': base_url,
                'Cookie': cookie_str
            }
            if self.router._token:
                headers['TokenID'] = self.router._token

            context = ssl._create_unverified_context()
            req = urllib.request.Request(logurl, headers=headers)
            with urllib.request.urlopen(req, context=context, timeout=10) as response:
                logcontent = response.read().decode('utf-8')

            if logcontent and len(logcontent) > 20:
                self._log(f"HTTP-Fallback erfolgreich: {len(logcontent)} Zeichen empfangen.")
                return re.sub(r"(202\d-)", r"\n\1", logcontent, count=1)
            else:
                self._log("HTTP-Fallback: Leere oder ungültige Antwort.", force=True)
                return None
        except Exception as e:
            self._log(f"HTTP-Fallback fehlgeschlagen: {e}", force=True)
            return None

    def _safe_int(self, value, default=0):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _act(self, kind, oid, stack=None, attrs=None):
        """Einen einzelnen OID abfragen und dessen Daten zurückgeben (oder None).

        Wichtig: Bei Sammelabfragen entfernt die Library OIDs ohne Daten aus der
        Ergebnisliste, wodurch sich die Positionen der übrigen Werte verschieben.
        Einzelabfragen vermeiden diese Fehlzuordnung.
        """
        try:
            if stack:
                item = self.router.ActItem(kind, oid, stack, attrs=attrs or [])
            else:
                item = self.router.ActItem(kind, oid, attrs=attrs or [])
            _, values = self.router.req_act([item])
            return values[0] if values else None
        except Exception as e:
            self._log(f"OID {oid} konnte nicht gelesen werden: {e}")
            return None

    def get_clients(self):
        if not self.router:
            if not self.login():
                return {'error': 'Login fail'}

        try:
            # Die Firmware ab Build 260908 liefert über DEV2_HOST_ENTRY, DEV2_ADT_LAN und
            # DEV2_ADT_WIFI_CLIENT keine Daten mehr ("data": null) - get_status()
            # scheitert damit. Die Weboberfläche nutzt die APDEV-Associationslisten,
            # die hier direkt abgefragt werden.
            #
            # Achtung: Die Library entfernt OIDs ohne Daten aus der Ergebnisliste einer
            # Sammelabfrage -> dadurch würden sich die Positionen verschieben. Daher
            # wird jeder OID einzeln abgefragt.
            dev_info = self._act(self.router.ActItem.GET, 'DEV2_DEV_INFO', attrs=[
                'modelName', 'softwareVersion', 'hardwareVersion', 'serialNumber', 'upTime'
            ])
            wlan_clients = self.router._to_list(self._act(self.router.ActItem.GL, 'DEV2_WIFI_APDEV_ASSOCDEV'))
            lan_clients = self.router._to_list(self._act(self.router.ActItem.GL, 'DEV2_WIFI_APDEV_ETHASSOCDEV'))
            if not isinstance(dev_info, dict):
                dev_info = {}

            if not dev_info and not wlan_clients and not lan_clients:
                self._log("Router lieferte keine Client-/Systemdaten (OIDs leer).", force=True)

            uptime = self._safe_int(dev_info.get('upTime', 0), 0)

            result = {
                'timestamp': time.time(),
                'system': {
                    'model': dev_info.get('modelName', 'N/A'),
                    'firmware': dev_info.get('softwareVersion', 'N/A'),
                    'hardware': dev_info.get('hardwareVersion', 'N/A'),
                    'serial': dev_info.get('serialNumber', 'N/A'),
                    'uptime_seconds': uptime,
                    'uptime_days': round(uptime / 86400, 1) if uptime > 0 else 0.0
                },
                'wlan': [],
                'lan': []
            }

            # Feldnamen wie in der Weboberfläche (playwright_client)
            for c in wlan_clients:
                mac = DatabaseManager._normalize_mac(str(c.get('MACAddress', '')))
                if not mac:
                    continue
                result['wlan'].append({
                    'mac': mac,
                    'hostname': c.get('X_TP_HostName', ''),
                    'ip': c.get('X_TP_IPAddress', ''),
                    'is_connected': 1 if str(c.get('active', '1')) == '1' else 0,
                    'signal_strength': self._safe_int(c.get('signalStrength', 0), 0),
                    'wifi_standard': c.get('operatingStandard', ''),
                    'download_rate_mbps': self._safe_int(c.get('lastDataDownlinkRate', 0), 0) // 1000,
                    'upload_rate_mbps': self._safe_int(c.get('lastDataUplinkRate', 0), 0) // 1000,
                    'bytes_total': 0  # liefert die API nicht
                })

            for c in lan_clients:
                mac = DatabaseManager._normalize_mac(str(c.get('MACAddress', '')))
                if not mac:
                    continue
                # Nur LAN-Clients liefern echte Byte-Zähler (die Firmware füllt bei
                # WLAN-Clients bytesReceived/bytesSent nicht). Achtung: 32-Bit-Zähler
                # (wie SNMP Counter32) -> nur Momentaufnahme, keine Deltas bilden.
                rx = self._safe_int(c.get('bytesReceived', 0), 0)
                tx = self._safe_int(c.get('bytesSent', 0), 0)
                result['lan'].append({
                    'mac': mac,
                    'hostname': c.get('X_TP_HostName', ''),
                    'ip': c.get('IPAddress', ''),
                    'is_connected': 1 if str(c.get('active', '1')) == '1' else 0,
                    'link_speed_mbps': self._safe_int(c.get('linkSpeed', 0), 0),
                    'bytes_received': rx,
                    'bytes_sent': tx,
                    'bytes_total': rx + tx
                })

            return result

        except Exception as e:
            return {'error': f'API read failed: {e}'}

    def get_dsl_data(self):
        if not self.router:
            return {}

        try:
            # Einzelabfragen: siehe _act() - Sammelabfragen verschieben bei leeren
            # OIDs die Ergebnisliste.
            line = self._act(self.router.ActItem.GET, 'DEV2_DSL_LINE', '1,0,0,0,0,0', attrs=[
                'upstreamMaxBitRate', 'downstreamMaxBitRate',
                'upstreamNoiseMargin', 'downstreamNoiseMargin',
                'upstreamAttenuation', 'downstreamAttenuation'
            ])
            channel = self._act(self.router.ActItem.GET, 'DEV2_DSL_CHANNEL', '1,0,0,0,0,0', attrs=[
                'upstreamCurrRate', 'downstreamCurrRate'
            ])
            wan_values = self._act(self.router.ActItem.GL, 'DEV2_ADT_WAN', attrs=[
                'connIPv4Address', 'connIPv6Address', 'connStatusV4', 'connStatusV6'
            ])

            # Einzelne OIDs können leer zurückkommen (Router-/Firmwarezustand) ->
            # dann lieber {} zurückgeben als mit AttributeError abzubrechen.
            line = line if isinstance(line, dict) else {}
            channel = channel if isinstance(channel, dict) else {}
            if not line and not channel:
                self._log("DSL-OIDs (DEV2_DSL_LINE/DEV2_DSL_CHANNEL) lieferten keine Daten.", force=True)
                return {}

            # Aktiven WAN-Port suchen (Index 2 in unserem Test pppoe_ptm_7_0)
            wan = {}
            for w in self.router._to_list(wan_values):
                if w.get('connStatusV4') == 'Connected' or w.get('connStatusV6') == 'Connected':
                    wan = w
                    break
            if not wan and wan_values:
                wan = wan_values[0] if isinstance(wan_values, list) else wan_values
            
            # Mapping der DSL-Werte
            # Hinweis: Wenn CurrRate 0 ist, nutzen wir MaxBitRate als Fallback für 'Aktuelle'
            up_curr = self._safe_int(channel.get('upstreamCurrRate', 0))
            down_curr = self._safe_int(channel.get('downstreamCurrRate', 0))
            up_max = self._safe_int(line.get('upstreamMaxBitRate', 0))
            down_max = self._safe_int(line.get('downstreamMaxBitRate', 0))
            
            return {
                "Aktuelle Upload-Rate (kbit/s)": str(up_curr if up_curr > 0 else up_max),
                "Aktuelle Download-Rate (kbit/s)": str(down_curr if down_curr > 0 else down_max),
                "Maximale Upload-Rate (kbit/s)": str(up_max),
                "Maximale Download-Rate (kbit/s)": str(down_max),
                "Signal-Rausch-Abstand Upload (dB)": str(int(line.get('upstreamNoiseMargin', 0)) / 10),
                "Signal-Rausch-Abstand Download (dB)": str(int(line.get('downstreamNoiseMargin', 0)) / 10),
                "Leitungsdämpfung Upload (dB)": str(int(line.get('upstreamAttenuation', 0)) / 10),
                "Leitungsdämpfung Download (dB)": str(int(line.get('downstreamAttenuation', 0)) / 10),
                "ip4_curr": wan.get('connIPv4Address', ''),
                "ip6_curr": wan.get('connIPv6Address', '')
            }
        except Exception as e:
            self._log(f"Fehler beim Abrufen der DSL-Daten (API): {e}", force=True)
            return {}

    def reconnect_wan(self, wait_time=5):
        if not self.router:
            if not self.login(): return False
            
        try:
            self._log("Starte Reconnect über API...")
            acts = [
                self.router.ActItem(self.router.ActItem.CGI, "/cgi/wan/reconn")
            ]
            self.router.req_act(acts)
            self._log(f"Reconnect-Kommando gesendet. Warte {wait_time} Sekunden...")
            time.sleep(wait_time)
            return True
        except Exception as e:
            self._log(f"Fehler beim Reconnect (API): {e}", force=True)
            return False

    def close(self):
        if self.router:
            try:
                self._log("Führe Logout (API) aus...")
                self.router.logout()
                self._log("Erfolgreich abgemeldet (API).")
            except:
                pass
            self.router = None

    def get_all_router_data(self) -> dict:
        """
        Ruft alle per tplinkrouterc6u verfügbaren Routerparameter ab.
        Nicht unterstützte Endpunkte werden mit {'error': '...'} markiert.
        Gibt ein Dict mit allen Parametern und deren Werten zurück.
        """
        if not self.router:
            if not self.login():
                return {'error': 'Login fehlgeschlagen'}

        results = {}

        # --- 1. get_firmware ---
        try:
            fw = self.router.get_firmware()
            results['firmware'] = {
                'hardware_version': fw.hardware_version,
                'model':            fw.model,
                'firmware_version': fw.firmware_version,
            }
        except Exception as e:
            results['firmware'] = {'error': str(e)}

        # --- 2. get_status ---
        try:
            st = self.router.get_status()
            results['status'] = {
                'wan_macaddr':           st.wan_macaddr,
                'lan_macaddr':           st.lan_macaddr,
                'wan_ipv4_addr':         st.wan_ipv4_addr,
                'lan_ipv4_addr':         st.lan_ipv4_addr,
                'wan_ipv4_gateway':      st.wan_ipv4_gateway,
                'wired_total':           st.wired_total,
                'wifi_clients_total':    st.wifi_clients_total,
                'guest_clients_total':   st.guest_clients_total,
                'clients_total':         st.clients_total,
                'iot_clients_total':     st.iot_clients_total,
                'guest_2g_enable':       st.guest_2g_enable,
                'guest_5g_enable':       st.guest_5g_enable,
                'guest_6g_enable':       st.guest_6g_enable,
                'iot_2g_enable':         st.iot_2g_enable,
                'iot_5g_enable':         st.iot_5g_enable,
                'iot_6g_enable':         st.iot_6g_enable,
                'wifi_2g_enable':        st.wifi_2g_enable,
                'wifi_5g_enable':        st.wifi_5g_enable,
                'wifi_6g_enable':        st.wifi_6g_enable,
                'wan_ipv4_uptime':       st.wan_ipv4_uptime,
                'mem_usage':             st.mem_usage,
                'cpu_usage':             st.cpu_usage,
                'conn_type':             st.conn_type,
                'devices': [
                    {
                        'type':             str(d.type),
                        'macaddr':          d.macaddr,
                        'ipaddr':           d.ipaddr,
                        'hostname':         d.hostname,
                        'packets_sent':     d.packets_sent,
                        'packets_received': d.packets_received,
                        'down_speed':       d.down_speed,
                        'up_speed':         d.up_speed,
                        'signal':           d.signal,
                        'active':           d.active,
                    }
                    for d in st.devices
                ],
            }
        except Exception as e:
            results['status'] = {'error': str(e)}

        # --- 3. get_ipv4_status ---
        try:
            ipv4 = self.router.get_ipv4_status()
            results['ipv4_status'] = {
                'wan_macaddr':           ipv4.wan_macaddr,
                'wan_ipv4_ipaddr':       ipv4.wan_ipv4_ipaddr,
                'wan_ipv4_gateway':      ipv4.wan_ipv4_gateway,
                'wan_ipv4_conntype':     ipv4.wan_ipv4_conntype,
                'wan_ipv4_netmask':      ipv4.wan_ipv4_netmask,
                'wan_ipv4_pridns':       ipv4.wan_ipv4_pridns,
                'wan_ipv4_snddns':       ipv4.wan_ipv4_snddns,
                'lan_macaddr':           ipv4.lan_macaddr,
                'lan_ipv4_ipaddr':       ipv4.lan_ipv4_ipaddr,
                'lan_ipv4_dhcp_enable':  ipv4.lan_ipv4_dhcp_enable,
                'lan_ipv4_netmask':      ipv4.lan_ipv4_netmask,
                'remote':                ipv4.remote,
            }
        except Exception as e:
            results['ipv4_status'] = {'error': str(e)}

        # --- 4. get_ipv4_reservations ---
        try:
            reservations = self.router.get_ipv4_reservations()
            results['ipv4_reservations'] = [
                {
                    'macaddr':  r.macaddr,
                    'ipaddr':   r.ipaddr,
                    'hostname': r.hostname,
                    'enabled':  r.enabled,
                }
                for r in reservations
            ]
        except Exception as e:
            results['ipv4_reservations'] = {'error': str(e)}

        # --- 5. get_ipv4_dhcp_leases ---
        try:
            leases = self.router.get_ipv4_dhcp_leases()
            results['ipv4_dhcp_leases'] = [
                {
                    'macaddr':    l.macaddr,
                    'ipaddr':     l.ipaddr,
                    'hostname':   l.hostname,
                    'lease_time': l.lease_time,
                }
                for l in leases
            ]
        except Exception as e:
            results['ipv4_dhcp_leases'] = {'error': str(e)}

        # --- 6. get_vpn_status ---
        try:
            vpn = self.router.get_vpn_status()
            results['vpn_status'] = {
                'openvpn_enable':        vpn.openvpn_enable,
                'pptpvpn_enable':        vpn.pptpvpn_enable,
                'openvpn_clients_total': vpn.openvpn_clients_total,
                'pptpvpn_clients_total': vpn.pptpvpn_clients_total,
            }
        except Exception as e:
            results['vpn_status'] = {'error': str(e)}

        # --- 7. get_lte_status (nur LTE-Router) ---
        try:
            lte = self.router.get_lte_status()
            results['lte_status'] = {
                'enable':            lte.enable,
                'connect_status':    lte.connect_status,
                'network_type':      lte.network_type,
                'sim_status':        lte.sim_status,
                'total_statistics':  lte.total_statistics,
                'cur_rx_speed':      lte.cur_rx_speed,
                'cur_tx_speed':      lte.cur_tx_speed,
                'sms_unread_count':  lte.sms_unread_count,
                'sig_level':         lte.sig_level,
                'rsrp':              lte.rsrp,
                'rsrq':              lte.rsrq,
                'snr':               lte.snr,
                'isp_name':          lte.isp_name,
            }
        except Exception as e:
            results['lte_status'] = {'error': str(e)}

        # --- 8. get_sms (nur LTE-Router) ---
        try:
            sms_list = self.router.get_sms()
            results['sms'] = [
                {
                    'id':          s.id,
                    'sender':      s.sender,
                    'content':     s.content,
                    'received_at': str(s.received_at),
                    'unread':      s.unread,
                }
                for s in sms_list
            ]
        except Exception as e:
            results['sms'] = {'error': str(e)}

        results['_timestamp'] = time.time()
        return results