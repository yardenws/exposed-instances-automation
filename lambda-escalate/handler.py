import json
import os
import boto3


def handler(event, context):
    """Escalation Lambda — sends a consolidated SES email for escalated instances."""
    body = event
    if isinstance(event.get("body"), str):
        body = json.loads(event["body"])

    instance_ids = body.get("instance_ids", [])
    details = body.get("details", [])
    if not instance_ids:
        return response(400, {"error": "No instance_ids provided"})

    sender = os.environ["SES_SENDER_EMAIL"]
    recipients = json.loads(os.environ["SES_RECIPIENT_EMAILS"])

    html_body = build_email_body(instance_ids, details)

    ses = boto3.client("ses")
    ses.send_email(
        Source=sender,
        Destination={"ToAddresses": recipients},
        Message={
            "Subject": {
                "Data": f"EC2 Exposure Alert — {len(instance_ids)} instance(s) escalated",
                "Charset": "UTF-8",
            },
            "Body": {
                "Html": {
                    "Data": html_body,
                    "Charset": "UTF-8",
                }
            },
        },
    )

    return response(200, {"escalated_instances": instance_ids})


def build_email_body(instance_ids, details):
    """Build an HTML table of escalated instances."""
    rows = ""
    details_map = {d["instance_id"]: d for d in details} if details else {}

    for iid in instance_ids:
        d = details_map.get(iid, {})
        rows += f"""<tr>
            <td>{iid}</td>
            <td>{d.get('account_id', 'N/A')}</td>
            <td>{d.get('public_ip', 'N/A')}</td>
            <td>{d.get('instance_type', 'N/A')}</td>
            <td>{d.get('reason', 'Manually escalated')}</td>
        </tr>"""

    return f"""
    <html>
    <body>
        <h2>EC2 Exposure — Escalated Instances</h2>
        <p>The following instances were flagged as publicly exposed and escalated for review.</p>
        <table border="1" cellpadding="8" cellspacing="0">
            <tr>
                <th>Instance ID</th>
                <th>Account</th>
                <th>Public IP</th>
                <th>Type</th>
                <th>Reason</th>
            </tr>
            {rows}
        </table>
    </body>
    </html>
    """


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
