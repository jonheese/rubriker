#!/usr/bin/env python

import sys, time, json
from rubriker import Rubriker
from config import rubrik_locations


print "This will add the provided VM to the selected SLA."
location_names = rubrik_locations.keys()
index = 1

if len(sys.argv) > 1:
    location_name = sys.argv[1]
    quiet = True
else:
    location_names = rubrik_locations.keys()
    index = 1
    for location_name in location_names:
        print "%d. %s" % (index, location_name)
        index += 1
    index = int(raw_input("Choose a Rubrik cluster: ")) - 1
    location_name = location_names[index]

config_dict = rubrik_locations[location_name]
rubriker = Rubriker(location_name, config_dict["rubrik_user"], config_dict["rubrik_pass"], config_dict["rubrik_url"])

vm_names = []
if len(sys.argv) > 3:
    vm_names = sys.argv[3:]
else:
    vm_names[0] = raw_input("Enter VM name: ")
    if vm_name == "":
        print "You must specify a VM."
        sys.exit(1)

vms = rubriker.do_api_call("api/v1/vmware/vm")['data']
for vm_name in vm_names:
    vm_id = None
    try:
        for vm in vms:
            if vm['name'] == vm_name:
                vm_id = vm['id']
                break
    except Exception as e:
        print "Unable to locate any data for vm %s" % vm_name
        continue

    if vm_id is None:
        print "Couldn't find vm %s, skipping..." % vm_name
        continue

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
             continue
    else:
        index = 1
        for sla in slas:
            print "%s. %s" % (index, sla['name'])
            index += 1
        index = int(raw_input("Selection? ")) - 1
        desired_sla_id = slas[index]['id']

    print "Assigning vm_id %s to sla_id %s" % (vm_id, desired_sla_id)
    json_data = "{\"managedIds\": [ \"%s\" ] }" % vm_id
    rubriker.do_api_call("api/internal/sla_domain/%s/assign" % desired_sla_id, json_data)

    vm_data = rubriker.do_api_call("api/v1/vmware/vm/%s" % vm_id)
    try:
        confd_sla_id = vm_data['configuredSlaDomainId']
        if confd_sla_id == desired_sla_id:
            sla_name = vm_data['configuredSlaDomainName']
            print "Successfully set SLA for VM %s to %s" % (vm_name, sla_name)
        else:
            raise Exception()
    except Exception as e:
        raise e
        print "There was an error setting the SLA to %s for VM %s.  Please check the Rubrik interface." % (desired_sla_id, vm_name)
