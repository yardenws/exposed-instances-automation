import json
import os
import boto3


def handler(event, context):
    """Scanner Lambda — scans target accounts for publicly exposed EC2 instances."""
    target_account_ids = json.loads(os.environ.get("TARGET_ACCOUNT_IDS", "[]"))
    skip_tag_key = os.environ.get("SKIP_TAG_KEY", "SkipScan")
    skip_tag_value = os.environ.get("SKIP_TAG_VALUE", "true")
    scan_regions = json.loads(os.environ.get("SCAN_REGIONS", '["us-east-1"]'))

    all_instances = []

    for account_id in target_account_ids:
        for region in scan_regions:
            instances = scan_account(account_id, region, skip_tag_key, skip_tag_value)
            all_instances.extend(instances)

    return {"instances": all_instances}


def scan_account(account_id, region, skip_tag_key, skip_tag_value):
    """Assume role in target account and scan for exposed instances."""
    sts = boto3.client("sts")
    assumed = sts.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/ExposedInstancesScannerRole",
        RoleSessionName="ExposedInstancesScanner",
    )
    credentials = assumed["Credentials"]

    ec2 = boto3.client(
        "ec2",
        region_name=region,
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )

    instances = get_exposed_instances(ec2, account_id, skip_tag_key, skip_tag_value)
    return instances


def get_exposed_instances(ec2, account_id, skip_tag_key, skip_tag_value):
    """Find instances with public IPs in public subnets."""
    public_subnets = get_public_subnets(ec2)

    paginator = ec2.get_paginator("describe_instances")
    exposed = []

    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                if instance.get("State", {}).get("Name") != "running":
                    continue

                if not instance.get("PublicIpAddress"):
                    continue

                subnet_id = instance.get("SubnetId", "")
                if subnet_id not in public_subnets:
                    continue

                if should_skip(instance, skip_tag_key, skip_tag_value):
                    continue

                sg_ids = [sg["GroupId"] for sg in instance.get("SecurityGroups", [])]
                security_groups = get_security_group_rules(ec2, sg_ids)

                exposed.append({
                    "instance_id": instance["InstanceId"],
                    "instance_type": instance.get("InstanceType", ""),
                    "public_ip": instance["PublicIpAddress"],
                    "subnet_id": subnet_id,
                    "vpc_id": instance.get("VpcId", ""),
                    "launch_time": instance.get("LaunchTime", "").isoformat()
                    if hasattr(instance.get("LaunchTime", ""), "isoformat")
                    else str(instance.get("LaunchTime", "")),
                    "tags": {
                        tag["Key"]: tag["Value"]
                        for tag in instance.get("Tags", [])
                    },
                    "account_id": account_id,
                    "security_groups": security_groups,
                })

    return exposed


def get_public_subnets(ec2):
    """Return set of subnet IDs that have a route to an internet gateway."""
    public_subnet_ids = set()

    route_tables = ec2.describe_route_tables()["RouteTables"]
    for rt in route_tables:
        has_igw = any(
            route.get("GatewayId", "").startswith("igw-")
            for route in rt.get("Routes", [])
        )
        if has_igw:
            for assoc in rt.get("Associations", []):
                if assoc.get("SubnetId"):
                    public_subnet_ids.add(assoc["SubnetId"])

    return public_subnet_ids


def should_skip(instance, skip_tag_key, skip_tag_value):
    """Check if instance has the skip tag."""
    for tag in instance.get("Tags", []):
        if tag["Key"] == skip_tag_key and tag["Value"] == skip_tag_value:
            return True
    return False


def get_security_group_rules(ec2, sg_ids):
    """Fetch inbound/outbound rules for the given security groups."""
    if not sg_ids:
        return []

    response = ec2.describe_security_groups(GroupIds=sg_ids)
    result = []

    for sg in response["SecurityGroups"]:
        result.append({
            "group_id": sg["GroupId"],
            "group_name": sg.get("GroupName", ""),
            "inbound_rules": [
                {
                    "protocol": rule.get("IpProtocol", ""),
                    "from_port": rule.get("FromPort", -1),
                    "to_port": rule.get("ToPort", -1),
                    "cidr_ranges": [ip["CidrIp"] for ip in rule.get("IpRanges", [])],
                    "ipv6_ranges": [ip["CidrIpv6"] for ip in rule.get("Ipv6Ranges", [])],
                }
                for rule in sg.get("IpPermissions", [])
            ],
            "outbound_rules": [
                {
                    "protocol": rule.get("IpProtocol", ""),
                    "from_port": rule.get("FromPort", -1),
                    "to_port": rule.get("ToPort", -1),
                    "cidr_ranges": [ip["CidrIp"] for ip in rule.get("IpRanges", [])],
                    "ipv6_ranges": [ip["CidrIpv6"] for ip in rule.get("Ipv6Ranges", [])],
                }
                for rule in sg.get("IpPermissionsEgress", [])
            ],
        })

    return result
