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
from core.reporter import TPLinkVX231vReport
from core.dashboard import DataCharter

def main():
    config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    config.read('config.ini')

    parser = argparse.ArgumentParser(description='TP-Link VX231v Monitor & Reporter')
    parser.add_argument('--output')
    parser.add_argument('--update', action='store_true', help='Daten in DB aktualisieren')
    parser.add_argument('--log', action='store_true', help='Router-Log erfassen')
    parser.add_argument('--gui', action='store_true', help='Alle Daten per WebGUI-Scraping holen')
    parser.add_argument('--report-send', action='store_true', help='Statusreport generieren und versenden')
    parser.add_argument('--report-show', action='store_true', help='Statusreport generieren und im Browser anzeigen')
    parser.add_argument('--dashboard', action='store_true', help='Starte Web-Dashboard')
    parser.add_argument('--json-only', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--test', action='store_true', help='Technologien und Konfiguration testen')
    args = parser.parse_args()

    if not (args.update or args.log or args.report_send or args.report_show or args.dashboard or args.test):
        sys.exit("Parameter --update, --log, --report-send, --report-show, --dashboard oder --test erforderlich.")

    if args.test:
        from core.tester import run_tests
        run_tests(config, debug=args.debug)
        if not (args.update or args.log or args.report_send or args.report_show or args.dashboard):
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
        gui_client = TPLinkVX231vPlaywright(
            config['Router']['routerip'],
            config['GUI']['username'],
            config['GUI']['password'],
            debug=args.debug
        )
        try:
            if gui_client.login():
                if do_log:
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

    try:
        if args.update or args.log:
            use_gui = args.gui
            # Wenn update=True, prüfen, ob wir GUI nutzen müssen (oder erzwungen). 
            # Wenn update=False, aber log=True, brauchen wir definitv GUI für das Log
            if args.update and not use_gui:
                is_telnet, is_snmp = router.check_services()
                if not (is_telnet and is_snmp):
                    use_gui = True
                    print(f"Hinweis: Telnet={is_telnet}, SNMP={is_snmp} -> wechsle automatisch auf --gui.")
            elif not args.update and args.log:
                 use_gui = True # Für reines --log brauchen wir GUI


            if use_gui:
                fetch_gui_data(args.update, args.log)
            else:
                # GUI nur für Log-Download nutzen, weil update via Telnet/SNMP lief
                if args.log:
                    fetch_gui_data(False, True)

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
            print("Starte DataCharter Web-Dashboard...")
            charter.run(host='0.0.0.0', port=31311, debug=args.debug)

    finally:
        db.close()


if __name__ == "__main__":
    main()
