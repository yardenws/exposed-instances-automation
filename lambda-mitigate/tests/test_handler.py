import json
from unittest.mock import patch, MagicMock

import pytest

from handler import handler


class TestHandler:
    def test_stops_instances(self):
        mock_ec2 = MagicMock()
        mock_ec2.stop_instances.return_value = {
            "StoppingInstances": [
                {
                    "InstanceId": "i-abc",
                    "PreviousState": {"Name": "running"},
                    "CurrentState": {"Name": "stopping"},
                },
                {
                    "InstanceId": "i-def",
                    "PreviousState": {"Name": "running"},
                    "CurrentState": {"Name": "stopping"},
                },
            ]
        }

        with patch("handler.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_ec2
            result = handler({"instance_ids": ["i-abc", "i-def"]}, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body["stopped_instances"]) == 2
        mock_ec2.stop_instances.assert_called_once_with(InstanceIds=["i-abc", "i-def"])

    def test_no_instance_ids(self):
        result = handler({"instance_ids": []}, None)
        assert result["statusCode"] == 400

    def test_missing_instance_ids(self):
        result = handler({}, None)
        assert result["statusCode"] == 400

    def test_parses_api_gateway_event(self):
        mock_ec2 = MagicMock()
        mock_ec2.stop_instances.return_value = {
            "StoppingInstances": [
                {
                    "InstanceId": "i-abc",
                    "PreviousState": {"Name": "running"},
                    "CurrentState": {"Name": "stopping"},
                }
            ]
        }

        event = {"body": json.dumps({"instance_ids": ["i-abc"]})}

        with patch("handler.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_ec2
            result = handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["stopped_instances"][0]["instance_id"] == "i-abc"
