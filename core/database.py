import sqlite3
import time
import re
from datetime import datetime
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path="router_data.db"):
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 1. System Daten + Index
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS system
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               time_ut
                               INTEGER,
                               model
                               TEXT,
                               firmware
                               TEXT,
                               hardware
                               TEXT,
                               serial
                               TEXT,
                               uptime_seconds
                               INTEGER,
                               uptime_days
                               REAL
                           )
                           ''')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_time_ut ON system (time_ut)")

            # 2. DSL Daten + Index
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS dsl
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               time_ut
                               INTEGER,
                               upstream_curr_rate
                               INTEGER,
                               downstream_curr_rate
                               INTEGER,
                               upstream_max_rate
                               INTEGER,
                               downstream_max_rate
                               INTEGER,
                               upstream_noise_margin
                               REAL,
                               downstream_noise_margin
                               REAL,
                               upstream_attenuation
                               REAL,
                               downstream_attenuation
                               REAL,
                               ucrc
                               INTEGER,
                               dcrc
                               INTEGER,
                               upstream_tx_power
                               REAL,
                               downstream_tx_power
                               REAL,
                               upstream_latency
                               REAL,
                               downstream_latency
                               REAL,
                               upstream_ginp
                               BOOLEAN,
                               downstream_ginp
                               BOOLEAN,
                               upstream_gvector
                               BOOLEAN,
                               downstream_gvector
                               BOOLEAN,
                               ip4_curr
                               TEXT,
                               ip6_curr
                               TEXT
                           )
                           ''')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dsl_time_ut ON dsl (time_ut)")

            # 3. Clients
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS clients
                           (
                               mac
                               TEXT
                               PRIMARY
                               KEY,
                               time_ut
                               INTEGER,
                               type
                               TEXT,
                               hostname
                               TEXT,
                               ip
                               TEXT,
                               signal_strength
                               INTEGER,
                               wifi_standard
                               TEXT,
                               is_connected
                               BOOLEAN,
                               download_rate_mbps
                               INTEGER,
                               upload_rate_mbps
                               INTEGER,
                               lan_port
                               INTEGER,
                               link_speed_mbps
                               INTEGER,
                               bytes_received
                               INTEGER,
                               bytes_sent
                               INTEGER,
                               bytes_total
                               INTEGER
                           )
                           ''')

            # 4. Events + Index (WICHTIG für Purge)
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS events
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               time_ut
                               INTEGER,
                               level_id
                               INTEGER,
                               type
                               TEXT,
                               event_text
                               TEXT,
                               UNIQUE
                           (
                               time_ut,
                               level_id,
                               type,
                               event_text
                           )
                               )
                           ''')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_time_ut ON events (time_ut)")

    # --- KOMPATIBILITÄTS-METHODE FÜR EXTERNE ABFRAGEN ---
    def _run_query(self, sql, params=None):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params or [])
                if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    conn.commit()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return columns, [list(r) for r in cursor.fetchall()]
        except Exception as e:
            print(f"SQL-Fehler in _run_query: {e}")
            return [], []

    # --- HILFSFUNKTIONEN ---
    def _clean_dsl_value_rate(self, value):
        if not value or value == 'N/A': return 0
        return int(str(value).replace('.', ''))

    def _clean_dsl_value_real(self, value):
        if not value or value == 'N/A': return 0.0
        return float(str(value).replace(',', '.'))

    def _clean_dsl_value_bool(self, value):
        if not value: return False
        return str(value).strip().lower() == 'ein'

    def _clean_lan_port(self, value):
        if not value or value == 'N/A': return 0
        return int(str(value).strip())

    @staticmethod
    def _normalize_mac(mac):
        if not mac: return ""
        parts = mac.replace("-", ":").split(":")
        return ":".join(p.strip().zfill(2).upper() for p in parts)

    def get_hostname_by_mac(self, mac):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT hostname FROM clients WHERE mac = ?", (mac.upper(),))
            row = cursor.fetchone()
            return row[0] if row and row[0] else None

    def insert_system(self, system_data, timestamp):
        current_firmware = system_data.get('firmware', '')
        if not current_firmware or current_firmware == 'N/A':
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, firmware FROM system ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()

            if row and row[1] == current_firmware:
                update_data = {
                    'id': row[0],
                    'time_ut': int(timestamp),
                    'uptime_seconds': int(system_data.get('uptime_seconds', 0)),
                    'uptime_days': float(system_data.get('uptime_days', 0.0))
                }
                cursor.execute('''
                               UPDATE system
                               SET time_ut        = :time_ut,
                                   uptime_seconds = :uptime_seconds,
                                   uptime_days    = :uptime_days
                               WHERE id = :id
                               ''', update_data)
            else:
                insert_data = {
                    'time_ut': int(timestamp),
                    'model': system_data.get('model', ''),
                    'firmware': current_firmware,
                    'hardware': system_data.get('hardware', ''),
                    'serial': system_data.get('serial', ''),
                    'uptime_seconds': int(system_data.get('uptime_seconds', 0)),
                    'uptime_days': float(system_data.get('uptime_days', 0.0))
                }
                cursor.execute('''
                               INSERT INTO system
                               (time_ut, model, firmware, hardware, serial, uptime_seconds, uptime_days)
                               VALUES (:time_ut, :model, :firmware, :hardware, :serial, :uptime_seconds, :uptime_days)
                               ''', insert_data)

    def insert_dsl(self, data, timestamp):
        dsl_dict = {
            'time_ut': int(timestamp),
            'upstream_curr_rate': self._clean_dsl_value_rate(data.get('Aktuelle Upload-Rate (kbit/s)', '')),
            'downstream_curr_rate': self._clean_dsl_value_rate(data.get('Aktuelle Download-Rate (kbit/s)', '')),
            'upstream_max_rate': self._clean_dsl_value_rate(data.get('Maximale Upload-Rate (kbit/s)', '')),
            'downstream_max_rate': self._clean_dsl_value_rate(data.get('Maximale Download-Rate (kbit/s)', '')),
            'upstream_noise_margin': self._clean_dsl_value_real(data.get('Signal-Rausch-Abstand Upload (dB)', '')),
            'downstream_noise_margin': self._clean_dsl_value_real(data.get('Signal-Rausch-Abstand Download (dB)', '')),
            'upstream_attenuation': self._clean_dsl_value_real(data.get('Leitungsdampfung Upload (dB)', '')),
            'downstream_attenuation': self._clean_dsl_value_real(data.get('Leitungsdampfung Download (dB)', '')),
            'ucrc': self._clean_dsl_value_rate(data.get('Fehler Upload (Pakete)', '')),
            'dcrc': self._clean_dsl_value_rate(data.get('Fehler Download (Pakete)', '')),
            'upstream_tx_power': self._clean_dsl_value_real(data.get('Sendeleistung Upload (dBm)', '')),
            'downstream_tx_power': self._clean_dsl_value_real(data.get('Sendeleistung Download (dBm)', '')),
            'upstream_latency': self._clean_dsl_value_real(data.get('Latenz Upload (ms)', '')),
            'downstream_latency': self._clean_dsl_value_real(data.get('Latenz Download (ms)', '')),
            'upstream_ginp': self._clean_dsl_value_bool(data.get('G.INP Upload', '')),
            'downstream_ginp': self._clean_dsl_value_bool(data.get('G.INP Download', '')),
            'upstream_gvector': self._clean_dsl_value_bool(data.get('G.Vector Upload', '')),
            'downstream_gvector': self._clean_dsl_value_bool(data.get('G.Vector Download', '')),
            'ip4_curr': data.get('ip4_curr', ''),
            'ip6_curr': data.get('ip6_curr', '')
        }
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO dsl
                           (time_ut, upstream_curr_rate, downstream_curr_rate, upstream_max_rate,
                            downstream_max_rate, upstream_noise_margin, downstream_noise_margin,
                            upstream_attenuation, downstream_attenuation, ucrc, dcrc,
                            upstream_tx_power, downstream_tx_power, upstream_latency,
                            downstream_latency, upstream_ginp, downstream_ginp,
                            upstream_gvector, downstream_gvector, ip4_curr, ip6_curr)
                           VALUES (:time_ut, :upstream_curr_rate, :downstream_curr_rate, :upstream_max_rate,
                                   :downstream_max_rate, :upstream_noise_margin, :downstream_noise_margin,
                                   :upstream_attenuation, :downstream_attenuation, :ucrc, :dcrc,
                                   :upstream_tx_power, :downstream_tx_power, :upstream_latency,
                                   :downstream_latency, :upstream_ginp, :downstream_ginp,
                                   :upstream_gvector, :downstream_gvector, :ip4_curr, :ip6_curr)
                           ''', dsl_dict)

    def insert_clients(self, clients_data):
        if 'error' in clients_data: return
        timestamp = clients_data.get('timestamp', time.time())
        batch_data = []

        for client_type, clients in [('wlan', clients_data.get('wlan', [])), ('lan', clients_data.get('lan', []))]:
            for c in clients:
                if not c.get('mac'): continue
                batch_data.append({
                    'mac': self._normalize_mac(c.get('mac')),
                    'time_ut': int(timestamp),
                    'type': client_type,
                    'hostname': c.get('hostname', ''),
                    'ip': c.get('ip', ''),
                    'signal_strength': int(c.get('signal_strength', 0)),
                    'wifi_standard': c.get('wifi_standard', ''),
                    'is_connected': 1,
                    'download_rate_mbps': int(c.get('download_rate_mbps', 0)),
                    'upload_rate_mbps': int(c.get('upload_rate_mbps', 0)),
                    'lan_port': self._clean_lan_port(c.get('lan_port', '')),
                    'link_speed_mbps': int(c.get('link_speed_mbps', 0)),
                    'bytes_received': int(c.get('bytes_received', 0)),
                    'bytes_sent': int(c.get('bytes_sent', 0)),
                    'bytes_total': int(c.get('bytes_total', 0))
                })

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE clients SET is_connected = 0")
            if batch_data:
                cursor.executemany('''
                    INSERT OR REPLACE INTO clients 
                    (mac, time_ut, type, hostname, ip, signal_strength, wifi_standard,
                     is_connected, download_rate_mbps, upload_rate_mbps, lan_port,
                     link_speed_mbps, bytes_received, bytes_sent, bytes_total)
                    VALUES (:mac, :time_ut, :type, :hostname, :ip, :signal_strength, :wifi_standard,
                            :is_connected, :download_rate_mbps, :upload_rate_mbps, :lan_port,
                            :link_speed_mbps, :bytes_received, :bytes_sent, :bytes_total)
                ''', batch_data)

    def insert_events_from_log(self, logcontent_or_path):
        if isinstance(logcontent_or_path, str) and '\n' in logcontent_or_path:
            lines = logcontent_or_path.splitlines()
        else:
            logpath = Path('logs') / logcontent_or_path
            if not logpath.exists(): return 0
            with open(logpath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        parsed_events = []

        for line in lines:
            event = self._parse_router_log_line(line)
            if event:
                parsed_events.append(event)

        if not parsed_events:
            return 0

        normalized_events = self._normalize_router_log_timestamps(parsed_events)
        events_batch = [(e['time_ut'], e['level_id'], e['type'], e['event_text']) for e in normalized_events]

        if not events_batch:
            return 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT OR IGNORE INTO events (time_ut, level_id, type, event_text) VALUES (?, ?, ?, ?)",
                events_batch
            )
            return cursor.rowcount

    def _parse_router_log_line(self, line):
        s = line.strip()
        if len(s) < 28:
            return None
        if s[4] != '-' or s[7] != '-' or s[10] != ' ' or s[13] != ':' or s[16] != ':':
            return None

        try:
            dt = datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None

        rest = s[20:]
        if not rest.startswith('['):
            return None
        rb = rest.find(']')
        if rb <= 1:
            return None

        level_str = rest[1:rb]
        if not level_str.isdigit():
            return None

        payload = rest[rb + 2:] if len(rest) > rb + 2 else ""
        sep = payload.find(': ')
        if sep <= 0:
            return None

        return {
            'dt': dt,
            'time_ut': int(dt.timestamp()),
            'level_id': int(level_str),
            'type': payload[:sep],
            'event_text': payload[sep + 2:],
        }

    def _normalize_router_log_timestamps(self, events):
        if len(events) < 2:
            return events

        # Sehr leichte Heuristik:
        # erster großer positiver Sprung => Anchor (ab hier korrekte Zeit),
        # alle vorherigen Einträge werden um dasselbe Delta verschoben.
        min_anchor_jump_seconds = 6 * 3600
        max_future_skew_seconds = 600

        corrected = [dict(e) for e in events]
        now_ut = int(time.time())
        n = len(corrected)

        for idx in range(1, n):
            prev_ev = corrected[idx - 1]
            curr_ev = corrected[idx]
            delta = curr_ev['time_ut'] - prev_ev['time_ut']

            if delta < min_anchor_jump_seconds:
                continue
            if curr_ev['time_ut'] > (now_ut + max_future_skew_seconds):
                continue
            if delta <= 0:
                continue

            for k in range(0, idx):
                corrected[k]['time_ut'] += delta
                corrected[k]['dt'] = datetime.fromtimestamp(corrected[k]['time_ut'])

            if corrected[idx - 1]['time_ut'] > corrected[idx]['time_ut']:
                return events
            return corrected

        return events

    def fix_event_timestamps(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, time_ut FROM events ORDER BY id ASC")
            events = cursor.fetchall()

            if len(events) < 2: return 0

            MIN_JUMP_THRESHOLD = -3600
            corrections = []
            i = 1
            while i < len(events):
                prev_id, prev_time = events[i - 1]
                curr_id, curr_time = events[i]
                if (curr_time - prev_time) < MIN_JUMP_THRESHOLD:
                    for j in range(i + 1, len(events)):
                        check_id, check_time = events[j]
                        if check_time > prev_time:
                            offset = check_time - events[j - 1][1]
                            affected_ids = [events[k][0] for k in range(i, j)]
                            corrections.append({'ids': affected_ids, 'offset': offset})
                            i = j
                            break
                    else:
                        i = len(events)
                i += 1

            if corrections:
                for corr in corrections:
                    id_str = ','.join(map(str, corr['ids']))
                    cursor.execute(
                        f"UPDATE OR REPLACE events SET time_ut = time_ut + {corr['offset']} WHERE id IN ({id_str})")
                return sum(len(c['ids']) for c in corrections)
        return 0

    def purge_old_events(self, days, event_types, debug=False):
        if days <= 0 or not event_types: return
        cutoff = int(time.time()) - (days * 86400)
        placeholders = ",".join(["?"] * len(event_types))
        params = [cutoff] + event_types

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if debug:
                    sql_sel = f"SELECT datetime(time_ut, 'unixepoch', 'localtime'), type, event_text FROM events WHERE time_ut < ? AND type IN ({placeholders})"
                    cursor.execute(sql_sel, params)
                    for r in cursor.fetchall():
                        print(f"  -> Lösche: [{r[0]}] {r[1]:<8} | {r[2]}")

                cursor.execute(f"DELETE FROM events WHERE time_ut < ? AND type IN ({placeholders})", params)
                if cursor.rowcount > 0:
                    print(f"Cleanup: {cursor.rowcount} Einträge gelöscht.")
        except Exception as e:
            print(f"Cleanup Fehler: {e}")

    def fix_future_timestamps(self, debug=False):
        now_ut = int(time.time())
        corrections = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cursor.fetchall() if r[0] != 'sqlite_sequence']

                for table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    if 'time_ut' in [c[1] for c in cursor.fetchall()]:
                        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE time_ut > ?", (now_ut,))
                        count = cursor.fetchone()[0]
                        if count > 0:
                            cursor.execute(f"UPDATE {table} SET time_ut = ? WHERE time_ut > ?", (now_ut, now_ut))
                            corrections.append({'table': table, 'count': count})
                conn.commit()

            if corrections:
                self._write_deleted_log(corrections, now_ut)
                if debug:
                    for c in corrections:
                        print(f"[Debug] {c['count']} Zukunfts-Werte in '{c['table']}' korrigiert.")
        except Exception as e:
            print(f"Fehler bei globaler Zukunfts-Korrektur: {e}")

    def _write_deleted_log(self, corrections, target_ts):
        Path('logs').mkdir(exist_ok=True)
        fname = Path('logs') / f"deleted_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(f"Korrektur Zukunfts-Zeitstempel - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n")
            for c in corrections:
                f.write(
                    f"Tabelle: {c['table']:<15} | Anzahl: {c['count']:<5} | Ziel: {datetime.fromtimestamp(target_ts)}\n")

    def print_summary(self):
        print("\n--- DB Übersicht ---")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for table in ['system', 'dsl', 'clients', 'events']:
                try:
                    cursor.execute(f"SELECT COUNT(*), MAX(time_ut) FROM {table}")
                    row = cursor.fetchone()
                    ts = datetime.fromtimestamp(row[1]).strftime('%m-%d %H:%M:%S') if row and row[1] else "N/A"
                    print(f"{table.capitalize():<8} Anzahl: {row[0] if row else 0:<5} Neuester: {ts}")
                except:
                    pass

            try:
                cursor.execute("SELECT SUM(bytes_total) FROM clients")
                res = cursor.fetchone()
                print(f"Traffic total: {((res[0] or 0) / 1048576):.1f} MB".replace('.', ','))
            except Exception as e:
                print(f"Traffic Fehler: {e}")

    def close(self):
        pass
