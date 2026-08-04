resource "aws_security_group" "dev_environment" {
  vpc_id = aws_vpc.main.id

  ingress {
    description = "Allow SSH from my public IP"
    protocol    = "tcp"
    from_port   = 22
    to_port     = 22
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  ingress {
    description = "Allow HTTP traffic"
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name          = "${var.project_name}-security-group"
    Project       = var.project_name
    Environment   = var.environment
    Owner         = var.owner
    ManagedBy     = var.managed_by
    CloudProvider = var.cloud_provider
    AutoDestroy   = "true"
  }
}