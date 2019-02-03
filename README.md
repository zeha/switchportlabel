# switchportlabel
Tool to label switchports on Cisco NXOS and HP Comware7 devices

# Quickstart

* Copy `facter/fibrechannel.rb` into your Puppet setup, so all physical hosts collect the `fc_host` information.

On a sufficiently privileged host, with Python 3 (preferably 3.7):

* `pip3 install -r requirements.txt`
* `edit data/*.ini`   # based upon data/*.ini.tpl

Update cached data:
* `python3 -m switchportlabel acquire-switches`
* `python3 -m switchportlabel acquire-puppetdb`
* XXX: implement acquire-lldpcli

Preview changes:
* `python3 -m switchportlabel configure`

Apply changes to switches:
* `python3 -m switchportlabel configure-apply`

# Development info

* Python 3.7 was tested
* Code formatter: black
