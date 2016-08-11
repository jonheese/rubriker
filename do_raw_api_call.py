#!/usr/bin/env python

import json, sys
from rubriker import do_api_call


if len(sys.argv) > 1:
    api_call = sys.argv[1]
else:
    api_call = raw_input("Enter desired API URL: ")

if api_call is None or api_call == "":
    print "You must enter an API URL."
    sys.exit(1)

print json.dumps(do_api_call(api_call), sort_keys=True, indent=4, separators=(',',': '))
