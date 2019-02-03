import itertools
from .configure_formatters import format_for


def set_port_attr(switches, switchname, switchport, attr, value):
    if switchname not in switches:
        print("I: switch", switchname, "not configured, ignoring")
        return
    if switchport not in switches[switchname]["interfaces"]:
        print("I: switch", switchname, "port", switchport, "not found, ignoring")
        return
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
        if remote_switchport == 'mgmt0':
            type = "Cust"

        if remote_switchport:
            desc = "%s: %s %s" % (type, remote_switchname, remote_switchport)
        else:
            desc = "%s: %s" % (type, remote_switchname)

    return desc


def link_hosts_lldp(switches, lldp_ifaces):
    for iface in lldp_ifaces:
        set_port_attr(switches, iface["switchname"], iface["switchport"], "hostname", iface["hostname"])
        set_port_attr(switches, iface["switchname"], iface["switchport"], "hostport", iface["hostport"])


def link_hosts_fc(switches, puppetdb_fc):
    for hostname, hosts in puppetdb_fc.items():
        for host_id, detail in hosts.items():
            port_name = detail["port_name"]
            for switchname, switch in switches.items():
                for row in switch["flogi"]:
                    if row["port_name"] == port_name:
                        set_port_attr(switches, switchname, row["switchport"], "hostname", hostname)
                        set_port_attr(switches, switchname, row["switchport"], "hostport", host_id)


def link_switches_lldp(switches):
    for switchname in switches:
        for iface in switches[switchname]["lldp"]:
            if iface["hostname"] in switches:
                set_port_attr(switches, switchname, iface["switchport"], "remote_switchname", iface["hostname"])
                set_port_attr(switches, switchname, iface["switchport"], "remote_switchport", iface["hostport"])
                set_port_attr(switches, iface["hostname"], iface["hostport"], "remote_switchname", switchname)
                set_port_attr(switches, iface["hostname"], iface["hostport"], "remote_switchport", iface["switchport"])


def configure(switches, lldp_ifaces, puppetdb_fc):
    link_hosts_lldp(switches, lldp_ifaces)
    link_hosts_fc(switches, puppetdb_fc)
    link_switches_lldp(switches)

    for switchname, switch in switches.items():
        for portname, detail in switch["interfaces"].items():
            if portname == 'mgmt0':
                # Ignore management port, the LLDP info is probably not that good.
                continue
            detail["new_description"] = format_description(detail)

    return switches
