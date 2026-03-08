import sqlite3
import re
import base64
from datetime import datetime, timedelta
from io import BytesIO, StringIO


class TPLinkVX231vReport:
    def __init__(self, config, db_path, router=None, debug=False):
        self.config = config
        self.db_path = db_path
        self.router = router
        self.debug = debug

    def _log(self, msg):
        if self.debug:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [Report-Debug] {msg}")

    def _run_query(self, sql, params=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(sql, params or [])
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            data_rows = cursor.fetchall()
            conn.close()
            return columns, [list(r) for r in data_rows]
        except Exception as e:
            self._log(f"SQL-Fehler: {e}")
            return [], []

    def _format_bytes(self, bytes_val):
        try:
            val = float(bytes_val)
        except (ValueError, TypeError):
            return "0 B"
        if val >= 1073741824: return f"{val / 1073741824:.2f} GB"
        if val >= 1048576: return f"{val / 1048576:.2f} MB"
        if val >= 1024: return f"{val / 1024:.2f} KB"
        return f"{val:.0f} Bytes"

    def _get_latest_model_name(self):
        _, rows = self._run_query("SELECT model FROM system ORDER BY time_ut DESC LIMIT 1")
        return rows[0][0] if rows else "Router"

    def _get_latest_firmware_info(self):
        import urllib.request
        url = "https://www.tp-link.com/de/support/download/vx231v/#Firmware"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8', errors='ignore')
            table_match = re.search(r'<table[^>]*class="download-resource-table"[^>]*>(.*?)</table>', content, re.S | re.I)
            if not table_match: return None, None, None, None
            table_content = table_match.group(1)
            title_match = re.search(r'<th[^>]*class="download-resource-name"[^>]*>.*?<p>(.*?)</p>', table_content, re.S | re.I)
            title = title_match.group(1).strip() if title_match else "Unbekannt"
            
            dl_link_match = re.search(r'href="([^"]+\.zip)"', table_content, re.I)
            dl_link = dl_link_match.group(1).strip() if dl_link_match else None
            
            date_match = re.search(r'Datum der Veröffentlichung:.*?</span>\s*<span>(.*?)</span>', table_content, re.S | re.I)
            date_ut = 0
            if date_match:
                try: date_ut = int(datetime.strptime(date_match.group(1).strip(), '%Y-%m-%d').timestamp())
                except: pass
            more_row = re.search(r'<tr[^>]*class="more-info"[^>]*>(.*?)</tr>', table_content, re.S | re.I)
            notes_html = ""
            if more_row:
                td_match = re.search(r'<td[^>]*class="more"[^>]*>(.*?)</td>', more_row.group(1), re.S | re.I)
                if td_match: notes_html = td_match.group(1).strip()
            return title, date_ut, notes_html, dl_link
        except Exception as e:
            self._log(f"Firmware-Scraping fehlgeschlagen: {e}")
            return None, None, None, None

    def _check_firmware_update(self):
        rn_title, rn_date, rn_txt, dl_link = self._get_latest_firmware_info()
        _, rows = self._run_query("SELECT firmware, time_ut FROM system ORDER BY id DESC LIMIT 2")
        if not rows or len(rows) < 1: 
            return False, None, None, None, None, None
            
        act_fw, act_ts = rows[0][0], int(rows[0][1])
        old_fw = rows[1][0] if len(rows) > 1 else None
        old_ts = int(rows[1][1]) if len(rows) > 1 else 0
        
        def extract_version_tuple(fw_str, fallback_str=None):
            if not fw_str: return (0,)
            import re
            
            # Check online standard structure: e.g. VX231v(DE)v1_0.23.0_...
            # The version is between the first and second underscore.
            m = re.search(r'^[^_]+_([^_]+)_', fw_str)
            if m:
                ver_str = m.group(1)
                parts = [int(p) for p in ver_str.split('.') if p.isdigit()]
                while len(parts) > 2 and parts[-1] == 0:
                    parts.pop()
                if parts:
                    return tuple(parts)
            
            # Check local standard structure: e.g. 231.0.23 / 231.0.19
            if fw_str.startswith('231.') or fw_str.startswith('0.'):
                m = re.search(r'^\d+\.((\d+\.)*\d+)', fw_str)
                if m:
                    parts = [int(p) for p in m.group(1).split('.') if p.isdigit()]
                    while len(parts) > 2 and parts[-1] == 0:
                        parts.pop()
                    if parts:
                        return tuple(parts)
                        
            # Use fallback (rn_title) if parsing the link failed but it's an online check
            if fallback_str:
                m = re.search(r'_V?[\d\.]+_((\d+\.)+\d+)', fallback_str)
                if m:
                    parts = [int(p) for p in m.group(1).split('.') if p.isdigit()]
                    while len(parts) > 2 and parts[-1] == 0:
                        parts.pop()
                    if parts:
                        return tuple(parts)
                
            return (0,)

        act_v = extract_version_tuple(act_fw)
        filename = dl_link.split('/')[-1] if dl_link else ""
        web_v = extract_version_tuple(filename, fallback_str=rn_title)
        
        if act_v < web_v and web_v != (0,):
            return True, old_fw, act_fw, rn_title, rn_date, rn_txt
            
        if act_v == web_v and web_v != (0,):
            cutoff = (datetime.now() - timedelta(hours=48)).timestamp()
            if old_ts > cutoff:
                return True, old_fw, act_fw, rn_title, rn_date, rn_txt
                
        return False, old_fw, act_fw, rn_title, rn_date, rn_txt

    def _build_client_sessions(self, hours=24):
        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp())
        sql = "SELECT time_ut, type, event_text FROM events WHERE time_ut >= ? AND type IN ('Mesh', 'DHCPD') ORDER BY time_ut ASC"
        _, rows = self._run_query(sql, params=[start_ts])

        def extract_mac(text):
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
            return None

        router_ip = self.config.get('Router', 'routerip', fallback='192.168.1.1')
        parts = router_ip.split('.')
        home_subnet = f"{parts[0]}.{parts[1]}.{parts[2]}." if len(parts) == 4 else "192.168.1."

        def detect_network_type(text):
            m = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', text)
            if m:
                ip = m.group(1)
                return 'home' if ip.startswith(home_subnet) else 'guest'
            return None

        current_time = datetime.now().timestamp()
        
        # PHASE 1: DHCP Correlation (DISCOVER -> OFFER)
        mac_network_assignments = {}
        pending_discovers = {} 
        pending_offers = {} 

        for r in rows:
            ts = int(r[0])
            text = r[2]
            event_type = r[1]

            if event_type == 'DHCPD':
                if 'Recv DISCOVER from' in text:
                    mac = extract_mac(text)
                    if mac:
                        if mac not in pending_discovers:
                            pending_discovers[mac] = []
                        pending_discovers[mac].append(ts)
                elif 'Send OFFER with ip' in text or 'Send ACK to' in text:
                    net_type = detect_network_type(text)
                    if net_type:
                        if net_type not in pending_offers:
                            pending_offers[net_type] = []
                        pending_offers[net_type].append(ts)

        TIME_WINDOW = 10 
        for mac, discover_times in pending_discovers.items():
            for disc_ts in discover_times:
                for net_type, offer_times in pending_offers.items():
                    for offer_ts in offer_times:
                        if abs(offer_ts - disc_ts) <= TIME_WINDOW:
                            if mac not in mac_network_assignments:
                                mac_network_assignments[mac] = []
                            mac_network_assignments[mac].append((disc_ts, net_type))
                            break

        # PHASE 2: Session Builder
        client_activity = {}
        for r in rows:
            ts = int(r[0])
            text = r[2]
            mac = extract_mac(text)
            if not mac: continue

            if mac not in client_activity:
                client_activity[mac] = []

            is_start = "Add Client" in text or "REQUEST" in text or "DISCOVER" in text
            is_end = "Del Client" in text
            sessions = client_activity[mac]

            if is_start:
                if not sessions or sessions[-1]['end'] is not None:
                    network = 'home'
                    if mac in mac_network_assignments:
                        closest = None
                        min_diff = float('inf')
                        for assign_ts, net in mac_network_assignments[mac]:
                            diff = abs(ts - assign_ts)
                            if diff <= TIME_WINDOW and diff < min_diff:
                                min_diff = diff
                                closest = net
                        if closest:
                            network = closest
                    sessions.append({'start': ts, 'end': None, 'network': network})
            elif is_end:
                if sessions and sessions[-1]['end'] is None:
                    sessions[-1]['end'] = ts

        for mac, sessions in client_activity.items():
            if sessions and sessions[-1]['end'] is None:
                sessions[-1]['end'] = current_time

        return client_activity

    def _get_connected_clients(self):
        client_activity = self._build_client_sessions(hours=24)
        current_time = datetime.now().timestamp()

        # Active calculation
        active_macs = set()
        for mac, sessions in client_activity.items():
            if not sessions: continue
            last_end = sessions[-1]['end']
            if current_time - last_end <= 300:
                active_macs.add(mac)

        router_ip = self.config.get('Router', 'routerip', fallback='192.168.1.1')
        parts = router_ip.split('.')
        home_subnet = f"{parts[0]}.{parts[1]}.{parts[2]}.%" if len(parts) == 4 else "192.168.1.%"

        sql_home = "SELECT hostname, ip, type, lan_port, mac FROM clients WHERE ip LIKE ?"
        _, home_rows = self._run_query(sql_home, [home_subnet])
        sql_guest = "SELECT hostname, ip, type, lan_port, mac FROM clients WHERE ip NOT LIKE ? AND ip IS NOT NULL AND ip != ''"
        _, guest_rows = self._run_query(sql_guest, [home_subnet])

        def ip_sort_key(ip_str):
            if not ip_str: return (0,0,0,0)
            try:
                return tuple(int(x) for x in ip_str.split('.'))
            except:
                return (0,0,0,0)

        home_rows.sort(key=lambda x: ip_sort_key(x[1]))
        guest_rows.sort(key=lambda x: ip_sort_key(x[1]))

        home_active = [r for r in home_rows if r[4] and r[4].upper() in active_macs]
        guest_active = [r for r in guest_rows if r[4] and r[4].upper() in active_macs]
        
        return {'home': home_active, 'guest': guest_active}

    def _get_data_volume_clients(self):
        sql = "SELECT hostname, ip, (bytes_received + bytes_sent) as total_bytes, bytes_sent, bytes_received FROM clients WHERE bytes_received > 0 OR bytes_sent > 0 ORDER BY total_bytes DESC"
        _, rows = self._run_query(sql)
        return rows

    def _get_events(self, hours=24, exclude_types=None, show_level=4):
        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp())
        params = [start_ts]
        exclude_clause = ""
        
        if show_level == 8:
            if exclude_types:
                exclude_clause = f"AND type NOT IN ({','.join('?' for _ in exclude_types)})"
                params.extend(exclude_types)
        else:
            if exclude_types:
                # Zeige Events, die NICHT in exclude_types stehen ODER die ein Fehler/Warnung (<= 4) sind.
                # UND zeige generell nur Events, die <= show_level sind.
                exclude_clause = f"AND (type NOT IN ({','.join('?' for _ in exclude_types)}) OR level_id <= 4) AND level_id <= ?"
                params.extend(exclude_types)
                params.append(show_level)
            else:
                exclude_clause = "AND level_id <= ?"
                params.append(show_level)
            
        sql = f"SELECT time_ut, type, event_text, level_id FROM events WHERE time_ut >= ? {exclude_clause} ORDER BY time_ut DESC"
        _, rows = self._run_query(sql, params)
        return [[datetime.fromtimestamp(int(r[0])).strftime('%d.%m.%y %H:%M:%S'), f"{r[3]} {r[1]}", r[2]] for r in rows]

    def _get_connection_status(self):
        # Verbunden seit: neuester erfolgreicher PPP-Connect
        sql_evt = "SELECT time_ut FROM events WHERE type = 'PPP' AND event_text LIKE '%PAP AuthAck%' ORDER BY time_ut DESC LIMIT 1"
        _, r_evt = self._run_query(sql_evt)
        sql_dsl = "SELECT ip4_curr, ip6_curr, downstream_curr_rate, upstream_curr_rate FROM dsl ORDER BY time_ut DESC LIMIT 1"
        _, r_dsl = self._run_query(sql_dsl)
        conn_since = datetime.fromtimestamp(int(r_evt[0][0])) if r_evt else None
        ip4, ip6, down, up = (r_dsl[0][0], r_dsl[0][1], r_dsl[0][2], r_dsl[0][3]) if r_dsl else (None, None, None, None)
        return conn_since, ip4, ip6, down, up

    def _get_ip_changes(self, limit=2):
        sql = """
              WITH ValidLogs AS (SELECT id, ip4_curr, ip6_curr, time_ut \
                                 FROM dsl \
                                 WHERE (ip4_curr IS NOT NULL AND ip4_curr != '') \
                                    OR (ip6_curr IS NOT NULL AND ip6_curr != '')),
                   CalcChanges AS (SELECT id, \
                                          ip4_curr, \
                                          ip6_curr, \
                                          time_ut, \
                                          LAG(ip4_curr) OVER (ORDER BY id) AS ip4_prev, LAG(ip6_curr) OVER (ORDER BY id) AS ip6_prev \
                                   FROM ValidLogs)
              SELECT time_ut, \
                     ip4_curr, \
                     ip6_curr
              FROM CalcChanges
              WHERE ip4_curr IS NOT ip4_prev \
                 OR ip6_curr IS NOT ip6_prev
              ORDER BY id DESC LIMIT ? \
              """
        _, rows = self._run_query(sql, [limit])
        return [
            [
                int(r[0]),
                datetime.fromtimestamp(int(r[0])).strftime('%d.%m.%y %H:%M:%S'),
                r[1],
                r[2]
            ]
            for r in rows
        ]

    def _analyze_ppp_events(self, hours=24):
        main_query = """
        WITH RawData AS (
            SELECT time_ut, datetime(time_ut, 'unixepoch', 'localtime') AS ts, 
                   strftime('%H:%M', datetime(time_ut, 'unixepoch', 'localtime')) AS clock, 
                   date(time_ut, 'unixepoch', 'localtime') AS d_date, event_text,
            CASE 
                WHEN event_text LIKE '%User request%' THEN 1 
                WHEN event_text LIKE '%LCP down%' THEN 2 
                WHEN event_text LIKE '%AuthAck%' THEN 3 
                ELSE 4 
            END as p
            FROM events 
            WHERE type = 'PPP' AND (event_text LIKE '%User request%' OR event_text LIKE '%LCP down%' OR event_text LIKE '%AuthAck%')
        ),
        Deduplicated AS (
            SELECT * FROM (SELECT *, ROW_NUMBER() OVER(PARTITION BY time_ut ORDER BY p) as rn FROM RawData) WHERE rn = 1
        ),
        Schedules AS (
            SELECT clock, COUNT(DISTINCT d_date) as freq FROM Deduplicated 
            WHERE event_text LIKE '%User request%' GROUP BY clock HAVING freq >= 2
        )
        SELECT d.ts, d.time_ut, d.event_text,
            CASE 
                WHEN d.event_text LIKE '%AuthAck%' THEN 'UP'
                WHEN d.event_text LIKE '%User request%' AND s.clock IS NOT NULL THEN 'ROUTER_SCHED'
                WHEN d.event_text LIKE '%User request%' THEN 'MANUAL'
                WHEN d.event_text LIKE '%LCP down%' THEN 'PROVIDER_DROP'
            END AS category
        FROM Deduplicated d LEFT JOIN Schedules s ON d.clock = s.clock
        WHERE category IS NOT NULL ORDER BY d.time_ut ASC;
        """
        try:
            _, rows = self._run_query(main_query)
        except Exception as e:
            self._log(f"Fehler in _analyze_ppp_events: {e}")
            return []

        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp())
        
        processed_events = []
        last_disconnect = None
        for r in rows:
            ts, time_ut, text, cat = r
            if cat in ['ROUTER_SCHED', 'MANUAL', 'PROVIDER_DROP']:
                last_disconnect = {'ts': ts, 'time_ut': time_ut, 'category': cat}
            elif cat == 'UP' and last_disconnect:
                duration = time_ut - last_disconnect['time_ut']
                processed_events.append({
                    'disconnect_ut': last_disconnect['time_ut'],
                    'disconnect_ts': last_disconnect['ts'],
                    'category': last_disconnect['category'],
                    'duration': duration,
                    'up_ut': time_ut,
                    'up_ts': ts
                })
                last_disconnect = None
                
        return [e for e in processed_events if e['up_ut'] >= start_ts or e['disconnect_ut'] >= start_ts]

    def _get_connection_analysis(self, hours=24):
        threshold_slow_reconnect = 45
        events = self._analyze_ppp_events(hours)
        min_level = self.config.getint('Analyse', 'report_disconnects_level', fallback=1)
        
        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp())
        start_ts_dsl = int((datetime.now() - timedelta(hours=hours + 2)).timestamp())

        try:
            _, pado_rows = self._run_query("SELECT COUNT(*) FROM events WHERE event_text LIKE '%PADO Timeout%' AND time_ut >= ?", [start_ts])
            pado_count = pado_rows[0][0] if pado_rows else 0

            _, dns_rows = self._run_query("SELECT datetime(time_ut, 'unixepoch', 'localtime') as ts FROM events WHERE type = 'Httpd' AND event_text LIKE '%failed%' AND time_ut >= ?", [start_ts])
            dns_errors = [r[0] for r in dns_rows]
            
            _, dsl_rows = self._run_query(
                "SELECT time_ut, downstream_noise_margin, downstream_curr_rate, dcrc FROM dsl WHERE time_ut >= ? ORDER BY time_ut ASC", 
                [start_ts_dsl]
            )
        except Exception:
            pado_count = 0
            dns_errors = []
            dsl_rows = []
        
        html_output = ""
        has_issues = False
        recs_list = []
        
        if pado_count > 10:
            recs_list.append(f"<li><span style='color: #d32f2f; font-weight: bold;'>Warnung:</span> {pado_count} PADO-Timeouts (Schwere Discovery-Störung). IPv6/RFC 4638 prüfen oder Provider-Störung melden.</li>")
            if min_level <= 3:
                has_issues = True
            
        event_html = ""
        for evt in events:
            trigger = evt['category']
            duration = evt['duration']
            ts = evt['disconnect_ts']
            
            severity = 0
            if trigger == 'PROVIDER_DROP':
                severity = 1
            
            trigger_labels = {
                'ROUTER_SCHED': 'Geplanter Neustart (Zeitplan)',
                'MANUAL': 'Benutzer / System Reset',
                'PROVIDER_DROP': 'Trennungsanforderung (ISP)'
            }
            trigger_lbl = trigger_labels.get(trigger, trigger)
            
            recommendations = []
            if duration > threshold_slow_reconnect:
                recommendations.append("Verzögerter Reconnect (Ggfs. Sync-Verlust)")
                severity = max(severity, 2)
            if trigger == 'PROVIDER_DROP':
                recommendations.append("Ungeplante Provider-Trennung")
            
            if any(ts[:16] == d[:16] or evt['up_ts'][:16] == d[:16] for d in dns_errors):
                recommendations.append("DNS-Auflösungsfehler im Zeitfenster")
                severity = max(severity, 2)
                
            # DSL Korrelation
            closest_before = None
            closest_after = None
            for row in dsl_rows:
                dsl_ut = row[0]
                if dsl_ut <= evt['disconnect_ut']:
                    closest_before = row
                if dsl_ut >= evt['up_ut'] and closest_after is None:
                    closest_after = row
                    
            if closest_before:
                dsl_snr_before = closest_before[1]
                dsl_rate_before = closest_before[2]
                dsl_crc_before = closest_before[3]
                
                # SNR Check
                if isinstance(dsl_snr_before, (int, float)) and dsl_snr_before > 0 and dsl_snr_before < 6.0:
                    recommendations.append(f"Signalstörung vor Abbruch (SNR fiel auf {dsl_snr_before} dB)")
                    severity = max(severity, 3)
                    
                # CRC Burst Check
                idx = dsl_rows.index(closest_before)
                if idx > 0:
                    prev_row = dsl_rows[idx - 1]
                    prev_crc = prev_row[3]
                    if isinstance(dsl_crc_before, (int, float)) and isinstance(prev_crc, (int, float)):
                        crc_diff = dsl_crc_before - prev_crc
                        if crc_diff > 1000:
                            recommendations.append(f"Massiver CRC-Fehler-Burst vor Trennung (+{int(crc_diff)} Fehler)")
                            severity = max(severity, 3)
                            
                # Rate Check (Bandbreitenverlust nach Reconnect)
                if closest_after:
                    dsl_rate_after = closest_after[2]
                    if isinstance(dsl_rate_before, (int, float)) and isinstance(dsl_rate_after, (int, float)):
                        if dsl_rate_before > 0 and dsl_rate_after > 0:
                            if dsl_rate_after < (dsl_rate_before * 0.9):
                                diff_mbps = (dsl_rate_before - dsl_rate_after) / 1000.0
                                recommendations.append(f"Profil-Rückfall! Mit {diff_mbps:.1f} Mbit/s weniger Download neu verbunden")
                                severity = max(severity, 2)
            
            if severity >= min_level:
                rec_str = " | <span style='color: #ed6c02; font-weight: bold;'>HINWEIS:</span> " + ", ".join(recommendations) if recommendations else ""
                
                if recommendations:
                    has_issues = True
                    event_html += f"<div style='margin-bottom: 5px;'>[{ts}] {trigger_lbl} | Dauer: {duration}s{rec_str}</div>"
                else:
                    event_html += f"<div style='margin-bottom: 5px; color: #555;'>[{ts}] {trigger_lbl} | Dauer: {duration}s</div>"

        if not has_issues and not event_html:
            if min_level > 0:
                html_output += "<p style='color: #555; text-align: center; font-style: italic; margin-top: 10px;'>Keine Verbindungsabbrüche auf diesem Schweregrad (Level " + str(min_level) + ") im Auswertungszeitraum gefunden.</p>"
            return html_output
            html_output = "<div style='color: #388e3c;'>Die Leitungswerte sind im Analysezeitraum unauffällig. Keine signifikanten Störungen erkannt.</div>"
        else:
            if recs_list:
                html_output += "<ul style='margin-top: 0; margin-bottom: 10px; padding-left: 20px;'>" + "".join(recs_list) + "</ul>"
            if event_html:
                html_output += f"<div style='font-family: monospace; font-size: 13px; background-color: #f5f5f5; padding: 10px; border-radius: 3px; border: 1px solid #e0e0e0;'>{event_html}</div>"

        return html_output

    def _generate_timeline(self, hours=24):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        """
        Generiert einen kompakten, visuellen Zeitstrahl für die letzten 24 Stunden.
        Markiert nur relevante Ereignisse (Internet weg/da, Systemfehler, DSL Sync).
        Gibt Base64-String des Bildes zurück oder None, wenn keine relevanten Events vorliegen.
        """
        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp())

        sql = "SELECT time_ut, type, event_text FROM events WHERE time_ut >= ? ORDER BY time_ut ASC"
        _, rows = self._run_query(sql, params=[start_ts])

        if not rows:
            return None

        ppp_events = self._analyze_ppp_events(hours)
        ppp_evt_map = {e['disconnect_ut']: e for e in ppp_events}

        timeline_events = []

        # Keywords für Kategorisierung
        # (Priorität: Rot > Gelb > Grün)
        for r in rows:
            try:
                ts = int(r[0])
                evt_type = r[1]
                text = r[2]
                dt = datetime.fromtimestamp(ts)

                category = None
                color = None
                marker = None
                label = None
                duration_text = None

                if ts in ppp_evt_map:
                    evt = ppp_evt_map[ts]
                    cat = evt['category']
                    if cat == 'ROUTER_SCHED':
                        color = '#8e24aa'
                        marker = 's'
                        label = 'Zeitplan'
                    elif cat == 'MANUAL':
                        color = '#ff9800'
                        marker = 'D'
                        label = 'Manuell'
                    elif cat == 'PROVIDER_DROP':
                        color = '#d32f2f'
                        marker = 'x'
                        label = 'Provider'
                    
                    category = "Down"
                    duration_text = f"{evt['duration']}s"

                if not category:
                    # 1. DISCONNECTS / FEHLER (ROT)
                    if "LCP down" in text or "DSL Link Status is DOWN" in text or "User request" in text:
                        category = "Down"
                        color = "#d32f2f"  # Rot
                        marker = "x"
                        label = "Down"
                    # 2. SYNC / WARNUNG (GELB)
                    elif "Initializing" in text or "EstablishingLink" in text or "dns disconnected" in text:
                        category = "Sync"
                        color = "#fbc02d"  # Gelb/Orange
                        marker = "o"
                        label = "Sync"
                    # 3. CONNECT / OK (GRÜN - Optional, gut für Feedback "Wieder da")
                    elif "DSL Link Status is UP" in text or ("ConfAck" in text and "addr" in text):
                        category = "Up"
                        color = "#388e3c"  # Grün
                        marker = "|"
                        label = "Up"
                    # System Reboots (Kritisch)
                    elif evt_type == "System" and "Log" not in text:
                        pass

                if category:
                    timeline_events.append({
                        'dt': dt,
                        'color': color,
                        'marker': marker,
                        'label': label,
                        'duration_text': duration_text
                    })

            except:
                continue

        if not timeline_events:
            pass

        # --- PLOTTING ---
        fig, ax = plt.subplots(figsize=(10, 1.2))  # Breite 10, Höhe 1.2 Zoll

        # X-Achse Limits (letzte hours Stunden)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        ax.set_xlim(start_time, end_time)

        # Basis-Linie (Zeitstrahl)
        ax.axhline(y=0, color='#9e9e9e', linewidth=2, zorder=1)

        # Events zeichnen
        # x (Zeit) und c (Farbe) für Scatter Plot
        for evt in timeline_events:
            ax.scatter(evt['dt'], 0, color=evt['color'], marker=evt['marker'], s=100, zorder=2, label=evt['label'])
            if evt.get('duration_text'):
                ax.annotate(evt['duration_text'], (evt['dt'], 0), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=8, color=evt['color'], rotation=0)

        # Formatierung
        ax.set_ylim(-0.5, 0.5)  # Vertikal fixiert
        ax.get_yaxis().set_visible(False)  # Keine Y-Achse

        # X-Achse formatieren
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))  # Alle 3 Stunden ein Tick
        plt.xticks(fontsize=9, color='#666')

        # Rahmen entfernen
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_visible(False)  # Linie macht axhline

        # Legende
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            ax.legend(by_label.values(), by_label.keys(), loc='center left', bbox_to_anchor=(1, 0.5), frameon=False,
                      fontsize=8)

        plt.tight_layout()

        # Base64
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', transparent=False)
        buf.seek(0)
        img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)

        return img_str

    def debug_print_timeline_data(self):
        """
        Numerische Auflistung der Reconnect-Blöcke für die Fehlerdiagnose.
        """
        evt_hours = self.config.getint('Events', 'hours_back', fallback=24)
        start_ts = int((datetime.now() - timedelta(hours=evt_hours)).timestamp())
        end_ts = int(datetime.now().timestamp())

        start_str = datetime.fromtimestamp(start_ts).strftime('%d.%m.%Y %H:%M')
        end_str = datetime.fromtimestamp(end_ts).strftime('%d.%m.%Y %H:%M')

        sql = """
              SELECT time_ut, type, event_text
              FROM events
              WHERE time_ut >= ?
                AND type NOT IN ('Mesh', 'DHCPD')
              ORDER BY time_ut ASC
              """
        _, rows = self._run_query(sql, [start_ts])

        reconnects = []
        current_reconnect = None

        for r in rows:
            ts, typ, txt = int(r[0]), r[1], r[2]
            is_down = "User request" in txt or any(
                k in txt for k in ["LCP down", "DSL Link Status is DOWN", "TermReq", "Timeout waiting for PADO"])
            is_up = "DSL Link Status is UP" in txt or ("ConfAck" in txt and "addr" in txt) or "PAP AuthAck" in txt

            if is_down:
                if current_reconnect is None:
                    current_reconnect = {
                        'type': 'User-indiziert' if "User request" in txt else 'ISP-indiziert',
                        'events': []
                    }

            if current_reconnect is not None:
                current_reconnect['events'].append((ts, typ, txt))
                if is_up:
                    reconnects.append(current_reconnect)
                    current_reconnect = None

        print(f"\nEventübersicht von {start_str} bis {end_str}")
        print(f"es wurden {len(reconnects)} Reconnects identifiziert\n")

        for i, rec in enumerate(reconnects, 1):
            print(f"{i}. Reconnect {rec['type']}-Block")
            for ts_val, typ_val, txt_val in rec['events']:
                ts_str = datetime.fromtimestamp(ts_val).strftime('%d.%m. %H:%M:%S')
                print(f"{ts_str} {typ_val:<8} {txt_val}")
            print("-" * 40)

    def _generate_client_gantt(self, hours=24):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        client_activity = self._build_client_sessions(hours=hours)

        # Namen aus clients-Tabelle
        try:
            _, c_rows = self._run_query("SELECT mac, hostname FROM clients")
            mac_to_name = {r[0].upper(): r[1] for r in c_rows if r[0] and r[1]}
        except:
            mac_to_name = {}

        current_time = datetime.now().timestamp()
        
        active_clients = {k: v for k, v in client_activity.items() if v}
        if not active_clients:
            return None

        # Helper to get formatted name
        def get_formatted_name(m):
            name = mac_to_name.get(m, m).strip()
            if len(name) > 13:
                name = name[:8] + "…" + name[-4:]
            return name

        # Sortieren alphabetisch nach Name, rückwärts, damit Matplotlib A-Z von oben nach unten zeichnet
        def sort_key(m):
            return get_formatted_name(m).lower()

        sorted_macs = sorted(active_clients.keys(), key=sort_key, reverse=True)

        # Plotting
        fig_height = max(4, len(sorted_macs) * 0.4)
        fig, ax = plt.subplots(figsize=(10, fig_height))

        y_ticks = []
        y_labels = []

        COLOR_HOME = '#4acbd6'
        COLOR_GUEST = '#ff9800'

        for i, mac in enumerate(sorted_macs):
            sessions = active_clients[mac]

            client_label = get_formatted_name(mac)

            y_ticks.append(i)
            y_labels.append(client_label)

            for sess in sessions:
                start = datetime.fromtimestamp(sess['start'])
                end = datetime.fromtimestamp(sess['end'])
                duration = (end - start).total_seconds()

                if duration <= 0:
                    continue

                net = sess.get('network', 'home')
                bar_color = COLOR_GUEST if net == 'guest' else COLOR_HOME

                ax.barh(i, end - start, left=start, height=0.6,
                        color=bar_color, alpha=0.7, edgecolor=bar_color)

        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels, fontsize=9)
        ax.tick_params(axis='y', which='both', length=0)

        end_dt = datetime.fromtimestamp(current_time)
        start_dt = end_dt - timedelta(hours=hours)
        ax.set_xlim(start_dt, end_dt)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.grid(True, axis='x', linestyle='--', alpha=0.5)

        # 00:00 Uhr Linie durchgehend, aber im exakt gleichen Stil (Dicke/Farbe/Transparenz) wie das Grid
        for tick_date in mdates.HourLocator(interval=1).tick_values(start_dt, end_dt):
            dt = mdates.num2date(tick_date)
            if dt.hour == 0 and dt.minute == 0:
                ax.axvline(x=dt, color='#b0b0b0', linestyle='-', linewidth=0.8, alpha=0.5, zorder=1)

        ax.set_title(f"Türkis=Heimnetz, Orange=Gastnetz", fontsize=10, pad=10)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)

        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)

        return img_str

    def _generate_charts(self, hours=24):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        charts = []
        for i in range(1, 5):
            table = self.config.get('Charts', f'table_{i}', fallback=None)
            field = self.config.get('Charts', f'field_{i}', fallback=None)
            label = self.config.get('Charts', f'label_{i}', fallback=field)
            if not table or not field: continue
            start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp())
            _, rows = self._run_query(f"SELECT time_ut, {field} FROM {table} WHERE time_ut >= ? ORDER BY time_ut", [start_ts])
            if not rows: continue
            ts, vs = [], []
            for r in rows:
                try:
                    v = float(r[1])
                    if v != 0:
                        ts.append(datetime.fromtimestamp(int(r[0])))
                        vs.append(v)
                except: continue
            if not vs: continue
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.plot(ts, vs, color='#4acbd6', linewidth=2, marker='o', markerfacecolor='#93365e', markeredgecolor='#93365e', markersize=6)
            ax.fill_between(ts, vs, min(vs)-0.1, color='#4acbd6', alpha=0.1)
            ax.grid(True, linestyle='--', linewidth=0.5, color='#ddd')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.\n%H:%M'))
            plt.tight_layout()
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            charts.append((label, base64.b64encode(buf.getvalue()).decode('utf-8')))
            plt.close(fig)
        return charts

    def _run_ai_analysis(self, hours=48):
        import csv
        import subprocess
        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp())
        cols, rows = self._run_query("SELECT datetime(time_ut, 'unixepoch', 'localtime'), downstream_curr_rate, downstream_noise_margin, dcrc FROM dsl WHERE time_ut >= ? ORDER BY time_ut ASC", [start_ts])
        if not rows: return None
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(cols)
        writer.writerows(rows)
        exclude = [t.strip() for t in self.config.get('Events', 'exclude_types', fallback='').split(',') if t.strip()]
        filtered_events = self._get_events(hours=48, exclude_types=exclude)
        events_as_text = ", ".join(str(event) for event in filtered_events)
        prompt = """Du bist ein Senior-Diagnostiker für Breitbandtechnik. Deine Aufgabe ist eine Anomalie-Erkennung, kein Statusreport.
        Analyse-Vorgabe: Betrachte die übergebenen DSL-Daten als Gesamtsystem. Ignoriere Einzelaspekte (wie die 3-Uhr-Trennung),
        sofern sie nicht in Kombination mit anderen Werten auf eine instabile Leitung hindeuten.
        Ausgabe-Regeln:        
        Relevanz-Filter: Antworte nur, wenn die Datenlage eine technische Verschlechterung oder ein drohendes Problem nahelegt.
        Wenn alles stabil ist, antworte ausschließlich mit: 'Verbindung ist stabil.'
        Synthese-Pflicht: Fasse deine Erkenntnisse in maximal zwei bis drei Sätzen als Fließtext zusammen.
        Verbotsliste: Keine Aufzählungen, keine Wiederholung von Rohdaten, keine Kommentare zu Routine-Events oder fehlenden Updates.
        Fokus: Benenne nur das 'Warum' der Störung (z.B. 'Kombination aus sinkendem SNR und steigenden Fehlern deutet auf Leitungsstörung hin').
        TOP PRIO!!! Prüfe, ob Du tatsächlich maximal drei Sätze verwendet hast, sonst erneut bearbeiten!

        CSV Daten:
        """ + output.getvalue() + events_as_text
        try:
            res = subprocess.run(["shortcuts", "run", "ai-cloud"], input=prompt.encode('utf-8'), capture_output=True, timeout=60)
            return res.stdout.decode('utf-8', errors='ignore').strip()
        except: return None

    def _get_reconnect_stats(self, hours):
        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp())
        sql = "SELECT time_ut, type, event_text FROM events WHERE time_ut >= ? AND type NOT IN ('Mesh', 'DHCPD') ORDER BY time_ut ASC"
        _, rows = self._run_query(sql, [start_ts])
        reconnects = 0
        current_reconnect = None
        for r in rows:
            ts, typ, txt = int(r[0]), r[1], r[2]
            is_down = "User request" in txt or any(
                k in txt for k in ["LCP down", "DSL Link Status is DOWN", "TermReq", "Timeout waiting for PADO"])
            is_up = "DSL Link Status is UP" in txt or ("ConfAck" in txt and "addr" in txt) or "PAP AuthAck" in txt

            if is_down:
                if current_reconnect is None:
                    current_reconnect = True
            if current_reconnect:
                if is_up:
                    reconnects += 1
                    current_reconnect = None
        return reconnects

    def _get_router_uptime(self):
        if self.router:
            is_telnet, is_snmp = self.router.check_services()
            if is_snmp:
                return self.router.get_snmp_uptime()
        return None

    def generate_report(self, send_email=True, show_browser=False):
        import smtplib
        from email.mime.image import MIMEImage
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        import tempfile
        import webbrowser
        import os

        self._log("Generiere Report...")
        if self.debug:
            self.debug_print_timeline_data()
        model_name = self._get_latest_model_name()
        date_str = datetime.now().strftime('%d.%m.%Y')
        hours_back = self.config.getint('Charts', 'hours_back', fallback=24)
        evt_hours = self.config.getint('Events', 'hours_back', fallback=24)
        exclude = [t.strip() for t in self.config.get('Events', 'exclude_types', fallback='').split(',') if t.strip()]
        conn_since, ip4, ip6, down, up = self._get_connection_status()
        uptime_data = self._get_router_uptime()
        latest_ips = self._get_ip_changes(3)
        fw_upd, fw_old, fw_act, rn_t, rn_d, rn_txt = self._check_firmware_update()
        ai_text = self._run_ai_analysis(evt_hours)
        conn_analysis_html = self._get_connection_analysis(evt_hours)
        timeline = self._generate_timeline(evt_hours)
        gantt = self._generate_client_gantt(evt_hours)
        clients = self._get_connected_clients()
        traffic = self._get_data_volume_clients()
        charts = self._generate_charts(hours_back)
        show_level = self.config.getint('Events', 'show_level', fallback=4)
        events = self._get_events(24, exclude, show_level)
        
        msg_root = MIMEMultipart('mixed')
        msg_root['Subject'] = f"Tägliche {model_name} Verbindungsübersicht vom {date_str}"
        msg_root['From'] = self.config.get('Email', 'sender_email')
        msg_root['To'] = self.config.get('Email', 'recipient_email')
        msg_rel = MIMEMultipart('related')
        msg_root.attach(msg_rel)
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
        <body style="color: #000000; background-color: #f0eee6; font-family: Arial, Helvetica, sans-serif;">
            <table width="100%" align="center" style="border:solid 2px #eeeeee; border-collapse: collapse; max-width: 800px; background: white;">
                <tr><td width="100%" align="center" style="background-color: #4acbd6; font-size: 18pt; color: white; padding: 15px;">
                    Täglicher {model_name} Statusreport<br><span style="font-size: 12pt;">vom {date_str}</span>
                </td></tr>"""

        if conn_since or ip4 or ip6:
            s_since = conn_since.strftime('%d.%m.%Y %H:%M') if conn_since else "unbekannt"
            
            time_diff_str = ""
            if conn_since:
                diff = datetime.now() - conn_since
                total_seconds = int(diff.total_seconds())
                hours_since = total_seconds // 3600
                minutes_since = (total_seconds % 3600) // 60
                time_diff_str = f" ({hours_since} Stunden {minutes_since} Minuten)"
                
            s_down = f"{float(down)/1000:.1f}".replace('.', ',') + " Mbit/s" if down else "n/a"
            s_up = f"{float(up)/1000:.1f}".replace('.', ',') + " Mbit/s" if up else "n/a"
            
            ipv4_str = f"IPv4 {ip4}" if ip4 else "IPv4 unbekannt"
            ipv6_str = f"IPv6 {ip6}" if ip6 else "IPv6 unbekannt"
            
            html += f"<tr><td style='padding: 20px; font-size: 13px; color: #333;'>Verbunden seit {s_since}{time_diff_str}<br>Aktuelle {ipv4_str}<br>Aktuelle {ipv6_str}<br>Datenrate Down {s_down} Up {s_up}."
            
            if uptime_data:
                u_days, u_hours = uptime_data
                html += f"<br><br>Firmware: {fw_act} Letzter Routerneustart vor {u_days} Tagen {u_hours} Stunden"
                
            html += "</td></tr>"
            
        if fw_upd:
            rn_ds = datetime.fromtimestamp(rn_d).strftime('%d.%m.%Y') if rn_d else "Unbekannt"
            html += f"""<tr><td style="padding: 20px;"><div style="border: 2px solid #ff9800; background-color: #fff3e0; padding: 15px; border-radius: 5px;">
                <h3 style="margin-top: 0; color: #e65100;">Firmware Hinweis</h3><div style="font-size: 14px; color: #333;">
                Aktuell installiert <span style="color: #2e7d32; font-weight: bold;">{fw_act}</span><br>
                Online verfügbar: <strong>{rn_t}</strong><br>
                <div style="border-top: 1px solid #ffcc80; margin-top: 10px; padding-top: 10px;"><strong>Release Notes ({rn_ds}):</strong><br>{rn_txt}</div></div></div></td></tr>"""
        if ai_text:
            html += f"<tr><td style='padding: 20px;'><div style='border: 2px solid #4acbd6; background-color: #f9ffff; padding: 15px; border-radius: 5px;'><h3 style='margin-top: 0; color: #008ba3;'>Auf einen Blick</h3><div style='font-size: 14px; color: #333;'>{ai_text}</div></div></td></tr>"
        if conn_analysis_html:
            padding_top = "0px" if ai_text else "20px"
            html += f"<tr><td style='padding: 20px; padding-top: {padding_top};'><div style='border: 1px solid #b0bec5; background-color: #fcfcfc; padding: 15px; border-radius: 5px;'><h3 style='margin-top: 0; color: #455a64;'>Leitungsanalyse</h3><div style='font-size: 14px; color: #333;'>{conn_analysis_html}</div></div></td></tr>"
        if timeline:
            img_src = "cid:timeline_img" if send_email else f"data:image/png;base64,{timeline}"
            html += f"<tr><td style='padding: 0 20px 20px 20px;'><div style='border: 1px solid #ddd; background-color: #fff; padding: 10px; border-radius: 5px;'><div style='font-size: 12px; font-weight: bold; color: #666;'>Eventübersicht</div><img src='{img_src}' style='width: 100%; max-width: 700px;'></div></td></tr>"
        if gantt:
            img_src = "cid:gantt_img" if send_email else f"data:image/png;base64,{gantt}"
            html += f"<tr><td style='padding: 10px 20px;'><table width='100%'><tr><td style='background-color: #4acbd6; color: white; padding: 5px;'>Anwesenheit</td></tr><tr><td><img src='{img_src}' style='width: 100%; max-width: 700px;'></td></tr></table></td></tr>"
        if clients['home']:
            html += "<tr><td style='padding: 10px 20px;'><table width='100%' style='border-collapse: collapse;'><tr><td style='background-color: #4acbd6; color: white; padding: 5px;'>Heimnetzübersicht aktuell aktiver Clients</td></tr><tr><td><table width='100%' style='font-size: 13px;'>"
            for i, c in enumerate(clients['home']):
                bg = "#ffffff" if i % 2 == 0 else "#f9f9f9"
                typ = f"LAN {c[3]}" if str(c[2]).lower() == 'lan' and c[3] != 0 else c[2]
                html += f"<tr style='background-color: {bg};'><td>{c[0]}</td><td style='color: #666;'>{c[1]}</td><td>{typ}</td></tr>"
            html += "</table></td></tr></table></td></tr>"
        
        # if traffic:
        #     html += "<tr><td style='padding: 10px 20px;'><table width='100%' style='border-collapse: collapse;'><tr><td style='background-color: #4acbd6; color: white; padding: 5px;'>Datenvolumen nach Clients</td></tr><tr><td><table width='100%' style='font-size: 12px; text-align: right;'><tr style='background-color: #f7f7f5;'><th style='text-align: left;'>Gerät</th><th>Gesamt</th><th>Up</th><th>Down</th></tr>"
        #     for i, c in enumerate(traffic):
        #         bg = "#ffffff" if i % 2 == 0 else "#f9f9f9"
        #         html += f"<tr style='background-color: {bg};'><td style='text-align: left;'><b>{c[0]}</b></td><td>{self._format_bytes(c[2])}</td><td>{self._format_bytes(c[3])}</td><td>{self._format_bytes(c[4])}</td></tr>"
        #     html += "</table></td></tr></table></td></tr>"
        
        for idx, (lbl, chart_data) in enumerate(charts):
            img_src = f"cid:chart_{idx}" if send_email else f"data:image/png;base64,{chart_data}"
            html += f"<tr><td style='padding: 10px 20px;'><table width='100%'><tr><td style='background-color: #4acbd6; color: white; padding: 5px;'>{lbl}</td></tr><tr><td style='text-align: center;'><img src='{img_src}' style='width: 100%; max-width: 700px;'></td></tr></table></td></tr>"
            
        do_reconnects = self.config.getboolean('Statistics', 'reconnects', fallback=False)
        do_pado = self.config.getboolean('Statistics', 'PADO_timeouts', fallback=False)
        
        if do_reconnects or do_pado:
            stat_html = ""
            start_ts_all = int((datetime.now() - timedelta(hours=evt_hours)).timestamp())
            start_ts_24 = int((datetime.now() - timedelta(hours=24)).timestamp())

            if do_reconnects:
                count_rec_all = self._get_reconnect_stats(evt_hours)
                stat_html += f"<b>Anzahl der Reconnects im Zeitraum ({evt_hours}h):</b> {count_rec_all}<br>"
                
                if evt_hours > 24:
                    count_rec_24 = self._get_reconnect_stats(24)
                    stat_html += f"<b>Anzahl der Reconnects in den letzten 24h:</b> {count_rec_24}<br>"

            if do_pado:
                sql_pado = "SELECT COUNT(*) FROM events WHERE event_text LIKE '%Timeout waiting for PADO%' AND time_ut >= ?"
                _, rows_pado_all = self._run_query(sql_pado, [start_ts_all])
                count_pado_all = rows_pado_all[0][0] if rows_pado_all else 0
                stat_html += f"<b>Anzahl der PADO_timeouts im Zeitraum ({evt_hours}h):</b> {count_pado_all}<br>"
                
                if evt_hours > 24:
                    _, rows_pado_24 = self._run_query(sql_pado, [start_ts_24])
                    count_pado_24 = rows_pado_24[0][0] if rows_pado_24 else 0
                    stat_html += f"<b>Anzahl der PADO_timeouts in den letzten 24h:</b> {count_pado_24}<br>"

            if stat_html:
                html += f"<tr><td style='padding: 10px 20px;'><table width='100%'><tr><td style='background-color: #4acbd6; color: white; padding: 5px;'>Statistiken</td></tr><tr><td style='padding: 10px; font-size: 13px; color: #333;'>{stat_html}</td></tr></table></td></tr>"

        if events:
            html += "<tr><td style='padding: 10px 20px;'><table width='100%'><tr><td style='background-color: #4acbd6; color: white; padding: 5px;'>Ereignislog (letzte 24h)</td></tr><tr><td><table width='100%' style='font-size: 11px; color: #555;'>"
            for i, e in enumerate(events):
                bg = "#ffffff" if i % 2 == 0 else "#f9f9f9"
                html += f"<tr style='background-color: {bg};'><td width='140'>{e[0]}</td><td width='80'>{e[1]}</td><td>{e[2]}</td></tr>"
            
            # Legend for log levels
            html += "<tr><td colspan='3' style='padding-top: 5px; font-size: 10px; color: #888; text-align: center; border-top: 1px solid #eee;'>"
            html += "0 Notfall &bull; 1 Alarm &bull; 2 Kritisch &bull; 3 Fehler &bull; 4 Vorsicht &bull; 5 Hinweis &bull; 6 Info &bull; 7 Debug"
            html += "</td></tr>"
            
            html += "</table></td></tr></table></td></tr>"
        html += "</table><p style='padding: 20px; text-align: center; font-size: 10pt; color: #999;'>Automatisch generiert und ohne Unterschrift gültig</p></body></html>"
        
        try:
            os.makedirs('reports', exist_ok=True)
            timestamp = datetime.now().strftime('%y%m%d_%H%M')
            filename = f"vx-report_{timestamp}.html"
            rel_path = os.path.join('reports', filename)
            with open(rel_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"Der Bericht wurde generiert und liegt unter {rel_path}")
            
            self._cleanup_old_reports()

            
            if show_browser:
                try:
                    abs_path = os.path.abspath(rel_path)
                    webbrowser.open('file://' + abs_path)
                    self._log(f"Report im Browser geöffnet: {abs_path}")
                except Exception:
                    pass
        except Exception as e:
            print(f"Fehler beim Erstellen des Reports: {e}")
        
        if send_email:
            msg_rel.attach(MIMEText(html, 'html'))
            if timeline:
                img = MIMEImage(base64.b64decode(timeline))
                img.add_header('Content-ID', '<timeline_img>')
                msg_rel.attach(img)
            if gantt:
                img = MIMEImage(base64.b64decode(gantt))
                img.add_header('Content-ID', '<gantt_img>')
                msg_rel.attach(img)
            for idx, (_, data) in enumerate(charts):
                img = MIMEImage(base64.b64decode(data))
                img.add_header('Content-ID', f'<chart_{idx}>')
                msg_rel.attach(img)
            try:
                srv = smtplib.SMTP(self.config.get('Email', 'smtp_server'), self.config.getint('Email', 'smtp_port'))
                srv.starttls()
                srv.login(self.config.get('Email', 'sender_email'), self.config.get('Email', 'sender_password'))
                srv.send_message(msg_root)
                srv.quit()
                print("E-Mail erfolgreich versendet.")
            except Exception as e:
                print(f"Versandfehler: {e}")

    def _cleanup_old_reports(self):
        import time
        from pathlib import Path
        cleanup_days = self.config.getint('Reports', 'cleanup_reports', fallback=0)
        if cleanup_days > 0:
            reports_dir = Path('reports')
            if reports_dir.exists() and reports_dir.is_dir():
                now = time.time()
                deleted_count = 0
                for f in reports_dir.glob('vx-report*.html'):
                    if f.is_file():
                        file_age_days = (now - f.stat().st_mtime) / (24 * 3600)
                        if file_age_days > cleanup_days:
                            try:
                                f.unlink()
                                deleted_count += 1
                                self._log(f"Gelöschter alter Report: {f.name}")
                            except Exception as e:
                                self._log(f"Fehler beim Löschen des Reports {f.name}: {e}")
                if deleted_count > 0:
                    print(f"Es wurden {deleted_count} alte Report(s) gelöscht (älter als {cleanup_days} Tage).")
