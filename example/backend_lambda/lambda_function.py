import json
import requests
import os

# Slack constants needed if you wish to post back to slack
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]

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

    if "payload" in event["detail"]:
        """
        If the payload has a "payload" field, assume its an interactivity event otherwise assume its a slash command
        """
        print("Recieved interactivity event")
        print(event)
        payload = json.loads(event["detail"]["payload"][0])
        private_metadata = json.loads(payload["view"]["private_metadata"])
        text = private_metadata.get("text")  # This is the text from the slash command
        channel_id = private_metadata.get("channel_id") # This is the slack channel ID from the slash command for posting back to the same channel on slack

        # Process the modal submission here

        return {"statusCode": 200, "body": ""}

    else:
        """
        Assume you are processing a slash command
        """
        print("Recieved slash command")
        print(event)

        """
        If you wish to open a modal in response to a slash command see below template, otherwise you can do processing here
        """
        trigger_id = event["detail"]["trigger_id"][0] # This is needed to open the modal
        channel_id = event["detail"]["channel_id"][0] # This is the slack channel ID from the slash command for posting back to the same channel on slack

        metadata = _generate_metadata(event)          # It is necessary to add metadata to the modal to route the modal submission correctly!!!
        modal = _generate_modal(metadata)

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


def _generate_modal(metadata):
    """
    Create a Slack modal for responding to /sre alert command

    Args:
    - metadata (dict): The metadata to be passed to the modal

    Comments:
    Use Slack's block kit builder to get the JSON for the modal: https://app.slack.com/block-kit-builder
    """
    modal = {
        "type": "modal",
        "private_metadata": metadata,
        "submit": {"type": "plain_text", "text": "Create alert", "emoji": True},
        "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
        "title": {"type": "plain_text", "text": "On Call Bot", "emoji": True},
        "blocks": [
            # Put your blocks here
        ],
    }

    print(modal)
    return modal

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
