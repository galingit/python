import time
from pysnmp.hlapi import *
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Define the OIDs for the metrics you want to collect (Example: Interface Bytes In/Out)
OIDS = {
    'ifInOctets': '1.3.6.1.2.1.2.2.1.10',  # Incoming bytes
    'ifOutOctets': '1.3.6.1.2.1.2.2.1.16',  # Outgoing bytes
    'ifOperStatus': '1.3.6.1.2.1.2.2.1.8',  # Interface operational status
}

# SNMPv3 credentials (example)
snmp_engine_id = 'my-engine-id'
auth_user = 'my-auth-user'
auth_key = 'my-auth-key'
priv_key = 'my-priv-key'

# Prometheus Pushgateway settings
PUSHGATEWAY_URL = 'http://localhost:9091'

# Devices to poll (hostname or IP)
devices = [
    {'ip': '192.168.1.1', 'community': 'public', 'device_name': 'router1'},
    {'ip': '192.168.1.2', 'community': 'public', 'device_name': 'switch1'}
]

# Function to perform an SNMP GET request
def snmp_get(host, community, oid):
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community),
        UdpTransportTarget((host, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )

    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

    if errorIndication:
        print(f"Error: {errorIndication}")
        return None
    elif errorStatus:
        print(f"Error: {errorStatus.prettyPrint()}")
        return None
    else:
        for varBind in varBinds:
            return varBind[1]

# Function to push metrics to Prometheus Pushgateway
def push_metrics(device, metric_name, value, registry):
    # Define Prometheus Gauge
    g = Gauge(metric_name, f'{metric_name} for {device["device_name"]}', ['device'], registry=registry)
    # Set the value
    g.labels(device=device['device_name']).set(value)
    
    # Push to Prometheus Pushgateway
    push_to_gateway(PUSHGATEWAY_URL, job=device['device_name'], registry=registry)

# Main function to collect and push metrics
def collect_snmp_metrics():
    registry = CollectorRegistry()

    for device in devices:
        print(f"Collecting metrics from {device['device_name']} ({device['ip']})")

        # Poll the device for each OID
        for metric, oid in OIDS.items():
            value = snmp_get(device['ip'], device['community'], oid)
            if value is not None:
                print(f"Metric: {metric}, Value: {value}")
                # Push the metric to Prometheus Pushgateway
                push_metrics(device, metric, value, registry)

if __name__ == "__main__":
    while True:
        # Collect SNMP metrics every 60 seconds
        collect_snmp_metrics()
        time.sleep(60)
