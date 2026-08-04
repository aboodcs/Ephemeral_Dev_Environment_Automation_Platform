output "bucket_name" {
  value       = var.bucket_name
}

output "bucket_arn" {
  value       = aws_s3_bucket.terraform_state.arn
}

output "aws_region" {
  value       = var.aws_region
}