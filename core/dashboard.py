import sqlite3
import json
import base64
import io
import time
from datetime import datetime


class DataCharter:
    def __init__(self, config, db_path):
        from flask import Flask
        import os
        self.config = config
        self.db_path = db_path
        self.lang_db_name = self.config.get('Database', 'lang_db_name', fallback='router_lang.db')
        
        # Determine the root 'dashboard' directory
        template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dashboard'))
        self.app = Flask(__name__, template_folder=template_dir)
        
        self.app.before_request(self.limit_to_local_network)
        self.app.route('/', methods=['GET', 'POST'])(self.index)

    def get_translation(self, table_name, field_name, language="de"):
        """Holt Übersetzung aus router_lang.db"""
        try:
            conn = sqlite3.connect(self.lang_db_name)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT translation 
                FROM translations 
                WHERE table_name = ? COLLATE NOCASE
                AND field_name = ? COLLATE NOCASE
                AND language = ?
            """, (table_name, field_name, language))

            result = cursor.fetchone()
            conn.close()
            return result["translation"] if result else field_name
        except Exception as e:
            return field_name

    def get_table_translations(self, table_name, language="de"):
        """Holt alle Feld-Übersetzungen für eine Tabelle"""
        try:
            conn = sqlite3.connect(self.lang_db_name)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT field_name, translation 
                FROM translations 
                WHERE table_name = ? COLLATE NOCASE
                AND language = ?
            """, (table_name, language))

            translations = {}
            for row in cursor.fetchall():
                translations[row["field_name"].lower()] = row["translation"]

            conn.close()
            return translations
        except:
            return {}

    def get_tables_and_columns(self):
        """Liest alle Tabellen und deren (Zahlen-)Spalten aus der Datenbank"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = {}

        for (table_name,) in cur.fetchall():
            if table_name == 'translations':
                continue
            cur.execute(f"PRAGMA table_info({table_name})")
            # row[1] = name, row[2] = type
            # Nur numerische Datentypen für das Charting zulassen
            columns = []
            for row in cur.fetchall():
                col_name = row[1]
                col_type = str(row[2]).upper()
                if 'INT' in col_type or 'REAL' in col_type or 'NUMERIC' in col_type or 'DECIMAL' in col_type or 'FLOAT' in col_type:
                    columns.append(col_name)
                    
            if columns:  # Tabelle nur aufnehmen, wenn es anzeigbare numerische Spalten gibt
                tables[table_name] = columns

        conn.close()
        return tables

    def get_tables_with_translations(self):
        """Erstellt Dictionary mit Tabellen, Feldern und deren deutschen Übersetzungen"""
        tables = self.get_tables_and_columns()
        tables_with_trans = {}

        for table_name, columns in tables.items():
            translations = self.get_table_translations(table_name, "de")
            fields = {}
            for col in columns:
                fields[col] = translations.get(col.lower(), col)
            tables_with_trans[table_name] = fields

        return tables_with_trans

    def get_latest_model_name(self):
        """Holt neuesten Router-Model-Namen aus system-Tabelle"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT model 
                FROM system 
                ORDER BY time_ut DESC 
                LIMIT 1
            """)
            row = cur.fetchone()
            conn.close()
            return row[0] if row and row[0] else "Router"
        except:
            return "Router"

    def limit_to_local_network(self):
        """Erlaubt nur Zugriffe aus lokalem Netz"""
        import ipaddress
        from flask import request, abort
        client_ip = request.remote_addr

        allowed_networks = [
            ipaddress.ip_network('192.168.0.0/16'),
            ipaddress.ip_network('127.0.0.0/8'),
            ipaddress.ip_network('10.0.0.0/8'),
            ipaddress.ip_network('::1/128')
        ]

        try:
            ip = ipaddress.ip_address(client_ip)
            if not any(ip in net for net in allowed_networks):
                abort(403)
        except:
            abort(403)

    def to_unix_seconds(self, dt_string):
        if not dt_string:
            return None
        try:
            dt = datetime.fromisoformat(dt_string)
            return int(dt.timestamp())
        except:
            return None

    def create_chart(self, timestamps1, values1, table1, field1, timestamps2=None, values2=None, table2=None, field2=None):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        fig, ax1 = plt.subplots(figsize=(12, 6))
        dates1 = [datetime.fromtimestamp(ts) for ts in timestamps1]

        field1_label = self.get_translation(table1, field1, "de")

        # Erste Y-Achse (links)
        color1 = '#4BC0C0'
        ax1.plot(dates1, values1, '-', linewidth=1.5, color=color1)
        ax1.set_ylabel(field1_label, color=color1)
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.grid(True, alpha=0.3)

        # Titel zusammensetzen
        if field2 and values2 and timestamps2:
            field2_label = self.get_translation(table2, field2, "de")
            plt.title(f'{field1_label} / {field2_label}')

            # Zweite Y-Achse (rechts)
            dates2 = [datetime.fromtimestamp(ts) for ts in timestamps2]
            ax2 = ax1.twinx()
            color2 = '#FF6384'
            ax2.plot(dates2, values2, '-', linewidth=1.5, color=color2)
            ax2.set_ylabel(field2_label, color=color2)
            ax2.tick_params(axis='y', labelcolor=color2)
        else:
            plt.title(f'{field1_label}')

        # Deutsche Datumsformatierung
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m. %H Uhr'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.gcf().autofmt_xdate()

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        return img_base64

    def index(self):
        from flask import request, render_template
        TABLES = self.get_tables_and_columns()
        TABLES_WITH_TRANS = self.get_tables_with_translations()

        error = None
        chart_img = None
        selected_table = request.form.get('table', '')
        selected_field = request.form.get('field', '')
        selected_table2 = request.form.get('table2', '')
        selected_field2 = request.form.get('field2', '')
        mode = request.form.get('mode', 'relative')
        days = int(request.form.get('days', 3))
        from_dt = request.form.get('from_dt', '')
        to_dt = request.form.get('to_dt', '')

        if request.method == 'POST':
            table = selected_table
            field = selected_field
            table2 = selected_table2 if selected_table2 else None
            field2 = selected_field2 if selected_field2 else None

            if not table or table not in TABLES:
                error = "Bitte eine gültige Tabelle auswählen"
            elif not field or field not in TABLES[table]:
                error = "Bitte ein gültiges Feld auswählen"
            elif table2 and table2 not in TABLES:
                error = "Bitte eine gültige zweite Tabelle auswählen"
            elif field2 and table2 and field2 not in TABLES[table2]:
                error = "Bitte ein gültiges zweites Feld auswählen"
            elif field2 and not table2:
                error = "Bitte eine Tabelle für Feld 2 auswählen"
            else:
                if mode == 'relative':
                    to_ts = int(datetime.now().timestamp())
                    from_ts = to_ts - (days * 86400)
                else:
                    from_ts = self.to_unix_seconds(from_dt)
                    to_ts = self.to_unix_seconds(to_dt)

                    if not from_ts or not to_ts or from_ts >= to_ts:
                        error = "Bitte einen gültigen Zeitraum angeben (Von < Bis)"

                if not error:
                    try:
                        conn = sqlite3.connect(self.db_path)
                        cur = conn.cursor()

                        # Erste Abfrage
                        if 'time_ut' not in TABLES[table]:
                            error = f"Tabelle '{table}' hat keine 'time_ut' Spalte"
                        else:
                            cur.execute(f'''
                                SELECT time_ut, {field}
                                FROM {table}
                                WHERE time_ut BETWEEN ? AND ?
                                ORDER BY time_ut ASC
                            ''', (from_ts, to_ts))

                            rows1 = cur.fetchall()

                            if not rows1:
                                error = "Keine Daten im ausgewählten Zeitraum gefunden"
                            else:
                                timestamps1 = []
                                values1 = []
                                for r in rows1:
                                    try:
                                        v = float(r[1])
                                        if v != 0:
                                            timestamps1.append(r[0])
                                            values1.append(v)
                                    except:
                                        pass

                                # Zweite Abfrage wenn vorhanden
                                if field2 and table2:
                                    if 'time_ut' not in TABLES[table2]:
                                        error = f"Tabelle '{table2}' hat keine 'time_ut' Spalte"
                                    else:
                                        cur.execute(f'''
                                            SELECT time_ut, {field2}
                                            FROM {table2}
                                            WHERE time_ut BETWEEN ? AND ?
                                            ORDER BY time_ut ASC
                                        ''', (from_ts, to_ts))

                                        rows2 = cur.fetchall()

                                        if rows2:
                                            timestamps2 = []
                                            values2 = []
                                            for r in rows2:
                                                try:
                                                    v = float(r[1])
                                                    if v != 0:
                                                        timestamps2.append(r[0])
                                                        values2.append(v)
                                                except:
                                                    pass

                                            chart_img = self.create_chart(timestamps1, values1, table, field,
                                                                          timestamps2, values2, table2, field2)
                                        else:
                                            chart_img = self.create_chart(timestamps1, values1, table, field)
                                else:
                                    chart_img = self.create_chart(timestamps1, values1, table, field)

                        conn.close()

                    except Exception as e:
                        error = f"Fehler beim Laden: {str(e)}"

        return render_template(
            'index.html',
            tables=TABLES.keys(),
            tables_json=json.dumps(TABLES_WITH_TRANS),
            selected_table=selected_table,
            selected_field=selected_field,
            selected_table2=selected_table2,
            selected_field2=selected_field2,
            mode=mode,
            days=days,
            from_dt=from_dt,
            to_dt=to_dt,
            error=error,
            chart_img=chart_img,
            model_name=self.get_latest_model_name()
        )

    def run(self, host='0.0.0.0', port=31311, debug=False):
        self.app.run(host=host, port=port, debug=debug)
