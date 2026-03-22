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

variable "target_account_ids" {
  type = list(string)
}

variable "skip_tag_key" {
  type = string
}

variable "skip_tag_value" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
