terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
    
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = var.common_tags
  }
}

# Docker Provider Configuration (for local development)
provider "docker" {
  host = var.docker_host
}