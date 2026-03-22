output "api_gateway_url" {
  value = module.common.api_gateway_url
}

output "step_function_arn" {
  value = module.common.step_function_arn
}

output "scanner_lambda_function_name" {
  value = module.common.scanner_lambda_function_name
}

output "agent_lambda_function_name" {
  value = module.common.agent_lambda_function_name
}

output "mitigation_lambda_function_name" {
  value = module.common.mitigation_lambda_function_name
}

output "escalation_lambda_function_name" {
  value = module.common.escalation_lambda_function_name
}

output "scanner_role_arn" {
  value = module.common.scanner_role_arn
}
