variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Terraform state bucket name"
  type        = string
  default     = "ephemeral-dev-terraform-state-abood-2026"
}
