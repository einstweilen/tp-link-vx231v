import time
import subprocess
import re

# Configuration
ROUTER_IP = "192.168.1.1"
COMMUNITY = "public"
WAN_INDEX = "52"

# OIDs
OID_ARP_TABLE = "1.3.6.1.2.1.4.22.1.2"  # ipNetToMediaPhysAddress
OID_IN_OCTETS = f"1.3.6.1.2.1.2.2.1.10.{WAN_INDEX}"
OID_OUT_OCTETS = f"1.3.6.1.2.1.2.2.1.16.{WAN_INDEX}"


def get_snmp_counter(oid):
    """Fetches a single SNMP counter value."""
    cmd = ["snmpget", "-v2c", "-c", COMMUNITY, ROUTER_IP, oid]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        match = re.findall(r'\d+', res.stdout.strip())
        return int(match[-1]) if match else None
    except Exception:
        return None


def show_arp_table():
    """Queries the ARP table via snmpwalk and displays IP/MAC pairs."""
    print(f"{'IP Address':<16} | {'MAC Address':<17}")
    print("-" * 36)

    # -Ox forces hex format for the MAC address
    cmd = ["snmpwalk", "-v2c", "-c", COMMUNITY, "-Ox", ROUTER_IP, OID_ARP_TABLE]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode != 0:
            print("Error: snmpwalk execution failed.")
            return

        for line in res.stdout.strip().split('\n'):
            if "=" not in line: continue

            # The IP is embedded at the end of the OID path (Index)
            oid_part, val_part = line.split("=")
            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)$', oid_part.strip())
            ip = ip_match.group(1) if ip_match else "Unknown"

            # Clean up MAC address (Hex-string formatting)
            mac = val_part.replace("Hex-STRING:", "").strip().replace(" ", ":").lower()

            print(f"{ip:<16} | {mac:<17}")
    except FileNotFoundError:
        print("Error: 'snmpwalk' is not installed on this system.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    print("-" * 36 + "\n")


def calc_mbps(curr, last, duration):
    """Calculates Mbps while handling 32-bit counter rollovers."""
    if curr is None or last is None: return 0.0
    if curr < last:
        # Handle 32-bit overflow
        diff = (4294967295 - last) + curr
    else:
        diff = curr - last
    return (diff * 8) / duration / 1_000_000


# --- Main Execution ---

# 1. Initial Device Inventory
print(f"Querying ARP table from {ROUTER_IP}...")
show_arp_table()

# 2. Monitoring Setup
print(f"Starting real-time WAN monitoring (Index {WAN_INDEX})...")
last = get_snmp_counter(OID_IN_OCTETS)
last_out = get_snmp_counter(OID_OUT_OCTETS)

if last is None or last_out is None:
    print("Error: Could not retrieve SNMP data. Please check IP and Community string.")
    exit(1)

try:
    while True:
        time.sleep(2)
        curr = get_snmp_counter(OID_IN_OCTETS)
        curr_out = get_snmp_counter(OID_OUT_OCTETS)

        down = calc_mbps(curr, last, 2)
        up = calc_mbps(curr_out, last_out, 2)

        print(f"Down: {down:6.2f} Mbps | Up: {up:6.2f} Mbps")

        last, last_out = curr, curr_out
except KeyboardInterrupt:
    print("\nMonitoring terminated by user.")
