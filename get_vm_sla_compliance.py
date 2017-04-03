#!/usr/bin/env python

from config import rubrik_locations
from rubriker import Rubriker


def get_rubrik_report(report_name):
    rubrik_reports = rubriker.do_api_call("api/internal/report?report_type=Canned")['data']
    report_id = None
    for report in rubrik_reports:
        if report['reportName'] == report_name:
            report_id = report['id']
            break
    if report_id == None or report_id == "":
        return None

    return rubriker.do_api_call("api/internal/report/%s/table?timezone_offset=0&limit=1000000" % report_id)['data']


for location in rubrik_locations.keys():
    config_dict = rubrik_locations[location]
    rubrik_user = config_dict["rubrik_user"]
    rubrik_pass = config_dict["rubrik_pass"]
    rubrik_url = config_dict["rubrik_url"]
    rubriker = Rubriker(location, rubrik_user, rubrik_pass, rubrik_url)

    print "Looking up VMs in Rubrik API..."
    vms = get_rubrik_report("SlaComplianceSummary")
    print "Done."

    found = 0
    no_fqdn = 0
    not_found = 0
    for vm in vms:
        sla_name = vm['slaDomainName']
        if sla_name is not None and sla_name != "Unprotected":
            vm_name = vm['objectName']
            compliant = vm['isSlaCompliant']
            device = rubriker.get_conflux_details_by_short_name(vm_name)
            if device is not None:
                if "DeviceFqdn" in device.keys() and device['DeviceFqdn'] is not None:
                    #print "%s : %s => %s" % (compliant, vm_name, device['DeviceFqdn'])
                    found = found + 1
                else:
                    print "%s : %s found in Conflux, but has no FQDN" % (compliant, vm_name)
                    no_fqdn = no_fqdn + 1
            else:
                print "%s : %s not found in Conflux" % (compliant, vm_name)
                not_found = not_found + 1

    total_devices = found + no_fqdn + not_found
    print ""
    print "Report for %s:" % location
    print "==============================="
    print "Devices with FQDNs:           %s" % found
    print "Devices with no FQDNs:        %s" % no_fqdn
    print "Devices not found in Conflux: %s" % not_found
    print "Devices:                      %s" % total_devices
