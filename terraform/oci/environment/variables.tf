variable "user_ocid" {
  description = "OCI user"
  type        = string
  sensitive   = true
}

variable "tenancy_ocid" {
  description = "OCID of the OCI tenancy"
  type        = string
  sensitive   = true
}

variable "fingerprint" {
  description = "Fingerprint of the OCI API signing key"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "OCI region"
  type        = string
}

variable "private_key_path" {
  description = "Path to the OCI private key"
  type        = string
  sensitive   = true
}

variable "compartment_id" {
  description = "OCID of the compartment where resources will be created"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "Public IP CIDR allowed to SSH into the instance"
  type        = string
}

variable "instance_shape" {
  description = "OCI Compute shape used for the development instance"
  type        = string
  default     = "VM.Standard.E2.1.Micro"
}

variable "availability_domain" {
  description = "Availability domain where the Compute instance will be created"
  type        = string
}

variable "image_id" {
  description = "OCID of the operating-system image"
  type        = string
}

variable "ssh_public_key_path" {
  description = "Path to the SSH public key used to access the instance"
  type        = string
}