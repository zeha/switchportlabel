from glob import glob
from subprocess import check_call
import json


def ssh_curl_into_file(device_name, fact_name, outfile):
    query = (
        'query=["and",["=","node_state","active"],["=","name","' + fact_name + '"]]'
    ).replace('"', '\\"')
    command = [
        "ssh",
        device_name,
        "--",
        "curl",
        "-G",
        "http://localhost:8080/pdb/query/v4/facts",
        "--data-urlencode",
        query,
    ]
    check_call(command, stdout=outfile)


def acquire(device_name, connect_options, datadir):
    print("Connecting to", device_name)
    for fact_name in ["fibrechannel", "lldp"]:
        with open("%s/%s.%s.json" % (datadir, device_name, fact_name), "wt") as fp:
            ssh_curl_into_file(device_name, fact_name, fp)


def read_fibrechannel(datadir):
    data = {}
    for fn in glob("%s/*.fibrechannel.json" % datadir):
        with open(fn, "rt") as fp:
            for el in json.load(fp):
                if not el["value"]["hosts"]:
                    continue
                data[el["certname"]] = el["value"]["hosts"]
    return data


def read_lldp(datadir):
    ifaces = []
    for fn in glob("%s/*.lldp.json" % datadir):
        with open(fn, "rt") as fp:
            for el in json.load(fp):
                if not el["value"]["neighbors"]:
                    continue
                for iface_name, detail in el["value"]["neighbors"].items():
                    ifaces.append(
                        {
                            "switchname": detail["sysname"].split()[0],
                            "switchport": detail["portid"].split()[1],
                            "hostname": el["certname"],
                            "hostport": iface_name,
                        }
                    )

    return ifaces
