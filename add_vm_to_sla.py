#!/usr/bin/env python

import sys, time
from rubriker import Rubriker
from config import rubrik_locations


print "This will add the provided VM to the selected SLA."
location_names = rubrik_locations.keys()
index = 1
for location_name in location_names:
    print "%d. %s" % (index, location_name)
    index += 1
index = int(raw_input("Choose a Rubrik cluster: ")) - 1
location_name = location_names[index]
config_dict = rubrik_locations[location_name]
rubriker = Rubriker(location_name, config_dict["rubrik_user"], config_dict["rubrik_pass"], config_dict["rubrik_url"])

if len(sys.argv) > 1:
    vm_name = sys.argv[1]
else:
    vm_name = raw_input("Enter VM name: ")
    if vm_name == "":
        print "You must specify a VM."
        sys.exit(1)

vm_id = None
vms = rubriker.do_api_call("vm")
for vm in vms:
    if vm['name'] == vm_name:
        vm_id = vm['id']
        break

if vm_id is None or vm_id == "":
    print "Unable to locate VM named %s, please check the name and try again." % vm_name
    sys.exit(1)

desired_sla_id = None
slas = rubriker.do_api_call("slaDomain")
if len(sys.argv) > 2:
    sla_name = sys.argv[2]
    for sla in slas:
        if sla['name'] == sla_name:
            desired_sla_id = sla['id']
            break
    if desired_sla_id is None:
         print "Unable to locate SLA named %s, please check the name and try again." % sla_name
         sys.exit(1)
else:
    index = 1
    for sla in slas:
        print "%s. %s" % (index, sla['name'])
        index += 1
    index = int(raw_input("Selection? ")) - 1
    desired_sla_id = slas[index]['id']

json_data = "{\"slaDomainId\": \"%s\"}" % desired_sla_id
vm_data = rubriker.do_api_call("vm/%s" % vm_id, json_data, 'PATCH')

confd_sla_id = vm_data['configuredSlaDomainId']
if confd_sla_id == desired_sla_id:
    sla_name = "ERROR!"
    for sla in slas:
        if sla['id'] == confd_sla_id:
            confd_sla_name = sla['name']
            break
    print "Successfully set SLA for VM %s to %s" % (vm_name, confd_sla_name)
else:
    print "There was an error setting the SLA to %s for VM %s.  Please check the Rubrik interface." % (desired_sla_id, vm_name)
