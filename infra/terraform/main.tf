# =============================================================================
# Data Sources
# =============================================================================

# Get latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# =============================================================================
# Networking
# =============================================================================

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-vpc-${var.environment}"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-igw-${var.environment}"
  })
}

# Public Subnet
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-public-subnet-${var.environment}"
  })
}

# Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-public-rt-${var.environment}"
  })
}

# Route Table Association
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# =============================================================================
# Security Groups
# =============================================================================

# Application Security Group
resource "aws_security_group" "app" {
  name_prefix = "${var.project_name}-app-${var.environment}-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for AI Knowledge Graph application"
  
  # SSH access
  ingress {
    from_port   = var.ssh_port
    to_port     = var.ssh_port
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "SSH access"
  }
  
  # FastAPI
  ingress {
    from_port   = var.app_ports.fastapi
    to_port     = var.app_ports.fastapi
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "FastAPI application"
  }
  
  # Streamlit
  ingress {
    from_port   = var.app_ports.streamlit
    to_port     = var.app_ports.streamlit
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Streamlit UI"
  }
  

  
  # Redis Commander UI
  ingress {
    from_port   = var.app_ports.redis_ui
    to_port     = var.app_ports.redis_ui
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Redis Commander UI"
  }
  
  # Redis port (for external access if needed)
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Redis JSON"
  }
  

  
  # Egress - all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-app-sg-${var.environment}"
  })
  
  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# SSH Key Pair
# =============================================================================

# Generate SSH key pair
resource "tls_private_key" "app_key" {
  count     = var.key_pair_name == "" ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create AWS key pair
resource "aws_key_pair" "app_key" {
  count      = var.key_pair_name == "" ? 1 : 0
  key_name   = "${var.project_name}-key-${var.environment}"
  public_key = tls_private_key.app_key[0].public_key_openssh
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-key-${var.environment}"
  })
}

# Save private key to local file
resource "local_file" "private_key" {
  count    = var.key_pair_name == "" ? 1 : 0
  content  = tls_private_key.app_key[0].private_key_pem
  filename = "${path.module}/../../keys/${var.project_name}-${var.environment}.pem"
  
  provisioner "local-exec" {
    command = "chmod 600 ${path.module}/../../keys/${var.project_name}-${var.environment}.pem"
  }
}

# =============================================================================
# EC2 Instance
# =============================================================================

# User data script for setting up Docker and application
locals {
  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    redis_data_dir        = var.redis_data_dir
    rdflib_data_dir       = var.rdflib_data_dir
    app_data_dir          = var.app_data_dir
    docker_compose_path   = var.docker_compose_path
    project_name          = var.project_name
    environment           = var.environment
  }))
}

# EC2 Instance
resource "aws_instance" "app" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type
  
  key_name               = var.key_pair_name != "" ? var.key_pair_name : aws_key_pair.app_key[0].key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app.id]
  
  user_data = local.user_data
  
  root_block_device {
    volume_type = "gp3"
    volume_size = 30
    encrypted   = true
    
    tags = merge(var.common_tags, {
      Name = "${var.project_name}-root-${var.environment}"
    })
  }
  
  # Additional EBS volume for application data
  ebs_block_device {
    device_name = "/dev/sdf"
    volume_type = "gp3"
    volume_size = 50
    encrypted   = true
    
    tags = merge(var.common_tags, {
      Name = "${var.project_name}-data-${var.environment}"
    })
  }
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.instance_name}-${var.environment}"
  })
  
  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# Elastic IP
# =============================================================================

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-eip-${var.environment}"
  })
  
  depends_on = [aws_internet_gateway.main]
}