module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = var.function_name
  description   = "Sends escalation emails via SES for exposed EC2 instances"
  handler       = "handler.handler"
  runtime       = "python3.13"
  timeout       = 120
  memory_size   = 128

  source_path = var.source_dir

  create_role = false
  lambda_role = var.role_arn

  environment_variables = {
    SES_SENDER_EMAIL     = var.ses_sender_email
    SES_RECIPIENT_EMAILS = jsonencode(var.ses_recipient_emails)
  }

  tags = var.tags
}
