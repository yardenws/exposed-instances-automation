import hashlib
import hmac
import json
import time
import urllib.request

SEVERITY_EMOJI = {
    "critical": "\U0001f534",
    "high": "\U0001f7e0",
    "medium": "\U0001f7e1",
    "low": "\U0001f7e2",
}

ACTION_EMOJI = {
    "mitigate": "\U0001f6d1",
    "escalate": "\U0001f4e7",
    "monitor": "\U0001f441\ufe0f",
}


def verify_slack_signature(
    signing_secret: str, timestamp: str, body: str, signature: str
) -> bool:
    """Verify Slack request signature using HMAC-SHA256."""
    if abs(time.time() - int(timestamp)) > 300:
        return False

    sig_basestring = f"v0:{timestamp}:{body}"
    computed = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


def build_analysis_blocks(
    summary: str, recommendations: list[dict], instances: list[dict]
) -> list[dict]:
    """Build Slack Block Kit blocks for the analysis message."""
    inst_map = {i["instance_id"]: i for i in instances}

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "\U0001f6a8 EC2 Public Exposure Alert",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Summary:* {summary}"},
        },
        {"type": "divider"},
    ]

    for rec in recommendations:
        severity_icon = SEVERITY_EMOJI.get(rec["severity"], "\u26aa")
        action_icon = ACTION_EMOJI.get(rec["recommended_action"], "\u2753")
        inst = inst_map.get(rec["instance_id"], {})

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{severity_icon} *{rec['instance_id']}* "
                        f"— _{rec['severity'].upper()}_\n"
                        f"IP: `{inst.get('public_ip', 'N/A')}` | "
                        f"Type: `{inst.get('instance_type', 'N/A')}` | "
                        f"Account: `{inst.get('account_id', 'N/A')}`\n"
                        f"{action_icon} Recommended: "
                        f"*{rec['recommended_action']}*\n"
                        f"_{rec['reasoning']}_"
                    ),
                },
            }
        )
        blocks.append({"type": "divider"})

    instance_ids = [r["instance_id"] for r in recommendations]
    details = [
        {
            "instance_id": r["instance_id"],
            "account_id": inst_map.get(r["instance_id"], {}).get("account_id", ""),
            "public_ip": inst_map.get(r["instance_id"], {}).get("public_ip", ""),
            "instance_type": inst_map.get(r["instance_id"], {}).get(
                "instance_type", ""
            ),
            "reason": r["reasoning"][:100],
        }
        for r in recommendations
    ]

    mitigate_value = json.dumps({"instance_ids": instance_ids, "details": details})
    escalate_value = json.dumps({"instance_ids": instance_ids, "details": details})

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "\U0001f6d1 Mitigate All",
                        "emoji": True,
                    },
                    "style": "danger",
                    "action_id": "mitigate_all",
                    "value": mitigate_value[:2000],
                    "confirm": {
                        "title": {
                            "type": "plain_text",
                            "text": "Confirm Mitigation",
                        },
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"This will *stop* {len(instance_ids)} "
                                f"instance(s). Continue?"
                            ),
                        },
                        "confirm": {
                            "type": "plain_text",
                            "text": "Stop Instances",
                        },
                        "deny": {"type": "plain_text", "text": "Cancel"},
                    },
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "\U0001f4e7 Escalate All",
                        "emoji": True,
                    },
                    "action_id": "escalate_all",
                    "value": escalate_value[:2000],
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "\u2705 Dismiss",
                        "emoji": True,
                    },
                    "action_id": "dismiss",
                },
            ],
        }
    )

    return blocks


def post_slack_message(
    bot_token: str, channel: str, blocks: list[dict], text: str = "EC2 Exposure Alert"
) -> dict:
    """Post a message to Slack using the Web API."""
    payload = json.dumps(
        {"channel": channel, "text": text, "blocks": blocks}
    ).encode()

    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def update_slack_message(
    bot_token: str,
    channel: str,
    ts: str,
    blocks: list[dict],
    text: str = "Message updated",
) -> dict:
    """Update an existing Slack message."""
    payload = json.dumps(
        {"channel": channel, "ts": ts, "text": text, "blocks": blocks}
    ).encode()

    req = urllib.request.Request(
        "https://slack.com/api/chat.update",
        data=payload,
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())
