import sys
import shutil
import socket
import subprocess

def print_result(label, success):
    icon = "✓" if success else "✗"
    print(f"  {icon}  {label}")

def run_tests(config, debug=False):
    # --- GUI Scraping ---
    print("\nGUI Scraping")
    pw_installed = False
    pw_chromium_installed = False
    try:
        import playwright
        pw_installed = True
        import os
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                ex_path = p.chromium.executable_path
                if os.path.exists(ex_path):
                    pw_chromium_installed = True
        except Exception:
            if debug:
                import traceback
                traceback.print_exc()
            pass
    except ImportError:
        if debug:
            print("ImportError: playwright ist nicht verfügbar")
        pass
        
    try:
        gui_user = config.get('GUI', 'username', fallback='')
        gui_pass = config.get('GUI', 'password', fallback='')
    except Exception:
        if debug:
            import traceback
            traceback.print_exc()
        gui_user, gui_pass = '', ''

    has_gui_creds = bool(gui_user and gui_pass)
    gui_login_ok = False
    
    if pw_chromium_installed and has_gui_creds:
        from core.playwright_client import TPLinkVX231vPlaywright
        original_exit = sys.exit
        def dummy_exit(code):
            raise RuntimeError(f"sys.exit called with {code}")
        sys.exit = dummy_exit
        
        try:
            client = TPLinkVX231vPlaywright(
                config.get('Router', 'routerip', fallback='192.168.1.1'), 
                gui_user, 
                gui_pass, 
                debug=debug
            )
            if client.login():
                gui_login_ok = True
            client.close()
        except Exception:
            if debug:
                import traceback
                traceback.print_exc()
            pass
        finally:
            sys.exit = original_exit

    if gui_login_ok:
        print_result("Login in Routerweboberfläche erfolgreich", True)
    else:
        print_result("playwright installiert", pw_installed)
        print_result("playwright chromium installiert", pw_chromium_installed)
        print_result("GUI Zugangsdaten in der Config", has_gui_creds)
        print_result("Login in Routerweboberfläche erfolgreich", gui_login_ok)


    # --- Telnet ---
    print("\nTelnet Konfiguration")
    telnet_cmd = shutil.which('telnet') is not None
    
    try:
        telnet_user = config.get('Telnet', 'username', fallback='')
        telnet_pass = config.get('Telnet', 'password', fallback='')
    except Exception:
        if debug:
            import traceback
            traceback.print_exc()
        telnet_user, telnet_pass = '', ''

    has_telnet_creds = bool(telnet_user and telnet_pass)
    telnet_login_ok = False
    
    if has_telnet_creds:
        from core.telnet_client import TPLinkVX231vTelnet
        try:
            client = TPLinkVX231vTelnet(
                ip=config.get('Router', 'routerip', fallback='192.168.1.1'),
                username=telnet_user,
                password=telnet_pass,
                community=config.get('SNMP', 'community', fallback=''),
                debug=debug
            )
            if client.login():
                telnet_login_ok = True
            client.close()
        except Exception:
            if debug:
                import traceback
                traceback.print_exc()
            pass

    if telnet_login_ok:
        print_result("telnet Login erfolgreich", True)
    else:
        print_result("telnet Kommando installiert", telnet_cmd)
        print_result("telnet Zugangsdaten in der Config", has_telnet_creds)
        print_result("telnet Login erfolgreich", telnet_login_ok)
    
    
    # --- SNMP ---
    print("\nSNMP Konfiguration")
    snmpget_cmd = shutil.which('snmpget') is not None
    snmpwalk_cmd = shutil.which('snmpwalk') is not None
    snmp_cmd_ok = snmpget_cmd and snmpwalk_cmd
    
    try:
        snmp_community = config.get('SNMP', 'community', fallback='')
    except Exception:
        if debug:
            import traceback
            traceback.print_exc()
        snmp_community = ''

    has_snmp_creds = bool(snmp_community)
    snmp_access_ok = False
    
    if snmp_cmd_ok and has_snmp_creds:
        ip = config.get('Router', 'routerip', fallback='192.168.1.1')
        cmd = ["snmpget", "-v2c", "-c", snmp_community, ip, "1.3.6.1.2.1.1.1.0"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if proc.returncode == 0:
                snmp_access_ok = True
        except Exception as e:
            if debug:
                print(f"snmpget error: {e}")
            pass

    if snmp_access_ok:
        print_result("snmp Zugriff erfolgreich", True)
    else:
        print_result("snmp (snmpget/walk) Kommando installiert", snmp_cmd_ok)
        print_result("snmp Zugangsdaten in der Config", has_snmp_creds)
        print_result("snmp Zugriff erfolgreich", snmp_access_ok)

    # --- Email ---
    print("\neMail Konfiguration")
    try:
        smtp_server = config.get('Email', 'smtp_server', fallback='')
        smtp_port = config.getint('Email', 'smtp_port', fallback=0)
        email_user = config.get('Email', 'sender_email', fallback='')
        email_pass = config.get('Email', 'sender_password', fallback='')
        email_recipient = config.get('Email', 'recipient_email', fallback='')
    except Exception:
        if debug:
            import traceback
            traceback.print_exc()
        smtp_server, smtp_port, email_user, email_pass, email_recipient = '', 0, '', '', ''

    has_email_config = bool(smtp_server and smtp_port and email_user and email_pass)
    email_login_ok = False
    email_sent_ok = False
    
    if has_email_config:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=5)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=5)
                try:
                    server.starttls()
                except Exception:
                    if debug:
                        import traceback
                        traceback.print_exc()
                    pass
            server.login(email_user, email_pass)
            email_login_ok = True
            
            if email_recipient:
                msg_root = MIMEMultipart('mixed')
                msg_root['Subject'] = "Test eMail vom TP-Link VX231v Tracker"
                msg_root['From'] = email_user
                msg_root['To'] = email_recipient
                
                msg_root.attach(MIMEText("Testversand erfolgreich", 'plain'))
                server.send_message(msg_root)
                email_sent_ok = True

            server.quit()
        except Exception:
            if debug:
                import traceback
                traceback.print_exc()
            pass

    if email_sent_ok:
        print_result("eMail erfolgreich versendet", True)
    else:
        print_result("eMail Zugangsdaten in der Config", has_email_config)
        print_result("SMTP Server Login möglich", email_login_ok)
        print_result("eMail erfolgreich versendet", email_sent_ok)
        
    print()
