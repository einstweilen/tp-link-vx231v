#!/usr/bin/env python3
"""
TP-Link VX231v Client Monitor & Reporter
"""

import argparse
import configparser
import json
import sqlite3
import sys
import time
from pathlib import Path

from core.database import DatabaseManager
from core.telnet_client import TPLinkVX231vTelnet
from core.playwright_client import TPLinkVX231vPlaywright
from core.api_client import TPLinkVX231vAPI
from core.reporter import TPLinkVX231vReport
from core.dashboard import DataCharter

def main():
    config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    config.read('config.ini')

    parser = argparse.ArgumentParser(description='TP-Link VX231v Monitor & Reporter')
    parser.add_argument('--output')
    parser.add_argument('--update', action='store_true', help='Daten in DB aktualisieren')
    parser.add_argument('--log', action='store_true', help='Router-Log erfassen')
    parser.add_argument('--gui', action='store_true', help='Alle Daten per API/WebGUI holen')
    parser.add_argument('--report-send', action='store_true', help='Statusreport generieren und versenden')
    parser.add_argument('--report-show', action='store_true', help='Statusreport generieren und im Browser anzeigen')
    parser.add_argument('--dashboard', action='store_true', help='Starte Browser-Dashboard')
    parser.add_argument('--reconnect', nargs='?', const=5, type=int, help='Führt einen PPPoE-Reconnect durch (Optionale Wartezeit in s)')
    parser.add_argument('--json-only', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--test', action='store_true', help='Technologien und Konfiguration testen')
    args = parser.parse_args()

    if not (args.update or args.log or args.report_send or args.report_show or args.dashboard or args.test or args.reconnect):
        sys.exit("Parameter --update, --log, --report-send, --report-show, --dashboard, --reconnect oder --test erforderlich.")

    if args.test:
        from core.tester import run_tests
        run_tests(config, debug=args.debug)
        if not (args.update or args.log or args.report_send or args.report_show or args.dashboard or args.reconnect):
            return

    db_path = config['Database']['db_name']
    db = DatabaseManager(db_path=db_path)

    router = TPLinkVX231vTelnet(
        ip=config.get('Router', 'routerip'),
        username=config.get('Telnet', 'username'),
        password=config.get('Telnet', 'password'),
        community=config.get('SNMP', 'community'),
        debug=args.debug
    )

    def export_json(output_path, sys_data, dsl_data):
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({'system': sys_data, 'dsl': dsl_data}, f, indent=2)
            except Exception as e:
                print(f"Fehler beim JSON Export: {e}")

    def fetch_gui_data(do_update, do_log):
        # Check if we should force scraping or use the new API
        force_scraping = config.getboolean('GUI', 'force_scraping', fallback=False)
        gui_client = None
        
        if not force_scraping:
            print("Mode: JSON API Client (Standard)")
            gui_client = TPLinkVX231vAPI(
                config['Router']['routerip'],
                config['GUI']['username'],
                config['GUI']['password'],
                debug=args.debug
            )
            # Try login with API
            if not gui_client.login():
                print("Hinweis: API Login fehlgeschlagen. Automatische Fallback auf Playwright...")
                gui_client.close()
                gui_client = None
        
        if gui_client is None:
            if force_scraping:
                print("Mode: Playwright GUI Scraping (erzwungen durch config.ini)")
            else:
                print("Mode: Playwright GUI Scraping (Fallback nach API-Fehler)")
                
            gui_client = TPLinkVX231vPlaywright(
                config['Router']['routerip'],
                config['GUI']['username'],
                config['GUI']['password'],
                debug=args.debug
            )

        is_api_client = isinstance(gui_client, TPLinkVX231vAPI)

        try:
            if gui_client.login():
                if do_log or is_api_client:
                    log_txt = gui_client.downloadrouterlog_to_memory()
                    if log_txt:
                        added = db.insert_events_from_log(log_txt)
                        print(f"Log: {added} neue Einträge.")

                if do_update:
                    gui_data = gui_client.get_clients()
                    if 'error' not in gui_data:
                        sys_info = gui_data.get('system', {})
                        db.insert_system(sys_info, time.time())
                        db.insert_clients(gui_data)

                    dsl_data = gui_client.get_dsl_data()
                    if dsl_data:
                        db.insert_dsl(dsl_data, time.time())

                    export_json(args.output, gui_data.get('system', {}), dsl_data)
                    db.update_unknown_hostnames()
        except ImportError:
            print("Warnung: Modul 'playwright' ist nicht installiert. WebGUI-Abruf fehlgeschlagen.")
        except Exception as e:
            print(f"Fehler im GUI-Ablauf: {e}")
        finally:
            if 'gui_client' in locals():
                gui_client.close()

    def get_rsyslog_path():
        """Prüft ob rsyslog aktiv ist und gibt den Pfad zur Logdatei zurück."""
        import os
        import getpass
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        user = getpass.getuser()
        
        # Mögliche Pfade (Primär: Skript-Verzeichnis, dann Standard Linux/DietPi)
        paths = [
            os.path.join(script_dir, "router.log"),
            "/var/log/router.log",
            f"/home/{user}/router.log",
            f"/home/{user}/vx231v/router.log"
        ]
        
        # Check ob rsyslog läuft (via systemctl)
        # Wir prüfen nur ob die Datei existiert und lesbar ist, 
        # das ist ein stärkeres Indiz als nur der Prozess-Status.
        for p in paths:
            if os.path.exists(p) and os.access(p, os.R_OK):
                # Wenn Datei existiert und nicht leer ist (> 0 bytes)
                if os.path.getsize(p) > 0:
                    return p
        return None

    try:
        if args.update or args.log:
            use_gui = args.gui
            rsyslog_log_file = None if args.gui else get_rsyslog_path()
            
            # Log-Logik:
            # 1. Wenn rsyslog gefunden wurde und NICHT --gui erzwungen ist -> rsyslog nutzen
            # 2. Sonst GUI Scraping (wenn --log gesetzt oder Telnet/SNMP fehlen)
            
            if args.log and rsyslog_log_file:
                print(f"Log: Rsyslog-Datei gefunden ({rsyslog_log_file}) -> Importiere direkt.")
                try:
                    with open(rsyslog_log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                        added = db.insert_events_from_log(log_content)
                        print(f"Log: {added} neue Einträge aus rsyslog importiert.")
                except Exception as e:
                    print(f"Log: Fehler beim Lesen der rsyslog-Datei: {e}. Falle zurück auf GUI.")
                    use_gui = True
            elif args.log:
                # Kein rsyslog gefunden, aber Log gewünscht -> GUI erzwingen für Log
                use_gui = True

            # Wenn update=True, prüfen, ob wir GUI nutzen müssen (oder erzwungen). 
            if args.update and not use_gui:
                is_telnet, is_snmp = router.check_services()
                if not (is_telnet and is_snmp):
                    use_gui = True
                    print(f"Hinweis: Telnet={is_telnet}, SNMP={is_snmp} -> wechsle automatisch auf --gui.")

            if use_gui:
                fetch_gui_data(args.update, args.log and not rsyslog_log_file)
            else:
                # Falls wir oben rsyslog genutzt haben, wurde fetch_gui_data(False, True) vermieden
                # Wir müssen nur noch den Update-Teil via Telnet/SNMP machen
                if args.update and router.login():
                    client_data = router.get_clients(db_manager=db)
                    db.insert_system(client_data.get('system', {}), time.time())
                    db.insert_clients(client_data)
                    dsl_data = router.get_dsl_data()
                    db.insert_dsl(dsl_data, time.time())
                    export_json(args.output, client_data.get('system'), dsl_data)
                    db.update_unknown_hostnames()
                    router.close()

            # Fixes and printout mainly relevant if data was updated, but cleanup is fine either way
            db.fix_future_timestamps(debug=args.debug)

            cleanup_days = config.getint('Events', 'cleanup_excludes', fallback=0)
            if cleanup_days > 0:
                exclude_raw = config.get('Events', 'exclude_types', fallback='')
                types_to_purge = [t.strip() for t in exclude_raw.split(',') if t.strip()]
                db.purge_old_events(cleanup_days, types_to_purge, debug=args.debug)

            if not args.json_only:
                db.print_summary()

        if args.reconnect:
            force_scraping = config.getboolean('GUI', 'force_scraping', fallback=False)
            gui_client = None
            
            if not force_scraping:
                gui_client = TPLinkVX231vAPI(
                    config['Router']['routerip'],
                    config['GUI']['username'],
                    config['GUI']['password'],
                    debug=args.debug
                )
                if not gui_client.login():
                    print("Hinweis: Reconnect via API fehlgeschlagen. Versuche Fallback auf Playwright...")
                    gui_client.close()
                    gui_client = None
                    
            if gui_client is None:
                gui_client = TPLinkVX231vPlaywright(
                    config['Router']['routerip'],
                    config['GUI']['username'],
                    config['GUI']['password'],
                    debug=args.debug
                )
                
            try:
                # Playwright login exit falls Login fehlschlägt, API login wurde oben schon probiert
                if not hasattr(gui_client, 'router') or gui_client.router is not None:
                    if not gui_client.login():
                        return # Sollte bei Playwright nicht passieren wegen sys.exit
                
                success = gui_client.reconnect_wan(wait_time=args.reconnect)
                if success:
                    print("PPPoE Reconnect erfolgreich ausgeführt.")
                else:
                    print("Fehler beim PPPoE Reconnect.")
            except ImportError:
                print("Warnung: Modul 'playwright' ist nicht installiert. WebGUI-Abruf fehlgeschlagen.")
            except Exception as e:
                print(f"Fehler beim Reconnect: {e}")
            finally:
                gui_client.close()

        if args.report_send or args.report_show:
            needs_gui_update = db.has_unknown_clients()

            if needs_gui_update:
                print("Es wurden 'Unknown'-Clients gefunden -> Aktualisiere Log und Client-Daten via WebGUI...")
                fetch_gui_data(True, True)
            else:
                print("Keine 'Unknown'-Clients gefunden -> Lade nur neues Router-Log herunter...")
                fetch_gui_data(False, True)

            reporter = TPLinkVX231vReport(config, db_path, router=router, debug=args.debug)
            reporter.generate_report(send_email=args.report_send, show_browser=args.report_show)

        if args.dashboard:
            charter = DataCharter(config, db_path)
            print("Starte DataCharter Browser-Dashboard...")
            charter.run(host='0.0.0.0', port=31311, debug=args.debug)

    finally:
        db.close()


if __name__ == "__main__":
    main()
