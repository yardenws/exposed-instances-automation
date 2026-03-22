module "common" {
  source = "../../terraform-common"

  environment          = var.environment
  aws_region           = var.aws_region
  target_account_ids   = var.target_account_ids
  ses_sender_email     = var.ses_sender_email
  ses_recipient_emails = var.ses_recipient_emails
  scan_schedule        = var.scan_schedule
  create_mock          = var.create_mock

  lambda_scan_source_dir     = abspath("${path.module}/../../lambda-scan")
  lambda_mitigate_source_dir = abspath("${path.module}/../../lambda-mitigate")
  lambda_escalate_source_dir = abspath("${path.module}/../../lambda-escalate")
  lambda_agent_source_dir    = abspath("${path.module}/../../lambda-agent")

  tags = {
    Environment = var.environment
  }
}
