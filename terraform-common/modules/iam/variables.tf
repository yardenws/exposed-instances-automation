variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "target_account_ids" {
  type = list(string)
}

variable "ses_sender_email" {
  type = string
}

variable "ses_recipient_emails" {
  type = list(string)
}

variable "tags" {
  type    = map(string)
  default = {}
}
