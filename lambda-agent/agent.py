import os
from dataclasses import dataclass

from pydantic_ai import Agent

from models import AnalysisOutput, ExposedInstance

SYSTEM_INSTRUCTIONS = """\
You are a cloud security analyst specializing in AWS EC2 exposure assessment.

You will receive data about EC2 instances detected as publicly exposed \
(running in a public subnet with a public IP address).

For each instance, analyze:
1. Security group inbound rules — look for overly permissive rules \
(0.0.0.0/0 or ::/0 on sensitive ports)
2. The exposed ports and protocols — SSH (22), RDP (3389), \
databases (3306, 5432, 27017), etc. are high risk
3. Instance tags — look for Name, Environment, Owner tags that indicate purpose
4. The combination of factors that determines overall risk

Severity levels:
- critical: Wide-open security groups (0.0.0.0/0 on multiple ports or all \
traffic) with no identifying tags
- high: Sensitive ports exposed to the internet (SSH, RDP, databases)
- medium: Non-sensitive ports exposed, or instances with clear ownership/purpose tags
- low: Only HTTP/HTTPS (80/443) exposed with proper tagging

Recommended actions:
- mitigate: For critical and high severity — instance should be stopped immediately
- escalate: For medium severity — notify the security team for review
- monitor: For low severity — acceptable risk, but should be tracked

Provide a concise executive summary followed by per-instance analysis. \
Each recommendation must reference the exact instance_id from the input data."""


@dataclass
class AgentDeps:
    instances: list[ExposedInstance]


analysis_agent = Agent(
    "anthropic:claude-sonnet-4-20250514",
    deps_type=AgentDeps,
    output_type=AnalysisOutput,
    instructions=SYSTEM_INSTRUCTIONS,
)


def run_analysis(instances: list[ExposedInstance], api_key: str) -> AnalysisOutput:
    """Run the AI analysis on exposed instances."""
    os.environ["ANTHROPIC_API_KEY"] = api_key

    deps = AgentDeps(instances=instances)

    instance_details = []
    for inst in instances:
        sg_lines = []
        for sg in inst.security_groups:
            rules = []
            for rule in sg.inbound_rules:
                sources = rule.cidr_ranges + rule.ipv6_ranges
                rules.append(
                    f"    Inbound: {rule.protocol} "
                    f"ports {rule.from_port}-{rule.to_port} "
                    f"from {sources}"
                )
            sg_lines.append(
                f"  SG {sg.group_id} ({sg.group_name}):\n" + "\n".join(rules)
            )

        instance_details.append(
            f"Instance: {inst.instance_id}\n"
            f"  Type: {inst.instance_type}\n"
            f"  Public IP: {inst.public_ip}\n"
            f"  Account: {inst.account_id}\n"
            f"  VPC: {inst.vpc_id} / Subnet: {inst.subnet_id}\n"
            f"  Tags: {inst.tags}\n"
            f"  Security Groups:\n" + "\n".join(sg_lines)
        )

    prompt = (
        f"Analyze these {len(instances)} publicly exposed EC2 instances:\n\n"
        + "\n\n---\n\n".join(instance_details)
    )

    result = analysis_agent.run_sync(prompt, deps=deps)
    return result.output
