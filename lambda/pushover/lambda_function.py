import json
import requests
import os

# Custom header added to Opsgenie webhook
AUTH_HEADER = os.environ["AUTH_HEADER"]
# Pushover constants
PUSHOVER_URL = os.environ["PUSHOVER_URL"]
PUSHOVER_TOKEN = os.environ["PUSHOVER_TOKEN"]
PUSHOVER_WEB3_GROUP = os.environ["PUSHOVER_WEB3_GROUP"]
PUSHOVER_HUB_GROUP = os.environ["PUSHOVER_HUB_GROUP"]
PUSHOVER_TRADING_GROUP = os.environ["PUSHOVER_TRADING_GROUP"]
PUSHOVER_BLOCKCHAIN_GROUP = os.environ["PUSHOVER_BLOCKCHAIN_GROUP"]
PUSHOVER_MPC_GROUP = os.environ["PUSHOVER_MPC_GROUP"]
PUSHOVER_DEVOPS_GROUP = os.environ["PUSHOVER_DEVOPS_GROUP"]
PUSHOVER_STAFF_GROUP = os.environ["PUSHOVER_STAFF_GROUP"]
PUSHOVER_SECURITY_GROUP = os.environ["PUSHOVER_SECURITY_GROUP"]
# Opsgenie constants
OPSGENIE_URL = os.environ["OPSGENIE_URL"]
OPSGENIE_TOKEN = os.environ["OPSGENIE_TOKEN"]
OPSGENIE_WEB3_TEAM = os.environ["OPSGENIE_WEB3_TEAM"]
OPSGENIE_HUB_TEAM = os.environ["OPSGENIE_HUB_TEAM"]
OPSGENIE_TRADING_TEAM = os.environ["OPSGENIE_TRADING_TEAM"]
OPSGENIE_BLOCKCHAIN_TEAM = os.environ["OPSGENIE_BLOCKCHAIN_TEAM"]
OPSGENIE_MPC_TEAM = os.environ["OPSGENIE_MPC_TEAM"]
OPSGENIE_DEVOPS_TEAM = os.environ["OPSGENIE_DEVOPS_TEAM"]
OPSGENIE_STAFF_TEAM = os.environ["OPSGENIE_STAFF_TEAM"]
OPSGENIE_SECURITY_TEAM = os.environ["OPSGENIE_SECURITY_TEAM"]


def lambda_handler(event, context):
    print(event)
    auth_header = event["headers"]["auth"]
    if auth_header != AUTH_HEADER:
        return {"statusCode": 401, "body": "Invalid auth header"}

    # Parse the payload
    payload = json.loads(event["body"])
    alert_id = payload["alert"]["alertId"]

    # Fetch the alert details
    alert_details = _get_alert_details(alert_id)
    message = alert_details["data"]["message"]
    responders = alert_details["data"]["responders"]

    for responder in responders:
        team_id = responder["id"]
        if team_id == OPSGENIE_WEB3_TEAM:
            _send_alert_to_pushover(PUSHOVER_WEB3_GROUP, "Incident detected", message)
        if team_id == OPSGENIE_HUB_TEAM:
            _send_alert_to_pushover(PUSHOVER_HUB_GROUP, "Incident detected", message)
        if team_id == OPSGENIE_TRADING_TEAM:
            _send_alert_to_pushover(PUSHOVER_TRADING_GROUP, "Incident detected", message)
        if team_id == OPSGENIE_BLOCKCHAIN_TEAM:
            _send_alert_to_pushover(PUSHOVER_BLOCKCHAIN_GROUP, "Incident detected", message)
        if team_id == OPSGENIE_MPC_TEAM:
            _send_alert_to_pushover(PUSHOVER_MPC_GROUP, "Incident detected", message)
        if team_id == OPSGENIE_DEVOPS_TEAM:
            _send_alert_to_pushover(PUSHOVER_DEVOPS_GROUP, "Incident detected", message)
        if team_id == OPSGENIE_STAFF_TEAM:
            _send_alert_to_pushover(PUSHOVER_STAFF_GROUP, "Incident detected", message)
        if team_id == OPSGENIE_SECURITY_TEAM:
            _send_alert_to_pushover(PUSHOVER_SECURITY_GROUP, "Incident detected", message)

    return {"statusCode": 200, "body": "Pushover alert sent successfully"}


def _get_alert_details(alert_id):
    """
    Retrieves the alert details from Opsgenie

    Args:
    - alert_id (str): The Opsgenie alert id
    """
    url = OPSGENIE_URL + "v2/alerts/" + alert_id
    headers = {
        "Authorization": f"GenieKey {OPSGENIE_TOKEN}",
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    print("Response from Opsgenie")
    print(response.json())
    return response.json()


def _send_alert_to_pushover(group_key, title, message):
    """
    Sends the alert to Pushover

    Args:
    - group_key (str): The Pushover group key
    - title (str): The title of the alert
    - message (str): The message of the alert
    """
    url = PUSHOVER_URL
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    data = {
        "token": PUSHOVER_TOKEN,
        "user": group_key,
        "title": title,
        "message": message,
    }

    response = requests.post(url, headers=headers, data=data)

    print(response.status_code)
    print(response.text)
