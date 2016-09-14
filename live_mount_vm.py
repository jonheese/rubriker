#!/usr/bin/env python

import sys, time
from rubriker import Rubriker
from config import rubrik_locations


print "This will perform a live mount of a snapshot backup of the provided VM."
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
    print "Unable to locate VM named %s, please check the name and try again." % vm_name
    sys.exit(1)

print "Gathering snapshots available for %s (id: %s)..." % (vm_name, vm_id)
snapshots = rubriker.do_api_call("snapshot?vm=%s" % vm_id)
if snapshots is None or len(snapshots) <= 0:
    print "No snapshots found for VM %s." % vm_name
    sys.exit(0)

print "Select the snapshot you would like to mount:"
count = 1
for snapshot in snapshots:
    print "%s. %s" % (count, snapshot['date'])
    count = count + 1
index = int(raw_input("Selection? ")) - 1

snapshot_id = snapshots[index]['id']

print "Getting ESXi host for VM %s..." % vm_name
host_id = ""
vms = rubriker.do_api_call("vm")
for vm in vms:
    if vm['id'] == vm_id:
        host_id = vm['hostId']
        break

print "Getting datastore for VM %s..." % vm_name
datastore_name = ""
vm = rubriker.do_api_call("vm/%s" % vm_id)
virtual_disk_ids = vm['virtualDiskIds']

datastores = rubriker.do_api_call("datastore")
for datastore in datastores:
    datastore_id = datastore['id']
    ds_detail = rubriker.do_api_call("datastore/%s" % datastore_id)
    if "virtualDisks" in ds_detail.keys():
        virtual_disks = ds_detail['virtualDisks']
        for virtual_disk in virtual_disks:
            if virtual_disk['id'] in virtual_disk_ids:
                datastore_name = datastore['name']
                break

json_data = "{\"snapshotId\": \"%s\", \"hostId\": \"%s\", \"vmName\": \"%s_LIVE_MOUNT\", \"dataStoreName\": \"%s\", \"disableNetwork\": true, \"removeNetworkDevices\": true}" % (snapshot_id, host_id, vm_name, datastore_name)

print "Submitting mount request for VM %s (%s)..." % (vm_name, vm_id)
job_id = rubriker.do_api_call("job/type/mount", json_data)

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
