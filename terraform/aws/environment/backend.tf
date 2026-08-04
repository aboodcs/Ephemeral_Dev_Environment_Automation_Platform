terraform {
  backend "s3" {
    bucket       = "ephemeral-dev-terraform-state-abood-2026"
    key          = "ephemeral-dev/environment/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}
