# =============================================================================
# Infrastructure Outputs
# =============================================================================

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "instance_type" {
  description = "EC2 instance type"
  value       = aws_instance.app.instance_type
}

output "public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.app.public_ip
}

output "private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.app.private_ip
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "subnet_id" {
  description = "Public subnet ID"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.app.id
}

# =============================================================================
# SSH Access Information
# =============================================================================

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value = var.key_pair_name != "" ? 
    "ssh -i /path/to/your/key.pem ec2-user@${aws_eip.app.public_ip}" :
    "ssh -i ${path.module}/../../keys/${var.project_name}-${var.environment}.pem ec2-user@${aws_eip.app.public_ip}"
}

output "key_pair_name" {
  description = "Name of the key pair used"
  value = var.key_pair_name != "" ? var.key_pair_name : aws_key_pair.app_key[0].key_name
}

output "private_key_path" {
  description = "Path to the private key file (if generated)"
  value = var.key_pair_name == "" ? "${path.module}/../../keys/${var.project_name}-${var.environment}.pem" : "Using existing key: ${var.key_pair_name}"
  sensitive = true
}

# =============================================================================
# Application URLs
# =============================================================================

output "application_urls" {
  description = "URLs for accessing the application services"
  value = {
    fastapi_docs   = "http://${aws_eip.app.public_ip}:${var.app_ports.fastapi}/docs"
    fastapi_redoc  = "http://${aws_eip.app.public_ip}:${var.app_ports.fastapi}/redoc"
    streamlit_ui   = "http://${aws_eip.app.public_ip}:${var.app_ports.streamlit}"

    redis_commander = "http://${aws_eip.app.public_ip}:${var.app_ports.redis_ui}"
  }
}

output "checkpointer_api_endpoints" {
  description = "Checkpointer API endpoints"
  value = {
    base_url     = "http://${aws_eip.app.public_ip}:${var.app_ports.fastapi}/api/v1/checkpoints"
    save         = "POST http://${aws_eip.app.public_ip}:${var.app_ports.fastapi}/api/v1/checkpoints"
    list_by_workflow = "GET http://${aws_eip.app.public_ip}:${var.app_ports.fastapi}/api/v1/checkpoints/{workflow_id}"
    latest       = "GET http://${aws_eip.app.public_ip}:${var.app_ports.fastapi}/api/v1/checkpoints/{workflow_id}/latest"
    delete       = "DELETE http://${aws_eip.app.public_ip}:${var.app_ports.fastapi}/api/v1/checkpoints/{workflow_id}"
    list_all     = "GET http://${aws_eip.app.public_ip}:${var.app_ports.fastapi}/api/v1/checkpoints"
    health       = "GET http://${aws_eip.app.public_ip}:${var.app_ports.fastapi}/api/v1/checkpoints/health/status"
  }
}

# =============================================================================
# Database Connection Information
# =============================================================================

output "redis_connection" {
  description = "Redis connection information"
  value = {
    host = aws_eip.app.public_ip
    port = 6379
    url  = "redis://${aws_eip.app.public_ip}:6379"
  }
}

output "rdflib_connection" {
  description = "RDFLib SQLite connection information"
  value = {
    data_path = "/opt/kg-system/rdflib-data/kg.db"
    sqlite_url = "sqlite:///./data/kg.db"
    graph_identifier = "kg"
    namespace_prefix = "http://example.org/kg/"
  }
}

# =============================================================================
# Deployment Information
# =============================================================================

output "deployment_info" {
  description = "Deployment and management information"
  value = {
    environment           = var.environment
    project_name         = var.project_name
    docker_compose_path  = var.docker_compose_path
    application_data_dir = var.app_data_dir
    redis_data_dir       = var.redis_data_dir
    rdflib_data_dir      = var.rdflib_data_dir
    health_check_script  = "/opt/kg-system/health-check.sh"
    service_name         = "kg-system"
  }
}

# =============================================================================
# Quick Start Commands
# =============================================================================

output "quick_start_commands" {
  description = "Commands to get started with the deployment"
  value = {
    ssh_connect = var.key_pair_name != "" ? 
      "ssh -i /path/to/your/key.pem ec2-user@${aws_eip.app.public_ip}" :
      "ssh -i ${path.module}/../../keys/${var.project_name}-${var.environment}.pem ec2-user@${aws_eip.app.public_ip}"
    
    upload_code = "scp -r -i /path/to/key.pem ../../../app ../../../server ec2-user@${aws_eip.app.public_ip}:/opt/kg-system/"
    
    setup_env = [
      "# 1. SSH to the instance",
      "# 2. Copy environment template: cp /opt/kg-system/.env.template /opt/kg-system/.env",
      "# 3. Edit the .env file with your API keys: nano /opt/kg-system/.env",
      "# 4. Start services: sudo systemctl start kg-system",
      "# 5. Check status: sudo systemctl status kg-system",
      "# 6. View logs: sudo journalctl -u kg-system -f",
      "# 7. Health check: /opt/kg-system/health-check.sh"
    ]
    
    service_management = {
      start    = "sudo systemctl start kg-system"
      stop     = "sudo systemctl stop kg-system"
      restart  = "sudo systemctl restart kg-system"
      status   = "sudo systemctl status kg-system"
      logs     = "sudo journalctl -u kg-system -f"
      health   = "/opt/kg-system/health-check.sh"
    }
  }
}