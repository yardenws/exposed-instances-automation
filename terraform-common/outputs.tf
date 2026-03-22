output "api_gateway_url" {
  description = "API Gateway base URL for Slack interactions"
  value       = module.api_gateway.api_gateway_url
}

output "step_function_arn" {
  description = "ARN of the Step Function state machine"
  value       = module.step_function.state_machine_arn
}

output "scanner_lambda_function_name" {
  description = "Name of the Scanner Lambda function"
  value       = module.lambda_scanner.lambda_function_name
}

output "agent_lambda_function_name" {
  description = "Name of the Agent Lambda function"
  value       = module.lambda_agent.lambda_function_name
}

output "mitigation_lambda_function_name" {
  description = "Name of the Mitigation Lambda function"
  value       = module.lambda_mitigation.lambda_function_name
}

output "escalation_lambda_function_name" {
  description = "Name of the Escalation Lambda function"
  value       = module.lambda_escalation.lambda_function_name
}

output "scanner_role_arn" {
  description = "ARN of the Scanner Lambda IAM role (needed for target account trust policies)"
  value       = module.iam.scanner_role_arn
}
