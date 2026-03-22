variable "name" {
  type = string
}

variable "mitigation_lambda_invoke_arn" {
  type = string
}

variable "escalation_lambda_invoke_arn" {
  type = string
}

variable "agent_lambda_invoke_arn" {
  type = string
}

variable "mitigation_lambda_function_name" {
  type = string
}

variable "escalation_lambda_function_name" {
  type = string
}

variable "agent_lambda_function_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
