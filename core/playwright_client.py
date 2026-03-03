import time
import sys
import re
from datetime import datetime
from pathlib import Path
from core.database import DatabaseManager


class TPLinkVX231vPlaywright:
    def __init__(self, ip, username, password, debug=False):
        self.base_url = f"https://{ip}"
        self.username = username
        self.password = password
        self.debug = debug
        self.playwright = None
        self.browser = None
        self.page = None
        self.screenshot_counter = 1

    def _log(self, msg, force=False):
        if self.debug or force: print(msg)

    def _take_screenshot(self, label):
        if not self.debug or not self.page: return
        Path('screenshots').mkdir(exist_ok=True)
        filename = f"screenshots/{self.screenshot_counter:02d}_{label}.png"
        try:
            self.page.screenshot(path=filename)
            self.screenshot_counter += 1
        except:
            pass

    def _init_browser(self):
        from playwright.sync_api import sync_playwright
        self._log("Initialisiere Browser...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
            '--disable-gpu', '--disable-software-rasterizer', '--disable-extensions'
        ])
        context = self.browser.new_context(ignore_https_errors=True, viewport={'width': 1280, 'height': 800})
        self.page = context.new_page()
        self.page.set_default_timeout(30000)

    def _write_error_file(self, message, playwright_log=""):
        Path('logs').mkdir(exist_ok=True)
        ts = datetime.now()
        fname = f"logs/error_{ts.strftime('%Y%m%d_%H%M')}.txt"

        # Korrektur für --debug: Fehler vor dem Exit auf der Konsole ausgeben
        self._log(f"KRITISCHER FEHLER: {message}", force=True)

        with open(fname, 'w', encoding='utf-8') as f:
            f.write(f"Fehler: TP-Link Monitor - {ts.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{message}\n")
            if playwright_log:
                f.write(f"Call log:\n{playwright_log}\n")
            f.write("\nLogin fehlgeschlagen!")
        sys.exit(1)

    def login(self):
        if not self.page: self._init_browser()
        try:
            self._log(f"\nLogin {self.base_url}...")
            self.page.goto(self.base_url, wait_until='domcontentloaded')

            self._log("Eingabe der Anmeldedaten...")
            self.page.evaluate(f"document.getElementById('pc-login-user').value = '{self.username}';")
            self.page.evaluate(f"document.getElementById('pc-login-password').value = '{self.password}';")

            self._log("Klicke Login-Button...")
            self.page.evaluate("const btn = document.getElementById('pc-login-btn'); if(btn) btn.click();")

            # Kurze Pause für die Verarbeitung des Logins
            time.sleep(2)

            # Popup-Handling gemäß Referenz-Skript (Text-basiert)
            popup_active = self.page.evaluate("""() => {
                return document.body && document.body.innerText && 
                       document.body.innerText.toLowerCase().includes('gleichzeitig anmelden');
            }""")

            if popup_active:
                self._log("Popup 'Gleichzeitig anmelden' erkannt und bestätigt.")
                self.page.evaluate("document.querySelector('.btn-msg-ok')?.click();")
                time.sleep(1)

            self._log("Login-Vorgang abgeschlossen.")
            return True

        except Exception as e:
            msg = f"Login-Fehler: {str(e)}"
            self._write_error_file(msg, f"URL: {self.base_url}")
            return False

    def downloadrouterlog_to_memory(self):
        import ssl
        import urllib.request
        import urllib.error
        if not self.page: return None
        try:
            logurl = f"{self.base_url}/cgi/log?down"
            self._log(f"Starte Log-Download von: {logurl}")

            # Cookies für den Header formatieren
            cookies = self.page.context.cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/plain,*/*;q=0.8',
                'Referer': self.base_url,
                'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
                'Cookie': cookie_str
            }

            # SSL-Verifizierung deaktivieren (entspricht verify=False)
            context = ssl._create_unverified_context()

            req = urllib.request.Request(logurl, headers=headers)

            with urllib.request.urlopen(req, context=context, timeout=10) as response:
                if self.debug:
                    self._log(f"HTTP-Status: {response.status}")

                logcontent = response.read().decode('utf-8')

            # Formatierung sicherstellen
            return re.sub(r"(202\d-)", r"\n\1", logcontent, count=1)

        except urllib.error.HTTPError as e:
            if e.code == 406:
                self._write_error_file("HTTP 406: Zugriff auf Logs verweigert (Header/Session ungültig).")
            self._log(f"HTTP-Fehler beim Log-Download: {e.code} {e.reason}", force=True)
            return None
        except Exception as e:
            self._log(f"Fehler beim Log-Download: {e}", force=True)
            return None

    def trigger_netzplan(self):
        if not self.page:
            return
        self.page.evaluate("""() => {
            const nodes = Array.from(document.querySelectorAll('li, a, span.text'));
            const target = nodes.find(el =>
                el && el.innerText && el.innerText.trim().toLowerCase() === 'netzplan'
            );
            if (target) target.click();
        }""")

    def _wait_for_js_variables(self, timeout_ms=12000):
        if not self.page:
            return False
        start = time.time()
        while (time.time() - start) * 1000 < timeout_ms:
            ready = self.page.evaluate("""() => {
                const dev = window.easyMeshApDeviceList;
                const wlan = window.easyMeshApWifiStaList;
                const lan = window.easyMeshApEthernetStaList;
                return (Array.isArray(dev) && dev.length > 0) ||
                       (Array.isArray(wlan) && wlan.length > 0) ||
                       (Array.isArray(lan) && lan.length > 0);
            }""")
            if ready:
                return True
            time.sleep(0.5)
        return False

    def _safe_int(self, value, default=0):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _is_connected(self, client):
        disassoc = self._safe_int(client.get('X_TP_DisassociationTime', 0), 0)
        if disassoc == 0:
            return True
        assoc = client.get('associationTime', '')
        try:
            return datetime.fromisoformat(assoc).timestamp() > disassoc
        except Exception:
            return False

    def _parse_bytes(self, text):
        if not text:
            return 0
        digits = []
        for ch in str(text):
            if ch.isdigit():
                digits.append(ch)
        return int("".join(digits)) if digits else 0

    def _extract_mac(self, text):
        s = (text or "").upper().replace("-", ":")
        allowed = "0123456789ABCDEF:"
        tokens = []
        cur = []
        for ch in s:
            if ch in allowed:
                cur.append(ch)
            else:
                if cur:
                    tokens.append("".join(cur))
                    cur = []
        if cur:
            tokens.append("".join(cur))

        for tok in tokens:
            parts = tok.split(":")
            if len(parts) == 6 and all(len(p) == 2 and all(c in "0123456789ABCDEF" for c in p) for p in parts):
                return ":".join(parts)
        return ""

    def get_all_client_traffic(self):
        if not self.page:
            return {}
        try:
            self.page.locator("ul#ul-nav li").filter(has_text="Erweiterte Einstellungen").first.click()
            time.sleep(0.8)
            self.page.locator("li a").filter(has_text="System").first.click()
            time.sleep(0.8)
            self.page.locator("li a").filter(has_text="Datenverkehr").first.click()
            time.sleep(1.2)
        except Exception:
            return {}

        traffic = {}
        try:
            rows = self.page.locator("table tbody tr")
            total = rows.count()
            for i in range(total):
                cols = rows.nth(i).locator("td")
                if cols.count() < 3:
                    continue
                text0 = cols.nth(0).inner_text()
                text1 = cols.nth(1).inner_text()
                mac = self._extract_mac(f"{text0} {text1}")
                if not mac:
                    continue
                traffic[mac] = self._parse_bytes(cols.nth(2).inner_text())
        except Exception:
            return {}

        return traffic

    def get_clients(self):
        if not self.page and not self.login():
            return {'error': 'Login fail'}
        try:
            self.trigger_netzplan()
            self._wait_for_js_variables()
            data = self.page.evaluate("""() => ({
                wlan_clients: window.easyMeshApWifiStaList || [],
                lan_clients: window.easyMeshApEthernetStaList || [],
                router: (window.easyMeshApDeviceList && window.easyMeshApDeviceList.length > 0)
                    ? window.easyMeshApDeviceList[0] : {}
            })""")
        except Exception as e:
            return {'error': f'GUI JS read failed: {e}'}

        traffic_stats = self.get_all_client_traffic()
        router_info = data.get('router', {}) if isinstance(data, dict) else {}
        uptime = self._safe_int(router_info.get('X_TP_UpTime', 0), 0)

        result = {
            'timestamp': time.time(),
            'system': {
                'model': router_info.get('X_TP_ModelName', 'N/A'),
                'firmware': router_info.get('softwareVersion', 'N/A'),
                'hardware': router_info.get('hardwareVersion', 'N/A'),
                'serial': router_info.get('serialNumber', 'N/A'),
                'uptime_seconds': uptime,
                'uptime_days': round(uptime / 86400, 1) if uptime > 0 else 0.0
            },
            'wlan': [],
            'lan': []
        }

        for c in data.get('wlan_clients', []) if isinstance(data, dict) else []:
            mac = DatabaseManager._normalize_mac(c.get('MACAddress', ''))
            if not mac:
                continue
            result['wlan'].append({
                'mac': mac,
                'hostname': c.get('X_TP_HostName', ''),
                'ip': c.get('X_TP_IPAddress', ''),
                'signal_strength': self._safe_int(c.get('signalStrength', 0), 0),
                'wifi_standard': c.get('operatingStandard', ''),
                'is_connected': 1 if self._is_connected(c) else 0,
                'download_rate_mbps': self._safe_int(c.get('lastDataDownlinkRate', 0), 0) // 1000,
                'upload_rate_mbps': self._safe_int(c.get('lastDataUplinkRate', 0), 0) // 1000,
                'bytes_total': traffic_stats.get(mac, 0)
            })

        for c in data.get('lan_clients', []) if isinstance(data, dict) else []:
            mac = DatabaseManager._normalize_mac(c.get('MACAddress', ''))
            if not mac:
                continue
            result['lan'].append({
                'mac': mac,
                'hostname': c.get('X_TP_HostName', ''),
                'ip': c.get('IPAddress', ''),
                'is_connected': 1 if self._is_connected(c) else 0,
                'link_speed_mbps': self._safe_int(c.get('linkSpeed', 0), 0),
                'bytes_total': traffic_stats.get(mac, 0)
            })
        return result

    def get_dsl_data(self):
        if not self.page:
            return {}

        def read_dsl_ids():
            return self.page.evaluate("""() => {
                const ids = {
                    "Aktuelle Upload-Rate (kbit/s)": "upstreamCurrRate",
                    "Aktuelle Download-Rate (kbit/s)": "downstreamCurrRate",
                    "Maximale Upload-Rate (kbit/s)": "upstreamMaxRate",
                    "Maximale Download-Rate (kbit/s)": "downstreamMaxRate",
                    "Signal-Rausch-Abstand Upload (dB)": "upstreamNoiseMargin",
                    "Signal-Rausch-Abstand Download (dB)": "downstreamNoiseMargin",
                    "Leitungsdämpfung Upload (dB)": "upstreamAttenuation",
                    "Leitungsdämpfung Download (dB)": "downstreamAttenuation",
                    "Fehler Upload (Pakete)": "UCRC",
                    "Fehler Download (Pakete)": "DCRC",
                    "Sendeleistung Upload (dBm)": "upstreamTransmitPower",
                    "Sendeleistung Download (dBm)": "downstreamTransmitPower",
                    "Latenz Upload (ms)": "upstreamLatency",
                    "Latenz Download (ms)": "downstreamLatency"
                };
                const out = {};
                for (const [label, id] of Object.entries(ids)) {
                    const el = document.getElementById(id);
                    out[label] = el ? (el.textContent || '').trim() : '';
                }
                const ip4 = document.getElementById('IPV4');
                const ip6 = document.getElementById('IPV6');
                out.ip4_curr = ip4 ? (ip4.value || '').trim() : '';
                out.ip6_curr = ip6 ? (ip6.value || '').trim() : '';
                return out;
            }""")

        try:
            dsl_data = read_dsl_ids()
            has_rates = bool(dsl_data.get("Aktuelle Download-Rate (kbit/s)") or dsl_data.get("Aktuelle Upload-Rate (kbit/s)"))
            if has_rates:
                return dsl_data
            self.page.locator("ul#ul-nav li").filter(has_text="Erweiterte Einstellungen").first.click()
            time.sleep(1.0)
            return read_dsl_ids()
        except Exception:
            return {}

    def close(self):
        """Abmelden über die WebGUI und Browser schließen."""
        try:
            if self.page:
                self._log("Führe Logout aus...")
                try:
                    if self.debug: self._log("DEBUG: Warte bis zu 10s auf Logout-Button (#topLogout)...")
                    self.page.locator('#topLogout').click(timeout=10000)
                    
                    if self.debug: self._log("DEBUG: Warte bis zu 5s auf Bestätigungs-Button (.btn-msg-ok)...")
                    self.page.locator('.btn-msg-ok').click(timeout=5000)
                    
                    self._log("Erfolgreich abgemeldet.")
                except Exception as inner_e:
                    if self.debug: self._log(f"DEBUG: Logout UI-Elemente nicht gefunden (Timeout): {inner_e}")
                    else: self._log("Fehler: Logout UI-Elemente nicht gefunden.")
        except Exception as e:
            self._log(f"Fehler beim Logout: {e}")
            
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()
