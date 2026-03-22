locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# --- IAM ---

module "iam" {
  source = "./modules/iam"

  project_name         = var.project_name
  environment          = var.environment
  target_account_ids   = var.target_account_ids
  ses_sender_email     = var.ses_sender_email
  ses_recipient_emails = var.ses_recipient_emails
  tags                 = var.tags
}

# --- Secrets (data sources for pre-created secrets) ---

module "secrets" {
  source = "./modules/secrets"

  project_name = var.project_name
  tags         = var.tags
}

# --- Lambda: Scanner ---

module "lambda_scanner" {
  source = "./modules/lambda_scanner"

  function_name      = "${local.name_prefix}-scanner"
  role_arn           = module.iam.scanner_role_arn
  source_dir         = var.lambda_scan_source_dir
  environment        = var.environment
  target_account_ids = var.target_account_ids
  skip_tag_key       = var.skip_tag_key
  skip_tag_value     = var.skip_tag_value
  scan_regions       = length(var.scan_regions) > 0 ? var.scan_regions : [var.aws_region]
  tags               = var.tags
}

# --- Deployment Artifacts Bucket ---
# Used for Lambda packages that exceed the 70MB direct upload limit (e.g. agent)

resource "aws_s3_bucket" "lambda_artifacts" {
  bucket_prefix = "${local.name_prefix}-artifacts-"
  force_destroy = true

  tags = var.tags
}

resource "aws_s3_bucket_versioning" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "lambda_artifacts" {
  bucket                  = aws_s3_bucket.lambda_artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- Lambda: Agent ---

module "lambda_agent" {
  source = "./modules/lambda_agent"

  function_name            = "${local.name_prefix}-agent"
  role_arn                 = module.iam.agent_role_arn
  source_dir               = var.lambda_agent_source_dir
  environment              = var.environment
  s3_bucket                = aws_s3_bucket.lambda_artifacts.id
  step_function_arn        = "arn:aws:states:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stateMachine:${local.name_prefix}-workflow"
  mitigation_function_name = "${local.name_prefix}-mitigation"
  escalation_function_name = "${local.name_prefix}-escalation"
  tags                     = var.tags
}

# --- Lambda: Mitigation ---

module "lambda_mitigation" {
  source = "./modules/lambda_mitigation"

  function_name = "${local.name_prefix}-mitigation"
  role_arn      = module.iam.mitigation_role_arn
  source_dir    = var.lambda_mitigate_source_dir
  tags          = var.tags
}

# --- Lambda: Escalation ---

module "lambda_escalation" {
  source = "./modules/lambda_escalation"

  function_name        = "${local.name_prefix}-escalation"
  role_arn             = module.iam.escalation_role_arn
  source_dir           = var.lambda_escalate_source_dir
  ses_sender_email     = var.ses_sender_email
  ses_recipient_emails = var.ses_recipient_emails
  tags                 = var.tags
}

# --- Step Function + EventBridge Schedule ---

module "step_function" {
  source = "./modules/step_function"

  name                 = "${local.name_prefix}-workflow"
  role_arn             = module.iam.step_function_role_arn
  scanner_lambda_arn   = module.lambda_scanner.lambda_function_arn
  agent_lambda_arn     = module.lambda_agent.lambda_function_arn
  schedule_expression  = var.scan_schedule
  eventbridge_role_arn = module.iam.eventbridge_role_arn
  tags                 = var.tags
}

# --- API Gateway ---

module "api_gateway" {
  source = "./modules/api_gateway"

  name                            = "${local.name_prefix}-api"
  mitigation_lambda_invoke_arn    = module.lambda_mitigation.lambda_function_invoke_arn
  escalation_lambda_invoke_arn    = module.lambda_escalation.lambda_function_invoke_arn
  agent_lambda_invoke_arn         = module.lambda_agent.lambda_function_invoke_arn
  mitigation_lambda_function_name = module.lambda_mitigation.lambda_function_name
  escalation_lambda_function_name = module.lambda_escalation.lambda_function_name
  agent_lambda_function_name      = module.lambda_agent.lambda_function_name
  tags                            = var.tags
}

# --- SES ---

module "ses" {
  source = "./modules/ses"

  sender_email     = var.ses_sender_email
  recipient_emails = var.ses_recipient_emails
  tags             = var.tags
}

# --- Mock Instance (testing only) ---

module "mock_instance" {
  source = "./modules/mock_instance"

  create      = var.create_mock
  name_prefix = local.name_prefix
  tags        = var.tags
}
