resource "aws_instance" "dev_environment" {
  ami                         = data.aws_ssm_parameter.amazon_linux_2023.value
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.dev_environment.id]
  key_name                    = aws_key_pair.dev_environment.key_name
  associate_public_ip_address = true

  user_data                   = local.bootstrap_script
  user_data_replace_on_change = true

  tags = {
    Name          = "${var.project_name}-ec2"
    Project       = var.project_name
    Environment   = var.environment
    Owner         = var.owner
    ManagedBy     = var.managed_by
    CloudProvider = var.cloud_provider
    AutoDestroy   = "true"
  }
}