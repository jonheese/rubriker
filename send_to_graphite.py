#!/usr/bin/env python

import socket, time, json, sys
from datetime import datetime, timedelta
from config import rubrik_locations, carbon_server, carbon_port, metric_prefix
from rubriker import Rubriker

# How often to gather and send data to Graphite, in seconds
SEND_INTERVAL_SECS = 300
SEND_INTERVAL = timedelta(seconds=SEND_INTERVAL_SECS)
ARMED=True


def send_to_graphite(location, metric, value, timestamp=time.time()):
    message = "%s.%s.%s %s %d\n" % (metric_prefix, location, metric.replace(" ", ""), value, int(timestamp))
    print "%s" % message,
    if ARMED:
        sock = socket.socket()
        sock.connect((carbon_server, carbon_port))
        sock.sendall(message)
        sock.close()


def send_if_recent(location, metric_name, value, last_entry):
    if last_entry is not None:
        timestamp = datetime.strptime(last_entry, "%Y-%m-%dT%H:%M:%SZ")
        if datetime.utcnow() - timestamp <= SEND_INTERVAL:
            send_to_graphite(location, metric_name, value, (timestamp - datetime.utcfromtimestamp(0)).total_seconds())
            return True
    return False


def send_latest_stat(rubriker, metric_name, endpoint, stat_name):
    json_results = rubriker.do_api_call(endpoint)
    for result in json_results:
        send_if_recent(rubriker.location, metric_name, result[stat_name], result['time'])


def send_singleton_stat(rubriker, metric_name, endpoint):
    try:
        json_results = rubriker.do_api_call(endpoint)
        send_if_recent(rubriker.location, metric_name, json_results['value'], json_results['lastUpdateTime'])
    except Exception as e:
        print e


def send_storage_stats(rubriker):
    try:
        json_results = rubriker.do_api_call("api/internal/stats/system_storage")
        last_entry = json_results['lastUpdateTime']
        if send_if_recent(rubriker.location, "storage.total_storage", json_results['total'], last_entry):
            send_if_recent(rubriker.location, "storage.used_storage", json_results['used'], last_entry)
            send_if_recent(rubriker.location, "storage.available_storage", json_results['available'], last_entry)
    except Exception as e:
        print e


def send_storage_and_compression_stats(rubriker):
    try:
        ingested_bytes = None
        snapshot_bytes = None
        json_results = rubriker.do_api_call("api/internal/stats/snapshot_storage/ingested")
        timestamp = datetime.strptime(json_results['lastUpdateTime'], "%Y-%m-%dT%H:%M:%SZ")
        if datetime.utcnow() - timestamp <= SEND_INTERVAL:
            ingested_bytes = json_results['value']
            send_to_graphite(rubriker.location, "performance.backend_ingested_bytes", ingested_bytes, (timestamp - datetime.utcfromtimestamp(0)).total_seconds())
        json_results = rubriker.do_api_call("api/internal/stats/snapshot_storage/physical")
        timestamp = datetime.strptime(json_results['lastUpdateTime'], "%Y-%m-%dT%H:%M:%SZ")
        if datetime.utcnow() - timestamp <= SEND_INTERVAL:
            snapshot_bytes = json_results['value']
            send_to_graphite(rubriker.location, "storage.physical_snapshot_storage", snapshot_bytes, (timestamp - datetime.utcfromtimestamp(0)).total_seconds())
        if ingested_bytes is not None and snapshot_bytes is not None:
            reduction = (1 - (float(snapshot_bytes) / float(ingested_bytes))) * 100
            ratio = float(ingested_bytes) / float(snapshot_bytes)
            send_to_graphite(rubriker.location, "performance.compression.reduction", reduction, (timestamp - datetime.utcfromtimestamp(0)).total_seconds())
            send_to_graphite(rubriker.location, "performance.compression.ratio", ratio, (timestamp - datetime.utcfromtimestamp(0)).total_seconds())
    except Exception as e:
        print e


def send_cross_compression_stats(rubriker):
    try:
        json_results = rubriker.do_api_call("api/internal/stats/cross_compression")
        last_entry = json_results['lastUpdateTime']
        data = json.loads(json_results['value'])
        if send_if_recent(rubriker.location, "performance.compression.logical_bytes", data['logicalBytes'], last_entry):
            send_if_recent(rubriker.location, "performance.compression.logical_bytes", data['logicalBytes'], last_entry)
            send_if_recent(rubriker.location, "performance.compression.zero_bytes", data['zeroBytes'], last_entry)
            send_if_recent(rubriker.location, "performance.compression.precomp_bytes", data['preCompBytes'], last_entry)
            send_if_recent(rubriker.location, "performance.compression.postcomp_bytes", data['postCompBytes'], last_entry)
            send_if_recent(rubriker.location, "performance.compression.physical_bytes", data['physicalBytes'], last_entry)
    except Exception as e:
        print e


def send_sla_stats(rubriker):
    try:
        sla_domains = rubriker.do_api_call("api/v1/sla_domain?primary_cluster_id=local")['data']
        for sla_domain in sla_domains:
            (sla_name, sla_id) = (sla_domain['name'], sla_domain['id'])
            send_singleton_stat(rubriker, "storage.sla_domain_storage.%s" % sla_name, "api/internal/stats/sla_domain_storage/%s" % sla_id)
            send_to_graphite(rubriker.location, "storage.vms_protected.%s" % sla_name, sla_domain['numVms'])
    except Exception as e:
        print e


def send_replication_storage_stats(rubriker):
    try:
        replication_stats = rubriker.do_api_call("api/internal/stats/total_replication_storage")
        for remote in replication_stats['remoteVmStorageOnPremise']:
            send_to_graphite(rubriker.location, "replication.remote_vm_storage_locally.%s" % remote['remoteClusterUuid'], remote['totalStorage'])
        for local in replication_stats['localVmStorageAcrossAllTargets']:
            send_to_graphite(rubriker.location, "replication.local_vm_storage_remotely.%s"% local['remoteClusterUuid'], local['totalStorage'])
    except Exception as e:
        print e


def send_archival_storage_stats(rubriker):
    try:
        archival_location_details = rubriker.do_api_call("api/internal/data_location/archival_location")['data']
        archival_location_storage = rubriker.do_api_call("api/internal/stats/data_location/usage")['data']
        for archival_location in archival_location_storage:
            archival_location_name = None
            archival_location_id = archival_location['locationId']
            for archival_location_detail in archival_location_details:
                if archival_location_detail['id'] == archival_location_id:
                    archival_location_name = "%s.%s" % (archival_location_detail['locationType'], archival_location_detail['bucket'])
                    break
            if archival_location_name is not None:
                send_to_graphite(rubriker.location, "archive.bytes_downloaded.%s" % archival_location_name, archival_location['dataDownloaded'])
                send_to_graphite(rubriker.location, "archive.bytes_archived.%s" % archival_location_name, archival_location['dataArchived'])
                send_to_graphite(rubriker.location, "archive.vms_archived.%s" % archival_location_name, archival_location['numVMsArchived'])
                send_latest_stat(rubriker, "archive.bandwidth.%s" % archival_location_name, "api/internal/stats/archival/bandwidth/time_series?data_location_id=%s" % archival_location_id, "stat")
    except Exception as e:
        print e


def send_all_data(rubriker):
    try:
        send_to_graphite(rubriker.location, "system.briks", rubriker.do_api_call("api/internal/cluster/me/brik_count")['count'])
        send_to_graphite(rubriker.location, "storage.disk_capacity", rubriker.do_api_call("api/internal/cluster/me/disk_capacity")['bytes'])
        send_to_graphite(rubriker.location, "storage.flash_capacity", rubriker.do_api_call("api/internal/cluster/me/flash_capacity")['bytes'])
        send_to_graphite(rubriker.location, "system.cpu_core_count", rubriker.do_api_call("api/internal/node/*/cpu_cores_count")['count'])
        send_to_graphite(rubriker.location, "performance.streams", rubriker.do_api_call("api/internal/stats/streams/count")['count'])
        send_to_graphite(rubriker.location, "storage.average_storage_growth_per_day", rubriker.do_api_call("api/internal/stats/average_storage_growth_per_day")['bytes'])
        send_to_graphite(rubriker.location, "performance.runway_remaining", rubriker.do_api_call("api/internal/stats/runway_remaining")['days'])
        send_to_graphite(rubriker.location, "storage.vms_in_vcenter", rubriker.do_api_call("api/internal/vmware/vm/count")['count'])
        send_to_graphite(rubriker.location, "performance.physical_ingest_per_day", rubriker.do_api_call("api/internal/stats/physical_ingest_per_day/time_series")[0]['stat'])
        send_to_graphite(rubriker.location, "memory.total_memory", rubriker.do_api_call("api/internal/cluster/me/memory_capacity")['bytes'])
    except Exception as e:
        print e

    try:
        send_latest_stat(rubriker, "performance.logical_ingest", "api/internal/stats/logical_ingest/time_series", "stat")
        send_latest_stat(rubriker, "performance.physical_ingest", "api/internal/stats/physical_ingest/time_series", "stat")
        send_latest_stat(rubriker, "performance.snapshot_ingest", "api/internal/stats/snapshot_ingest/time_series", "stat")
        send_latest_stat(rubriker, "replication.bandwidth.outgoing", "api/internal/stats/replication/outgoing/time_series", "stat")
        send_latest_stat(rubriker, "replication.bandwidth.incoming", "api/internal/stats/replication/incoming/time_series", "stat")
    except Exception as e:
        print e

    try:
        send_singleton_stat(rubriker, "storage.protected_primary_storage", "api/internal/stats/protected_primary_storage")
        send_singleton_stat(rubriker, "storage.logical_snapshot_storage", "api/internal/stats/snapshot_storage/logical")
        send_singleton_stat(rubriker, "storage.live_snapshot_storage", "api/internal/stats/snapshot_storage/live")
        send_singleton_stat(rubriker, "storage.cloud_storage", "api/internal/stats/cloud_storage")
        send_singleton_stat(rubriker, "storage.sla_domain_storage", "api/internal/stats/sla_domain_storage")
        send_singleton_stat(rubriker, "storage.unprotected_vm_storage", "api/internal/stats/unprotected_snappable_storage")
    except Exception as e:
        print e

    # These API calls fail, probably new or deprecated feature
    #send_singleton_stat("replication.managed_physical_storage", "stats/replicated/managedPhysicalStorage")
    #send_singleton_stat("replication.used_physical_storage", "stats/replicated/physicalStorage")

    send_storage_stats(rubriker)
    send_cross_compression_stats(rubriker)
    send_storage_and_compression_stats(rubriker)
    send_sla_stats(rubriker)
    send_replication_storage_stats(rubriker)
    send_archival_storage_stats(rubriker)


#while True:
#    send_all_data()
#    time.sleep(SEND_INTERVAL)

print datetime.now()
for location in rubrik_locations.keys():
    config_dict = rubrik_locations[location]
    rubrik_user = config_dict["rubrik_user"]
    rubrik_pass = config_dict["rubrik_pass"]
    rubrik_url = config_dict["rubrik_url"]
    rubriker = Rubriker(location, rubrik_user, rubrik_pass, rubrik_url)
    send_all_data(rubriker)
