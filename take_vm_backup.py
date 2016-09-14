#!/usr/bin/env python

import sys, time
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
vms = rubriker.do_api_call("vm")
for vm in vms:
    if vm['name'] == vm_name:
        vm_id = vm['id']
        break

if vm_id is None or vm_id == "":
    print "Unable to locate VM named %s, please check the name and try again." % vm_id
    sys.exit(1)

json_data = "{\"vmId\": \"%s\"}" % vm_id
print "Submitting backup request for VM %s (%s)..." % (vm_name, vm_id)
json_results = rubriker.do_api_call("job/type/backup", json_data)

job_id = None
if "status" in json_results.keys():
    status = json_results['status']
    if status == "Success":
        job_id = json_results['description']
    else:
        print "Error submitting job. Status: %s" % status
else:
    print "Error submitting job. Results: %s" % str(json_results)

while job_id is not None:
    progress = rubriker.do_api_call("job/instance/%s" % job_id)
    percentage = 0
    status = ""
    error_info = ""
    if progress is not None:
        if "jobProgress" in progress.keys():
            percentage = progress['jobProgress']
        if "status" in progress.keys():
            status = progress['status']
        if "errorInfo" in progress.keys():
            error_info = progress['errorInfo']
        rubriker.render_progress_bar(percentage, status, error_info)
        if "endTime" in progress.keys():
            job_id = None
            print
#        else:
#            time.sleep(0.25)
print "Complete."
