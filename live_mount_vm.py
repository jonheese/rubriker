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
host_id = None
vms = rubriker.do_api_call("api/v1/vmware/vm")['data']
for vm in vms:
    if vm['name'] == vm_name:
        vm_id = vm['id']
        host_id = vm['hostId']
        break

if vm_id is None or vm_id == "":
    print "Unable to locate VM named %s, please check the name and try again." % vm_name
    sys.exit(1)

print "Gathering snapshots available for %s (id: %s)..." % (vm_name, vm_id)
snapshots = rubriker.do_api_call("api/v1/vmware/vm/%s/snapshot" % vm_id)['data']
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

print "Getting datastore for VM %s..." % vm_name
datastore_name = None
vm = rubriker.do_api_call("api/v1/vmware/vm/%s" % vm_id)['data']
virtual_disk_ids = vm['virtualDiskIds']

datastores = rubriker.do_api_call("api/v1/vmware/datastore")['']
for datastore in datastores:
    datastore_id = datastore['id']
    ds_detail = rubriker.do_api_call("api/v1/vmware/datastore/%s" % datastore_id)
    if "virtualDisks" in ds_detail.keys():
        virtual_disks = ds_detail['virtualDisks']
        for virtual_disk in virtual_disks:
            if virtual_disk['id'] in virtual_disk_ids:
                datastore_name = datastore['name']
                break
    if datastore_name is not None:
        break

if datastore_name is None:
    print "Unable to locate datastore for vm %s" % vm_name
    sys.exit(0)

json_data = "{\"snapshotId\": \"%s\", \"hostId\": \"%s\", \"vmName\": \"%s_LIVE_MOUNT\", \"dataStoreName\": \"%s\", \"disableNetwork\": true, \"removeNetworkDevices\": true, \"powerOn\": true}" % (snapshot_id, host_id, vm_name, datastore_name)

print "Submitting mount request for VM %s (%s)..." % (vm_name, vm_id)
mount_id = rubriker.do_api_call("api/v1/vmware/vm/mount", json_data)['id']


mount_ready = None
while mount_id is not None:
    mount_data = rubriker.do_api_call("api/v1/vmware/vm/mount/%s" % mount_id)
    if mount_data is not None:
        if mount_ready != mount_data['isReady']:
            mount_ready = mount_data['isReady']
            if mount_ready != 1 and mount_data['isReady'] != "1":
                print "Waiting for live mount to complete..."
            else:
                print "Live mount complete."
        time.sleep(1)
