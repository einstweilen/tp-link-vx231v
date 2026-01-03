# Activate superadmin and SNMP on TP-Link VX231v
__Warning: You can only activate the superadmin account right after a factory reset. This will wipe all your settings!__

I was looking for a simple way to monitor connected clients and real-time traffic.

As I haven't found any VX231v specific documention I ended up using Google Gemini to brute-force/trial-and-error the correct OIDs.

**Steps to enable the superadmin**

* Hold the Reset button on the back for about 10 seconds.
* Once the blue light blinks, connect via LAN and go to http://192.168.1.1/superadmin.
* Set a password for 'superadmin'
* enter your ISP credentials, and head to Advanced > System.

You should now see three additional sub menus

<img src="images/new-sub-00.jpg" alt="new menu items Screenshot">

<details>
  <summary><b>CWMP Settings</b> (Click to show screenshot)</summary>
  <br>
  <img src="images/cwmp-00.jpg" alt="CWMP Settings Screenshot" width="800">
</details>

<details>
  <summary><b>TR369 Settings</b> (Click to show screenshot)</summary>
  <br>
  <img src="images/tr369-00.jpg" alt="TR369 Settings Screenshot" width="800">
</details>

<details>
  <summary><b>SNMP Settings</b> (Click to show screenshot)</summary>
  <br>
  <img src="images/snmp-00.jpg" alt="SNMP Settings Screenshot" width="800">
</details>

* Go to **SNMP Settings** and enable the SNMP Agent. But make sure to disable it for WAN.
Set your Community Strings for Read-only and Write access.

* Go to the **Administration** menu, select the standard user from the dropdown, and set a login password.<details>
  <img src="images/account-00.jpg" alt="SNMP Settings Screenshot" width="800">
</details>
After that, you can log in normally via the standard IP or use the /superuser path for full access.

## SNMP Python Demo 
[Check out the SNMP demo script](vx231v-snmp-demo.py). The script lists the connected clients and monitors real-time throughput data and is tested on macos 26.

### Demo Output

```
Querying ARP table from 192.168.1.1...
IP Address       | MAC Address      
------------------------------------
192.168.1.52   | string::b8:27:eb:8e:ca:fe
192.168.1.53   | string::e4:5f:1:58:ca:fe
192.168.1.90   | string::70:4f:57:51:ca:fe
192.168.1.100  | string::3c:28:6d:da:ca:fe
192.168.1.101  | string::14:98:77:4e:ca:fe
192.168.1.103  | string::ee:90:2:43:ca:fe
192.168.1.105  | string::aa:98:bf:55:ca:fe
------------------------------------

Starting real-time WAN monitoring (Index 52)...
Down: 109.52 Mbps | Up:   3.67 Mbps
Down: 215.80 Mbps | Up:   6.97 Mbps
Down: 215.83 Mbps | Up:   6.91 Mbps
Down: 216.50 Mbps | Up:   7.26 Mbps
Down:   1.98 Mbps | Up:  50.19 Mbps
Down:   1.98 Mbps | Up:  49.08 Mbps
```

This might not be a complete OID list, but it’s what I’ve found so far.

If there is any offical documention, please let me know.
