variable "function_name" {
  type = string
}

variable "role_arn" {
  type = string
}

variable "source_dir" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
