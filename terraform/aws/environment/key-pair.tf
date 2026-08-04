resource "aws_key_pair" "dev_environment" {
  key_name = "ephemeral-dev-key"

  public_key = file(
    pathexpand(var.ssh_public_key_path)
  )

  tags = {
    Name = "ephemeral-dev-key"
  }
}