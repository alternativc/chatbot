import json
import requests
import os
import base64
import re
import boto3
from botocore.signers import RequestSigner
from kubernetes import client, config


# Slack constants
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]

# Qchain constants
STS_TOKEN_EXPIRES_IN = 60
AWS_REGION = os.environ["QCHAIN_AWS_REGION"]
EKS_CLUSTER_NAME = os.environ["QCHAIN_EKS_CLUSTER_NAME"]
EKS_NAMESPACE = os.environ["QCHAIN_EKS_NAMESPACE"]
DEPLOYMENTS = [
    ### REMOVED FOR SECURITY REASONS ###
]

"""
Initialize clients before lambda_handler to avoid cold starts
"""
# Assume role in Staging A
sts = boto3.client('sts')
service_id = sts.meta.service_model.service_id
assumed_role=sts.assume_role(
    RoleArn="REMOVED FOR SECURITY REASONS",
    RoleSessionName="KillSwitchSession"
)
credentials=assumed_role['Credentials']

# Create a new session with the assumed role's credentials
session = boto3.Session(region_name=AWS_REGION,
    aws_access_key_id=credentials['AccessKeyId'],
    aws_secret_access_key=credentials['SecretAccessKey'],
    aws_session_token=credentials['SessionToken'],
)

# New EKS client
eks = session.client("eks")

def lambda_handler(event, context):
    """
    Process event from event bridge and respond to Slack
    """
    # Check if the incoming event is a Scheduled Event from EventBridge to keep the lambda function warm.
    if (
        event.get("source") == "aws.events"
        and event.get("detail-type") == "Scheduled Event"
    ):
        print("Received keep-warm event. Exiting without further processing.")
        return {"statusCode": 200, "body": json.dumps("Keep-warm event processed.")}

    # Load kubeconfig
    _load_kubeconfig()

    print("Event received:")
    print(event)
    # If the payload has a "payload" field, assume its an interactivity event otherwise assume its a slash command
    if "payload" in event["detail"]:
        payload = json.loads(event["detail"]["payload"][0])

        # IMPORTANT: only listen to view_submission events
        if payload.get("type", "") != "view_submission":
            return {"statusCode": 200, "body": "Ignoring event"}

        print("Recieved interactivity event")
        private_metadata = json.loads(payload["view"]["private_metadata"])
        command = private_metadata.get("text")
        channel_id = private_metadata.get("channel_id")

        if command == "killswitch":
            print("Recieved alert modal submissions")
            _process_killswitch_modal(payload, channel_id)
            msg = f'*[Qchain]* Qredochain Killswitch procedure completed'
            _post_message_to_slack(channel_id, msg)
        else:
            print("Unknown modal submission")
            _post_message_to_slack(channel_id, "Unknown modal submission")
            return {"statusCode": 500, "body": ""}

    else:
        """
        The following code is for /qchain killswitch command only. Break into multiple functions if you want to support multiple command actions
        """
        print("Recieved slash command")
        trigger_id = event["detail"]["trigger_id"][0]
        channel_id = event["detail"]["channel_id"][0]

        metadata = _generate_metadata(event)
        print("metadata:")
        print(metadata)
        modal = _generate_killswitch_modal(metadata)

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
        # Send notification to Slack
        msg = f'*[Qchain]* @{event["detail"]["user_name"][0]} started the Qredochain Killswitch procedure'
        _post_message_to_slack(event['detail']['channel_id'][0], msg)

        return {"statusCode": 200, "body": "Modal opened successfully"}


def _generate_metadata(event):
    """
    Add internal metadata for modals to route events correctly

    Args:
    - event (dict): The event object from the lambda handler
    """
    command = event["detail"]["route"]
    channel_id = event["detail"]["channel_id"][0]
    user_id = event["detail"]["user_id"][0]
    user_name = event["detail"]["user_name"][0]
    text = event["detail"]["text"][0]
    metadata = {
        "command": command,
        "text": text,
        "channel_id": channel_id,
        "user_id": user_id,
        "user_name": user_name,
    }
    return json.dumps(metadata)


def _generate_killswitch_modal(metadata):
    """
    Create a Slack modal for responding to /qchain killswitch command

    Args:
    - metadata (dict): The metadata to be passed to the modal
    """
    modal = {
        "type": "modal",
        "private_metadata": metadata,
        "submit": {"type": "plain_text", "text": "Submit", "emoji": True},
        "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
        "title": {"type": "plain_text", "text": "Qredochain Killswitch", "emoji": True},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":rotating_light: Qredochain Killswitch actions :rotating_light:"
                }
            },
            {
                "type": "divider"
            },
        ],
    }

    # Get current status of deployments
    status = _get_killswitch_services_status()
    print(status)
    # Populate sections with the killswitch deployments
    for service in DEPLOYMENTS:
        section = {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": f"*{service}*"
            },
            "accessory": {
              "type": "static_select",
              "placeholder": {
                "type": "plain_text",
                "text": status[service],
                "emoji": True
              },
              "options": [
                {
                  "text": {
                    "type": "plain_text",
                    "text": "Running",
                    "emoji": True
                  },
                  "value": "Running"
                },
                {
                  "text": {
                    "type": "plain_text",
                    "text": "Stopped",
                    "emoji": True
                  },
                  "value": "Stopped"
                }
              ],
              "action_id": f"{service}"
            }
        }
        modal['blocks'].append(section)

    return modal


def _process_killswitch_modal(payload, channel_id):
    """
    Process the data from the alert modal and scale deployments accordingly

    Args:
    - payload (dict): The payload from the modal submission
    - channel_id (str): Slack channel id
    """
    print(payload)
    user_selection = {}
    # TODO: Get selection for each service in a dict and call scale_killswitch_services()
    values = (
        payload.get("view", {})
        .get("state", {})
        .get("values", {})
    )
    for v in values.keys():
        service = list(values[v].keys())[0]
        selection = values[v][service].get("selected_option", {})
        if selection is not None:
            value = selection.get("value", "")
            user_selection[service] = value

    print("User selection:")
    print(user_selection)
    _scale_killswitch_services(user_selection, channel_id)
    return "Done"


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

def _get_cluster_info():
    """
    Retrieve cluster endpoint and certificate
    """
    cluster_info = eks.describe_cluster(name=EKS_CLUSTER_NAME)
    endpoint = cluster_info['cluster']['endpoint']
    cert_authority = cluster_info['cluster']['certificateAuthority']['data']
    cluster_info = {
        "endpoint" : endpoint,
        "ca" : cert_authority
    }
    return cluster_info

def _get_bearer_token():
    """
    Create authentication token
    """
    signer = RequestSigner(
        service_id,
        session.region_name,
        'sts',
        'v4',
        session.get_credentials(),
        session.events
    )

    params = {
        'method': 'GET',
        'url': 'https://sts.{}.amazonaws.com/'
               '?Action=GetCallerIdentity&Version=2011-06-15'.format(session.region_name),
        'body': {},
        'headers': {
            'x-k8s-aws-id': EKS_CLUSTER_NAME
        },
        'context': {}
    }

    signed_url = signer.generate_presigned_url(
        params,
        region_name=session.region_name,
        expires_in=STS_TOKEN_EXPIRES_IN,
        operation_name=''
    )
    base64_url = base64.urlsafe_b64encode(signed_url.encode('utf-8')).decode('utf-8')

    # remove any base64 encoding padding:
    return 'k8s-aws-v1.' + re.sub(r'=*', '', base64_url)

def _load_kubeconfig():
    """
    Loads the generated kubeconfig file
    """
    cluster = _get_cluster_info()
    kubeconfig = {
        'apiVersion': 'v1',
        'clusters': [{
          'name': 'cluster1',
          'cluster': {
            'certificate-authority-data': cluster["ca"],
            'server': cluster["endpoint"]}
        }],
        'contexts': [{'name': 'context1', 'context': {'cluster': 'cluster1', "user": "user1"}}],
        'current-context': 'context1',
        'kind': 'Config',
        'preferences': {},
        'users': [{'name': 'user1', "user" : {'token': _get_bearer_token()}}]
    }
    config.load_kube_config_from_dict(config_dict=kubeconfig)
    print("Kubeconfig loaded")

def _get_killswitch_services_status():
    """
    Retrieves the status of killswitch services, Running or Stopped
    """
    status = {}
    apps_v1_api = client.AppsV1Api()
    for deployment in DEPLOYMENTS:
        scale = apps_v1_api.read_namespaced_deployment_scale(deployment, EKS_NAMESPACE, async_req=False)
        if scale.status.replicas >= 1:
            status[deployment] = "Running"
        else:
            status[deployment] = "Stopped"
    return status

def _scale_killswitch_services(services, channel_id):
    """
    Compare the current status of services and the desired given in `services` then update them accordingly.

    Args:
    - services (Dict{str: str}): Set of services with the desired state: Running or Stopped
    - channel_id (str): Slack channel id
    """
    status = _get_killswitch_services_status()
    apps_v1_api = client.AppsV1Api()
    report_msg = []

    for service in services.keys():
        # Skip services already in the desired state or without a given state
        if services[service] == status[service] or services[service] == "":
            continue
        else:
            scale = apps_v1_api.read_namespaced_deployment_scale(service, EKS_NAMESPACE, async_req=False)
            scale.spec.replicas = 1 if services[service] == "Running" else 0
            apps_v1_api.replace_namespaced_deployment_scale(service, EKS_NAMESPACE, scale)
            # Add report message
            report_msg.append(f"Scaled service `{service}` to `{scale.spec.replicas}` replicas")
    if len(report_msg) >= 1:
        _post_message_to_slack(channel_id, ('\n').join(report_msg))
