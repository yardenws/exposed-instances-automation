module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = var.function_name
  description   = "Pydantic AI agent that enriches scan results and posts to Slack"
  handler       = "handler.handler"
  runtime       = "python3.13"
  timeout       = 300
  memory_size   = 512
  architectures = ["arm64"]

  source_path = [{
    path             = var.source_dir
    pip_requirements = true
    patterns = [
      "!\\.build/.*",
      "!agent-package\\.zip",
      "!build\\.sh",
      "!__pycache__/.*",
      "!\\.pytest_cache/.*",
      "!tests/.*"
    ]
  }]

  build_in_docker = true

  store_on_s3 = true
  s3_bucket   = var.s3_bucket
  s3_prefix   = "lambda-agent/"

  create_role = false
  lambda_role = var.role_arn

  environment_variables = {
    ENVIRONMENT              = var.environment
    STEP_FUNCTION_ARN        = var.step_function_arn
    MITIGATION_FUNCTION_NAME = var.mitigation_function_name
    ESCALATION_FUNCTION_NAME = var.escalation_function_name
  }

  tags = var.tags
}
