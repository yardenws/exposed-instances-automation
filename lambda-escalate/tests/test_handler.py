import json
import os
from unittest.mock import patch, MagicMock

import pytest

from handler import handler, build_email_body


@pytest.fixture(autouse=True)
def env_vars():
    with patch.dict(os.environ, {
        "SES_SENDER_EMAIL": "alerts@example.com",
        "SES_RECIPIENT_EMAILS": '["team@example.com"]',
    }):
        yield


class TestBuildEmailBody:
    def test_builds_html_with_details(self):
        html = build_email_body(
            ["i-abc"],
            [{"instance_id": "i-abc", "account_id": "111", "public_ip": "1.2.3.4", "instance_type": "t3.micro"}],
        )
        assert "i-abc" in html
        assert "1.2.3.4" in html
        assert "t3.micro" in html

    def test_builds_html_without_details(self):
        html = build_email_body(["i-abc"], [])
        assert "i-abc" in html
        assert "N/A" in html

    def test_multiple_instances(self):
        html = build_email_body(["i-abc", "i-def"], [])
        assert "i-abc" in html
        assert "i-def" in html


class TestHandler:
    def test_sends_email(self):
        mock_ses = MagicMock()

        with patch("handler.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_ses
            result = handler(
                {"instance_ids": ["i-abc"], "details": []},
                None,
            )

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["escalated_instances"] == ["i-abc"]
        mock_ses.send_email.assert_called_once()

        call_kwargs = mock_ses.send_email.call_args[1]
        assert call_kwargs["Source"] == "alerts@example.com"
        assert call_kwargs["Destination"]["ToAddresses"] == ["team@example.com"]

    def test_no_instance_ids(self):
        result = handler({"instance_ids": []}, None)
        assert result["statusCode"] == 400

    def test_parses_api_gateway_event(self):
        mock_ses = MagicMock()

        event = {"body": json.dumps({"instance_ids": ["i-abc"], "details": []})}

        with patch("handler.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_ses
            result = handler(event, None)

        assert result["statusCode"] == 200
