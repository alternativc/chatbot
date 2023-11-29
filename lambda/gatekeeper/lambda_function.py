import asyncio
from concurrent.futures import ThreadPoolExecutor
from boto3 import client
import hashlib
import hmac
import urllib.parse
import json
import os


# Slack constants
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]

# Channel and command constants
ALLOWED_CHANNELS = {
    "/sre": ["*"],  # Commmand can be used in any channel
    "/ops-bot": ["C05RSEC6QCA"],  # Command can be used in designated channels
    "/qchain": ["*"],
}
ALLOWED_COMMANDS = {
    "/sre": ["alert"],
    "/ops-bot": ["alert", "ack", "close", "mute", "maintenance", "help"],
    "/command": ["test"],
    "/qchain": ["killswitch"],
}

RESTRICTED_COMMANDS = {
    "/qchain": {
        "killswitch": ["urban.jurca", "iris.garcia", "chris", "alexander", "david", "tangui", "khalifa", "lazar"],
    },
}

# EventBridge constants
EVENT_BUS_NAME = "default"
EVENT_SOURCE = "gatekeeper"
EVENT_DETAIL_TYPE = "Slack Command Invoked"


def lambda_handler(event, context):
    """
    Validate and decode request from Slack. Route the payload to EventBRidge.
    """
    print(event)
    # Check if the incoming event is a Scheduled Event from EventBridge to keep the lambda function warm.
    if (
        event.get("source") == "aws.events"
        and event.get("detail-type") == "Scheduled Event"
    ):
        print("Received keep-warm event. Exiting without further processing.")
        return {"statusCode": 200, "body": json.dumps("Keep-warm event processed.")}

    if not _is_valid_request(event):
        print("Invalid request signature")
        return {"statusCode": 200, "body": "Invalid request signature"}

    # This is the payload from slack whi is in URL encoded format. Always decode it.
    decoded_body = urllib.parse.parse_qs(event["body"])

    # If the payload has a "payload" field, assume its an interactivity event otherwise assume its a slash command
    if "payload" in decoded_body:
        payload = json.loads(decoded_body["payload"][0])
        print(payload)
        private_metadata = json.loads(payload["view"]["private_metadata"])
        command = private_metadata.get("command")

        asyncio.run(_put_event_to_eventbridge_async(command, decoded_body))
        return {"statusCode": 200, "body": ""}
    else:
        channel_id = decoded_body.get("channel_id", [None])[0]
        user_id = decoded_body.get("user_id", [None])[0]
        user_name = decoded_body.get("user_name", [None])[0]
        command = decoded_body.get("command", [None])[0]
        action = decoded_body.get("text", [None])[0]

        if not _is_authorized_user(command, action, user_name):
            print("User not authorized")
            return {
                "statusCode": 200,
                "body": "User not authorized",
            }

        if not _is_valid_channel(command, channel_id):
            print("Invalid channel usage")
            return {
                "statusCode": 200,
                "body": "Invalid channel usage. Contact application owner for more information.",
            }

        if not _is_valid_action(command, action):
            print("Invalid command usage")
            return {
                "statusCode": 200,
                "body": "Invalid command usage. Only the following actions are allowed for "
                + command
                + ": "
                + ", ".join(ALLOWED_COMMANDS[command])
                + ".",
            }

        asyncio.run(_put_event_to_eventbridge_async(command, decoded_body))
        # return {"statusCode": 200, "body": f"Received Slack message: {decoded_body}"}
        return {"statusCode": 200, "body": ""}


def _is_authorized_user(command, action, user_name):
    """
    Validates authorization of user to a given command + action

    Args:
    - command (str): The command from the slack request
    - action (str): The action from the slack request
    - user_name (str): The user_name from the slack request
    """
    if command not in RESTRICTED_COMMANDS:
        return True
    elif action not in RESTRICTED_COMMANDS[command]:
        return True
    elif user_name in RESTRICTED_COMMANDS[command][action]:
        return True

    return False

def _is_valid_request(event):
    """
    Validates Slack request signature

    Args:
    - event (dict): The event object from the lambda handler
    """
    slack_signature = event["headers"].get("X-Slack-Signature", "")
    slack_request_timestamp = event["headers"].get("X-Slack-Request-Timestamp", "")
    request_body = event["body"]

    # Create a basestring by concatenating the version, the request timestamp, and the request body
    base_string = f"v0:{slack_request_timestamp}:{request_body}"

    # Calculate the HMAC using SHA256
    calculated_signature = (
        "v0="
        + hmac.new(
            bytes(SLACK_SIGNING_SECRET, "utf-8"),
            msg=bytes(base_string, "utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(calculated_signature, slack_signature)


def _is_valid_channel(command, channel_id):
    """
    Validates command and channel id combination

    Args:
    - command (str): The command from the slack request
    - channel_id (str): The channel id from the slack request
    """
    if ALLOWED_CHANNELS[command][0] == "*":
        return True

    if channel_id not in ALLOWED_CHANNELS[command]:
        return False
    else:
        return True


def _is_valid_action(command, action):
    """
    Validates command and action combination

    Args:
    - command (str): The command from the slack request
    - action (str): The action from the slack request
    """
    if command not in ALLOWED_COMMANDS.keys():
        return False
    if action not in ALLOWED_COMMANDS[command]:
        return False
    return True


async def _put_event_to_eventbridge_async(command, payload):
    """
    Workaround method to perform async calls from a lambda function. Slack requires a response within 3 seconds.

    Args:
    - command (str): The command from the slack request
    - payload (dict): The payload from the slack request
    """
    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor() as executor:
        await loop.run_in_executor(
            executor, _put_event_to_eventbridge, command, payload
        )


def _put_event_to_eventbridge(command, payload):
    """
    Sends the given payload to Amazon EventBridge.

    Args:
    - command (str): The command from the slack request
    - payload (dict): The payload from the slack request
    """
    eventbridge = client("events")
    payload["route"] = command

    eventbridge.put_events(
        Entries=[
            {
                "EventBusName": EVENT_BUS_NAME,
                "Source": EVENT_SOURCE,
                "DetailType": EVENT_DETAIL_TYPE,
                "Detail": json.dumps(payload),
            }
        ]
    )

    print("Event sent to EventBridge")
