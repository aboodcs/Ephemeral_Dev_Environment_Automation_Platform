variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used in resource tags"
  type        = string
  default     = "Ephemeral-Dev-Environment"
}

variable "environment" {
  description = "Environment name used in resource tags"
  type        = string
  default     = "Development"
}

variable "managed_by" {
  description = "Tool managing the infrastructure"
  type        = string
  default     = "Terraform"
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
  default     = "abdulrehman-yahya"
}

variable "cloud_provider" {
  description = "Cloud provider used by this environment"
  type        = string
  default     = "AWS"
}

variable "vpc_cidr" {
  description = "CIDR block used by the AWS VPC"
  type        = string
  default     = "10.0.0.0/16" ## private ip
}

variable "public_subnet_cidr" {
  description = "CIDR block used by the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "allowed_ssh_cidr" {
  description = "Public IP address allowed to connect using SSH"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type used by the development environment"
  type        = string
  default     = "t3.micro"
}

variable "ssh_public_key_path" {
  description = "Local path to the SSH public key used for EC2 access"
  type        = string
}

variable "availability_zone" {
  description = "Availability Zone used by the public subnet"
  type        = string
  default     = "us-east-1a"
}