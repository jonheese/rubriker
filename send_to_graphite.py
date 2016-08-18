#!/usr/bin/env python

import socket, time, json, sys
from datetime import datetime, timedelta
from rubriker import do_api_call

CARBON_SERVER = "inetu-grphite01.inetu.net"
CARBON_PORT = 2003
METRIC_PREFIX = "rubrik.abe01"

# How often to gather and send data to Graphite, in seconds
SEND_INTERVAL_SECS = 300
SEND_INTERVAL = timedelta(seconds=SEND_INTERVAL_SECS)
ARMED=True


def send_to_graphite(metric, value, timestamp=time.time()):
    message = "%s.%s %s %d\n" % (METRIC_PREFIX, metric.replace(" ", ""), value, int(timestamp))
    print "%s" % message,
    if ARMED:
        sock = socket.socket()
        sock.connect((CARBON_SERVER, CARBON_PORT))
        sock.sendall(message)
        sock.close()


def send_if_recent(metric_name, value, last_entry):
    timestamp = datetime.strptime(last_entry, "%Y-%m-%dT%H:%M:%SZ")
    if datetime.utcnow() - timestamp <= SEND_INTERVAL:
        send_to_graphite(metric_name, value, (timestamp - datetime.utcfromtimestamp(0)).total_seconds())
        return True
    return False


def send_latest_stat(metric_name, endpoint, stat_name):
    json_results = do_api_call(endpoint)
    for result in json_results:
        send_if_recent(metric_name, result[stat_name], result['time'])


def send_singleton_stat(metric_name, endpoint):
    json_results = do_api_call(endpoint)
    send_if_recent(metric_name, json_results['value'], json_results['lastUpdateTime'])


def send_storage_stats():
    json_results = do_api_call("stats/systemStorage")
    last_entry = json_results['lastUpdateTime']
    if send_if_recent("storage.total_storage", json_results['total'], last_entry):
        send_if_recent("storage.used_storage", json_results['used'], last_entry)
        send_if_recent("storage.available_storage", json_results['available'], last_entry)


def send_storage_and_compression_stats():
    ingested_bytes = None
    snapshot_bytes = None
    json_results = do_api_call("stats/ingestedBytes")
    timestamp = datetime.strptime(json_results['lastUpdateTime'], "%Y-%m-%dT%H:%M:%SZ")
    if datetime.utcnow() - timestamp <= SEND_INTERVAL:
        ingested_bytes = json_results['value']
        send_to_graphite("performance.backend_ingested_bytes", ingested_bytes, (timestamp - datetime.utcfromtimestamp(0)).total_seconds())
    json_results = do_api_call("stats/physicalSnapshotStorage")
    timestamp = datetime.strptime(json_results['lastUpdateTime'], "%Y-%m-%dT%H:%M:%SZ")
    if datetime.utcnow() - timestamp <= SEND_INTERVAL:
        snapshot_bytes = json_results['value']
        send_to_graphite("storage.physical_snapshot_storage", snapshot_bytes, (timestamp - datetime.utcfromtimestamp(0)).total_seconds())
    if ingested_bytes is not None and snapshot_bytes is not None:
        reduction = (1 - (float(snapshot_bytes) / float(ingested_bytes))) * 100
        ratio = float(ingested_bytes) / float(snapshot_bytes)
        send_to_graphite("performance.compression.reduction", reduction, (timestamp - datetime.utcfromtimestamp(0)).total_seconds())
        send_to_graphite("performance.compression.ratio", ratio, (timestamp - datetime.utcfromtimestamp(0)).total_seconds())


def send_cross_compression_stats():
    json_results = do_api_call("stats/crossCompression")
    last_entry = json_results['lastUpdateTime']
    data = json.loads(json_results['value'])
    if send_if_recent("performance.compression.logical_bytes", data['logicalBytes'], last_entry):
        send_if_recent("performance.compression.logical_bytes", data['logicalBytes'], last_entry)
        send_if_recent("performance.compression.zero_bytes", data['zeroBytes'], last_entry)
        send_if_recent("performance.compression.precomp_bytes", data['preCompBytes'], last_entry)
        send_if_recent("performance.compression.postcomp_bytes", data['postCompBytes'], last_entry)
        send_if_recent("performance.compression.physical_bytes", data['physicalBytes'], last_entry)


def send_sla_stats():
    sla_domains = do_api_call("slaDomain?primaryClusterUuidOpt=local")
    for sla_domain in sla_domains:
        (sla_name, sla_id) = (sla_domain['name'], sla_domain['id'])
        send_singleton_stat("storage.sla_domain_storage.%s" % sla_name, "stats/slaDomainStorage/%s" % sla_id)
        send_to_graphite("storage.vms_protected.%s" % sla_name, sla_domain['numVms'])


def send_replication_storage_stats():
    replication_stats = do_api_call("stats/totalReplicationStorage")
    for remote in replication_stats['remoteVmStorageOnPremise']:
        send_to_graphite("replication.remote_vm_storage_locally", remote['stat'])
    for local in replication_stats['localVmStorageAcrossAllTargets']:
        send_to_graphite("replication.local_vm_storage_remotely", local['stat'])


def send_archival_storage_stats():
    location_details = do_api_call("data_location/archival_locations")
    location_storage = do_api_call("stats/data_location/usage")
    for location in location_storage:
        location_name = None
        location_id = location['locationId']
        for location_detail in location_details:
            if location_detail['id'] == location_id:
                location_name = "%s.%s" % (location_detail['locationType'], location_detail['bucket'])
                break
        if location_name is not None:
            send_to_graphite("archive.bytes_downloaded.%s" % location_name, location['dataDownloaded'])
            send_to_graphite("archive.bytes_archived.%s" % location_name, location['dataArchived'])
            send_to_graphite("archive.vms_archived.%s" % location_name, location['numVMsArchived'])
            send_latest_stat("archive.bandwidth.%s" % location_name, "stats/archival/bandwidth?data_location_id=%s" % location_id, "stat")


def send_all_data():
    send_to_graphite("system.briks", do_api_call("system/brik/count")['count'])
    send_to_graphite("memory.total_memory", do_api_call("system/memory/capacity")['bytes'])
    send_to_graphite("storage.disk_capacity", do_api_call("system/disk/capacity")['bytes'])
    send_to_graphite("storage.flash_capacity", do_api_call("system/flash/capacity")['bytes'])
    send_to_graphite("system.cpu_core_count", do_api_call("system/cpuCores/count/*")['count'])
    send_to_graphite("performance.streams", do_api_call("stats/streams")['count'])
    send_to_graphite("storage.average_storage_growth_per_day", do_api_call("stats/averageStorageGrowthPerDay")['bytes'])
    send_to_graphite("performance.runway_remaining", do_api_call("stats/runwayRemaining")['days'])
    send_to_graphite("storage.vms_in_vcenter", do_api_call("vm/count")['count'])
    send_to_graphite("performance.physical_ingest_per_day", do_api_call("stats/physicalIngestPerDay")[0]['stat']) 

    send_latest_stat("performance.logical_ingest", "stats/logicalIngest", "stat")
    send_latest_stat("performance.physical_ingest", "stats/physicalIngest", "stat")
    send_latest_stat("performance.snapshot_ingest", "stats/snapshotIngest", "stat")
    send_latest_stat("replication.bandwidth.outgoing", "stats/replication/bandwidth/outgoing", "stat")
    send_latest_stat("replication.bandwidth.incoming", "stats/replication/bandwidth/incoming", "stat")

    send_singleton_stat("storage.protected_primary_storage", "stats/protectedPrimaryStorage")
    send_singleton_stat("storage.logical_snapshot_storage", "stats/logicalStorage")
    send_singleton_stat("storage.live_snapshot_storage", "stats/liveSnapshotStorage")
    send_singleton_stat("storage.cloud_storage", "stats/cloudStorage")
    send_singleton_stat("storage.sla_domain_storage", "stats/slaDomainStorage")
    send_singleton_stat("storage.unprotected_vm_storage", "stats/unprotectedVMStorage")

    # These API calls fail, probably new or deprecated feature
    #send_singleton_stat("replication.managed_physical_storage", "stats/replicated/managedPhysicalStorage")
    #send_singleton_stat("replication.used_physical_storage", "stats/replicated/physicalStorage")

    send_storage_stats()
    send_cross_compression_stats()
    send_storage_and_compression_stats()
    send_sla_stats()
    send_replication_storage_stats()
    send_archival_storage_stats()


#while True:
#    send_all_data()
#    time.sleep(SEND_INTERVAL)

print datetime.now() 
send_all_data()
