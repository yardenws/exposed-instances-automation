variable "env" {
  description = "Working environment short"
  default     = "dev"
}

variable "aws_region" {
  description = "AWS Region for the S3 and DynamoDB"
  default     = "us-east-1"
}

variable "state_bucket" {
  description = "S3 bucket for holding Terraform state files. Must be globally unique."
  type        = string
}