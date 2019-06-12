import itertools


def set_port_attr(switches, switchname, switchport, attr, value, overwrite=False):
    if switchname not in switches:
        print("I: switch", switchname, "not configured, ignoring")
        return
    if switchport not in switches[switchname]["interfaces"]:
        switchport_alias = None
        for switchport_real, iface in switches[switchname]["interfaces"].items():
            if switchport in iface['switchport_aliases']:
                switchport_alias = switchport_real
                break
        if switchport_alias:
            switchport = switchport_alias
        else:
            print("I: switch", switchname, "port", switchport, "not found, ignoring")
            return
    if overwrite or attr not in switches[switchname]["interfaces"][switchport]:
        switches[switchname]["interfaces"][switchport][attr] = value


def format_description(switchport):
    hostname = switchport.get("hostname", "").split(".")[0]
    hostport = switchport.get("hostport", "")
    remote_switchname = switchport.get("remote_switchname", "").split(".")[0]
    remote_switchport = switchport.get("remote_switchport", "")

    desc = None

    if hostname:
        type = "Cust"
        if hostport:
            desc = "%s: %s %s" % (type, hostname, hostport)
        else:
            desc = "%s: %s" % (type, hostname)

    elif remote_switchname:
        type = "Core"
        if remote_switchport == "mgmt0":
            type = "Cust"

        if remote_switchport:
            desc = "%s: %s %s" % (type, remote_switchname, remote_switchport)
        else:
            desc = "%s: %s" % (type, remote_switchname)

    if switchport.get("stack", False):
        if desc is None:
            print("I: not setting STACK attr on none description for switchport", switchport)
        else:
            desc += " [STACK]"

    return desc


def link_hosts_fc(switches, hosts_fc):
    for hostname, hosts in hosts_fc.items():
        for host_id, detail in hosts.items():
            port_name = detail["port_name"]
            for switchname, switch in switches.items():
                for row in switch["flogi"]:
                    if row["port_name"] == port_name:
                        set_port_attr(switches, switchname, row["switchport"], "hostname", hostname, True)
                        set_port_attr(switches, switchname, row["switchport"], "hostport", host_id, True)


def link_hosts_lldp(switches, hosts_lldp):
    for iface in hosts_lldp:
        set_port_attr(switches, iface["switchname"], iface["switchport"], "hostname", iface["hostname"], True)
        set_port_attr(switches, iface["switchname"], iface["switchport"], "hostport", iface["hostport"], True)


def find_unique_mac(switches, mac):
    all_macs = [
        mac_entry for switch in switches.values() for mac_entry in switch["mactable"] if mac_entry["address"] == mac
    ]
    for maybe_entry in all_macs:
        macs = [
            mac_entry
            for mac_entry in switches[maybe_entry["switchname"]]["mactable"]
            if mac_entry["switchport"] == maybe_entry["switchport"]
        ]
        if len(macs) == 1:
            return macs[0]
    return None


def link_hosts_ipmi(switches, hosts_ipmi):
    for hostname, ifaces in hosts_ipmi.items():
        for host_iface in ifaces:
            iface = find_unique_mac(switches, host_iface["mac"])
            if iface:
                set_port_attr(switches, iface["switchname"], iface["switchport"], "hostname", hostname)
                set_port_attr(switches, iface["switchname"], iface["switchport"], "hostport", "lom")


def link_hosts_networking(switches, hosts_networking):
    for hostname, ifaces in hosts_networking.items():
        for host_iface_name, host_iface in ifaces.items():
            iface = find_unique_mac(switches, host_iface["mac"])
            if iface:
                set_port_attr(switches, iface["switchname"], iface["switchport"], "hostname", hostname)
                set_port_attr(switches, iface["switchname"], iface["switchport"], "hostport", host_iface_name)


def link_switches_lldp(switches):
    for switchname in switches:
        for iface in switches[switchname]["lldp"]:
            if iface["hostname"] in switches:
                set_port_attr(switches, switchname, iface["switchport"], "remote_switchname", iface["hostname"])
                set_port_attr(switches, switchname, iface["switchport"], "remote_switchport", iface["hostport"])
                set_port_attr(switches, iface["hostname"], iface["hostport"], "remote_switchname", switchname)
                set_port_attr(switches, iface["hostname"], iface["hostport"], "remote_switchport", iface["switchport"])


def configure(switches, hosts_fc, hosts_ipmi, hosts_lldp, hosts_networking):
    link_hosts_lldp(switches, hosts_lldp)
    link_hosts_fc(switches, hosts_fc)
    link_hosts_ipmi(switches, hosts_ipmi)
    link_hosts_networking(switches, hosts_networking)
    link_switches_lldp(switches)

    for switchname, switch in switches.items():
        for portname, detail in switch["interfaces"].items():
            if portname == "mgmt0":
                # Ignore management port, the LLDP info is probably not that good.
                continue
            detail["new_description"] = format_description(detail)

    return switches
