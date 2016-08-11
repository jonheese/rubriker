#!/usr/bin/env python

from config import rubrik_user, rubrik_pass, conflux_user, conflux_pass
from rubriker import do_api_call, get_conflux_details_by_short_name


print "Looking up VMs in Rubrik API..."
vms = do_api_call("report/slaCompliance/detail")
print "Done."


found = 0
no_fqdn = 0
not_found = 0
for vm in vms:
    sla_name = vm['slaDomainName']
    if sla_name is not None and sla_name != "Unprotected":
         vm_name = vm['vmName']
         compliant = vm['isSlaCompliant']
         device = get_conflux_details_by_short_name(vm_name)
         if device is not None:
             if "DeviceFqdn" in device.keys() and device['DeviceFqdn'] is not None:
                 print "%s : %s => %s" % (compliant, vm_name, device['DeviceFqdn'])
                 found = found + 1
             else:
                 print "%s : %s found in Conflux, but has no FQDN" % (compliant, vm_name)
                 no_fqdn = no_fqdn + 1
         else:
             print "%s : %s not found in Conflux" % (compliant, vm_name)
             not_found = not_found + 1

total_devices = found + no_fqdn + not_found
print ""
print "Report:"
print "==============================="
print "Devices with FQDNs:           %s" % found
print "Devices with no FQDNs:        %s" % no_fqdn
print "Devices not found in Conflux: %s" % not_found
print "Devices:                      %s" % total_devices
