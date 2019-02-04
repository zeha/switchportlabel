from operator import itemgetter
import configparser
import itertools
import os
import shutil
import sys

from . import acquire_puppetdb
from . import acquire_switches

DATADIR_PUPPETDB = "data/puppetdb/"
DATADIR_SWITCHES = "data/switches/"


def read_switch_device_options():
    devices = {}
    device_parser = configparser.ConfigParser()
    device_parser.read("data/switches.ini")
    for device_name in device_parser.sections():
        d = {}
        for option, value in device_parser[device_name].items():
            d[option] = value
        if "ip" not in d:
            d["ip"] = device_name
        devices[device_name] = d
    return devices


def clean_datadir(datadir):
    if os.path.exists(datadir):
        shutil.rmtree(datadir)
    os.makedirs(datadir)


def do_acquire_switches():
    datadir = DATADIR_SWITCHES
    clean_datadir(datadir)
    devices = read_switch_device_options()
    for device_name, device_options in devices.items():
        acquire_switches.acquire(device_name, device_options, datadir)


def do_acquire_puppetdb():
    datadir = DATADIR_PUPPETDB
    clean_datadir(datadir)
    device_parser = configparser.ConfigParser()
    device_parser.read("data/puppetdb.ini")
    for device_name in device_parser.sections():
        acquire_puppetdb.acquire(device_name, {}, datadir)


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
    from .configure import configure
    from .configure_formatters import format_for

    switch_device_options = read_switch_device_options() if apply_changes else None

    switches = acquire_switches.read_switches(DATADIR_SWITCHES)

    hosts_fc = acquire_puppetdb.read_fibrechannel(DATADIR_PUPPETDB)
    hosts_ipmi = acquire_puppetdb.read_ipmi(DATADIR_PUPPETDB)
    hosts_lldp = acquire_puppetdb.read_lldp(DATADIR_PUPPETDB)
    hosts_networking = acquire_puppetdb.read_networking(DATADIR_PUPPETDB)

    configure(switches, hosts_fc, hosts_ipmi, hosts_lldp, hosts_networking)

    for switchname, switch in switches.items():
        linesets = format_for(switch)
        if not linesets:
            continue

        print("--", switchname)
        lines = []
        for lineset in linesets:
            lines.extend(lineset)

        if apply_changes:
            acquire_switches.apply_config(switchname, switch_device_options[switchname], lines)
        else:
            print("\n".join(lines))


def main(args):
    action = args[1]
    ok = False

    if action == "configure":
        do_configure(False)
        ok = True

    if action == "configure-apply":
        do_configure(True)
        ok = True

    if action in ("acquire", "acquire-puppetdb"):
        do_acquire_puppetdb()
        ok = True

    if action in ("acquire", "acquire-switches"):
        do_acquire_switches()
        ok = True

    if not ok:
        print("Usage: %s ACTION" % args[0])
        print()
        print("Where ACTION is one of:")
        print("  * configure")
        print("  * configure-apply")
        print("  * acquire")
        print("  * acquire-puppetdb")
        print("  * acquire-switches")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
