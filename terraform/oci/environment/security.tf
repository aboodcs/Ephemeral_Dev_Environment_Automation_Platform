resource "oci_core_network_security_group" "web_server" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id

  display_name = "ephemeral-dev-web-nsg"

  freeform_tags = {
    project   = "Ephemeral-Dev-Environment"
    ManagedBy = "Terraform"
  }
}

resource "oci_core_network_security_group_security_rule" "allow_ssh" {
  network_security_group_id = oci_core_network_security_group.web_server.id

  direction   = "INGRESS"
  protocol    = "6"
  description = "allow the ssh"
  source      = var.allowed_ssh_cidr
  source_type = "CIDR_BLOCK"
  stateless   = true

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_network_security_group_security_rule" "allow_http" {
  network_security_group_id = oci_core_network_security_group.web_server.id
  direction                 = "INGRESS"
  protocol                  = "6"
  description               = "allow the http"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = 80
      max = 80
    }
  }
}

resource "oci_core_network_security_group_security_rule" "allow_egress" {
  network_security_group_id = oci_core_network_security_group.web_server.id

  direction        = "EGRESS"
  protocol         = "all"
  destination      = "0.0.0.0/0"
  destination_type = "CIDR_BLOCK"

  description = "allow the outbound internet traffic"
}