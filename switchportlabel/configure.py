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

    if hostname and hostport:
        desc = "Cust: %s %s" % (hostname, hostport)
    elif hostname:
        desc = "Cust: %s" % (hostname,)
    else:
        if remote_switchname and remote_switchport:
            desc = "Core: %s %s" % (remote_switchname, remote_switchport)
        elif hostname:
            desc = "Core: %s" % (remote_switchname,)
        else:
            desc = None

    return desc


def configure(switches, lldp_ifaces, puppetdb_fc):
    for iface in lldp_ifaces:
        set_port_attr(switches, iface["switchname"], iface["switchport"], "hostname", iface["hostname"])
        set_port_attr(switches, iface["switchname"], iface["switchport"], "hostport", iface["hostport"])

    for hostname, hosts in puppetdb_fc.items():
        for host_id, detail in hosts.items():
            port_name = detail["port_name"]
            for switchname, switch in switches.items():
                for row in switch["flogi"]:
                    if row["port_name"] == port_name:
                        set_port_attr(switches, switchname, row["switchport"], "hostname", hostname)
                        set_port_attr(switches, switchname, row["switchport"], "hostport", host_id)

    for switchname, switch in switches.items():
        for portname, detail in switch["interfaces"].items():
            detail["new_description"] = format_description(detail)

    return switches
