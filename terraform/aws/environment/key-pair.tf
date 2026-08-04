resource "aws_key_pair" "dev_environment" {
  key_name   = "ephemeral-dev-key"
  public_key = var.ssh_public_key

  tags = {
    Name = "ephemeral-dev-key"
  }
}