variable "sender_email" {
  type = string
}

variable "recipient_emails" {
  description = "List of recipient emails to verify in SES sandbox"
  type        = list(string)
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
