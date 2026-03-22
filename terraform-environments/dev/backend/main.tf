terraform {
  backend "s3" {
    bucket       = "exposed-instances-terraform-state"
    key          = "dev/backend/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.10.5"
}

provider "aws" {
  region  = var.aws_region
  default_tags {
    tags = {
      "Environment" = var.env,
      "Deployedby"  = "Terraform",
    }
  }
}

resource "aws_kms_key" "terraform_state_key" {
  description             = "This key is used to encrypt bucket objects"
  deletion_window_in_days = 10

  tags = {
    "Name" = "${var.env}-terraform-kms"
  }
}

resource "aws_kms_alias" "terraform_state_key_alias" {
  name          = "alias/${var.env}-terraform-kms"
  target_key_id = aws_kms_key.terraform_state_key.id
}

resource "aws_s3_bucket" "terraform_state" {
  bucket              = var.state_bucket
  object_lock_enabled = true
  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name        = var.state_bucket
    description = "S3 Remote Terraform State Store"
  }
}

resource "aws_s3_bucket_versioning" "terraform_s3_versioning" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tf_encryption" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.terraform_state_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "s3_access_block" {
  bucket                  = aws_s3_bucket.terraform_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- Scanner Lambda Role ---
# Created here so it exists before the main Terraform runs.
# The target account ExposedInstancesScannerRole trust policy
# references this role ARN, so it must be created first.

resource "aws_iam_role" "scanner_lambda" {
  name = "${var.env}-exposed-instances-scanner-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${var.env}-exposed-instances-scanner-lambda"
  }
}