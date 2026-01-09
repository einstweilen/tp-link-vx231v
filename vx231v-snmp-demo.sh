#!/bin/bash

IP="192.168.1.1"   # router ip
COMMUNITY="public" # SNMP community string
INTERVAL=5         # traffic data sample interval in seconds
MAX_32=4294967296  # 32 bit 
IF_INDEX=52        # nas9

OID_IN=".1.3.6.1.2.1.2.2.1.10.$IF_INDEX"   # ifInOctets
OID_OUT=".1.3.6.1.2.1.2.2.1.16.$IF_INDEX"  # ifOutOctets

echo
echo "TP-Link VX231v SNMP Demo"
echo

# --- router data ---

# use SNMP flags to format command output
# -Ov	Output values only (hides OID).
# -Oq	Quick format (removes "=" and data type)
#
# snmpget -v2c -c "$COMMUNITY" "$IP" 1.3.6.1.2.1.1.5.0
# OUTPUT: SNMPv2-MIB::sysName.0 = STRING: VX231v
#
# snmpget -v2c -c "$COMMUNITY" -Ov "$IP" 1.3.6.1.2.1.1.5.0
# OUTPUT: STRING: VX231v
#
# snmpget -v2c -c "$COMMUNITY" -Ovq "$IP" 1.3.6.1.2.1.1.5.0
# OUTPUT: VX231v

echo "Router Name      : $(snmpget -v2c -c "$COMMUNITY" -Ovq "$IP" 1.3.6.1.2.1.1.5.0)"
echo "Firmware Version : $(snmpget -v2c -c "$COMMUNITY" -Ovq $IP 1.3.6.1.2.1.1.1.0)"
echo "Uptime d:hh:mm:ss: $(snmpget -v2c -c "$COMMUNITY" -Ovq $IP 1.3.6.1.2.1.1.3.0)"
echo

# --- Dynamic Interface IP Discovery ---
# Identify LAN_IP via ifIndex 19 and GUEST_IP via ifIndex 37
# Walk ipAdEntIfIndex (.1.3.6.1.2.1.4.20.1.2) to extract the IP suffix
  LAN_IP=$(snmpwalk -v2c -c "$COMMUNITY" "$IP" .1.3.6.1.2.1.4.20.1.2 | grep ": 19$" | awk -F'ipAdEntIfIndex.' '{print $2}' | awk '{print $1}')
GUEST_IP=$(snmpwalk -v2c -c "$COMMUNITY" "$IP" .1.3.6.1.2.1.4.20.1.2 | grep ": 37$" | awk -F'ipAdEntIfIndex.' '{print $2}' | awk '{print $1}')

# Fetch subnet masks using the discovered IP addresses
  LAN_MASK=$(snmpget -v2c -c "$COMMUNITY" "$IP" .1.3.6.1.2.1.4.20.1.3."$LAN_IP" | awk '{print $NF}')
GUEST_MASK=$(snmpget -v2c -c "$COMMUNITY" "$IP" .1.3.6.1.2.1.4.20.1.3."$GUEST_IP" | awk '{print $NF}')

# --- Network Ranges ---
echo "--- Networks ---"
echo "Main Network : $LAN_IP / $LAN_MASK"
echo "Guest Network: $GUEST_IP / $GUEST_MASK"

# --- Internet Traffic ---
# Retrieve Counter32 values for ingress and egress traffic
get_traffic() {
  snmpget -v2c -c "$COMMUNITY" -Oqv "$IP" "$OID_IN" "$OID_OUT" | tr '\n' ' '
}

echo -e "\n--- Live Internet Traffic  ---"
echo "Please wait ... sampling interval: $INTERVAL seconds"
SAMPLE1=($(get_traffic))
sleep "$INTERVAL"
SAMPLE2=($(get_traffic))

DIFF_IN=$(( SAMPLE2[0] - SAMPLE1[0] ))
[ $DIFF_IN -lt 0 ] && DIFF_IN=$(( DIFF_IN + MAX_32 )) # correcion for 32 bit overrun

DIFF_OUT=$(( SAMPLE2[1] - SAMPLE1[1] ))
[ $DIFF_OUT -lt 0 ] && DIFF_OUT=$(( DIFF_OUT + MAX_32 )) # correcion for 32 bit overrun

DOWN_KBIT=$(( DIFF_IN * 8 / INTERVAL / 1000 ))
UP_KBIT=$(( DIFF_OUT * 8 / INTERVAL / 1000 ))

echo "Download: $DOWN_KBIT kbit/s | Upload: $UP_KBIT kbit/s"


# --- SECTION 4: Connected Clients (ARP) ---
# Dynamic walk of ipNetToMediaTable to map IP to MAC
echo -e "\n--- Connected Clients ---"
printf "%-15s | %-17s\n" "IP-Address" "MAC-Address"
 ips=($(snmpwalk -v2c -c "$COMMUNITY" "$IP" .1.3.6.1.2.1.4.22.1.3 | awk '{print $NF}'))
macs=($(snmpwalk -v2c -c "$COMMUNITY" "$IP" .1.3.6.1.2.1.4.22.1.2 | awk '{print $NF}'))

for i in "${!ips[@]}"; do
    printf "%-15s | %-17s\n" "${ips[$i]}" "${macs[$i]}"
done

exit 0
