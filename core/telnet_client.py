import re
import socket
import time
from datetime import datetime
from core.database import DatabaseManager


class TPLinkVX231vTelnet:

    def __init__(self, ip, username, password, community, debug=False):
        self.ip = ip
        self.username = username
        self.password = password
        self.community = community
        self.debug = debug
        self.sock = None
        self.prompt_pattern = re.compile(r'TP-Link.*#')

    def check_services(self):
        import subprocess
        telnet_enabled = False
        try:
            with socket.create_connection((self.ip, 23), timeout=2):
                telnet_enabled = True
        except (socket.timeout, ConnectionRefusedError, OSError):
            telnet_enabled = False

        snmp_enabled = False
        cmd = ["snmpget", "-v2c", "-c", self.community, self.ip, "1.3.6.1.2.1.1.1.0"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if proc.returncode == 0:
                snmp_enabled = True
        except (subprocess.TimeoutExpired, Exception):
            snmp_enabled = False

        return telnet_enabled, snmp_enabled

    def _log(self, msg):
        if self.debug:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [Telnet-Debug] {msg}")

    def login(self):
        self._log(f"Verbindung zu {self.ip}...")
        try:
            self.sock = socket.create_connection((self.ip, 23), timeout=10)
            if self._expect_regex(r'password:', timeout=10):
                self.sock.sendall(self.password.encode('ascii') + b"\n")
                if self._expect_regex(self.prompt_pattern, timeout=10):
                    self._log("Login erfolgreich.")
                    return True
            else:
                print("Fehler: Keine Passwort-Abfrage vom Router erhalten. - Anderer Login aktiv?")
            return False
        except Exception as e:
            self._log(f"Login-Fehler: {e}")
            return False

    def _expect_regex(self, pattern, timeout=10):
        start_time = time.time()
        buffer = ""
        while time.time() - start_time < timeout:
            try:
                self.sock.settimeout(1.0)
                data = self.sock.recv(4096).decode('ascii', errors='ignore')
                if data:
                    buffer += data
                    if self.debug: print(f"    [RAW]: {repr(data)}")
                    if (isinstance(pattern, re.Pattern) and pattern.search(buffer)) or \
                            (isinstance(pattern, str) and pattern in buffer):
                        return True
            except socket.timeout:
                continue
        return False

    def _read_until_prompt(self, cmd, timeout=7):
        # Puffer leeren, falls noch Reste vorhanden sind
        self.sock.settimeout(0.1)
        try:
            while self.sock.recv(4096): pass
        except:
            pass

        self.sock.sendall(cmd.encode('ascii') + b"\n")
        start_time = time.time()
        buffer = ""
        while time.time() - start_time < timeout:
            try:
                self.sock.settimeout(1.0)
                data = self.sock.recv(4096).decode('ascii', errors='ignore')
                buffer += data
                # Wir warten explizit auf den Prompt oder den SUCC-Status
                if "cmd:SUCC" in buffer or self.prompt_pattern.search(buffer):
                    break
            except socket.timeout:
                break
        return buffer

    def _parse_block(self, cmd):
        raw = self._read_until_prompt(cmd)
        if self.debug: self._log(f"Parse {cmd}: {raw.strip()}")
        # Findet key=value Paare
        return dict(re.findall(r'(\w+)=([^ \n\r\}]+)', raw))

    def get_system_data(self):
        res = {
            'model': self._parse_block("dev show prodName").get('modelName', 'N/A'),
            'firmware': self._parse_block("dev show prodSoftVer").get('softwareVersion', 'N/A'),
            'hardware': self._parse_block("dev show prodHardVer").get('hardwareVersion', 'N/A'),
            'serial': self._parse_block("dev serial show").get('serialNumber', 'N/A')
        }
        gw_info = self._parse_block("wan show defaultgw")
        service_name = gw_info.get('name')
        if service_name:
            conn_info = self._parse_block(f"wan show connection info {service_name}")
            upt = int(conn_info.get("X_TP_Uptime", 0))
            res.update({'uptime_seconds': upt, 'uptime_days': round(upt / 86400, 1)})
        else:
            self._log("Warnung: Kein Standard-Gateway gefunden.")
            res.update({'uptime_seconds': 0, 'uptime_days': 0.0})
        return res

    def get_dsl_data(self):
        d = self._parse_block("adsl show info")
        dsl_dict = {
            "Aktuelle Upload-Rate (kbit/s)": d.get("upstreamCurrRate", "0"),
            "Aktuelle Download-Rate (kbit/s)": d.get("downstreamCurrRate", "0"),
            "Maximale Upload-Rate (kbit/s)": d.get("upstreamMaxBitRate", "0"),
            "Maximale Download-Rate (kbit/s)": d.get("downstreamMaxBitRate", "0"),
            "Signal-Rausch-Abstand Upload (dB)": str(int(d.get("upstreamNoiseMargin", 0)) / 10),
            "Signal-Rausch-Abstand Download (dB)": str(int(d.get("downstreamNoiseMargin", 0)) / 10),
            "Leitungsdämpfung Upload (dB)": str(int(d.get("upstreamAttenuation", 0)) / 10),
            "Leitungsdämpfung Download (dB)": str(int(d.get("downstreamAttenuation", 0)) / 10),
            "Fehler Upload (Pakete)": "0", "Fehler Download (Pakete)": "0",
            "Sendeleistung Upload (dBm)": str(int(d.get("upstreamPower", 0)) / 10),
            "Sendeleistung Download (dBm)": str(int(d.get("downstreamPower", 0)) / 10),
            "Latenz Upload (ms)": d.get("X_TP_UpstreamDelay", "0"),
            "Latenz Download (ms)": d.get("X_TP_DownstreamDelay", "0"),
            "G.INP Upload": "Ein" if d.get("X_TP_UpstreamGinp") == "1" else "Aus",
            "G.INP Download": "Ein" if d.get("X_TP_DownstreamGinp") == "1" else "Aus",
            "G.Vector Upload": "Ein" if d.get("X_TP_UpstreamGvector") == "1" else "Aus",
            "G.Vector Download": "Ein" if d.get("X_TP_DownstreamGvector") == "1" else "Aus"
        }
        ip4 = self._parse_block("wan show defaultgw").get('connIPv4Gateway', '')
        dsl_dict.update({'ip4_curr': ip4, 'ip6_curr': self._parse_block("lan show info").get('IPv6Address', '')})
        return dsl_dict

    def get_clients(self, db_manager=None):
        import subprocess
        self._log("Starte Client-Erfassung (SNMP)...")
        system_info = self.get_system_data()
        clients_wlan = []
        cmd = ["snmpwalk", "-v2c", "-c", self.community, "-Ox", self.ip, "1.3.6.1.2.1.4.22.1.2"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if proc.returncode == 0:
                for line in proc.stdout.strip().split('\n'):
                    if "=" not in line: continue
                    oid_part, val_part = line.split("=")
                    ip = (re.search(r'(\d+\.\d+\.\d+\.\d+)$', oid_part.strip()) or [None, "Unknown"])[0]
                    mac_raw = re.sub(r'^(Hex-)?STRING:\s*', '', val_part.strip())

                    # Nutzung der statischen Methode zur Normalisierung
                    mac = DatabaseManager._normalize_mac(mac_raw.replace(" ", ":"))

                    if mac and ip:
                        name = db_manager.get_hostname_by_mac(mac) if db_manager else None
                        if not name:
                            try:
                                name = socket.gethostbyaddr(ip)[0]
                            except:
                                name = "Unknown"
                        clients_wlan.append({'mac': mac, 'hostname': name, 'ip': ip, 'is_connected': 1,
                                             'signal_strength': 0, 'wifi_standard': 'SNMP-ARP',
                                             'download_rate_mbps': 0, 'upload_rate_mbps': 0, 'bytes_total': 0})
        except Exception as e:
            self._log(f"SNMP-Fehler: {e}")

        return {'timestamp': time.time(), 'system': system_info, 'wlan': clients_wlan, 'lan': []}

    def downloadrouterlog_to_memory(self):
        return None

    def close(self):
        if self.sock: self.sock.close()
