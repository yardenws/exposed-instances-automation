output "scanner_role_arn" {
  value = data.aws_iam_role.scanner_lambda.arn
}

output "scanner_role_name" {
  value = data.aws_iam_role.scanner_lambda.name
}

output "agent_role_arn" {
  value = module.agent_role.iam_role_arn
}

output "mitigation_role_arn" {
  value = module.mitigation_role.iam_role_arn
}

output "escalation_role_arn" {
  value = module.escalation_role.iam_role_arn
}

output "step_function_role_arn" {
  value = module.step_function_role.iam_role_arn
}

output "eventbridge_role_arn" {
  value = module.eventbridge_role.iam_role_arn
}
