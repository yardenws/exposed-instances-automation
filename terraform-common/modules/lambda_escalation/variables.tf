variable "function_name" {
  type = string
}

variable "role_arn" {
  type = string
}

variable "source_dir" {
  type = string
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
