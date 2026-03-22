module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = var.function_name
  description   = "Scans target accounts for publicly exposed EC2 instances"
  handler       = "handler.handler"
  runtime       = "python3.13"
  timeout       = 300
  memory_size   = 256

  source_path = var.source_dir

  create_role = false
  lambda_role = var.role_arn

  environment_variables = {
    TARGET_ACCOUNT_IDS = jsonencode(var.target_account_ids)
    SKIP_TAG_KEY       = var.skip_tag_key
    SKIP_TAG_VALUE     = var.skip_tag_value
    SCAN_REGIONS       = jsonencode(var.scan_regions)
  }

  tags = var.tags
}
