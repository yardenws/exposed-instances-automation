data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# --- Scanner Lambda Role ---
# The role itself is created in the backend bootstrap (terraform-environments/<env>/backend/)
# so it exists before the target account ExposedInstancesScannerRole is created.
# Here we only reference it and attach the required policies.

data "aws_iam_role" "scanner_lambda" {
  name = "${var.environment}-exposed-instances-scanner-lambda"
}

resource "aws_iam_role_policy_attachment" "scanner_policy" {
  role       = data.aws_iam_role.scanner_lambda.name
  policy_arn = module.scanner_policy.arn
}

resource "aws_iam_role_policy_attachment" "scanner_basic_execution" {
  role       = data.aws_iam_role.scanner_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

module "scanner_policy" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-policy"
  version = "~> 5.0"

  name        = "${local.name_prefix}-scanner"
  description = "Allows Scanner Lambda to assume roles in target accounts"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Resource = [
          for account_id in var.target_account_ids :
          "arn:aws:iam::${account_id}:role/ExposedInstancesScannerRole"
        ]
      }
    ]
  })

  tags = var.tags
}

# --- Agent Lambda Role ---

module "agent_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "~> 5.0"

  create_role       = true
  role_name         = "${local.name_prefix}-agent-lambda"
  role_requires_mfa = false

  trusted_role_services = ["lambda.amazonaws.com"]

  custom_role_policy_arns = [
    module.agent_policy.arn,
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
  ]

  tags = var.tags
}

module "agent_policy" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-policy"
  version = "~> 5.0"

  name        = "${local.name_prefix}-agent"
  description = "Allows Agent Lambda to read secrets and invoke mitigate/escalate Lambdas"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "secretsmanager:GetSecretValue"
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:exposed-instances/*"
        ]
      },
      {
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = [
          "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${local.name_prefix}-mitigation",
          "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${local.name_prefix}-escalation"
        ]
      },
      {
        Effect = "Allow"
        Action = "states:StartExecution"
        Resource = [
          "arn:aws:states:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stateMachine:${local.name_prefix}-workflow"
        ]
      }
    ]
  })

  tags = var.tags
}

# --- Mitigation Lambda Role ---

module "mitigation_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "~> 5.0"

  create_role       = true
  role_name         = "${local.name_prefix}-mitigation-lambda"
  role_requires_mfa = false

  trusted_role_services = ["lambda.amazonaws.com"]

  custom_role_policy_arns = [
    module.mitigation_policy.arn,
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
  ]

  tags = var.tags
}

module "mitigation_policy" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-policy"
  version = "~> 5.0"

  name        = "${local.name_prefix}-mitigation"
  description = "Allows Mitigation Lambda to stop EC2 instances"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ec2:StopInstances"
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

# --- Escalation Lambda Role ---

module "escalation_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "~> 5.0"

  create_role       = true
  role_name         = "${local.name_prefix}-escalation-lambda"
  role_requires_mfa = false

  trusted_role_services = ["lambda.amazonaws.com"]

  custom_role_policy_arns = [
    module.escalation_policy.arn,
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
  ]

  tags = var.tags
}

module "escalation_policy" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-policy"
  version = "~> 5.0"

  name        = "${local.name_prefix}-escalation"
  description = "Allows Escalation Lambda to send emails via SES"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ses:SendEmail"
        Resource = "*"
        Condition = {
          StringEquals = {
            "ses:FromAddress" = var.ses_sender_email
          }
        }
      }
    ]
  })

  tags = var.tags
}

# --- Step Function Role ---

module "step_function_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "~> 5.0"

  create_role       = true
  role_name         = "${local.name_prefix}-step-function"
  role_requires_mfa = false

  trusted_role_services = ["states.amazonaws.com"]

  custom_role_policy_arns = [
    module.step_function_policy.arn,
  ]

  tags = var.tags
}

module "step_function_policy" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-policy"
  version = "~> 5.0"

  name        = "${local.name_prefix}-step-function"
  description = "Allows Step Function to invoke Scanner and Agent Lambdas"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

# --- EventBridge Role ---

module "eventbridge_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "~> 5.0"

  create_role       = true
  role_name         = "${local.name_prefix}-eventbridge"
  role_requires_mfa = false

  trusted_role_services = ["events.amazonaws.com"]

  custom_role_policy_arns = [
    module.eventbridge_policy.arn,
  ]

  tags = var.tags
}

module "eventbridge_policy" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-policy"
  version = "~> 5.0"

  name        = "${local.name_prefix}-eventbridge"
  description = "Allows EventBridge to start Step Function executions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "states:StartExecution"
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}
