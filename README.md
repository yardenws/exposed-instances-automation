# EC2 Public Exposure — Automated Mitigation Workflow

An event-driven system that scans for EC2 instances exposed to the public internet, enriches the findings with an AI agent, and lets a human decide how to respond — production safe due to human in the loop procedure.

## Problem

EC2 instances in public subnets with public IPs are a common attack surface. Manually auditing them doesn't scale. This project automates the detection, enrichment, and response workflow while keeping a human in the loop for safety.

## Architecture

```
EventBridge (cron schedule) ──┐
                               ├──► AWS Step Function (orchestration)
Slack /scan command ──────────┘          │
                                         ▼
                              Scanner Lambda (cross-account)
                                         │
                                         ▼
                              Agent Lambda (Pydantic AI + Claude)
                                   │
                                   ▼
                             Slack App (interactive message)
                             User clicks: Mitigate | Escalate | Dismiss
                                   │
                                   ▼
                             API Gateway ──► Agent Lambda (dispatcher)
                                              ├──► Mitigation Lambda ──► ec2:StopInstances
                                              └──► Escalation Lambda ──► SES email to team
```

## Components

### Lambda Responsibilities (TL;DR)

| Lambda | Role | What It Does |
|--------|------|--------------|
| **Scanner** | Worker | Scans target AWS accounts for EC2 instances with public IPs and permissive security groups |
| **Agent** | Hub / Dispatcher | The central Lambda — handles all Slack interactions (slash commands, button clicks), runs Claude AI analysis on scan results, and invokes the other Lambdas accordingly |
| **Mitigation** | Worker | Stops EC2 instances flagged by the scanner |
| **Escalation** | Worker | Sends an SES email alert to the security team |

> Slack only talks to the **Agent Lambda** (via a single API Gateway endpoint). The Agent decides which worker to invoke based on the user's action.

### 1. Scanner Lambda (Python)

Runs on a schedule via EventBridge → Step Functions, or on-demand via Slack `/scan` command.

- Iterates over a list of target AWS account IDs
- For each account, assumes a cross-account IAM role (`sts:AssumeRole`) to obtain temporary credentials
- Calls `ec2:DescribeInstances` across the configured region in the target account
- Identifies instances that are **both** in a public subnet **and** have a public IP assigned
- Skips instances with a configurable exclusion tag (e.g. `SkipScan: true`)
- Collects per instance: Instance ID, Instance Type, Public IP, Subnet ID, VPC ID, Launch Time, Tags, Account ID
- Collects attached Security Groups and their inbound/outbound rules for each instance
- Returns the aggregated results (across all accounts) to the Step Function for the next stage

**IAM permissions (central account — Scanner Lambda role):**
- `sts:AssumeRole` on `arn:aws:iam::*:role/ExposedInstancesScannerRole` (scoped to target accounts)

**IAM permissions (granted by the assumed role in each target account):**
- `ec2:DescribeInstances`, `ec2:DescribeRouteTables`, `ec2:DescribeSubnets`, `ec2:DescribeSecurityGroups`

### 2. Step Function (Orchestration)

Coordinates the workflow as a state machine:

1. **Scan** — Invoke Scanner Lambda
2. **CheckResults** — If no instances found, succeed early
3. **Enrich** — Invoke Agent Lambda (passes scan results → AI analysis → Slack post)

Triggered by:
- **EventBridge cron rule** — e.g. every 6 hours (scheduled)
- **Slack `/scan` command** — on-demand via Agent Lambda → `states:StartExecution`

### 3. Agent Lambda (Python — Pydantic AI + Claude API)

A Python Lambda function running a [Pydantic AI](https://ai.pydantic.dev/) agent with Claude as the LLM backend. Serves as both the AI analysis engine and the Slack interaction dispatcher.

**Entry point 1 — Step Function invocation (AI analysis):**
- Receives scan JSON payload from the Step Function (including security group rules)
- Retrieves Claude API key and Slack secrets from Secrets Manager
- Runs Pydantic AI agent with Claude to analyze security groups and assess exposure severity
- Generates structured output: executive summary + per-instance recommendation (severity, action, reasoning)
- Posts an interactive Slack message (Block Kit) with Mitigate All / Escalate All / Dismiss buttons

**Entry point 2 — API Gateway (Slack interactions):**
- Receives Slack interaction payloads via `POST /slack/interactions`
- Verifies Slack request signature (HMAC-SHA256)
- Dispatches button clicks to the appropriate Lambda:
  - **Mitigate All** → invokes Mitigation Lambda asynchronously
  - **Escalate All** → invokes Escalation Lambda asynchronously
  - **Dismiss** → updates the Slack message to show dismissed status
- Updates the original Slack message with action confirmation

**Entry point 3 — API Gateway (Slack slash command):**
- Receives `/scan` slash command via `POST /slack/interactions`
- Verifies Slack request signature
- Starts a new Step Function execution (`states:StartExecution`)
- Responds with acknowledgment message to user

**IAM permissions:**
- `secretsmanager:GetSecretValue` (for Claude API key & Slack secrets)
- `lambda:InvokeFunction` (for Mitigation & Escalation Lambdas)
- `states:StartExecution` (for on-demand scan trigger via `/scan`)

### 4. Slack App (Human in the Loop)

A Slack app installed in a workspace channel.

- Receives the agent's interactive message showing all flagged instances with severity ratings
- User reviews the AI analysis and clicks one of three buttons:
  - **Mitigate All** — stops all flagged instances (with confirmation dialog)
  - **Escalate All** — sends email to security team with full details
  - **Dismiss** — acknowledges and dismisses the alert
- Supports on-demand scanning via the `/scan` slash command
- All Slack interactions are routed through API Gateway to the Agent Lambda

### 5. API Gateway

An HTTP API with routes:

| Route | Method | Target | Purpose |
|-------|--------|--------|---------|
| `/slack/interactions` | POST | Agent Lambda | Slack button clicks and `/scan` slash command |
| `/mitigate` | POST | Mitigation Lambda | Direct API access (optional) |
| `/escalate` | POST | Escalation Lambda | Direct API access (optional) |

### 6. Mitigation Lambda (Python)

- Receives a list of instance IDs (from Agent Lambda async invocation)
- Calls `ec2:StopInstances` (stop, **never** terminate/delete)
- `StopInstances` accepts up to 1000 IDs in a single API call
- Returns success/failure status per instance

**IAM permissions:** `ec2:StopInstances` only

### 7. Escalation Lambda (Python)

- Receives a list of instance IDs and their details (from Agent Lambda async invocation)
- Sends a single consolidated HTML email via Amazon SES
- Email contains a table of all escalated instances with context
- Sent to a configurable team distribution list

**IAM permissions:** `ses:SendEmail`

### 8. Amazon SES

- Terraform automatically verifies both sender and recipient email identities
- In sandbox mode, both sides must click the AWS verification link sent to their inbox
- Used only by the Escalation Lambda

## Cross-Account Setup (Target Accounts)

This solution is designed as a **centralized scanner** that can onboard multiple AWS accounts. Each target account needs a single read-only IAM role.

### Target Account IAM Role

Create the following role in each target account to be scanned:

**Role name:** `ExposedInstancesScannerRole`

**Trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<CENTRAL_ACCOUNT_ID>:role/<SCANNER_LAMBDA_ROLE_NAME>"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permissions policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

### Onboarding a New Account

1. Deploy the `ExposedInstancesScannerRole` in the target account (a Terraform module is provided in `terraform-common/modules/target_account_role/`)
2. Add the target account ID to the `target_account_ids` variable
3. The scanner will automatically include the new account in the next scheduled scan

### Required Information per Target Account

| Field | Description | Example |
|-------|-------------|---------|
| Account ID | AWS account number | `123456789012` |
| Regions | Regions to scan (or use default) | `["us-east-1", "eu-west-1"]` |

## Infrastructure

All AWS infrastructure is managed with **Terraform**, following these conventions:

- `terraform-common/` contains a reusable Terraform module with all resource definitions (Lambdas, Step Functions, API Gateway, SES, IAM)
- `terraform-environments/` contains per-environment configurations (dev, staging, prod) that call the common module with environment-specific variables
- Uses [terraform-aws-modules](https://github.com/terraform-aws-modules) where possible (Lambda, IAM)
- Uses [serverless.tf](https://serverless.tf) patterns for Lambda packaging
- Each Lambda has its own top-level directory (`lambda-scan/`, `lambda-mitigate/`, `lambda-escalate/`, `lambda-agent/`) with independent code, dependencies, and tests
- All Lambdas are Python — the agent uses [Pydantic AI](https://ai.pydantic.dev/) + Claude API

## Project Structure

```
├── terraform-common/                 # Reusable Terraform module (all resources)
│   ├── main.tf                       # Module entrypoint — wires sub-modules
│   ├── variables.tf                  # Module input variables
│   ├── outputs.tf                    # Module outputs
│   └── modules/
│       ├── iam/                      # IAM roles & policies for all Lambdas
│       ├── lambda_scanner/           # Scanner Lambda deployment
│       ├── lambda_mitigation/        # Mitigation Lambda deployment
│       ├── lambda_escalation/        # Escalation Lambda deployment
│       ├── lambda_agent/             # Agent Lambda deployment (S3-backed)
│       ├── step_function/            # Step Function state machine + EventBridge rule
│       ├── api_gateway/              # HTTP API with /slack/interactions, /mitigate, /escalate
│       ├── ses/                      # SES email identity verification (sender + recipients)
│       ├── secrets/                  # Secrets Manager data sources for Slack & Claude API key
│       ├── mock_instance/            # Optional: test EC2 instance with permissive SGs
│       └── target_account_role/      # IAM role to deploy in each target account
│
├── terraform-environments/           # Per-environment configs calling common module
│   ├── dev/
│   │   ├── backend/                  # Bootstrap: S3 bucket + KMS key for remote state
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── terraform.tfvars
│   │   ├── main.tf                   # module "common" { source = "../../terraform-common" }
│   │   ├── variables.tf
│   │   ├── terraform.auto.tfvars
│   │   ├── terraform.tfvars.example
│   │   ├── backend.tf
│   │   └── providers.tf
│   ├── staging/
│   │   └── ...                       # Same structure, different values
│   └── prod/
│       └── ...
│
├── lambda-scan/                      # Python — EC2 scan logic
│   ├── handler.py
│   ├── requirements.txt
│   └── tests/
│       └── test_handler.py
│
├── lambda-mitigate/                  # Python — stop instances
│   ├── handler.py
│   ├── requirements.txt
│   └── tests/
│       └── test_handler.py
│
├── lambda-escalate/                  # Python — SES email
│   ├── handler.py
│   ├── requirements.txt
│   └── tests/
│       └── test_handler.py
│
└── lambda-agent/                     # Python — Pydantic AI agent (runs in Lambda)
    ├── handler.py                    # Lambda handler — Step Function + Slack dispatcher
    ├── agent.py                      # Pydantic AI agent definition + Claude config
    ├── slack_utils.py                # Slack Block Kit, signature verification, posting
    ├── models.py                     # Pydantic models for scan data & agent output
    ├── requirements.txt
    └── tests/
        └── test_handler.py
```

## Configuration

### Terraform Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `aws_region` | AWS region to deploy and scan | `us-east-1` |
| `environment` | Deployment environment | `dev` |
| `scan_schedule` | EventBridge schedule expression | `rate(6 hours)` |
| `skip_tag_key` | Tag key to exclude instances from scan | `SkipScan` |
| `skip_tag_value` | Tag value to exclude instances from scan | `true` |
| `ses_sender_email` | Verified SES sender address | `yardenws@gmail.com` |
| `ses_recipient_emails` | Email addresses for escalation | `["yardenws@gmail.com"]` |
| `target_account_ids` | AWS account IDs to scan | `["195275656557"]` |
| `create_mock` | Create a test EC2 instance with permissive SGs | `false` |

### Secrets (AWS Secrets Manager — created manually)

| Secret Name | Key | Description |
|-------------|-----|-------------|
| `exposed-instances/claude-api-key` | `api_key` | Claude API key for the Pydantic AI agent |
| `exposed-instances/slack` | `bot_token` | Slack Bot User OAuth Token (`xoxb-...`) |
| `exposed-instances/slack` | `signing_secret` | Slack app Signing Secret |
| `exposed-instances/slack` | `channel_id` | Slack channel ID for posting scan reports |

## Deployment

### Prerequisites

- Terraform >= 1.10.5
- AWS CLI configured with appropriate credentials (profile: `devops`)
- Python >= 3.13
- A [Claude API key](https://console.anthropic.com/)
- A Slack workspace with permissions to create apps

### Step 1 — Bootstrap the Terraform Backend

The S3 bucket, KMS key for remote state, and the Scanner Lambda IAM role must exist before the main infrastructure can be deployed. A dedicated `backend/` folder inside each environment handles this.

The Scanner Lambda role is created here so that the target account `ExposedInstancesScannerRole` (Step 3) can reference it in its trust policy before the main Terraform runs.

```bash
cd terraform-environments/dev/backend
terraform init
terraform plan
terraform apply
```

Note the scanner role ARN from the outputs — you'll need it in Step 3:

```bash
terraform output scanner_lambda_role_arn
```

Once the S3 bucket is created, uncomment the `backend "s3"` block in `backend/main.tf` and migrate the state:

```bash
terraform init -migrate-state
```

After migration, the backend folder's own state is stored in S3. This is a **one-time** operation per environment.

### Step 2 — Create Claude API Key Secret

Create the Claude API key secret **before** deploying the main infrastructure.

```bash
aws secretsmanager create-secret \
  --name "exposed-instances/claude-api-key" \
  --region us-east-1 \
  --profile devops \
  --secret-string '{"api_key": "<YOUR_CLAUDE_API_KEY>"}'
```

### Step 3 — Create the Scanner Assume Role in Target Accounts

Each AWS account to be scanned needs an `ExposedInstancesScannerRole` IAM role that the Scanner Lambda assumes via `sts:AssumeRole`. Create this role in every target account (including the central account if you want to scan it too).

**Create the role** (replace `<SCANNER_LAMBDA_ROLE_ARN>` with the output from Step 1):

```bash
aws iam create-role \
  --role-name ExposedInstancesScannerRole \
  --profile devops \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "<SCANNER_LAMBDA_ROLE_ARN>"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'
```

**Attach the read-only EC2 policy:**

```bash
aws iam put-role-policy \
  --role-name ExposedInstancesScannerRole \
  --policy-name ExposedInstancesScannerPolicy \
  --profile devops \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ec2:DescribeInstances",
          "ec2:DescribeRouteTables",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups"
        ],
        "Resource": "*"
      }
    ]
  }'
```

Then list the target account IDs in your environment tfvars:

```hcl
target_account_ids = ["123456789012", "987654321098"]
```

> **Note:** The scanner only operates via `sts:AssumeRole` — there is no implicit local-account fallback. Every account to be scanned must have this role created and its ID listed in `target_account_ids`.

### Step 4 — Deploy AWS Infrastructure

```bash
cd terraform-environments/dev
terraform init
terraform plan
terraform apply
```

After apply, note the API Gateway URL from the outputs:

```bash
terraform output api_gateway_url
# Example: https://abc123def4.execute-api.us-east-1.amazonaws.com
```

SES verification emails will be sent automatically to the sender and recipient addresses. **Click the verification links** in your inbox to complete SES setup.

To also deploy a mock exposed instance for testing:

```bash
terraform apply -var="create_mock=true"
```

### Step 5 — Configure Slack Application

This step requires the API Gateway URL from Step 4.

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App** → **From an app manifest**
2. Select your workspace
3. Paste the following manifest (replace `<API_GATEWAY_URL>` with the URL from Step 4):

```yaml
display_information:
  name: EC2 Exposure Scanner
  description: Scans for publicly exposed EC2 instances and enables human-in-the-loop mitigation
  background_color: "#d32f2f"

features:
  bot_user:
    display_name: EC2 Exposure Scanner
    always_online: true
  slash_commands:
    - command: /scan
      url: <API_GATEWAY_URL>/slack/interactions
      description: Trigger an on-demand EC2 exposure scan
      usage_hint: Run a scan now
      should_escape: false

oauth_config:
  scopes:
    bot:
      - chat:write
      - chat:write.public
      - commands

settings:
  interactivity:
    is_enabled: true
    request_url: <API_GATEWAY_URL>/slack/interactions
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
```

4. Click **Create** and then **Install to Workspace**

**After installation:**

1. Copy the **Bot User OAuth Token** (`xoxb-...`) from OAuth & Permissions
2. Copy the **Signing Secret** from the Basic Information page
3. Get the **Channel ID** of the target channel (right-click channel → View channel details → copy ID at bottom)
4. Invite the bot to the channel: `/invite @EC2 Exposure Scanner`
5. Create the Slack secret in Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name "exposed-instances/slack" \
  --region us-east-1 \
  --profile devops \
  --secret-string '{"bot_token": "xoxb-...", "signing_secret": "...", "channel_id": "C0123456789"}'
```

### Mock Instance (Testing)

To validate the full scan → analyze → alert pipeline, deploy a deliberately exposed EC2 instance:

```bash
terraform apply -var="create_mock=true"
```

This creates:
- A VPC with an internet gateway and public subnet
- A security group open to `0.0.0.0/0` on SSH (22), HTTP (80), and PostgreSQL (5432)
- A `t3.micro` instance with a public IP

Trigger a scan via `/scan` in Slack and the mock instance should appear in the results. To tear down:

```bash
terraform apply -var="create_mock=false"
```

### Test Lambdas Locally

#### Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Run tests

```bash
cd lambda-scan
pip install -r requirements.txt pytest
pytest tests/

cd ../lambda-mitigate
pip install -r requirements.txt pytest
pytest tests/

cd ../lambda-escalate
pip install -r requirements.txt pytest
pytest tests/

cd ../lambda-agent
pip install -r requirements.txt pytest
pytest tests/
```

## Security Notes

- Scanner Lambda has **read-only** EC2 permissions — it cannot modify any resources in any account
- Cross-account access is scoped to explicitly configured `target_account_ids` only
- Target account role is strictly read-only — no write or modify permissions
- Mitigation Lambda can only **stop** instances — it cannot terminate or delete
- Escalation Lambda can only **send email** — no other AWS access
- All secrets (Slack tokens, Claude API key) are stored in AWS Secrets Manager — never in environment variables or code
- Slack request signatures are verified (HMAC-SHA256) before processing any interaction
- The human-in-the-loop step ensures no automated action runs without explicit approval
- Mock instance module is gated by a `create_mock = false` default — never deployed unless explicitly enabled
