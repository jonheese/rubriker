<<<<<<< HEAD
=======
#!/usr/bin/python

>>>>>>> 2d766bb064bbe340bf5f0ac73c530e74bb1e50e5
import socket, time, json, sys
from datetime import datetime, timedelta
from config import rubrik_locations
from rubriker import Rubriker


<<<<<<< HEAD
start_date="2018-01-07"
end_date="2018-01-10"

early_cutoff_time = datetime.strptime("2018-01-07 20:00:00 EST", "%Y-%m-%d %H:%M:%S %Z")
breakpoint_time = datetime.strptime("2018-01-08 20:00:00 EST", "%Y-%m-%d %H:%M:%S %Z")
late_cutoff_time = datetime.strptime("2018-01-09 20:00:00 EST", "%Y-%m-%d %H:%M:%S %Z")
location_name = "abe01"

config_dict = rubrik_locations[location_name]
results = {}

rubriker = Rubriker(location_name, config_dict["rubrik_user"], config_dict["rubrik_pass"], config_dict["rubrik_url"])
try:
    vms = rubriker.do_api_call("api/v1/vmware/vm?is_relic=false&sla_assignment=Direct")["data"]
    for vm in vms:
        before_events = []
        after_events = []
        vm_name = vm["name"]
        events = rubriker.do_api_call("api/internal/event?event_type=Backup&object_ids=%s&object_type=VmwareVm&after_date=%s&before_date=%s" % (vm["id"], start_date, end_date))["data"]
        for event in events:
            event_series = rubriker.do_api_call("api/internal/event_series/%s" % event["eventSeriesId"])["data"]
            for event_log in event_series:
                if event_log["status"] == "Warning":
                    if vm_name not in results:
                        results[vm_name] = {}
                    message = json.loads(event_log["eventInfo"])["message"]
                    results[vm_name][event_log["id"]] = (event_log["time"], message)
        if vm_name in results.keys():
            events = results[vm_name]
            for event_id in events.keys():
                (time, message) = events[event_id]
                event_time = datetime.strptime(time, "%a %b %d %H:%M:%S %Z %Y")
                if event_time < early_cutoff_time or event_time > late_cutoff_time:
                    continue
                if event_time < breakpoint_time:
                    if message not in before_events:
                        before_events.append(message)
                else:
                    if message not in after_events:
                        after_events.append(message)

            reported_events = []
            for message in before_events:
                if message in after_events:
#                    print "%s - %s" % (vm_name, message)
                    continue
                if message in reported_events:
                    continue
                print "%s - %s" % (vm_name, message)
                reported_events.append(message)
finally:
    rubriker.logout_of_api()
=======
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
>>>>>>> 2d766bb064bbe340bf5f0ac73c530e74bb1e50e5
