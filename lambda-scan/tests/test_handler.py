import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest

from handler import (
    handler,
    get_exposed_instances,
    get_public_subnets,
    should_skip,
    get_security_group_rules,
)


@pytest.fixture(autouse=True)
def env_vars():
    with patch.dict(os.environ, {
        "TARGET_ACCOUNT_IDS": '["111111111111"]',
        "SKIP_TAG_KEY": "SkipScan",
        "SKIP_TAG_VALUE": "true",
        "AWS_REGION_SCAN": "us-east-1",
    }):
        yield


MOCK_ROUTE_TABLES = {
    "RouteTables": [
        {
            "Routes": [{"GatewayId": "igw-12345", "DestinationCidrBlock": "0.0.0.0/0"}],
            "Associations": [{"SubnetId": "subnet-pub1"}, {"SubnetId": "subnet-pub2"}],
        },
        {
            "Routes": [{"GatewayId": "local"}],
            "Associations": [{"SubnetId": "subnet-priv1"}],
        },
    ]
}


def make_instance(instance_id, public_ip, subnet_id, state="running", tags=None, sgs=None):
    return {
        "InstanceId": instance_id,
        "InstanceType": "t3.micro",
        "PublicIpAddress": public_ip,
        "SubnetId": subnet_id,
        "VpcId": "vpc-123",
        "LaunchTime": datetime(2025, 1, 1),
        "State": {"Name": state},
        "Tags": tags or [],
        "SecurityGroups": sgs or [{"GroupId": "sg-111"}],
    }


MOCK_SECURITY_GROUPS = {
    "SecurityGroups": [
        {
            "GroupId": "sg-111",
            "GroupName": "web-sg",
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 443,
                    "ToPort": 443,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    "Ipv6Ranges": [],
                }
            ],
            "IpPermissionsEgress": [],
        }
    ]
}


class TestGetPublicSubnets:
    def test_identifies_public_subnets(self):
        ec2 = MagicMock()
        ec2.describe_route_tables.return_value = MOCK_ROUTE_TABLES
        result = get_public_subnets(ec2)
        assert result == {"subnet-pub1", "subnet-pub2"}

    def test_no_igw_routes(self):
        ec2 = MagicMock()
        ec2.describe_route_tables.return_value = {
            "RouteTables": [
                {
                    "Routes": [{"GatewayId": "local"}],
                    "Associations": [{"SubnetId": "subnet-priv1"}],
                }
            ]
        }
        result = get_public_subnets(ec2)
        assert result == set()


class TestShouldSkip:
    def test_skip_tagged_instance(self):
        instance = {"Tags": [{"Key": "SkipScan", "Value": "true"}]}
        assert should_skip(instance, "SkipScan", "true") is True

    def test_no_skip_tag(self):
        instance = {"Tags": [{"Key": "Name", "Value": "web-server"}]}
        assert should_skip(instance, "SkipScan", "true") is False

    def test_no_tags(self):
        instance = {}
        assert should_skip(instance, "SkipScan", "true") is False


class TestGetSecurityGroupRules:
    def test_returns_rules(self):
        ec2 = MagicMock()
        ec2.describe_security_groups.return_value = MOCK_SECURITY_GROUPS
        result = get_security_group_rules(ec2, ["sg-111"])
        assert len(result) == 1
        assert result[0]["group_id"] == "sg-111"
        assert result[0]["inbound_rules"][0]["cidr_ranges"] == ["0.0.0.0/0"]

    def test_empty_sg_ids(self):
        ec2 = MagicMock()
        result = get_security_group_rules(ec2, [])
        assert result == []
        ec2.describe_security_groups.assert_not_called()


class TestGetExposedInstances:
    def test_finds_exposed_instance(self):
        ec2 = MagicMock()
        ec2.describe_route_tables.return_value = MOCK_ROUTE_TABLES
        ec2.describe_security_groups.return_value = MOCK_SECURITY_GROUPS
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "Reservations": [
                    {
                        "Instances": [
                            make_instance("i-exposed", "1.2.3.4", "subnet-pub1"),
                        ]
                    }
                ]
            }
        ]
        ec2.get_paginator.return_value = paginator

        result = get_exposed_instances(ec2, "111111111111", "SkipScan", "true")
        assert len(result) == 1
        assert result[0]["instance_id"] == "i-exposed"
        assert result[0]["public_ip"] == "1.2.3.4"
        assert result[0]["account_id"] == "111111111111"

    def test_skips_private_subnet(self):
        ec2 = MagicMock()
        ec2.describe_route_tables.return_value = MOCK_ROUTE_TABLES
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "Reservations": [
                    {
                        "Instances": [
                            make_instance("i-private", "1.2.3.4", "subnet-priv1"),
                        ]
                    }
                ]
            }
        ]
        ec2.get_paginator.return_value = paginator

        result = get_exposed_instances(ec2, "111111111111", "SkipScan", "true")
        assert len(result) == 0

    def test_skips_no_public_ip(self):
        ec2 = MagicMock()
        ec2.describe_route_tables.return_value = MOCK_ROUTE_TABLES
        inst = make_instance("i-nopub", None, "subnet-pub1")
        del inst["PublicIpAddress"]
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Reservations": [{"Instances": [inst]}]}
        ]
        ec2.get_paginator.return_value = paginator

        result = get_exposed_instances(ec2, "111111111111", "SkipScan", "true")
        assert len(result) == 0

    def test_skips_stopped_instance(self):
        ec2 = MagicMock()
        ec2.describe_route_tables.return_value = MOCK_ROUTE_TABLES
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "Reservations": [
                    {
                        "Instances": [
                            make_instance("i-stopped", "1.2.3.4", "subnet-pub1", state="stopped"),
                        ]
                    }
                ]
            }
        ]
        ec2.get_paginator.return_value = paginator

        result = get_exposed_instances(ec2, "111111111111", "SkipScan", "true")
        assert len(result) == 0

    def test_skips_tagged_instance(self):
        ec2 = MagicMock()
        ec2.describe_route_tables.return_value = MOCK_ROUTE_TABLES
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "Reservations": [
                    {
                        "Instances": [
                            make_instance(
                                "i-skipped", "1.2.3.4", "subnet-pub1",
                                tags=[{"Key": "SkipScan", "Value": "true"}],
                            ),
                        ]
                    }
                ]
            }
        ]
        ec2.get_paginator.return_value = paginator

        result = get_exposed_instances(ec2, "111111111111", "SkipScan", "true")
        assert len(result) == 0


class TestHandler:
    @patch("handler.scan_account")
    def test_aggregates_across_accounts(self, mock_scan):
        mock_scan.side_effect = [
            [{"instance_id": "i-aaa", "account_id": "111111111111"}],
            [{"instance_id": "i-bbb", "account_id": "222222222222"}],
        ]
        with patch.dict(os.environ, {"TARGET_ACCOUNT_IDS": '["111111111111","222222222222"]'}):
            result = handler({}, None)

        assert len(result["instances"]) == 2
        assert mock_scan.call_count == 2

    @patch("handler.scan_account")
    def test_empty_accounts(self, mock_scan):
        with patch.dict(os.environ, {"TARGET_ACCOUNT_IDS": "[]"}):
            result = handler({}, None)

        assert result["instances"] == []
        mock_scan.assert_not_called()
