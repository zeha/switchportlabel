# switchportlabel
Tool to label switchports on Cisco NXOS and HP Comware7 devices

# Quickstart

* Copy `facter/fibrechannel.rb` into your Puppet setup, so all physical hosts collect the `fc_host` information.

On a sufficiently privileged host:

* `pip3 install -r requirements.txt`
* `edit data/*.ini`   # based upon data/*.ini.tpl
* `python3 -m switchportlabel acquire-switches`
* `python3 -m switchportlabel acquire-puppetdb`
* `python3 -m switchportlabel configure`
* `python3 -m switchportlabel configure-apply`
