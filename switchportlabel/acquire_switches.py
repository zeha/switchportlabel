from glob import glob
from netmiko import Netmiko
import json


ACQUIRE_COMMANDS = {
    "interfaces": {"cisco_nxos": "show int", "hp_comware": "display interface"},
    "flogi": {"cisco_nxos": "show flogi database"},
    "lldp": {
        "cisco_nxos": "show lldp neighbors detail | json",
        "hp_comware-7": "display lldp neighbor-information agent nearest-bridge verbose",
        "hp_comware-5": "display lldp neighbor-information",
    },
}


def parse_cisco_nxos_interfaces(device_name, text):
    """
    fc2/11 is down (Link failure: loss of sync)
        Port description is foo
        Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)
        Port WWN is 20:4b:00:de:fb:ee:ab:c0
        Admin port mode is auto, trunk mode is on
        snmp link state traps are enabled
        Port vsan is 1
        Receive data field Size is 2112
        Beacon is turned off
        1 minute input rate 0 bits/sec, 0 bytes/sec, 0 frames/sec
        1 minute output rate 0 bits/sec, 0 bytes/sec, 0 frames/sec
        4540562 frames input, 339027424 bytes
            0 discards, 0 errors
            0 CRC,  0 unknown class
            0 too long, 0 too short
        4540999 frames output, 357166908 bytes
            0 discards, 0 errors
        0 input OLS, 0 LRR, 0 NOS, 0 loop inits
        4 output OLS, 4 LRR, 4 NOS, 0 loop inits
        last clearing of "show interface" counters never
        Interface last changed at Thu Aug  9 12:41:31 2018

    Ethernet1/4 is up
    Dedicated Interface

    Belongs to Po4
    Hardware: 1000/10000 Ethernet, address: 00de.fbee.abab (bia 00de.fbee.abab)
    Description: bar
    MTU 1500 bytes,  BW 10000000 Kbit, DLY 10 usec
    reliability 255/255, txload 1/255, rxload 1/255
    Encapsulation ARPA, medium is broadcast
    Port mode is trunk
    full-duplex, 10 Gb/s, media type is 10G
    Beacon is turned off
    Input flow-control is off, output flow-control is off
    Rate mode is dedicated
    Switchport monitor is off
    EtherType is 0x8100
    Last link flapped 22week(s) 4day(s)
    Last clearing of "show interface" counters never
    7 interface resets
    30 seconds input rate 227112 bits/sec, 110 packets/sec
    30 seconds output rate 4921616 bits/sec, 996 packets/sec
    Load-Interval #2: 5 minute (300 seconds)
        input rate 10.04 Mbps, 897 pps; output rate 4.86 Mbps, 961 pps
    RX
        41682888016 unicast packets  1750939 multicast packets  38498 broadcast packets
        41684677453 input packets  131894499558140 bytes
        15085420582 jumbo packets  0 storm suppression bytes
        0 runts  0 giants  0 CRC  0 no buffer
        0 input error  0 short frame  0 overrun   0 underrun  0 ignored
        0 watchdog  0 bad etype drop  0 bad proto drop  0 if down drop
        0 input with dribble  0 input discard
        0 Rx pause
    TX
        42910039734 unicast packets  24940038 multicast packets  16458216 broadcast packets
        42951437988 output packets  74856481807857 bytes
        12220089271 jumbo packets
        0 output error  0 collision  0 deferred  0 late collision
        0 lost carrier  0 no carrier  0 babble 0 output discard
        0 Tx pause

    """
    iface = None
    ifaces = []
    indent = 0
    for line in text.splitlines():
        indent = 0
        for char in line:
            if char == " ":
                indent += 1
            else:
                break

        line = line.strip()
        wsplit = line.split()

        if indent == 0 and line and wsplit[1] == "is":
            if iface:
                ifaces.append(iface)
            name = wsplit[0]
            name = name.replace("Ethernet", "Eth")
            name = name.replace("port-channel", "Po")
            iface = {"name": name, "state": wsplit[2]}  # up/down
        elif iface and indent and line.startswith("Dedicated Interface") or line.startswith("vPC Status:"):
            continue
        elif iface and indent and line.startswith("Port description is"):
            iface["description"] = line.split("Port description is ", 1)[1].strip()
        elif iface and indent and line.startswith("Description:"):
            iface["description"] = line.split(":", 1)[1].strip()
        elif iface and indent and line.startswith("Port WWN is"):
            iface["address"] = line.split("Port WWN is ", 1)[1].replace(":", "")
        elif iface and indent and line.startswith("Hardware is"):
            iface["type"] = line.split("Hardware is ", 1)[1].split(",")[0]
        elif iface and indent and line.startswith("Members in this channel:"):
            iface["members"] = line.split(":", 1)[1].split()
        elif iface and indent and line.startswith("Hardware:"):
            cs = [x.strip().split(":") for x in line.split(",")]
            iface["type"] = cs[0][1].strip()
            iface["address"] = cs[1][1].strip().split()[0].replace(".", "")

    if iface:
        ifaces.append(iface)
    return ifaces


def map_flogi(switch, data):
    if not data:
        return {}
    return data


def parse_cisco_nxos_flogi(device_name, text):
    """
    --------------------------------------------------------------------------------
    INTERFACE        VSAN    FCID           PORT NAME               NODE NAME
    --------------------------------------------------------------------------------
    fc2/9            1     0x0b0200  10:00:98:f2:b3:a2:5a:d6 20:00:98:f2:b3:a2:5a:d6
    fc2/12           1     0x0b0140  10:00:00:90:fa:ce:d8:96 20:00:00:90:fa:ce:d8:96
    fc2/13           1     0x0b00c0  10:00:e0:07:1b:d4:f4:41 20:00:e0:07:1b:d4:f4:41
    fc2/17           1     0x0b0160  10:00:00:90:fa:ce:cf:16 20:00:00:90:fa:ce:cf:16
    """
    rows = []
    for line in text.splitlines():
        if not line.startswith("fc"):
            continue
        line = line.split()
        rows.append(
            {
                "switchport": line[0],
                "vsan": line[1],
                "fcid": line[2].replace("0x", ""),
                "port_name": line[3].replace(":", ""),
                "node_name": line[4].replace(":", ""),
            }
        )
    return rows


def map_interfaces(switch, data):
    if not data:
        return {}
    return {iface["name"]: iface for iface in data}


def parse_hp_comware_interfaces(device_name, text):
    """
    Ten-GigabitEthernet2/0/34
    Current state: UP
    Line protocol state: UP
    IP packet frame type: Ethernet II, hardware address: 5c8a-3828-71a8
    Description: zomg
    Bandwidth: 1000000 kbps
    Loopback is not set
    Media type is twisted pair, port hardware type is 1000_BASE_T_AN_SFP
    1000Mbps-speed mode, full-duplex mode
    Link speed type is autonegotiation, link duplex type is autonegotiation
    Flow-control is not enabled
    Maximum frame length: 10000
    Allow jumbo frames to pass
    Broadcast max-ratio: 100%
    Multicast max-ratio: 100%
    Unicast max-ratio: 100%
    PVID: 191
    MDI type: Automdix
    Port link-type: Access
    Tagged VLANs:   None
    Untagged VLANs: 191
    Port priority: 0
    Last link flapping: 2 days 0 hours 6 minutes
    Last clearing of counters: Never
    Peak input rate: 123227249 bytes/sec, at 2018-10-24 05:29:40
    Peak output rate: 288172772 bytes/sec, at 2018-06-23 06:44:31
    Last 300 second input: 112 packets/sec 19834 bytes/sec 0%
    Last 300 second output: 142 packets/sec 44772 bytes/sec 0%
    Input (total):  4358237286 packets, 4432560568556 bytes
        4303929389 unicasts, 62 broadcasts, 33895095 multicasts, 20412740 pauses
    Input (normal):  4337824546 packets, - bytes
        4303929389 unicasts, 62 broadcasts, 33895095 multicasts, 20412740 pauses
    Input:  0 input errors, 0 runts, 0 giants, 0 throttles
        0 CRC, 0 frame, - overruns, 0 aborts
        - ignored, - parity errors
    Output (total): 3755453007 packets, 2061360496941 bytes
        3243358465 unicasts, 56720 broadcasts, 509956054 multicasts, 2081768 pauses
    Output (normal): 3753371239 packets, - bytes
        3243358465 unicasts, 56720 broadcasts, 509956054 multicasts, 2081768 pauses
    Output: 0 output errors, - underruns, - buffer failures
        0 aborts, 0 deferred, 0 collisions, 0 late collisions
        0 lost carrier, - no carrier

    """

    iface = None
    ifaces = []
    for line in text.splitlines():
        if line == "" and iface:
            ifaces.append(iface)
            iface = None
        if not line:
            continue

        indent = 0
        for char in line:
            if char == " ":
                indent += 1
            else:
                break

        line = line.strip()

        if not iface:
            if indent in (0, 1) and 'current state:' in line:
                # comware 5
                line = line.split()
                iface = {"name": line[0], "state": line[3].lower()}
            elif indent == 0:
                # comware 7, state is in a dedicated line
                iface = {"name": line}
        elif indent == 0 and line.startswith("Media type is"):
            line = line.split(", ")
            if line[1].split()[-1].startswith("STACK_"):
                iface["stack"] = True
        elif indent == 0:
            csplit = line.split(": ", 1)
            if csplit[0] == "Current state":
                iface["state"] = csplit[1].lower()
            elif csplit[0] == "Description":
                iface["description"] = csplit[1]
            elif csplit[0] == "Description":
                iface["description"] = csplit[1]
            elif csplit[0] == "IP packet frame type" and csplit[1].startswith("Ethernet"):
                iface["type"] = "Ethernet"
                iface["address"] = csplit[1].split(",")[1].split(":")[1].strip().replace("-", "")

    if iface:
        ifaces.append(iface)
    return ifaces


def map_lldp(switch, data):
    if not data:
        return {}
    return data


def parse_cisco_nxos_lldp(device_name, json_text):
    ifaces = []
    rows = json.loads(json_text)["TABLE_nbor_detail"]["ROW_nbor_detail"]
    for row in rows:
        if row["l_port_id"] == "mgmt0":
            continue
        iface = {
            "switchname": device_name,
            "switchport": row["l_port_id"],
            "hostname": row["sys_name"],
            "hostport": row["port_id"],
        }
        ifaces.append(iface)
    return ifaces


def parse_hp_comware_lldp(device_name, text):
    """
    LLDP neighbor-information of port 33[Ten-GigabitEthernet1/0/33]:
    LLDP agent nearest-bridge:
    LLDP neighbor index : 1
    Update time         : 1 days, 23 hours, 7 minutes, 8 seconds
    Chassis type        : MAC address
    Chassis ID          : acxx-xxxx-xxxx
    Port ID type        : MAC address
    Port ID             : acxx-xxxx-xxxx
    Time to live        : 120
    Port description    : eth5
    System name         : something
    System description  : Debian GNU/Linux (stretch) Linux #1 SMP
                        PVE (yolo +0100) x86_64
    System capabilities supported : Bridge, WlanAccessPoint, Router, StationOnly
    System capabilities enabled   : StationOnly
    Management address type           : IPv4
    Management address                : 192.168.1.1
    Management address interface type : IfIndex
    Management address interface ID   : 6
    Management address OID            : 0
    Management address type           : IPv6
    Management address                : FE80::X:X:X:X
    Management address interface type : IfIndex
    Management address interface ID   : 3
    Management address OID            : 0
    Link aggregation supported : Yes
    Link aggregation enabled   : No
    Aggregation port ID        : 0
    Auto-negotiation supported : Yes
    Auto-negotiation enabled   : Yes
    OperMau                    : Speed(1000)/Duplex(Full)

    """
    iface = None
    ifaces = []
    for line in text.splitlines():
        if line == "" and iface:
            ifaces.append(iface)
            iface = None
        if not line:
            continue

        indent = 0
        for char in line:
            if char == " ":
                indent += 1
            else:
                break

        line = line.strip()

        if not iface:
            if indent == 0 and line.startswith("LLDP neighbor-information of port"):
                iface = {"switchname": device_name, "switchport": line.split("[")[1].split("]")[0].strip()}
        else:
            csplit = line.split(": ", 1)
            csplit[0] = csplit[0].strip()
            if len(csplit) > 1:
                csplit[1] = csplit[1].strip()
                if csplit[0] == "Port ID":
                    iface["hostport"] = csplit[1]
                elif csplit[0] == "Port ID type":
                    iface["hostporttype"] = csplit[1]
                elif csplit[0] == "Port ID description":
                    if iface["hostporttype"] == "MAC address":
                        iface["hostport"] = csplit[1]
                    else:
                        del iface["hostporttype"]
                elif csplit[0] == "System name":
                    iface["hostname"] = csplit[1]

    if iface:
        ifaces.append(iface)
    return ifaces


def acquire(device_name, device_options, datadir):
    print("Connecting to", device_name)
    try:
        device_type = device_options["device_type"]
        device_type_flavor = device_options.get("device_type_flavor", "")

        connect_options = dict(device_options)
        if "device_type_flavor" in connect_options:
            del connect_options["device_type_flavor"]
        conn = Netmiko(**connect_options)

        total = {"device_type": device_type, "device_type_flavor": device_type_flavor, "device_name": device_name}
        for datatype, device_commands in ACQUIRE_COMMANDS.items():
            command = device_commands.get("%s-%s" % (device_type, device_type_flavor), None)
            if not command:
                command = device_commands.get(device_type, None)
            if command:
                text = conn.send_command(command)
            else:
                text = ""
            total["raw_%s" % datatype] = text

        with open("%s/%s.json" % (datadir, device_name), "wt") as fp:
            json.dump(total, fp)

    finally:
        del conn


def read_switches(datadir):
    switches = {}
    for fn in glob("%s/*.json" % datadir):
        with open(fn, "rt") as fp:
            switch = json.load(fp)
            device_name = switch["device_name"]
            device_type = switch["device_type"]
            for datatype in ACQUIRE_COMMANDS:
                parse_funcname = "parse_%s_%s" % (device_type, datatype)
                mapper_funcname = "map_%s" % (datatype,)
                if parse_funcname in globals():
                    data = globals()[parse_funcname](device_name, switch["raw_%s" % datatype])
                else:
                    data = None
                switch[datatype] = globals()[mapper_funcname](switch, data)

            switches[device_name] = switch

    return switches


def apply_config(device_name, connect_options, lines):
    device_type = connect_options["device_type"]

    try:
        conn = Netmiko(**connect_options)
        print(conn.send_config_set(lines))
        if device_type in ("cisco_ios", "cisco_nxos"):
            print(conn.send_command("copy running-config startup-config"))
        elif device_type == "hp_comware":
            print(conn.send_command("save main force"))
        else:
            print("ERROR: configuration not saved, as device_type %s is unhandled" % device_type)
    finally:
        del conn
