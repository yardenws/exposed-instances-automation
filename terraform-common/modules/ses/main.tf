resource "aws_ses_email_identity" "sender" {
  email = var.sender_email
}

resource "aws_ses_email_identity" "recipients" {
  for_each = toset(var.recipient_emails)
  email    = each.value
}
