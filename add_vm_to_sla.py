#!/usr/bin/env python

import sys, time, json
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

managed_id = None
vm_id = None
try:
    vms = rubriker.do_api_call("api/v1/vmware/vm")['data']
    for vm in vms:
        if vm['name'] == vm_name:
            managed_id = vm['managedId']
            vm_id = vm['id']
            break
except Exception as e:
    print "Unable to locate any data for vm %s" % vm_name
    exit(0)

if managed_id is None or managed_id == "":
    print "Unable to locate VM named %s, please check the name and try again." % vm_name
    sys.exit(1)

desired_sla_id = None
slas = rubriker.do_api_call("api/v1/sla_domain")['data']
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

print "Assigning managed_id %s to sla_id %s" % (managed_id, desired_sla_id)
json_data = "{\"managedIds\": [ \"%s\" ] }" % managed_id
rubriker.do_api_call("api/v1/sla_domain/%s/assign_sync" % desired_sla_id, json_data)

vm_data = rubriker.do_api_call("api/v1/vmware/vm/%s" % vm_id)
try:
    confd_sla_id = vm_data['slaDomain']['id']
    if confd_sla_id == desired_sla_id:
        sla_name = vm_data['slaDomain']['name']
        print "Successfully set SLA for VM %s to %s" % (vm_name, sla_name)
    else:
        raise Exception()
except Exception as e:
    print "There was an error setting the SLA to %s for VM %s.  Please check the Rubrik interface." % (desired_sla_id, vm_name)
