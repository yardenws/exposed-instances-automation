variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "scan_regions" {
  description = "List of AWS regions to scan (defaults to aws_region)"
  type        = list(string)
  default     = []
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "target_account_ids" {
  description = "List of AWS account IDs to scan"
  type        = list(string)
  default     = []
}

variable "ses_sender_email" {
  description = "Verified SES sender email address"
  type        = string
}

variable "ses_recipient_emails" {
  description = "Email addresses for escalation notifications"
  type        = list(string)
}

variable "scan_schedule" {
  description = "EventBridge schedule expression"
  type        = string
  default     = "rate(6 hours)"
}

variable "create_mock" {
  description = "Create a mock exposed EC2 instance for testing"
  type        = bool
  default     = false
}
