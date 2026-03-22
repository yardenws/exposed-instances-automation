import json
import os
import boto3


def handler(event, context):
    """Mitigation Lambda — stops exposed EC2 instances."""
    body = event
    if isinstance(event.get("body"), str):
        body = json.loads(event["body"])

    instance_ids = body.get("instance_ids", [])
    if not instance_ids:
        return response(400, {"error": "No instance_ids provided"})

    ec2 = boto3.client("ec2")
    result = ec2.stop_instances(InstanceIds=instance_ids)

    stopped = [
        {
            "instance_id": i["InstanceId"],
            "previous_state": i["PreviousState"]["Name"],
            "current_state": i["CurrentState"]["Name"],
        }
        for i in result.get("StoppingInstances", [])
    ]

    return response(200, {"stopped_instances": stopped})


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
