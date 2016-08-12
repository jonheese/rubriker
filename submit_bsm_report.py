#!/usr/bin/env python

import json, time, calendar, math, subprocess
from rubriker import do_api_call, get_conflux_details_by_short_name

snapshot_counts = dict()
capacity_details = do_api_call("report/systemCapacity/detail")

json_data = json.dumps({"reportType": "daily"})
jobs = do_api_call("report/backupJobs/detail", json_data)
for job in jobs:
    job_type = job['jobType']
    misc_data = job['status']
    if job_type != "Backup" or misc_data == "Running":
        continue
    job_id = job['jobId']
    vm_id = job['vmId']
    vm_name = job['vmName']
    fqdn = vm_name
    device = get_conflux_details_by_short_name(vm_name)
    if device is not None and "DeviceFqdn" in device.keys() and device['DeviceFqdn'] is not None:
        fqdn = device['DeviceFqdn']
    else:
        continue

    if misc_data == "Succeeded":
        status = 0
    else:
        status = 1
        if "failureDescription" in job.keys():
            misc_data = job['failureDescription']

    start_time = calendar.timegm(time.strptime(job['startTime'], "%Y-%m-%dT%H:%M:%S+0000"))
    try:
        end_time = calendar.timegm(time.strptime(job['endTime'], "%Y-%m-%dT%H:%M:%S+0000"))
    except Exception as e:
        end_time = ""

    size = 0
    if "transferredBytes" in job.keys(): 
        size = int(job['transferredBytes'])

    used = 0
    for detail in capacity_details:
        if detail['vmId'] == vm_id:
            used = int(int(detail['totalStorage']) / 1024)
            break

    total = int(1024 * 1024 * 1024 * max(1, math.ceil(float(used) / 1024 / 1024 / 1024)))

    # Always set level to Synthetic Full, since that's what Rubrik is always doing on the backend
    level = "S"

    snapshot_count = 0
    if vm_id in snapshot_counts.keys():
        snapshot_count = snapshot_counts[vm_id]
    else:
        vm_details = do_api_call("vm/%s" % vm_id)
        if "snapshotCount" in vm_details.keys():
            snapshot_count = vm_details['snapshotCount']
            snapshot_counts[vm_id] = snapshot_count

    nsca_message = "%s\tRubrik Backups\t%s\trubrik::%s::%s::%s::%s::%s::::%s::%s::::::::::%s\n" % (fqdn, status, used, total, start_time, end_time, level, snapshot_count, size, misc_data)
    process = subprocess.Popen(['/usr/local/nagios/bin/send_nsca', '-H', 'localhost', '-p', '5667', '-c', '/usr/local/nagios/etc/send_nsca.cfg'], stdin=subprocess.PIPE)
    process.communicate(nsca_message)
    print nsca_message,
