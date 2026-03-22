variable "create" {
  description = "Whether to create the mock exposed instance"
  type        = bool
  default     = false
}

variable "name_prefix" {
  description = "Prefix for resource naming"
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
