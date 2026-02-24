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
from core.webserver import DataCharter

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')

    parser = argparse.ArgumentParser(description='TP-Link VX231v Monitor & Reporter')
    parser.add_argument('--output')
    parser.add_argument('--update', action='store_true', help='Daten in DB aktualisieren')
    parser.add_argument('--log', action='store_true', help='Router-Log erfassen')
    parser.add_argument('--gui', action='store_true', help='Alle Daten per WebGUI-Scraping holen')
    parser.add_argument('--report-send', action='store_true', help='Statusbericht generieren und versenden')
    parser.add_argument('--report-show', action='store_true', help='Statusbericht generieren und im Browser anzeigen')
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
                router_gui = TPLinkVX231vPlaywright(
                    config['Router']['routerip'],
                    config['GUI']['username'],
                    config['GUI']['password'],
                    debug=args.debug
                )
                try:
                    if router_gui.login():
                        if args.log:
                            log_txt = router_gui.downloadrouterlog_to_memory()
                            if log_txt:
                                added = db.insert_events_from_log(log_txt)
                                print(f"Log: {added} neue Einträge.")
                                with open('last_import.txt', 'w') as f:
                                    f.write(str(int(time.time())))

                        if args.update:
                            gui_data = router_gui.get_clients()
                            if 'error' not in gui_data:
                                db.insert_system(gui_data.get('system', {}), time.time())
                                db.insert_clients(gui_data)

                            dsl_data = router_gui.get_dsl_data()
                            if dsl_data:
                                db.insert_dsl(dsl_data, time.time())

                            if args.output:
                                with open(args.output, 'w', encoding='utf-8') as f:
                                    json.dump({'system': gui_data.get('system', {}), 'dsl': dsl_data}, f, indent=2)
                finally:
                    router_gui.close()
            else:
                # GUI nur für Log-Download nutzen, weil update via Telnet/SNMP lief
                if args.log:
                    router_gui = TPLinkVX231vPlaywright(
                        config['Router']['routerip'],
                        config['GUI']['username'],
                        config['GUI']['password'],
                        debug=args.debug
                    )
                    try:
                        if router_gui.login():
                            log_txt = router_gui.downloadrouterlog_to_memory()
                            if log_txt:
                                added = db.insert_events_from_log(log_txt)
                                print(f"Log: {added} neue Einträge.")
                                with open('last_import.txt', 'w') as f:
                                    f.write(str(int(time.time())))
                    finally:
                        router_gui.close()

                if args.update and router.login():
                    client_data = router.get_clients(db_manager=db)
                    db.insert_system(client_data.get('system', {}), time.time())
                    db.insert_clients(client_data)

                    dsl_data = router.get_dsl_data()
                    db.insert_dsl(dsl_data, time.time())

                    if args.output:
                        with open(args.output, 'w', encoding='utf-8') as f:
                            json.dump({'system': client_data.get('system'), 'dsl': dsl_data}, f, indent=2)

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
            last_import_age = float('inf')
            try:
                if Path('last_import.txt').exists():
                    with open('last_import.txt', 'r') as f:
                        last_import_age = time.time() - int(f.read().strip())
            except:
                pass

            if last_import_age > 900:
                print("Letzter Log-Import älter als 15 Minuten. Versuche aktuelles Router-Log herunterzuladen...")
                try:
                    router_gui = TPLinkVX231vPlaywright(
                        config['Router']['routerip'],
                        config['GUI']['username'],
                        config['GUI']['password'],
                        debug=args.debug
                    )
                    if router_gui.login():
                        log_txt = router_gui.downloadrouterlog_to_memory()
                        if log_txt:
                            added = db.insert_events_from_log(log_txt)
                            print(f"Log: {added} neue Einträge.")
                            with open('last_import.txt', 'w') as f:
                                f.write(str(int(time.time())))
                    router_gui.close()
                except ImportError:
                    print("Warnung: Modul 'playwright' ist nicht installiert. Automatischer Log-Download übersprungen.")
                except Exception as e:
                    print(f"Fehler beim automatischen Log-Download: {e}")

            reporter = TPLinkVX231vReport(config, db_path, debug=args.debug)
            reporter.generate_report(send_email=args.report_send, show_browser=args.report_show)

        if args.dashboard:
            charter = DataCharter(config, db_path)
            print("Starte DataCharter Web-Dashboard...")
            charter.run(host='0.0.0.0', port=31311, debug=args.debug)

    finally:
        db.close()


if __name__ == "__main__":
    main()
