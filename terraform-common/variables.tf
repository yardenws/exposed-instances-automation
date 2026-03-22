variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "exposed-instances"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy resources and scan"
  type        = string
}

variable "scan_schedule" {
  description = "EventBridge schedule expression for the scanner"
  type        = string
  default     = "rate(6 hours)"
}

variable "skip_tag_key" {
  description = "Tag key used to exclude instances from scanning"
  type        = string
  default     = "SkipScan"
}

variable "skip_tag_value" {
  description = "Tag value used to exclude instances from scanning"
  type        = string
  default     = "true"
}

variable "target_account_ids" {
  description = "List of AWS account IDs to scan via cross-account AssumeRole"
  type        = list(string)
  default     = []
}

variable "ses_sender_email" {
  description = "Verified SES sender email address"
  type        = string
}

variable "ses_recipient_emails" {
  description = "List of email addresses to receive escalation emails"
  type        = list(string)
}

variable "lambda_scan_source_dir" {
  description = "Path to the lambda-scan source directory"
  type        = string
}

variable "lambda_mitigate_source_dir" {
  description = "Path to the lambda-mitigate source directory"
  type        = string
}

variable "lambda_escalate_source_dir" {
  description = "Path to the lambda-escalate source directory"
  type        = string
}

variable "lambda_agent_source_dir" {
  description = "Path to the lambda-agent source directory"
  type        = string
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default     = {}
}

variable "create_mock" {
  description = "Create a mock exposed EC2 instance for testing the scanner"
  type        = bool
  default     = false
}
