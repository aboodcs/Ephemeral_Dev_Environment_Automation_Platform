output "vpc_id" {
  description = "ID of the AWS VPC"
  value       = aws_vpc.main.id
}

output "internet_gateway_id" {
  description = "ID of the AWS Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "subnet_id" {
  description = "ID of the AWS public subnet"
  value       = aws_subnet.public.id
}

output "route_table" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "security_group_id" {
  description = "value"
  value       = aws_security_group.dev_environment.id
}

output "ec2_public_ip" {
  description = "Public IPv4 address of the EC2 instance"
  value       = aws_instance.dev_environment.public_ip
}

output "ec2_private_ip" {
  description = "Private IPv4 address of the EC2 instance"
  value       = aws_instance.dev_environment.private_ip
}

output "ec2_instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.dev_environment.id
}

output "ec2_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.dev_environment.public_dns
}

output "application_url" {
  description = "Public URL of the application"
  value       = "http://${aws_instance.dev_environment.public_ip}"
}

## this two for slack notifications
output "public_ip" {
  description = "Public IP for notifications"
  value       = aws_instance.dev_environment.public_ip
}

output "app_url" {
  description = "Application URL for notifications"
  value       = "http://${aws_instance.dev_environment.public_ip}"
}