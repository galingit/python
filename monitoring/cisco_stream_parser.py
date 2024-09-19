import grpc
import telemetry_pb2
import telemetry_pb2_grpc
import requests
import time
import json

# gRPC settings (replace with your Cisco device IP and credentials)
GRPC_SERVER = '192.168.1.1:57400'  # Cisco telemetry server address
USERNAME = 'admin'
PASSWORD = 'password'

# Time-series database settings (e.g., InfluxDB or Prometheus Pushgateway)
TSDB_URL = 'http://localhost:8086/write?db=network_metrics'  # Example for InfluxDB

# Function to establish gRPC connection and get telemetry stream
def get_telemetry_stream():
    # Set up gRPC channel credentials (plaintext for simplicity, use SSL in production)
    channel = grpc.insecure_channel(GRPC_SERVER)

    # Initialize stub to receive telemetry data
    stub = telemetry_pb2_grpc.gRPCConfigOperStub(channel)

    # Create subscription request
    subscription = telemetry_pb2.SubscriptionRequest(
        subidstr="interface-stats",  # The telemetry path subscription name
        encoding="gpb",  # Use GPB encoding
        stream=True,  # Keep stream alive
    )

    # Start telemetry stream
    telemetry_stream = stub.GetTelemetryData(subscription)

    return telemetry_stream

# Function to parse telemetry data (GPB format)
def parse_telemetry_data(telemetry_message):
    try:
        # Parse the GPB-encoded telemetry message
        telemetry = telemetry_pb2.Telemetry()
        telemetry.ParseFromString(telemetry_message.data)

        # Extract common telemetry information
        timestamp = telemetry.msg_timestamp
        sensor_path = telemetry.encoding_path

        # Process each data point in the telemetry message
        data = []
        for field in telemetry.data_gpb.row:
            fields = {}
            for element in field.content:
                # Map key-value telemetry data points
                fields[element.name] = element.value

            data.append(fields)

        return timestamp, sensor_path, data

    except Exception as e:
        print(f"Error parsing telemetry data: {e}")
        return None, None, None

# Function to filter and format the telemetry data for time-series database
def filter_and_format_data(sensor_path, data):
    # Example of filtering specific data, e.g., interface statistics
    filtered_metrics = []
    for item in data:
        if "interface" in sensor_path:
            # Example filter for interface statistics (you can filter other fields here)
            filtered_metrics.append({
                "interface_name": item.get("interface-name", "unknown"),
                "ifInOctets": item.get("in-octets", 0),
                "ifOutOctets": item.get("out-octets", 0),
                "ifErrors": item.get("input-errors", 0),
                "timestamp": time.time_ns()
            })

    return filtered_metrics

# Function to push data to time-series database (InfluxDB format example)
def push_to_tsdb(metrics):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    for metric in metrics:
        # Convert the metric to line protocol (InfluxDB format)
        line_protocol = f"interface_stats,interface_name={metric['interface_name']} ifInOctets={metric['ifInOctets']},ifOutOctets={metric['ifOutOctets']},ifErrors={metric['ifErrors']} {metric['timestamp']}\n"

        try:
            # Send the formatted data to InfluxDB
            response = requests.post(TSDB_URL, data=line_protocol, headers=headers)
            if response.status_code != 204:
                print(f"Failed to write data to TSDB: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending data to TSDB: {e}")

# Main function to run the telemetry collection and processing loop
def main():
    # Get the telemetry stream
    telemetry_stream = get_telemetry_stream()

    # Loop to process telemetry data
    for telemetry_message in telemetry_stream:
        # Parse the incoming telemetry data
        timestamp, sensor_path, data = parse_telemetry_data(telemetry_message)

        if data:
            # Filter and format the telemetry data for time-series database
            metrics = filter_and_format_data(sensor_path, data)

            # Push the formatted metrics to the time-series database
            push_to_tsdb(metrics)

if __name__ == "__main__":
    main()
