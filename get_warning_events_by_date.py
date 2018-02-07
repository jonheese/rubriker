#!/usr/bin/python

import socket, time, json, sys
from datetime import datetime, timedelta
from config import rubrik_locations
from rubriker import Rubriker


location_name = "abe01lab"
start_date="2018-01-07"
end_date="2018-01-08"
config_dict = rubrik_locations[location_name]

results = {}

rubriker = Rubriker(location_name, config_dict["rubrik_user"], config_dict["rubrik_pass"], config_dict["rubrik_url"])
vms = rubriker.do_api_call("vmware/vm?is_relic=false&sla_assignment=Direct")["data"]
for vm in vms:
    vm_name = vm["name"]
    event = rubriker.do_api_call("api/internal/event?event_type=Backup&object_ids=%s&object_type=VmwareVm&after_data=%s&before_date=%s" % (vm["id"], start_date, end_date))["data"]
    event_series = rubriker.do_api_call("api/internal/event_series/%s" % event["eventSeriesId"])["data"]
    for event_log in event_series:
        if event_log["status"] == "Warning":
            if vm_name not in results:
                results[vm_name] = {}
            message = json.loads(event_log["event_info"])["message"]
            results[vm_name][event_log["id"]] = (event_log["time"], message)

for vm_name in results.keys():
    print "%s:" % vm_name
    events = results[vm_name]
    for event_log in events.keys():
        print "  %s" % message
