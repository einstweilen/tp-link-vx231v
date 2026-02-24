#!/usr/bin/env python3
"""
Router Database Translation Management Script
Creates and manages a translation database (router_lang.db) for router_data.db fields
"""

import sqlite3
import os

def create_translation_db(db_path="router_lang.db"):
    """Create the translation database with schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create translations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            table_name TEXT NOT NULL,
            field_name TEXT NOT NULL,
            language TEXT NOT NULL,
            translation TEXT NOT NULL,
            PRIMARY KEY (table_name, field_name, language)
        )
    """)

    conn.commit()
    return conn

def insert_translations(conn):
    """Insert all field translations for EN and DE"""
    cursor = conn.cursor()

    # Translation data: (table, field, en_translation, de_translation)
    translations = [
        # system table
        ("system", "id", "ID", "ID"),
        ("system", "time_ut", "Timestamp", "Zeitstempel"),
        ("system", "model", "Model", "Modell"),
        ("system", "firmware", "Firmware Version", "Firmware-Version"),
        ("system", "hardware", "Hardware Version", "Hardware-Version"),
        ("system", "serial", "Serial Number", "Seriennummer"),
        ("system", "uptime_seconds", "Uptime (Seconds)", "Betriebszeit (Sekunden)"),
        ("system", "uptime_days", "Uptime (Days)", "Betriebszeit (Tage)"),

        # dsl table
        ("dsl", "id", "ID", "ID"),
        ("dsl", "time_ut", "Timestamp", "Zeitstempel"),
        ("dsl", "ip_curr", "Current IP", "Aktuelle IP"),
        ("dsl", "upstream_curr_rate", "Upstream Current Rate", "Upstream Aktuelle Rate (kbit/s)"),
        ("dsl", "downstream_curr_rate", "Downstream Current Rate", "Downstream Aktuelle Rate (kbit/s)"),
        ("dsl", "upstream_max_rate", "Upstream Max Rate", "Upstream Maximale Rate (kbit/s)"),
        ("dsl", "downstream_max_rate", "Downstream Max Rate", "Downstream Maximale Rate (kbit/s)"),
        ("dsl", "upstream_noise_margin", "Upstream Noise Margin", "Upstream Störabstand (dB)"),
        ("dsl", "downstream_noise_margin", "Downstream Noise Margin", "Downstream Störabstand (dB)"),
        ("dsl", "upstream_attenuation", "Upstream Attenuation", "Upstream Dämpfung (dB)"),
        ("dsl", "downstream_attenuation", "Downstream Attenuation", "Downstream Dämpfung (dB)"),
        ("dsl", "ucrc", "Upstream CRC Errors", "Upstream CRC-Fehler (Pakete)"),
        ("dsl", "dcrc", "Downstream CRC Errors", "Downstream CRC-Fehler (Paket)"),
        ("dsl", "upstream_tx_power", "Upstream TX Power", "Upstream Sendeleistung (dBm)"),
        ("dsl", "downstream_tx_power", "Downstream TX Power", "Downstream Sendeleistung (dBm)"),
        ("dsl", "upstream_latency", "Upstream Latency", "Upstream Latenz (ms)"),
        ("dsl", "downstream_latency", "Downstream Latency", "Downstream Latenz (ms)"),
        ("dsl", "upstream_ginp", "Upstream G.INP", "Upstream G.INP(G.998.4)"),
        ("dsl", "downstream_ginp", "Downstream G.INP", "Downstream G.INP(G.998.4)"),
        ("dsl", "upstream_gvector", "Upstream G.Vector", "Upstream G.Vector(G.993.5)"),
        ("dsl", "downstream_gvector", "Downstream G.Vector", "Downstream G.Vector(G.993.5)"),

        # clients table
        ("clients", "mac", "MAC Address", "MAC-Adresse"),
        ("clients", "time_ut", "Timestamp", "Zeitstempel"),
        ("clients", "type", "Connection Type", "Verbindungstyp"),
        ("clients", "hostname", "Host Name", "Hostname"),
        ("clients", "ip", "IP Address", "IP-Adresse"),
        ("clients", "signal_strength", "Signal Strength", "Signalstärke"),
        ("clients", "wifi_standard", "WiFi Standard", "WLAN-Standard"),
        ("clients", "is_connected", "Connected", "Verbunden"),
        ("clients", "download_rate_mbps", "Download Rate (Mbps)", "Download-Rate (Mbps)"),
        ("clients", "upload_rate_mbps", "Upload Rate (Mbps)", "Upload-Rate (Mbps)"),
        ("clients", "lan_port", "LAN Port", "LAN-Port"),
        ("clients", "link_speed_mbps", "Link Speed (Mbps)", "Verbindungsgeschwindigkeit (Mbps)"),
        ("clients", "bytes_received", "Bytes Received", "Empfangene Bytes"),
        ("clients", "bytes_sent", "Bytes Sent", "Gesendete Bytes"),
        ("clients", "bytes_total", "Bytes Sent", "Bytes insgesamt"),

        # events table
        ("events", "id", "ID", "ID"),
        ("events", "time_ut", "Timestamp", "Zeitstempel"),
        ("events", "level_id", "Level ID", "Level-ID"),
        ("events", "type", "Event Type", "Ereignistyp"),
        ("events", "event_text", "Event", "Ereignis"),
    ]

    # Insert translations
    for table, field, en_text, de_text in translations:
        cursor.execute("""
            INSERT OR REPLACE INTO translations (table_name, field_name, language, translation)
            VALUES (?, ?, 'en', ?)
        """, (table, field, en_text))

        cursor.execute("""
            INSERT OR REPLACE INTO translations (table_name, field_name, language, translation)
            VALUES (?, ?, 'de', ?)
        """, (table, field, de_text))

    conn.commit()
    print(f"✓ Inserted {len(translations)} field translations for EN and DE")

def main():
    """Main function to create and populate translation database"""
    db_path = "router_lang.db"

    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✓ Removed existing {db_path}")

    # Create and populate database
    conn = create_translation_db(db_path)
    print(f"✓ Created translation database: {db_path}")

    insert_translations(conn)

    # Display summary
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM translations")
    total_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT table_name) FROM translations")
    table_count = cursor.fetchone()[0]

    print(f"\n✓ Database created successfully!")
    print(f"  - Tables: {table_count}")
    print(f"  - Total translations: {total_count}")

    conn.close()

if __name__ == "__main__":
    main()
