# Secrets are created manually (see README deployment steps).
# These data sources reference the existing secrets so other modules
# can use their ARNs.

data "aws_secretsmanager_secret" "claude_api_key" {
  name = "exposed-instances/claude-api-key"
}

# The Slack secret is created post-deploy (Step 5 in README).
# Uncomment after creating the secret in Secrets Manager.
# data "aws_secretsmanager_secret" "slack" {
#   name = "exposed-instances/slack"
# }
