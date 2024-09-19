import requests
import json
import os
import yaml
from jinja2 import Template

# Configuration for CMDB, Prometheus, SNMP Exporter, and Grafana
CMDB_API_URL = 'https://cmdb.example.com/api/devices'  # CMDB API endpoint (replace with actual URL)
SNMP_EXPORTER_CONFIG_PATH = '/etc/snmp_exporter/snmp.yml'
PROMETHEUS_CONFIG_PATH = '/etc/prometheus/prometheus.yml'
GRAFANA_API_URL = 'http://localhost:3000/api'
GRAFANA_API_KEY = 'grafana_api_key'
GRAFANA_DASHBOARD_TEMPLATE_PATH = 'grafana_network_dashboard_template.json'  # Predefined Grafana dashboard template

# Helper function to pull device data from CMDB
def get_devices_from_cmdb():
    # Replace this with actual CMDB API or CSV reading logic
    response = requests.get(CMDB_API_URL)
    if response.status_code == 200:
        return response.json()  # Assuming CMDB returns JSON with devices info
    else:
        raise Exception(f"Failed to get data from CMDB: {response.status_code} {response.text}")

# Helper function to generate SNMP Exporter config
def generate_snmp_exporter_config(devices):
    # Load existing SNMP Exporter config
    if os.path.exists(SNMP_EXPORTER_CONFIG_PATH):
        with open(SNMP_EXPORTER_CONFIG_PATH, 'r') as file:
            snmp_config = yaml.safe_load(file)
    else:
        snmp_config = {'modules': {}}

    for device in devices:
        device_name = device['hostname']
        ip_address = device['ip']
        snmp_version = device['snmp_version']

        # Create SNMP Exporter module for each device
        snmp_config['modules'][device_name] = {
            'version': snmp_version,
            'walk': ['1.3.6.1.2.1.1'],  # Example OID, you can change this based on your needs
            'auth': {
                'community': device.get('snmp_community', 'public')
            }
        }

    # Write updated config to file
    with open(SNMP_EXPORTER_CONFIG_PATH, 'w') as file:
        yaml.dump(snmp_config, file)

# Helper function to update Prometheus config with new SNMP targets
def update_prometheus_config(devices):
    # Load Prometheus config
    with open(PROMETHEUS_CONFIG_PATH, 'r') as file:
        prometheus_config = yaml.safe_load(file)

    # Find the SNMP Exporter job in the config
    snmp_exporter_job = None
    for job in prometheus_config['scrape_configs']:
        if job['job_name'] == 'snmp_exporter':
            snmp_exporter_job = job
            break

    if not snmp_exporter_job:
        # If no SNMP job exists, create a new one
        snmp_exporter_job = {
            'job_name': 'snmp_exporter',
            'metrics_path': '/snmp',
            'static_configs': [],
        }
        prometheus_config['scrape_configs'].append(snmp_exporter_job)

    # Update static configs with new devices
    snmp_exporter_job['static_configs'] = [
        {'targets': [device['ip']], 'labels': {'device': device['hostname']}}
        for device in devices
    ]

    # Write updated Prometheus config to file
    with open(PROMETHEUS_CONFIG_PATH, 'w') as file:
        yaml.dump(prometheus_config, file)

# Helper function to create a Grafana dashboard for each new device
def create_grafana_dashboards(devices):
    headers = {
        'Authorization': f'Bearer {GRAFANA_API_KEY}',
        'Content-Type': 'application/json',
    }

    # Load predefined Grafana dashboard template
    with open(GRAFANA_DASHBOARD_TEMPLATE_PATH, 'r') as file:
        dashboard_template = json.load(file)

    for device in devices:
        # Render dashboard from the template using Jinja2
        dashboard = json.dumps(dashboard_template)
        dashboard = Template(dashboard).render(
            device_name=device['hostname'],
            device_ip=device['ip']
        )
        dashboard = json.loads(dashboard)

        # Set unique dashboard title
        dashboard['dashboard']['title'] = f"{device['hostname']} - Network Dashboard"

        # Send the dashboard to Grafana API
        response = requests.post(
            f'{GRAFANA_API_URL}/dashboards/db',
            headers=headers,
            data=json.dumps(dashboard)
        )

        if response.status_code == 200:
            print(f"Dashboard for {device['hostname']} created successfully")
        else:
            print(f"Failed to create dashboard for {device['hostname']}: {response.status_code} {response.text}")

# Main function to run the automation
def main():
    # Step 1: Pull device data from CMDB
    devices = get_devices_from_cmdb()
    
    # Step 2: Generate SNMP Exporter configuration
    generate_snmp_exporter_config(devices)

    # Step 3: Update Prometheus configuration
    update_prometheus_config(devices)

    # Step 4: Create Grafana dashboards
    create_grafana_dashboards(devices)

    print("Automation complete: SNMP Exporter, Prometheus, and Grafana are up-to-date.")

if __name__ == "__main__":
    main()
