output "vcn_id" {
  description = "OCID of the VCN"
  value       = oci_core_vcn.main.id
}

output "internet_gateway_id" {
  description = "OCID of the Internet Gateway"
  value       = oci_core_internet_gateway.main.id
}

output "route_table_id" {
  description = "OCID of the public route table"
  value       = oci_core_route_table.public.id
}

output "subnet_id" {
  description = "OCID of the public subnet"
  value       = oci_core_subnet.public.id
}

output "security_group_id" {
  description = "OCID of the Network Security Group"
  value       = oci_core_network_security_group.web_server.id
}

output "instance_shape_id" {
  description = "Compute shape configured for the future instance"
  value       = var.instance_shape
}