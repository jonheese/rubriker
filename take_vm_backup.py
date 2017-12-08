#!/usr/bin/env python

import sys, time, json
from rubriker import Rubriker
from config import rubrik_locations


quiet = False
print "This will take an on-demand snapshot backup of the provided VM."
if len(sys.argv) > 1:
    location_name = sys.argv[1]
    arg_offset = 1
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
if len(sys.argv) > 1:
    vm_names = sys.argv[2:]
else:
    vm_names[0] = raw_input("Enter VM name: ")

print "doing VM API call"
vms = rubriker.do_api_call("api/v1/vmware/vm?limit=9999")['data']

for vm_name in vm_names:
    vm_id = None
    for vm in vms:
        if vm['name'] == vm_name:
            vm_id = vm['id']
            if "configuredSlaDomainId" in vm:
                sla_id = vm['configuredSlaDomainId']
            else:
		# if the VM doesn't have an SLA today, just grab the third one, because
                #     it happens that the third SLA in abe01 is "Daily - 14d" (this is kinda shitty)
                sla_id = rubriker.do_api_call("api/v1/sla_domain", method="GET")["data"][0]["id"]
            break

    if vm_id is None or vm_id == "":
        print "Unable to locate VM named %s, please check the name and try again." % vm_name
        continue
        #sys.exit(1)

    json_data = "{\"slaId\": \"%s\"}" % sla_id
    print "Submitting backup request for VM %s (%s)..." % (vm_name, vm_id)
    json_results = rubriker.do_api_call("api/v1/vmware/vm/%s/snapshot" % vm_id, json_data)

    job_id = None
    if "status" in json_results.keys():
        status = json_results['status']
        if status == "Success" or status == "QUEUED" or status == "ACQUIRED":
            job_id = json_results['id']
            print "Successfully submited job for %s" % vm_name
        else:
            print "Error submitting job. Status: %s" % status
    else:
        print "Error submitting job. Results: %s" % str(json_results)

    # Only show progress bar if this is a 1 VM request
    if len(vm_names) > 1:
        continue

    status = ""
    error_info = "None"

    if not quiet:
        while job_id is not None:
            json_data = "{\"jobId\": \"%s\"}" % job_id
            request_status = rubriker.do_api_call("api/v1/vmware/vm/request/%s" % job_id)
            if request_status is not None:
                if request_status['status'] != status or request_status['progress'] != progress:
                    if "progress" in request_status:
                        progress = request_status['progress']
                    else:
                        progress = None
                    status = request_status['status']
                    print "Status: %s, Progress: %s             Error: %s" % (status, progress, error_info)
                if 'error' in request_status.keys() and request_status['error'] is not None and request_status['error']['message'] != error_info:
                    error_info = request_status['error']['message']
                    print "Status: %s             Error: %s" % (status, error_info)

                if status == "FAILED" or status == "SUCCEEDED":
                    break
                time.sleep(1)
    else:
        print "Job queued successfully."
        continue
    print "Complete."
