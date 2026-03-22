module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = var.function_name
  description   = "Stops publicly exposed EC2 instances (mitigation)"
  handler       = "handler.handler"
  runtime       = "python3.13"
  timeout       = 120
  memory_size   = 128

  source_path = var.source_dir

  create_role = false
  lambda_role = var.role_arn

  tags = var.tags
}
