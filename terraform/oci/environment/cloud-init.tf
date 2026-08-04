locals {
  bootstrap_script = file("${path.module}/../../scripts/bootstrap.sh")
  user_data        = base64encode(local.bootstrap_script)
}