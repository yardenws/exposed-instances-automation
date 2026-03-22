output "s3_bucket_id" {
  value       = aws_s3_bucket.terraform_state.id
  description = "The name of the S3 bucket"
}

output "scanner_lambda_role_arn" {
  value       = aws_iam_role.scanner_lambda.arn
  description = "ARN of the Scanner Lambda IAM role (use in target account trust policies)"
}

output "scanner_lambda_role_name" {
  value       = aws_iam_role.scanner_lambda.name
  description = "Name of the Scanner Lambda IAM role"
}