# AI Knowledge Graph System - Infrastructure

This directory contains infrastructure automation for deploying the AI Knowledge Graph System to AWS using Terraform and Docker Compose.

## 🏗️ Architecture Overview

The system is deployed as a single EC2 instance running Docker Compose with the following services:

- **FastAPI Backend** - AI Knowledge Graph API with Checkpointer endpoints
- **Streamlit Frontend** - User interface for the system
- **Redis with JSON Module** - State snapshots and caching (Redis Stack)
- **RDFLib + SQLite** - Knowledge graph storage
- **Redis Commander** - Redis management UI (optional)

## 📁 Directory Structure

```
infra/
├── docker-compose.yml          # Local development compose file
├── terraform/                  # AWS infrastructure as code
│   ├── versions.tf             # Provider versions and configuration
│   ├── variables.tf            # Input variables
│   ├── main.tf                 # Main infrastructure resources
│   ├── outputs.tf              # Output values
│   └── user-data.sh            # EC2 instance initialization script
├── scripts/                    # Automation scripts
│   ├── deploy.sh               # Main deployment script
│   └── manage.sh               # Infrastructure management script
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials (`aws configure`)
3. **Terraform** installed (>= 1.0)
4. **Git** for repository management
5. **jq** for JSON processing (optional but recommended)

### Deploy Infrastructure

```bash
# Deploy to development environment
./infra/scripts/deploy.sh

# Deploy to production with custom settings
./infra/scripts/deploy.sh -e prod -r us-east-1 -t t3.large

# Deploy with existing SSH key
./infra/scripts/deploy.sh -k my-existing-key
```

### Manage Infrastructure

```bash
# Check infrastructure status
./infra/scripts/manage.sh status

# SSH into the instance
./infra/scripts/manage.sh ssh

# View application logs
./infra/scripts/manage.sh logs

# Upload code changes
./infra/scripts/manage.sh upload

# Restart services
./infra/scripts/manage.sh restart

# Run health check
./infra/scripts/manage.sh health

# Backup data
./infra/scripts/manage.sh backup

# Destroy infrastructure
./infra/scripts/manage.sh destroy
```

## 🔧 Configuration

### Environment Variables

The deployment creates a template file at `/opt/kg-system/.env.template` on the EC2 instance. Copy this to `.env` and configure your API keys:

```bash
# SSH to instance
./infra/scripts/manage.sh ssh

# Configure environment
cp /opt/kg-system/.env.template /opt/kg-system/.env
nano /opt/kg-system/.env
```

Required environment variables:
- `ANTHROPIC_API_KEY` - For AI model access
- `PERPLEXITY_API_KEY` - For research features
- `OPENAI_API_KEY` - For OpenAI models

### Terraform Variables

Create `infra/terraform/terraform.tfvars` to customize deployment:

```hcl
# Environment and basic settings
environment  = "prod"
aws_region   = "us-east-1"
project_name = "my-kg-system"

# Instance configuration
instance_type = "t3.large"
key_pair_name = "my-existing-key"  # Optional

# Security (restrict in production!)
allowed_cidr_blocks = ["YOUR.IP.ADDRESS/32"]

# Application ports
app_ports = {
  fastapi   = 8000
  streamlit = 8501
  # neo4j_ui  = 7474  # Removed - using RDFLib
  redis_ui  = 8081
}
```

## 🌐 Service Endpoints

After deployment, the following endpoints will be available:

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| FastAPI | 8000 | `http://<public-ip>:8000/docs` | API documentation |
| Streamlit | 8501 | `http://<public-ip>:8501` | Web interface |
| RDFLib Storage | N/A | File-based storage | Local SQLite graph storage |
| Redis Commander | 8081 | `http://<public-ip>:8081` | Redis management |

### Checkpointer API Endpoints

The Redis-JSON checkpoint system provides these endpoints:

```bash
# Base URL
BASE_URL="http://<public-ip>:8000/api/v1/checkpoints"

# Health check
GET $BASE_URL/health/status

# Save checkpoint
POST $BASE_URL
{
  "workflow_id": "test-workflow",
  "checkpoint_type": "manual",
  "state_snapshot": {...},
  "metadata": {...}
}

# List checkpoints by workflow
GET $BASE_URL/{workflow_id}

# Get latest checkpoint
GET $BASE_URL/{workflow_id}/latest

# Delete checkpoints
DELETE $BASE_URL/{workflow_id}

# List all checkpoints (paginated)
GET $BASE_URL?page=1&page_size=20
```

## 🐳 Local Development

For local development, use the Docker Compose setup:

```bash
# Start services locally
cd infra
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📊 Monitoring and Health Checks

### Automated Health Checks

The system includes automated health monitoring:

- **Health Check Script**: `/opt/kg-system/health-check.sh`
- **Cron Job**: Runs every 5 minutes
- **Logs**: Health check results logged to `/var/log/kg-health.log`

### Manual Monitoring

```bash
# Run health check
./infra/scripts/manage.sh health

# View service status
./infra/scripts/manage.sh status

# View application logs
./infra/scripts/manage.sh logs

# SSH and inspect manually
./infra/scripts/manage.sh ssh
sudo systemctl status kg-system
docker ps
```

## 💾 Data Management

### Backup and Restore

```bash
# Create backup
./infra/scripts/manage.sh backup

# List backups
ls -la backups/

# Restore from backup
./infra/scripts/manage.sh restore
```

### Data Persistence

Data is stored in the following locations on the EC2 instance:

- **Redis Data**: `/opt/kg-system/redis-data`
- **RDFLib Data**: `/opt/kg-system/data/kg.db`
- **Application Data**: `/opt/kg-system/app-data`
- **Configuration**: `/opt/kg-system/.env`

## 🔒 Security Considerations

### Production Deployment

1. **Restrict Access**: Update `allowed_cidr_blocks` in Terraform variables
2. **Use Existing SSH Keys**: Specify `key_pair_name` instead of generating new keys
3. **Environment Separation**: Deploy to separate AWS accounts/regions
4. **Secrets Management**: Consider AWS Secrets Manager for API keys
5. **Network Security**: Use private subnets and load balancers for production

### Default Security Groups

The deployment creates security groups allowing access to:
- SSH (port 22)
- Application ports (8000, 8501, 7474, 8081)
- Redis (port 6379)
- RDFLib SQLite (file-based storage)

**Important**: Default configuration allows access from anywhere (0.0.0.0/0). Restrict this in production!

## 🚨 Troubleshooting

### Common Issues

1. **Terraform Errors**:
   ```bash
   # Check AWS credentials
   aws sts get-caller-identity
   
   # Re-initialize Terraform
   cd infra/terraform
   terraform init -upgrade
   ```

2. **Application Not Starting**:
   ```bash
   # Check service status
   ./infra/scripts/manage.sh ssh
   sudo systemctl status kg-system
   sudo journalctl -u kg-system -f
   ```

3. **SSH Connection Issues**:
   ```bash
   # Check security group rules
   # Verify key permissions: chmod 600 /path/to/key.pem
   # Check instance public IP
   ```

4. **Redis-JSON Not Working**:
   ```bash
   # Verify Redis Stack image is running
   docker ps | grep redis
   
   # Test Redis JSON module
   redis-cli JSON.GET test-key
   ```

### Log Locations

- **Setup Logs**: `/var/log/kg-setup.log`
- **Health Check Logs**: `/var/log/kg-health.log`
- **Service Logs**: `sudo journalctl -u kg-system`
- **Docker Logs**: `docker-compose logs`

## 📚 Additional Resources

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Redis Stack Documentation](https://redis.io/docs/stack/)
- [RDFLib Documentation](https://rdflib.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🤝 Support

For issues and questions:

1. Check the troubleshooting section above
2. Review deployment logs and health checks
3. Use the management scripts for debugging
4. Check individual service logs and configurations

---

*This infrastructure supports the AI Knowledge Graph System with Redis-JSON checkpoint storage, providing a complete deployment solution for the multi-agent knowledge graph and wiki generation system.*