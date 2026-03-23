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
        self.host = ip
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
            # Wir nutzen die interne _request Methode der Library
            # WICHTIG: Die URL muss über _get_url generiert werden, wie in get_vx_syslog.py
            url = self.router._get_url('cgi/log')
            code, response = self.router._request(url, data_str="", encrypt=True)
            
            if code != 200:
                self._log(f"HTTP-Fehler beim Log-Download: {code}", force=True)
                return None
                
            # Formatierung sicherstellen (wie in playwright_client)
            return re.sub(r"(202\d-)", r"\n\1", response, count=1)
        except Exception as e:
            self._log(f"Fehler beim Log-Download (API): {e}", force=True)
            return None

    def _safe_int(self, value, default=0):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def get_clients(self):
        if not self.router:
            if not self.login():
                return {'error': 'Login fail'}

        try:
            # Holen des Status (enthält bereits die Geräteliste aus DEV2_HOST_ENTRY)
            status = self.router.get_status()
            
            # Holen der Firmware-Infos für System-Details
            # (get_status nutzt DEV2_DEV_INFO nicht für alles, wir nehmen die OIDs direkt)
            acts = [
                self.router.ActItem(self.router.ActItem.GET, 'DEV2_DEV_INFO', attrs=[
                    'modelName', 'softwareVersion', 'hardwareVersion', 'serialNumber', 'upTime'
                ]),
                # WLAN Client Details für Signalstärke etc.
                self.router.ActItem(self.router.ActItem.GL, 'DEV2_ADT_WIFI_CLIENT', attrs=[
                    'MACAddress', 'signalStrength', 'packetsSent', 'packetsReceived', 'band'
                ])
            ]
            _, values = self.router.req_act(acts)
            
            dev_info = values[0]
            wlan_details = {c['MACAddress'].upper(): c for c in self.router._to_list(values[1])}
            
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
            
            # In der EX-Library sind alle Geräte in status.devices (aus DEV2_HOST_ENTRY)
            for device in status.devices:
                mac = DatabaseManager._normalize_mac(str(device._macaddr))
                if not mac: continue
                
                # Unterscheidung LAN/WLAN via Connection Enum
                from tplinkrouterc6u.common.package_enum import Connection
                
                is_wlan = device.type in [Connection.HOST_2G, Connection.HOST_5G, Connection.GUEST_2G, Connection.GUEST_5G]
                
                client_data = {
                    'mac': mac,
                    'hostname': device.hostname,
                    'ip': str(device._ipaddr),
                    'is_connected': 1 # Wenn in HOST_ENTRY aktiv, dann verbunden
                }
                
                if is_wlan:
                    detail = wlan_details.get(mac.upper(), {})
                    client_data.update({
                        'signal_strength': self._safe_int(detail.get('signalStrength', 0), 0),
                        'wifi_standard': '', # API liefert das nicht direkt wie JS
                        'download_rate_mbps': 0, # API liefert das nicht direkt
                        'upload_rate_mbps': 0,
                        'bytes_total': self._safe_int(detail.get('packetsReceived', 0)) * 1000 # Schätzung/Pakete
                    })
                    result['wlan'].append(client_data)
                else:
                    client_data.update({
                        'link_speed_mbps': 0, # API liefert das nicht direkt
                        'bytes_total': 0
                    })
                    result['lan'].append(client_data)
                    
            return result

        except Exception as e:
            return {'error': f'API read failed: {e}'}

    def get_dsl_data(self):
        if not self.router:
            return {}

        try:
            acts = [
                # DSL Leitungswerte
                self.router.ActItem(self.router.ActItem.GET, 'DEV2_DSL_LINE', '1,0,0,0,0,0', attrs=[
                    'upstreamMaxBitRate', 'downstreamMaxBitRate', 
                    'upstreamNoiseMargin', 'downstreamNoiseMargin',
                    'upstreamAttenuation', 'downstreamAttenuation'
                ]),
                # Aktuelle Raten
                self.router.ActItem(self.router.ActItem.GET, 'DEV2_DSL_CHANNEL', '1,0,0,0,0,0', attrs=[
                    'upstreamCurrRate', 'downstreamCurrRate'
                ]),
                # IP Status
                self.router.ActItem(self.router.ActItem.GL, 'DEV2_ADT_WAN', attrs=[
                    'connIPv4Address', 'connIPv6Address', 'connStatusV4', 'connStatusV6'
                ])
            ]
            _, values = self.router.req_act(acts)
            
            line = values[0]
            channel = values[1]
            
            # Aktiven WAN-Port suchen (Index 2 in unserem Test pppoe_ptm_7_0)
            wan = {}
            for w in self.router._to_list(values[2]):
                if w.get('connStatusV4') == 'Connected' or w.get('connStatusV6') == 'Connected':
                    wan = w
                    break
            if not wan and values[2]:
                wan = values[2][0] if isinstance(values[2], list) else values[2]
            
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
