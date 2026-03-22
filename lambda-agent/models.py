from pydantic import BaseModel


class SecurityGroupRule(BaseModel):
    protocol: str
    from_port: int = -1
    to_port: int = -1
    cidr_ranges: list[str] = []
    ipv6_ranges: list[str] = []


class SecurityGroup(BaseModel):
    group_id: str
    group_name: str = ""
    inbound_rules: list[SecurityGroupRule] = []
    outbound_rules: list[SecurityGroupRule] = []


class ExposedInstance(BaseModel):
    instance_id: str
    instance_type: str = ""
    public_ip: str
    subnet_id: str = ""
    vpc_id: str = ""
    launch_time: str = ""
    tags: dict[str, str] = {}
    account_id: str = ""
    security_groups: list[SecurityGroup] = []


class InstanceRecommendation(BaseModel):
    instance_id: str
    severity: str  # critical, high, medium, low
    reasoning: str
    recommended_action: str  # mitigate, escalate, monitor


class AnalysisOutput(BaseModel):
    summary: str
    recommendations: list[InstanceRecommendation]
