# switchportlabel
Tool to label switchports on Cisco NXOS and HP Comware7 devices.

Data acquisition is done using PuppetDB for hosts and direct SSH for switches.

# Quickstart

* Copy `facter/*.rb` into your Puppet setup, so all physical hosts collect the `fibrechannel` and `lldp` information.

On a sufficiently privileged host, with Python 3 (preferably 3.7):

* `pip3 install -r requirements.txt`
* `edit data/*.ini`   # based upon data/*.ini.tpl

Update cached data:
* `python3 -m switchportlabel acquire`

Preview changes:
* `python3 -m switchportlabel configure`

Apply changes to switches:
* `python3 -m switchportlabel configure-apply`

# PuppetDB hints

As PuppetDB is usually not accessible except from localhost, `acquire`/`acquire-puppetdb` connect using `ssh` to the PuppetDB host and call `curl` there.

This requires SSH to work with no further configuration: username, ssh-key must come from the OpenSSH client configuration.

PuppetDB must be reachable on the default plaintext port 8080.

# Development info

* Python 3.7 was tested
* Code formatter: black
