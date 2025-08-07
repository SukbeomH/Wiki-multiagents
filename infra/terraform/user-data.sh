#!/bin/bash
set -e

# =============================================================================
# AI Knowledge Graph System - EC2 Instance Setup Script
# =============================================================================

# Variables (passed from Terraform)
REDIS_DATA_DIR="${redis_data_dir}"
RDFLIB_DATA_DIR="${rdflib_data_dir}"
APP_DATA_DIR="${app_data_dir}"
DOCKER_COMPOSE_PATH="${docker_compose_path}"
PROJECT_NAME="${project_name}"
ENVIRONMENT="${environment}"

# Log file
LOG_FILE="/var/log/kg-setup.log"
exec > >(tee -a $LOG_FILE)
exec 2>&1

echo "=========================================="
echo "AI Knowledge Graph System Setup Started"
echo "Environment: $ENVIRONMENT"
echo "Timestamp: $(date)"
echo "=========================================="

# =============================================================================
# System Updates and Dependencies
# =============================================================================

echo "[STEP 1] Updating system packages..."
yum update -y

echo "[STEP 2] Installing required packages..."
yum install -y \
    docker \
    git \
    curl \
    wget \
    unzip \
    htop \
    tree \
    vim \
    python3 \
    python3-pip

# =============================================================================
# Docker Setup
# =============================================================================

echo "[STEP 3] Setting up Docker..."

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add ec2-user to docker group
usermod -a -G docker ec2-user

# Install Docker Compose
DOCKER_COMPOSE_VERSION="2.24.0"
curl -L "https://github.com/docker/compose/releases/download/v$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verify installations
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker-compose --version)"

# =============================================================================
# File System Setup
# =============================================================================

echo "[STEP 4] Setting up file system..."

# Format and mount additional EBS volume for application data
if [ -b /dev/nvme1n1 ]; then
    DEVICE="/dev/nvme1n1"
elif [ -b /dev/xvdf ]; then
    DEVICE="/dev/xvdf"
else
    echo "Warning: Additional EBS volume not found, using root volume"
    DEVICE=""
fi

if [ -n "$DEVICE" ]; then
    echo "Formatting device $DEVICE..."
    mkfs.ext4 $DEVICE
    
    echo "Creating mount point..."
    mkdir -p /opt/kg-system
    
    echo "Mounting device..."
    mount $DEVICE /opt/kg-system
    
    # Add to fstab for persistence
    echo "$DEVICE /opt/kg-system ext4 defaults,nofail 0 2" >> /etc/fstab
else
    # Use root volume if no additional EBS volume
    mkdir -p /opt/kg-system
fi

# Create application directories
mkdir -p "$APP_DATA_DIR"
mkdir -p "$REDIS_DATA_DIR"
mkdir -p "$RDFLIB_DATA_DIR"
mkdir -p "$(dirname "$DOCKER_COMPOSE_PATH")"

# Set permissions
chown -R ec2-user:ec2-user /opt/kg-system
chmod -R 755 /opt/kg-system

echo "[STEP 5] Creating Docker Compose configuration..."

# Create docker-compose.yml
cat > "$DOCKER_COMPOSE_PATH" << 'EOF'
services:
  # Streamlit UI Service
  streamlit:
    build:
      context: .
      dockerfile: app/Dockerfile
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://fastapi:8000
    volumes:
      - ./app:/app
    depends_on:
      - fastapi
    networks:
      - kg-network
    restart: unless-stopped

  # FastAPI Backend Service
  fastapi:
    build:
      context: .
      dockerfile: server/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - RDFLIB_STORE_URI=sqlite:///./data/kg.db
      - RDFLIB_GRAPH_IDENTIFIER=kg
      - RDFLIB_NAMESPACE_PREFIX=http://example.org/kg/
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env
    volumes:
      - ./server:/server
      - ./data:/server/data
    depends_on:
      - redis
    networks:
      - kg-network
    restart: unless-stopped

  # Redis with JSON Module (Caching & State Management)
  redis:
    image: redis/redis-stack-server:7.2.0-v9
    ports:
      - "6379:6379"
    environment:
      - REDIS_ARGS=--save 60 1 --loglevel warning
    volumes:
      - ${REDIS_DATA_DIR}:/data
    networks:
      - kg-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Redis Commander (Optional - Redis UI)
  redis-commander:
    image: rediscommander/redis-commander:latest
    environment:
      - REDIS_HOSTS=local:redis:6379
    ports:
      - "8081:8081"
    depends_on:
      - redis
    networks:
      - kg-network
    profiles:
      - dev

volumes:
  redis_data:

networks:
  kg-network:
    driver: bridge
EOF

# Replace variables in docker-compose.yml
sed -i "s|\${REDIS_DATA_DIR}|$REDIS_DATA_DIR|g" "$DOCKER_COMPOSE_PATH"

echo "[STEP 6] Creating environment template..."

# Create .env.template
cat > "/opt/kg-system/.env.template" << 'EOF'
# =============================================================================
# Azure OpenAI Configuration
# =============================================================================
AOAI_API_KEY=your_azure_openai_api_key_here
AOAI_ENDPOINT=https://your-resource.openai.azure.com/
AOAI_API_VERSION=2024-02-15-preview
AOAI_DEPLOY_GPT4O=gpt-4o
AOAI_DEPLOY_GPT4O_MINI=gpt-4o-mini
AOAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

# =============================================================================
# Database Configuration
# =============================================================================
RDFLIB_STORE_URI=sqlite:///./data/kg.db
RDFLIB_GRAPH_IDENTIFIER=kg
RDFLIB_NAMESPACE_PREFIX=http://example.org/kg/

# Redis Cache & State Management
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_URL=redis://localhost:6379

# =============================================================================
# External APIs
# =============================================================================
# SERPAPI_KEY=your_serpapi_key_here  # SerpAPI 제거
# DuckDuckGo는 API 키가 필요하지 않음 (무료 사용)

# =============================================================================
# Application Configuration
# =============================================================================
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
API_BASE_URL=http://localhost:8000
STREAMLIT_BASE_URL=http://localhost:8501
API_RATE_LIMIT=100
API_RATE_LIMIT_WINDOW=60

# =============================================================================
# Retry Configuration
# =============================================================================
RETRY_MAX_ATTEMPTS=3
RETRY_BASE_DELAY=1
RETRY_BACKOFF_MULTIPLIER=2
RETRY_JITTER_PERCENT=20

# =============================================================================
# Checkpoint Configuration
# =============================================================================
CHECKPOINT_INTERVAL_SECONDS=60
CHECKPOINT_REDIS_KEY_PREFIX=kg_checkpoint:

# =============================================================================
# Agent Configuration
# =============================================================================
RESEARCH_TOP_K_DOCS=10
RESEARCH_CACHE_TTL=3600
EXTRACTOR_CONFIDENCE_THRESHOLD=0.7
EXTRACTOR_MAX_ENTITIES=100
RETRIEVER_TOP_K=5
RETRIEVER_SIMILARITY_THRESHOLD=0.8
EOF

echo "[STEP 7] Creating systemd service..."

# Create systemd service file
cat > "/etc/systemd/system/kg-system.service" << EOF
[Unit]
Description=AI Knowledge Graph System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/kg-system
ExecStart=/usr/bin/docker-compose -f $DOCKER_COMPOSE_PATH up -d
ExecStop=/usr/bin/docker-compose -f $DOCKER_COMPOSE_PATH down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable kg-system

echo "[STEP 8] Creating health check script..."

# Create health check script
cat > "/opt/kg-system/health-check.sh" << 'EOF'
#!/bin/bash

# Health check script for AI Knowledge Graph System
echo "=========================================="
echo "AI Knowledge Graph System Health Check"
echo "Timestamp: $(date)"
echo "=========================================="

# Check if services are running
services=("FastAPI:8000/docs" "Streamlit:8501" "Redis-UI:8081")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -f -s "http://localhost:$port" > /dev/null 2>&1; then
        echo "✅ $name is running on port $port"
    else
        echo "❌ $name is not responding on port $port"
    fi
done

# Check Docker containers
echo ""
echo "Docker Container Status:"
docker-compose -f /opt/kg-system/docker-compose.yml ps

# Check disk usage
echo ""
echo "Disk Usage:"
df -h /opt/kg-system

# Check memory usage
echo ""
echo "Memory Usage:"
free -h

# Check system load
echo ""
echo "System Load:"
uptime
EOF

chmod +x /opt/kg-system/health-check.sh

echo "[STEP 9] Setting up monitoring..."

# Create log rotation configuration
cat > "/etc/logrotate.d/kg-system" << EOF
/var/log/kg-setup.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF

echo "[STEP 10] Finalizing setup..."

# Set proper permissions
chown -R ec2-user:ec2-user /opt/kg-system
chmod -R 755 /opt/kg-system

# Create a simple status page
cat > "/opt/kg-system/status.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>AI Knowledge Graph System Status</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .healthy { background-color: #d4edda; color: #155724; }
        .unhealthy { background-color: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>AI Knowledge Graph System Status</h1>
    <div class="status healthy">
        <h2>✅ System is running</h2>
        <p>All services are operational.</p>
    </div>
    <h3>Service URLs:</h3>
    <ul>
        <li><a href="http://localhost:8501">Streamlit UI</a></li>
        <li><a href="http://localhost:8000/docs">FastAPI Documentation</a></li>
        <li><a href="http://localhost:8081">Redis Commander</a></li>
    </ul>
    <p><small>Last updated: $(date)</small></p>
</body>
</html>
EOF

echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. SSH to the instance: ssh -i your-key.pem ec2-user@$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "2. Copy environment template: cp /opt/kg-system/.env.template /opt/kg-system/.env"
echo "3. Edit the .env file with your API keys: nano /opt/kg-system/.env"
echo "4. Start services: sudo systemctl start kg-system"
echo "5. Check status: sudo systemctl status kg-system"
echo "6. View logs: sudo journalctl -u kg-system -f"
echo "7. Health check: /opt/kg-system/health-check.sh"
echo ""
echo "Service URLs:"
echo "- Streamlit UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8501"
echo "- FastAPI Docs: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000/docs"
echo "- Redis Commander: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8081"
echo "=========================================="