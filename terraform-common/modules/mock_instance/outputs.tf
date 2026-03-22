output "instance_id" {
  value = var.create ? aws_instance.mock[0].id : null
}

output "public_ip" {
  value = var.create ? aws_instance.mock[0].public_ip : null
}

output "vpc_id" {
  value = var.create ? aws_vpc.mock[0].id : null
}

output "subnet_id" {
  value = var.create ? aws_subnet.mock[0].id : null
}

output "security_group_id" {
  value = var.create ? aws_security_group.mock[0].id : null
}
