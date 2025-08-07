# =============================================================================
# AWS & Infrastructure Variables
# =============================================================================

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ai-knowledge-graph"
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "AI Knowledge Graph System"
    ManagedBy   = "Terraform"
    Environment = "dev"
  }
}

# =============================================================================
# Docker & Local Development Variables
# =============================================================================

variable "docker_host" {
  description = "Docker host for provider"
  type        = string
  default     = "unix:///var/run/docker.sock"
}

# =============================================================================
# EC2 Instance Variables
# =============================================================================

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "instance_name" {
  description = "EC2 instance name"
  type        = string
  default     = "kg-server"
}

variable "key_pair_name" {
  description = "AWS key pair name for EC2 access"
  type        = string
  default     = ""
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Public subnet CIDR block"
  type        = string
  default     = "10.0.1.0/24"
}

variable "availability_zone" {
  description = "Availability zone for resources"
  type        = string
  default     = "us-west-2a"
}

# =============================================================================
# Redis Configuration Variables
# =============================================================================

variable "redis_enabled" {
  description = "Enable Redis deployment"
  type        = bool
  default     = true
}

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "7.2"
}

variable "redis_json_enabled" {
  description = "Enable Redis JSON module"
  type        = bool
  default     = true
}

variable "redis_memory_limit" {
  description = "Redis memory limit"
  type        = string
  default     = "2Gi"
}

variable "redis_data_dir" {
  description = "Redis data directory on host"
  type        = string
  default     = "/opt/kg-system/redis-data"
}

# =============================================================================
# RDFLib Configuration Variables
# =============================================================================

variable "rdflib_data_dir" {
  description = "RDFLib SQLite data directory on host"
  type        = string
  default     = "/opt/kg-system/rdflib-data"
}

# =============================================================================
# Application Configuration Variables
# =============================================================================

variable "app_data_dir" {
  description = "Application data directory on host"
  type        = string
  default     = "/opt/kg-system/app-data"
}

variable "docker_compose_path" {
  description = "Path to docker-compose.yml file"
  type        = string
  default     = "/opt/kg-system/docker-compose.yml"
}

# =============================================================================
# Security Variables
# =============================================================================

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the EC2 instance"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict this in production
}

variable "ssh_port" {
  description = "SSH port for EC2 access"
  type        = number
  default     = 22
}

variable "app_ports" {
  description = "Application ports to expose"
  type        = map(number)
  default = {
    fastapi   = 8000
    streamlit = 8501
    redis_ui  = 8081
  }
}