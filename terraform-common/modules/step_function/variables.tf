variable "name" {
  type = string
}

variable "role_arn" {
  type = string
}

variable "scanner_lambda_arn" {
  type = string
}

variable "agent_lambda_arn" {
  type = string
}

variable "schedule_expression" {
  type = string
}

variable "eventbridge_role_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
