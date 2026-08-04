resource "oci_core_instance" "app" {
  compartment_id      = var.compartment_id
  availability_domain = var.availability_domain
  shape               = var.instance_shape

  display_name = "ephemeral-dev-compute"

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    hostname_label   = "ephemeraldev"

    nsg_ids = [
      oci_core_network_security_group.web_server.id
    ]
  }

  source_details {
    source_type = "image"
    source_id   = var.image_id
  }

  metadata = {
    ssh_authorized_keys = file(pathexpand(var.ssh_public_key_path))
    user_data = base64encode(
      file("${path.module}/../../scripts/bootstrap.sh")
    )
  }

  preserve_boot_volume = false

  freeform_tags = {
    Project     = "Ephemeral-Dev-Environment"
    Environment = "Development"
    Owner       = "abdulrehman-yahya"
    ManagedBy   = "Terraform"
    AutoDestroy = "true"
  }
}