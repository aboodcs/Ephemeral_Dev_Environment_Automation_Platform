resource "oci_core_vcn" "main" {
  compartment_id = var.compartment_id

  cidr_blocks = ["10.0.0.0/16"]

  display_name = "ephemeral-dev-vcn"
  dns_label    = "ephemeralvcn"

  freeform_tags = {
    Project     = "Ephemeral-Dev-Environment"
    Environment = "Development"
    Owner       = "abdulrehman-yahya"
    ManagedBy   = "Terraform"
    AutoDestroy = "true"
  }
}

resource "oci_core_internet_gateway" "main" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id

  display_name = "ephemeral-dev-internet-gateway"
  enabled      = true

  freeform_tags = {
    Project   = "Ephemeral-Dev-Environment"
    ManagedBy = "Terraform"
  }
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id

  display_name = "ephemeral-dev-public-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.main.id
    description       = "Route internet traffic through the Internet Gateway"
  }

  freeform_tags = {
    Project   = "Ephemeral-Dev-Environment"
    ManagedBy = "Terraform"
  }
}

resource "oci_core_subnet" "public" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.main.id

  cidr_block   = "10.0.1.0/24"
  display_name = "ephemeral-dev-public-subnet"
  dns_label    = "publicsubnet"

  route_table_id = oci_core_route_table.public.id

  prohibit_public_ip_on_vnic = false

  freeform_tags = {
    Project     = "Ephemeral-Dev-Environment"
    Environment = "Development"
    ManagedBy   = "Terraform"
  }
}


# VCN
# ├── Internet Gateway
# ├── Public Route Table → Internet Gateway
# └── Public Subnet → Public Route Table