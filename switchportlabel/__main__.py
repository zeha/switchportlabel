#!/usr/bin/env python3

from operator import itemgetter
import itertools
import sys
import os
import configparser
from glob import glob
import json
from subprocess import check_call

from . import data_lldp


def read_switch_connect_options():
    devices = {}
    device_parser = configparser.ConfigParser()
    device_parser.read("data/switches.ini")
    for devicename in device_parser.sections():
        d = {}
        for option, value in device_parser[devicename].items():
            d[option] = value
        if "ip" not in d:
            d["ip"] = devicename
        devices[devicename] = d
    return devices


def do_acquire_switches():
    from . import acquire_switches

    devices = read_switch_connect_options()
    for devicename, connect_options in devices.items():
        acquire_switches.acquire(devicename, connect_options, "data/switches/")


def do_acquire_puppetdb():
    device_parser = configparser.ConfigParser()
    device_parser.read("data/puppetdb.ini")
    for devicename in device_parser.sections():
        with open("data/puppetdb.fibrechannel.json", "wb") as fd:
            check_call(
                [
                    "ssh",
                    devicename,
                    "--",
                    "curl",
                    "-G",
                    "http://localhost:8080/pdb/query/v4/facts",
                    "--data-urlencode",
                    'query=["and",["=","node_state","active"],["=","name","fibrechannel"]]'.replace(
                        '"', '\\"'
                    ),
                ],
                stdout=fd,
            )


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
    if hostname and hostport:
        desc = "Cust: %s %s" % (hostname, hostport)
    elif hostname:
        desc = "Cust: %s" % (hostname,)
    else:
        desc = None
    return desc


def do_configure(apply_changes):
    from .configure_formatters import format_for

    switch_connect_options = read_switch_connect_options() if apply_changes else None

    lldp_ifaces = []
    for fn in glob("data/lldpcli/*.txt"):
        devicename = fn.split("/")[-1].split(".")[0]
        with open(fn, "rt") as fp:
            lldp_ifaces.extend(data_lldp.parse_lldpcli(devicename, fp.read()))

    switches = {}
    for fn in glob("data/switches/*.json"):
        devicename = fn.split("/")[-1].split(".")[0]
        with open(fn, "rt") as fp:
            switches[devicename] = json.load(fp)

    puppetdb_fc = {}
    with open("data/puppetdb.fibrechannel.json", "rt") as fp:
        for el in json.load(fp):
            if not el["value"]["hosts"]:
                continue
            puppetdb_fc[el["certname"]] = el["value"]["hosts"]

    for iface in lldp_ifaces:
        set_port_attr(
            switches,
            iface["switchname"],
            iface["switchport"],
            "hostname",
            iface["hostname"],
        )
        set_port_attr(
            switches,
            iface["switchname"],
            iface["switchport"],
            "hostport",
            iface["hostport"],
        )

    for hostname, hosts in puppetdb_fc.items():
        for host_id, detail in hosts.items():
            port_name = detail["port_name"]
            for switchname, switch in switches.items():
                for row in switch["flogi"]:
                    if row["port_name"] == port_name:
                        set_port_attr(
                            switches,
                            switchname,
                            row["switchport"],
                            "hostname",
                            hostname,
                        )
                        set_port_attr(
                            switches, switchname, row["switchport"], "hostport", host_id
                        )

    for switchname, switch in switches.items():
        for portname, detail in switch["interfaces"].items():
            detail["new_description"] = format_description(detail)

    for switchname, switch in switches.items():
        print("--- ", switchname)
        linesets = format_for(switch)
        lines = []
        for lineset in linesets:
            lines.extend(lineset)

        if apply_changes:
            try:
                import netmiko

                conn = netmiko.Netmiko(**switch_connect_options[switchname])
                print(conn.send_config_set(lines))
                if switch_connect_options[switchname]["device_type"] == "cisco_nxos":
                    print(conn.send_command("copy running-config startup-config"))
                else:
                    print(conn.send_command("save main force"))
            finally:
                del conn
        else:
            print("\n".join(lines))


def main(args):
    action = args[1]
    if action == "configure":
        do_configure(False)

    elif action == "configure-apply":
        do_configure(True)

    elif action == "acquire-switches":
        do_acquire_switches()

    elif action == "acquire-puppetdb":
        do_acquire_puppetdb()


if __name__ == "__main__":
    main(sys.argv)
