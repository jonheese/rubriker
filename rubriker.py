#!/usr/bin/env python

import urllib2, json, base64, sys, socket, time
from config import conflux_user, conflux_pass, conflux_url, bsm_hosts


class Rubriker(object):
    def __init__(self, location, rubrik_user, rubrik_pass, rubrik_url):
        self.location = location
        self.__rubrik_user = rubrik_user
        self.__rubrik_pass = rubrik_pass
        self.__rubrik_url = rubrik_url
        self.__rubrik_token = None
        self.__rubrik_token_expires = 0
        self.__conflux_devices = None
        self.__rubrik_version = None


    def login_to_api(self):
        print("Logging in to Rubrik at URL %s..." % self.__rubrik_url)
        json_results = self.do_api_call("api/v1/session", json_data="{}")

        if json_results is None or len(json_results) == 0 or json_results['token'] is None:
            print( "Couldn't log in.")
            print(json_results)
            sys.exit(1)

        self.__rubrik_token = json_results['token']
        print("Logged in, token: %s" % self.__rubrik_token)
        self.__rubrik_token_expires = int(time.time() + 10800)


    def logout_of_api(self):
        print("Logging out of Rubrik API")
        self.do_api_call("api/v1/session/me", json_data="{}", method="DELETE")


    def do_api_call(self, endpoint, json_data=None, method="POST", quiet=False):
        json_results = {}
        url =  "%s/%s" % (self.__rubrik_url, endpoint)
        request = urllib2.Request(url)

        if endpoint != "api/v1/session":
            if self.__rubrik_token is None or self.__rubrik_token_expires < time.time():
                self.login_to_api()
            request.add_header("Authorization", "Bearer %s" % self.__rubrik_token)
        else:
            auth_string = base64.b64encode(("%s:%s" % (self.__rubrik_user, self.__rubrik_pass)).replace('\n', ''))
            request.add_header("Authorization", "Basic %s" % auth_string)

        try:
            if json_data is not None:
                if method is not "POST":
                    request.get_method = lambda: method
                handle = urllib2.urlopen(request, json_data)
            else:
                handle = urllib2.urlopen(request)
            output = handle.read()

            try:
               if output is not None and output != "":
                   json_results = json.loads(output)
            except Exception:
                print("Failure parsing JSON data: %s" % output)
        except urllib2.URLError as url_e:
            if hasattr(url_e, "reason"):
                if not quiet:
                    print("Got error: %s, hitting URL: %s, with method: %s" % (url_e.reason, url, method))
                if url_e.reason == "Unauthorized":
                    self.__rubrik_token_expires = 0
                    json_results = self.do_api_call(endpoint, json_data, method)
                elif not quiet:
                    print(
                        "We failed to reach the Rubrik API."
                        " URL: %s"
                        " Reason: %s" %
                        (url, url_e.reason)
                    )
            elif hasattr(url_e, "code") and not quiet:
                print(
                    "Rubrik API couldn't fulfill the request."
                    " URL: %s"
                    " Error Code: %s" %
                    (url, url_e.code)
                )

        return json_results


    def get_rubrik_version(self):
        if not self.__rubrik_version:
            self.__rubrik_version = float(".".join(self.do_api_call("api/v1/cluster/me/version")["version"].split(".")[:2]))
        return self.__rubrik_version


    def get_conflux_details_by_short_name(self, shortname):
        global conflux_url, conflux_user, conflux_pass
        if self.__conflux_devices is None:
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
                        self.__conflux_devices = json_results['Data']
                else:
                    print("API FAILURE: %s" % shortname)
            print("Done.")

        for device in self.__conflux_devices:
            if device is not None and device['DeviceName'] == shortname:
                return device

        return None


    def render_progress_bar(self, percentage=0, status="", error_info=""):
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
        print "{0} [{1}] {2}% {3} {4}\r".format("00:00:00", prog_bar, percentage, status, error_info),
