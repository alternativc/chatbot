import json
import requests
import os

# Slack constants
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
# Opsgenie constants
OPSGENIE_URL = os.environ["OPSGENIE_URL"]
OPSGENIE_TOKEN = os.environ["OPSGENIE_TOKEN"]


def lambda_handler(event, context):
    """
    Process event from event bridge and route to Opsgenie
    """
    # Check if the incoming event is a Scheduled Event from EventBridge to keep the lambda function warm.
    if (
        event.get("source") == "aws.events"
        and event.get("detail-type") == "Scheduled Event"
    ):
        print("Received keep-warm event. Exiting without further processing.")
        return {"statusCode": 200, "body": json.dumps("Keep-warm event processed.")}

    # If the payload has a "payload" field, assume its an interactivity event otherwise assume its a slash command
    if "payload" in event["detail"]:
        print("Recieved interactivity event")
        print(event)
        payload = json.loads(event["detail"]["payload"][0])
        # IMPORTANT: only listen to view_submission events
        if payload.get("type", "") != "view_submission":
            return {"statusCode": 200, "body": "Ignoring event"}

        private_metadata = json.loads(payload["view"]["private_metadata"])
        command = private_metadata.get("text")
        channel_id = private_metadata.get("channel_id")

        

        if command == "alert":
            print("Recieved alert modal submissions")
            _process_alert_modal(payload)
            _post_message_to_slack(channel_id, "[SRE] Alert created successfully")
        elif command == "ack":
            # To be implemented or discarded
            pass
        elif command == "close":
            # To be implemented or discarded
            pass
        elif command == "override":
            # To be implemented or discarded
            pass
        elif command == "maintenance":
            # To be implemented or discarded
            pass
        else:
            print("Unknown modal submission")
            _post_message_to_slack(channel_id, "Unknown modal submission")
            return {"statusCode": 500, "body": ""}

    else:
        """
        The following code is for /sre alert command only. Break into multiple functions if you want to support multiple command actions
        """
        print("Recieved slash command")
        print(event)
        trigger_id = event["detail"]["trigger_id"][0]
        channel_id = event["detail"]["channel_id"][0]

        metadata = _generate_metadata(event)

        servies = _get_services()
        modal = _generate_alert_modal(metadata, servies)

        # Call Slack's API to open the modal
        response = requests.post(
            "https://slack.com/api/views.open",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"trigger_id": trigger_id, "view": modal},
        )
        print("Response from Slack")
        print(response.text)

        if not response.ok:
            print(response.text)
            return {
                "statusCode": 500,
                "body": f"Failed to open Slack modal. Error: {response.text}",
            }

        return {"statusCode": 200, "body": "Modal opened successfully"}


def _generate_metadata(event):
    """
    Add internal metadata for modals to route events correctly

    Args:
    - event (dict): The event object from the lambda handler
    """
    command = event["detail"]["route"]
    channel_id = event["detail"]["channel_id"][0]
    text = event["detail"]["text"][0]
    metadata = {
        "command": command,
        "text": text,
        "channel_id": channel_id,
    }
    return json.dumps(metadata)


def _get_services():
    """
    Retrieves a list of services from Opsgenie where the owner team matches Opsgenie token integration
    """
    url = f"{OPSGENIE_URL}/v1/services?sort=name&order=asc"
    headers = {
        "Authorization": f"GenieKey {OPSGENIE_TOKEN}",
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    print("Response from Opsgenie")
    print(response.json())
    return response.json()


def _generate_alert_modal(metadata, services={}):
    """
    Create a Slack modal for responding to /sre alert command

    Args:
    - metadata (dict): The metadata to be passed to the modal
    - services (dict): The list of services from Opsgenie
    """
    modal = {
        "type": "modal",
        "private_metadata": metadata,
        "submit": {"type": "plain_text", "text": "Create alert", "emoji": True},
        "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
        "title": {"type": "plain_text", "text": "On Call Bot", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":wave: Hi there! I'm the On Call Bot. I can help you create an alert in Opsgenie.",
                },
            },
            {
                "type": "divider",
            },
            {
                "type": "section",
                "block_id": "service_select_block",
                "text": {
                    "type": "mrkdwn",
                    "text": ":gear: *Choose a service*\nSelect the service that is affected by the issue",
                },
                "accessory": {
                    "type": "static_select",
                    "action_id": "service_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Choose a service",
                        "emoji": True,
                    },
                    "initial_option": None,
                    "options": [],
                },
            },
            {
                "type": "section",
                "block_id": "priority_select_block",
                "text": {
                    "type": "mrkdwn",
                    "text": ":1234: *Choose priority*\nP1 -> Critical, P2 -> High, P3 -> Medium",
                },
                "accessory": {
                    "type": "static_select",
                    "action_id": "priority_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Choose priority",
                        "emoji": True,
                    },
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "P1", "emoji": True},
                        "value": "P1",
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "P1", "emoji": True},
                            "value": "P1",
                        },
                        {
                            "text": {"type": "plain_text", "text": "P2", "emoji": True},
                            "value": "P2",
                        },
                        {
                            "text": {"type": "plain_text", "text": "P3", "emoji": True},
                            "value": "P3",
                        }
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "issue_description_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "issue_description",
                },
                "label": {
                    "type": "plain_text",
                    "text": ":spiral_note_pad: Describe the issue with as much detail as possible",
                    "emoji": True,
                },
            },
            {
                "type": "input",
                "block_id": "issue_url_block",
                "element": {"type": "url_text_input", "action_id": "issue_url"},
                "label": {
                    "type": "plain_text",
                    "text": ":link: If there is a link to the issue, please provide it here",
                    "emoji": True,
                },
                "optional": True,
            },
        ]
    }

    # Populate initial service and other services
    for service in services.get("data", []):
        if modal["blocks"][2]["accessory"]["initial_option"] == None:
            modal["blocks"][2]["accessory"]["initial_option"] = {
                "text": {
                    "type": "plain_text",
                    "text": service["name"],
                    "emoji": True,
                },
                "value": service["id"],
            }

        modal["blocks"][2]["accessory"]["options"].append(
            {
                "text": {
                    "type": "plain_text",
                    "text": service["name"],
                    "emoji": True,
                },
                "value": service["id"],
            }
        )
    print(modal)
    return modal


def _process_alert_modal(payload):
    """
    Process the data from the alert modal and submit to Opsgenie

    Args:
    - payload (dict): The payload from the modal submission
    """
    service_block = (
        payload.get("view", {})
        .get("state", {})
        .get("values", {})
        .get("service_select_block", {})
    )
    service_id = (
        service_block.get("service_select", {}).get("selected_option", {}).get("value")
    )
    service_name = (
        service_block.get("service_select", {})
        .get("selected_option", {})
        .get("text", {})
        .get("text")
    )

    issue_description_block = (
        payload.get("view", {})
        .get("state", {})
        .get("values", {})
        .get("issue_description_block", {})
    )
    issue_description = issue_description_block.get("issue_description", {}).get(
        "value", ""
    )

    issue_priority_block = (
        payload.get("view", {})
        .get("state", {})
        .get("values", {})
        .get("priority_select_block", {})
    )

    issue_priority = issue_priority_block.get("priority_select", {}).get(
        "selected_option", {}
    ).get("value", "")

    issue_url_block = (
        payload.get("view", {})
        .get("state", {})
        .get("values", {})
        .get("issue_url_block", {})
    )
    issue_url = issue_url_block.get("issue_url", {}).get("value", "")

    print(
        "Service ID: "
        + service_id
        + "\nIssue description: "
        + issue_description
        + "\nIssue priority: "
        + issue_priority
        + "\nIssue URL: "
        + issue_url
    )

    # Create an incident in Opsgenie via rest API
    url = f"{OPSGENIE_URL}/v1/incidents/create"
    headers = {
        "Authorization": f"GenieKey {OPSGENIE_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "message": service_name + ": " + issue_description,
        "description": "Affected service:\n"
        + service_name
        + "\n\nIssue description:\n"
        + issue_description
        + "\n\nAdditional links:\n"
        + issue_url,
        "tags": ["slack", service_name],
        "priority": issue_priority,
        "impactedServices": [service_id],
        "statusPageEntry": {
            "title": service_name + " issues",
            "detail": "Service: "
            + service_name
            + " is experiencing the following issues: "
            + issue_description
            + " | The following additional link was added: "
            + issue_url,
        },
        "notifyStakeholders": False,
    }

    response = requests.post(url, headers=headers, json=payload)
    response_data = response.json()
    if response_data["result"] != "Request will be processed":
        print(f"Error sending message to Opsgenie: {response_data.get('requestId', 'Unknown ID')}")
        # raise Exception(f"Error sending message to Opsgenie: {response_data.get('requestId', 'Unknown ID')}") -> This causes eventbridge to loop and retry sending the event avoid raising exceptions like so

    print("Response from Opsgenie:")
    print(response_data)
    return response_data


def _get_slack_channel_name(channel_id):
    """
    Retrieves the name of a Slack channel given its ID.

    Args:
    - channel_id (str): ID of the Slack channel to retrieve the name for.
    """
    url = "https://slack.com/api/conversations.info"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    }
    params = {"channel": channel_id}

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if data.get("ok"):
        return data["channel"]["name"]
    else:
        print(f"Error: {data.get('error')}")
        return None


def _post_message_to_slack(channel_id, message_text):
    """
    Posts a message to a Slack channel.

    Args:
    - channel_id (str): ID of the Slack channel to send the message to.
    - message_text (str): Text of the message to send.
    """

    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    }
    data = {
        "channel": channel_id,
        "text": message_text,
    }
    print(data)

    response = requests.post(url, headers=headers, json=data)
    response_data = response.json()

    if not response_data["ok"]:
        print(f"Error sending message to Slack: {response_data['error']}")
        # raise Exception(f"Error sending message to Slack: {response_data['error']}") <- this causes eventbridge to retry event sending avoid raising exceptions like so

    print("Response from Slack:")
    print(response_data)
    return response_data
