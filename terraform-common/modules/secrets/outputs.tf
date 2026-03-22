output "claude_api_key_secret_arn" {
  value = data.aws_secretsmanager_secret.claude_api_key.arn
}

# Uncomment after creating the Slack secret (Step 5 in README)
# output "slack_secret_arn" {
#   value = data.aws_secretsmanager_secret.slack.arn
# }
