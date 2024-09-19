import requests
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import pypd
import time

# Configuration for Alertmanager, Prometheus, Slack, and PagerDuty
ALERTMANAGER_API_URL = 'http://localhost:9093/api/v2/alerts'  # Alertmanager API URL
PROMETHEUS_RULES_URL = 'http://localhost:9090/api/v1/rules'   # Prometheus rules URL

# Slack configuration
SLACK_API_TOKEN = 'xoxb-your-slack-token'
SLACK_CHANNEL = '#on-call-engineers'

# PagerDuty configuration
PAGERDUTY_API_TOKEN = 'your_pagerduty_token'
PAGERDUTY_SERVICE_KEY = 'your_service_key'

# Severity thresholds
SEVERITY_CRITICAL = 'critical'
SEVERITY_WARNING = 'warning'

# Slack client initialization
slack_client = WebClient(token=SLACK_API_TOKEN)

# PagerDuty client initialization
pypd.api_key = PAGERDUTY_API_TOKEN

# Helper function to fetch active alerts from Alertmanager
def get_active_alerts():
    try:
        response = requests.get(ALERTMANAGER_API_URL)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get alerts from Alertmanager: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Alertmanager: {e}")
        return []

# Helper function to notify via Slack
def send_slack_notification(alert):
    try:
        message = f"Alert: {alert['labels']['alertname']} - {alert['annotations']['description']}\n"
        message += f"Severity: {alert['labels']['severity']}\n"
        message += f"Starts at: {alert['startsAt']}\n"

        # Send message to the defined Slack channel
        slack_client.chat_postMessage(channel=SLACK_CHANNEL, text=message)
        print(f"Slack notification sent for alert: {alert['labels']['alertname']}")
    except SlackApiError as e:
        print(f"Failed to send Slack message: {e.response['error']}")

# Helper function to trigger PagerDuty alert
def trigger_pagerduty_alert(alert):
    try:
        # Trigger an incident via PagerDuty API
        pypd.EventV2.create(data={
            'routing_key': PAGERDUTY_SERVICE_KEY,
            'event_action': 'trigger',
            'payload': {
                'summary': f"Critical Alert: {alert['labels']['alertname']}",
                'severity': 'critical',
                'source': alert['labels']['instance'],
                'component': alert['labels'].get('job', 'unknown'),
                'custom_details': {
                    'description': alert['annotations']['description'],
                    'severity': alert['labels']['severity'],
                    'startsAt': alert['startsAt'],
                }
            }
        })
        print(f"PagerDuty incident triggered for alert: {alert['labels']['alertname']}")
    except Exception as e:
        print(f"Failed to trigger PagerDuty alert: {e}")

# Helper function to route alerts based on severity and type
def route_alert(alert):
    severity = alert['labels']['severity']
    alert_name = alert['labels']['alertname']

    # Custom routing logic
    if severity == SEVERITY_CRITICAL:
        # Send PagerDuty alert for critical incidents
        print(f"Critical alert detected: {alert_name}")
        trigger_pagerduty_alert(alert)
        send_slack_notification(alert)  # Send notification to Slack as well
    elif severity == SEVERITY_WARNING:
        # For warnings, send notification to Slack only
        print(f"Warning alert detected: {alert_name}")
        send_slack_notification(alert)
    else:
        print(f"Unrecognized severity: {severity}. Skipping...")

# Helper function to
