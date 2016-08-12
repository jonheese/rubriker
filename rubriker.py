#!/usr/bin/env python

import urllib2, json, base64, sys, socket, time
from config import rubrik_user, rubrik_pass, conflux_user, conflux_pass, rubrik_host
from rubriker_token import token, expires

top_level_url = "http://%s" % rubrik_host

conflux_url = "https://conflux.inetu.net/ConfluxService/RestJson/Devices/?devicetype=SERVER&devicetype=GCCLOUD&devicetype=PRIVCLOUD&devicetype=CUSTOM%20VM"
token_file = "rubriker_token.py"

conflux_devices = None


def login_to_api():
    print("Logging in to Rubrik...")
    json_data = json.dumps({"userId": rubrik_user, "password": rubrik_pass})
    json_results = do_api_call("login", json_data)

    if json_results is None or json_results['status'] is None or json_results['status'] != "Success":
        print( "Couldn't log in.")
        print(json_results)
        sys.exit(1)

    global token, expires
    token = json_results['token']
    print("Logged in")
    expires = int(time.time() + 10800)

    with open(token_file, 'w') as f:
        f.truncate()
        f.write("token = \"%s\"\n" % token)
        f.write("expires = %s\n" % expires)


def do_api_call(endpoint, json_data=None):
    global token, expires, top_level_url
    json_results = None
    url =  "%s/%s" % (top_level_url, endpoint)
    request = urllib2.Request(url)

    if endpoint != "login":
        if token is None or expires < time.time():
            login_to_api()
        auth_string = base64.encodestring("%s:" % token).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % auth_string)

    try:
        if json_data is not None:
            handle = urllib2.urlopen(request, json_data)
        else:
            handle = urllib2.urlopen(request)
        output = handle.read()

        try:
           json_results = json.loads(output)
        except Exception:
            print("Failure parsing JSON data")
    except urllib2.URLError as url_e:
        if hasattr(url_e, "reason"):
            if "Connection timed out" in url_e.reason:
                rubrik_ip = socket.gethostbyname("inetu-rubrik.inetu.net")
                top_level_url = "https://%s" % rubrik_ip
                json_results = do_api_call(endpoint, json_data)
            else:
                print(
                    "We failed to reach the Rubrik API."
                    " URL: %s"
                    " Reason: %s" %
                    (url, url_e.reason)
                )
        elif hasattr(url_e, "code"):
            print(
                "Rubrik API couldn't fulfill the request."
                " URL: %s"
                " Error Code: %s" %
                (url, url_e.code)
            )

    return json_results


def get_conflux_details_by_short_name(shortname):
    global conflux_devices
    if conflux_devices is None:
        print("Gathering device data from Conflux...")
        passwd_man = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passwd_man.add_password(
            None,
            conflux_url,
            conflux_user,
            conflux_pass
        )
        auth_handler = urllib2.HTTPBasicAuthHandler(passwd_man)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        try:
            handle = urllib2.urlopen(conflux_url)
            output = handle.read()
            try:
                json_results = json.loads(output)
            except Exception:
                print("Failure parsing JSON data")
        except urllib2.URLError as url_e:
            if hasattr(url_e, "reason"):
                print(
                    "We failed to reach Conflux."
                    " Reason: %s" %
                    url_e.reason
                )
            elif hasattr(url_e, "code"):
                print(
                    "Conflux couldn't fulfill the request."
                    " Error Code: %s" %
                    url_e.code
                )

        if json_results is not None:
            if json_results["IsSuccess"]:
                if "Data" in json_results.keys():
                    conflux_devices = json_results['Data']
            else:
                print("API FAILURE: %s" % shortname)
        print("Done.")

    for device in conflux_devices:
        if device is not None and device['DeviceName'] == shortname:
            return device

    return None


def render_progress_bar(percentage=0, status="", error_info=""):
    prog_bar = ""
    char = 0
    percentage = int(float(percentage))
    while len(prog_bar) < 100:
        if len(prog_bar) < percentage:
            prog_bar = "%s=" % prog_bar
        elif len(prog_bar) == percentage:
            prog_bar = "%s>" % prog_bar
        else:
            prog_bar = "%s " % prog_bar
    print("{0} [{1}] {2}% {3} {4}\r".format("00:00:00", prog_bar, percentage, status, error_info),)
