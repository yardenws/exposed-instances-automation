import json
import logging
import os
import urllib.parse

import boto3

from slack_utils import (
    build_analysis_blocks,
    post_slack_message,
    update_slack_message,
    verify_slack_signature,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """Agent Lambda — two entry points:

    1. Step Function invocation: receives scan results, runs AI analysis, posts to Slack
    2. API Gateway (Slack interactions): receives button clicks, dispatches to mitigate/escalate
    3. API Gateway (Slack slash command): /scan triggers on-demand Step Function execution
    """
    # Slack interaction or slash command via API Gateway
    if "requestContext" in event:
        return handle_api_gateway(event)

    # Step Function invocation
    return handle_step_function(event)


def handle_step_function(event):
    """Process scan results from Step Function — run AI analysis and post to Slack."""
    instances_raw = event.get("instances", [])

    secrets = get_secrets()
    bot_token = secrets["slack"]["bot_token"]
    channel_id = secrets["slack"]["channel_id"]

    if not instances_raw:
        logger.info("No exposed instances found")
        post_slack_message(
            bot_token,
            channel_id,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "\u2705 *Scan complete* — no publicly exposed instances found.",
                    },
                }
            ],
            text="Scan complete — no exposed instances found",
        )
        return {"status": "no_instances"}

    # Lazy imports — pydantic/anthropic require Linux binaries (Docker build)
    from agent import run_analysis
    from models import ExposedInstance

    instances = [ExposedInstance(**i) for i in instances_raw]

    claude_api_key = secrets["claude"]["api_key"]

    logger.info("Running AI analysis on %d instances", len(instances))
    analysis = run_analysis(instances, claude_api_key)

    recommendations = [r.model_dump() for r in analysis.recommendations]
    blocks = build_analysis_blocks(analysis.summary, recommendations, instances_raw)

    post_slack_message(bot_token, channel_id, blocks)

    return {
        "status": "posted",
        "instance_count": len(instances),
        "summary": analysis.summary,
    }


def handle_api_gateway(event):
    """Handle Slack interactions and slash commands from API Gateway."""
    body = event.get("body", "")
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode()

    # Verify Slack signature
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")

    secrets = get_secrets()
    signing_secret = secrets["slack"]["signing_secret"]

    if not verify_slack_signature(signing_secret, timestamp, body, signature):
        logger.warning("Invalid Slack signature")
        return api_response(401, {"error": "Invalid signature"})

    # Parse body — Slack sends form-encoded for interactions, form-encoded for slash commands
    parsed = urllib.parse.parse_qs(body)

    # Slash command: /scan
    if "command" in parsed:
        return handle_slash_command(parsed, secrets)

    # Interactive message: button clicks
    if "payload" in parsed:
        payload = json.loads(parsed["payload"][0])
        return handle_interaction(payload, secrets)

    return api_response(400, {"error": "Unknown request type"})


def handle_slash_command(parsed, secrets):
    """Handle /scan slash command — start Step Function execution."""
    command = parsed.get("command", [""])[0]

    if command != "/scan":
        return slash_response(f"Unknown command: {command}")

    step_function_arn = os.environ.get("STEP_FUNCTION_ARN", "")
    if not step_function_arn:
        return slash_response("Step Function ARN not configured")

    sfn = boto3.client("stepfunctions")
    sfn.start_execution(stateMachineArn=step_function_arn, input="{}")

    logger.info("On-demand scan triggered via /scan command")
    return slash_response("\U0001f50d Scan triggered! Results will be posted here shortly.")


def handle_interaction(payload, secrets):
    """Handle Slack interactive message button clicks."""
    bot_token = secrets["slack"]["bot_token"]
    action = payload.get("actions", [{}])[0]
    action_id = action.get("action_id", "")
    value = action.get("value", "{}")
    channel = payload.get("channel", {}).get("id", "")
    message_ts = payload.get("message", {}).get("ts", "")
    user_name = payload.get("user", {}).get("username", "unknown")

    data = json.loads(value) if value else {}
    instance_ids = data.get("instance_ids", [])
    details = data.get("details", [])

    lambda_client = boto3.client("lambda")

    if action_id == "mitigate_all":
        invoke_lambda(
            lambda_client,
            os.environ.get("MITIGATION_FUNCTION_NAME", ""),
            {"instance_ids": instance_ids},
        )
        update_message_after_action(
            bot_token, channel, message_ts,
            f"\U0001f6d1 *Mitigation initiated* by @{user_name} — "
            f"stopping {len(instance_ids)} instance(s)",
        )
        logger.info("Mitigation triggered by %s for %d instances", user_name, len(instance_ids))

    elif action_id == "escalate_all":
        invoke_lambda(
            lambda_client,
            os.environ.get("ESCALATION_FUNCTION_NAME", ""),
            {"instance_ids": instance_ids, "details": details},
        )
        update_message_after_action(
            bot_token, channel, message_ts,
            f"\U0001f4e7 *Escalation sent* by @{user_name} — "
            f"{len(instance_ids)} instance(s) escalated to security team",
        )
        logger.info("Escalation triggered by %s for %d instances", user_name, len(instance_ids))

    elif action_id == "dismiss":
        update_message_after_action(
            bot_token, channel, message_ts,
            f"\u2705 *Dismissed* by @{user_name}",
        )
        logger.info("Alert dismissed by %s", user_name)

    # Slack expects 200 with empty body for interaction acknowledgment
    return api_response(200, "")


def invoke_lambda(client, function_name, payload):
    """Invoke another Lambda function asynchronously."""
    if not function_name:
        logger.error("Lambda function name not configured")
        return
    client.invoke(
        FunctionName=function_name,
        InvocationType="Event",
        Payload=json.dumps(payload),
    )


def update_message_after_action(bot_token, channel, ts, text):
    """Replace the interactive message with a status update."""
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        }
    ]
    update_slack_message(bot_token, channel, ts, blocks, text=text)


def get_secrets():
    """Retrieve Claude API key and Slack secrets from Secrets Manager."""
    sm = boto3.client("secretsmanager")

    claude_secret = sm.get_secret_value(SecretId="exposed-instances/claude-api-key")
    claude = json.loads(claude_secret["SecretString"])

    slack_secret = sm.get_secret_value(SecretId="exposed-instances/slack")
    slack = json.loads(slack_secret["SecretString"])

    return {"claude": claude, "slack": slack}


def api_response(status_code, body):
    """Return API Gateway-compatible response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body) if isinstance(body, (dict, list)) else body,
    }


def slash_response(text):
    """Return a Slack slash command response (ephemeral by default)."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"response_type": "ephemeral", "text": text}),
    }
