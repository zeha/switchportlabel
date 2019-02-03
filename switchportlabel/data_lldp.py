def parse_cisco(text):
    ifaces = []
    iface = None
    for line in text.splitlines():
        if line == "":
            if iface is not None and iface["switchport"] is not None:
                ifaces.append(iface)
            iface = {"switchport": None, "hostname": None, "hostport": None}
        elif line.startswith("Local Port id:"):
            switchport = line.split(": ", 1)[1]
            if switchport != "mgmt0":
                iface["switchport"] = switchport
        elif line.startswith("Port Description:"):
            hostport = line.split(": ", 1)[1]
            if hostport != "not advertised":
                iface["hostport"] = hostport
        elif line.startswith("System Name:"):
            hostname = line.split(": ", 1)[1]
            if hostname != "not advertised":
                iface["hostname"] = hostname
    return ifaces


def parse_lldpcli(hostname, text):
    ifaces = []
    iface = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Interface:"):
            hostport = line.split()[1].rstrip(",")
            iface = {
                "switchname": None,
                "switchport": None,
                "hostname": hostname,
                "hostport": hostport,
            }
        elif line.startswith("---"):
            if iface is not None and iface["switchport"] is not None:
                ifaces.append(iface)
                iface = None
        elif line.startswith("SysName:"):
            iface["switchname"] = line.split()[1]
        elif line.startswith("PortID:"):
            iface["switchport"] = line.split()[2]
    return ifaces
