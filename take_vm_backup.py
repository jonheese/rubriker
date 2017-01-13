#!/usr/bin/env python

import sys, time, json
from rubriker import Rubriker
from config import rubrik_locations


print "This will take an on-demand snapshot backup of the provided VM."
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

vm_id = None
print "doing VM API call"
vms = rubriker.do_api_call("api/v1/vmware/vm")['data']
for vm in vms:
    if vm['name'] == vm_name:
        vm_id = vm['id']
        break

if vm_id is None or vm_id == "":
    print "Unable to locate VM named %s, please check the name and try again." % vm_id
    sys.exit(1)

json_data = "{\"vmId\": \"%s\", \"isOnDemandSnapshot\": true}" % vm_id
print "Submitting backup request for VM %s (%s)..." % (vm_name, vm_id)
json_results = rubriker.do_api_call("api/internal/job/type/backup", json_data)

job_id = None
if "status" in json_results.keys():
    status = json_results['status']
    if status == "Success":
        job_id = json_results['description']
    else:
        print "Error submitting job. Status: %s" % status
else:
    print "Error submitting job. Results: %s" % str(json_results)

status = ""
error_info = "None"

while job_id is not None:
    json_data = "{\"jobId\": \"%s\"}" % job_id
    request_status = rubriker.do_api_call("api/v1/vmware/vm/request/%s" % job_id)
    if request_status is not None:
        if request_status['status'] != status:
            status = request_status['status']
            print "Status: %s             Error: %s" % (status, error_info)
        if 'error' in request_status.keys() and request_status['error'] is not None and request_status['error']['message'] != error_info:
            error_info = request_status['error']['message']
            print "Status: %s             Error: %s" % (status, error_info)

        if status == "FAILED" or status == "SUCCEEDED":
            break
        time.sleep(1)
print "Complete."
