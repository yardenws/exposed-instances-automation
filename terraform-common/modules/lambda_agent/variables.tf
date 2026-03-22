variable "function_name" {
  type = string
}

variable "role_arn" {
  type = string
}

variable "source_dir" {
  type = string
}

variable "environment" {
  type = string
}

variable "s3_bucket" {
  description = "S3 bucket for storing the Lambda deployment package"
  type        = string
}

variable "step_function_arn" {
  description = "ARN of the Step Function to trigger on-demand scans"
  type        = string
}

variable "mitigation_function_name" {
  description = "Name of the Mitigation Lambda function"
  type        = string
}

variable "escalation_function_name" {
  description = "Name of the Escalation Lambda function"
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
