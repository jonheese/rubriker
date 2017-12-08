#!/usr/bin/env python

import json, sys
from rubriker import Rubriker
from config import rubrik_locations


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
    api_call = sys.argv[1]
else:
    api_call = raw_input("Enter desired API URL: ")

if api_call is None or api_call == "":
    print "You must enter an API endpoint."
    sys.exit(1)

if len(sys.argv) > 2:
    method = sys.argv[2]
else:
    method = raw_input("Enter desired HTTP method (GET, POST, etc.): ")

if not api_call.startswith("api/v1") and not api_call.startswith("api/internal"):
    api_call = "api/v1/%s" % api_call

print json.dumps(rubriker.do_api_call(api_call, method=method), sort_keys=True, indent=4, separators=(',',': '))
rubriker.logout_of_api()
