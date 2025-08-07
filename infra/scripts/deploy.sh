#!/bin/bash
set -e

# =============================================================================
# AI Knowledge Graph System - Deployment Script
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infra/terraform"
KEYS_DIR="$PROJECT_ROOT/keys"

# Default values
ENVIRONMENT="dev"
REGION="us-west-2"
INSTANCE_TYPE="t3.medium"
SKIP_CONFIRM="false"

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}=========================================="
    echo -e "$1"
    echo -e "==========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy AI Knowledge Graph System to AWS

OPTIONS:
    -e, --environment ENVIRONMENT    Environment (dev, staging, prod) [default: dev]
    -r, --region REGION             AWS region [default: us-west-2]
    -t, --instance-type TYPE        EC2 instance type [default: t3.medium]
    -k, --key-pair KEY_NAME         Existing AWS key pair name (optional)
    -y, --yes                       Skip confirmation prompts
    -h, --help                      Show this help message

EXAMPLES:
    $0                              # Deploy to dev environment
    $0 -e prod -r us-east-1         # Deploy to prod in us-east-1
    $0 -t t3.large -y               # Deploy with larger instance, skip prompts

EOF
}

check_requirements() {
    print_info "Checking requirements..."
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install Terraform first."
        exit 1
    fi
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "All requirements satisfied"
}

create_terraform_vars() {
    local vars_file="$TERRAFORM_DIR/terraform.tfvars"
    
    print_info "Creating Terraform variables file..."
    
    cat > "$vars_file" << EOF
# AI Knowledge Graph System - Terraform Variables
# Generated on: $(date)

# Environment Configuration
environment  = "$ENVIRONMENT"
aws_region   = "$REGION"
project_name = "ai-knowledge-graph"

# Instance Configuration
instance_type = "$INSTANCE_TYPE"
instance_name = "kg-server"

EOF

    if [ -n "$KEY_PAIR_NAME" ]; then
        echo "key_pair_name = \"$KEY_PAIR_NAME\"" >> "$vars_file"
    fi

    cat >> "$vars_file" << EOF

# Common Tags
common_tags = {
  Project     = "AI Knowledge Graph System"
  Environment = "$ENVIRONMENT"
  ManagedBy   = "Terraform"
  DeployedBy  = "$(whoami)"
  DeployedAt  = "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

# Redis Configuration
redis_enabled      = true
redis_version      = "7.2"
redis_json_enabled = true
redis_memory_limit = "2Gi"

# RDFLib Configuration (Neo4j 대체)
rdflib_enabled = true

# Application Configuration
app_ports = {
  fastapi   = 8000
  streamlit = 8501
  # neo4j_ui  = 7474  # Removed - using RDFLib
  redis_ui  = 8081
}

EOF

    print_success "Terraform variables file created: $vars_file"
}

terraform_init() {
    print_info "Initializing Terraform..."
    cd "$TERRAFORM_DIR"
    terraform init
    print_success "Terraform initialized"
}

terraform_plan() {
    print_info "Planning Terraform deployment..."
    cd "$TERRAFORM_DIR"
    terraform plan -var-file="terraform.tfvars" -out="tfplan"
    print_success "Terraform plan created"
}

terraform_apply() {
    print_info "Applying Terraform deployment..."
    cd "$TERRAFORM_DIR"
    terraform apply "tfplan"
    print_success "Terraform deployment completed"
}

show_outputs() {
    print_header "Deployment Information"
    cd "$TERRAFORM_DIR"
    
    echo -e "${BLUE}Instance Information:${NC}"
    terraform output instance_id
    terraform output public_ip
    terraform output instance_type
    
    echo -e "\n${BLUE}Application URLs:${NC}"
    terraform output application_urls | jq -r 'to_entries[] | "\(.key): \(.value)"'
    
    echo -e "\n${BLUE}Checkpointer API Endpoints:${NC}"
    terraform output checkpointer_api_endpoints | jq -r 'to_entries[] | "\(.key): \(.value)"'
    
    echo -e "\n${BLUE}SSH Access:${NC}"
    terraform output ssh_command
    
    echo -e "\n${BLUE}Quick Start:${NC}"
    terraform output -json quick_start_commands | jq -r '.setup_env[]'
}

create_deployment_summary() {
    local summary_file="$PROJECT_ROOT/deployment-summary.md"
    
    print_info "Creating deployment summary..."
    
    cd "$TERRAFORM_DIR"
    
    cat > "$summary_file" << EOF
# AI Knowledge Graph System - Deployment Summary

**Deployment Date:** $(date)  
**Environment:** $ENVIRONMENT  
**Region:** $REGION  
**Instance Type:** $INSTANCE_TYPE  

## Infrastructure

EOF

    # Add Terraform outputs to summary
    echo "### Instance Information" >> "$summary_file"
    echo '```' >> "$summary_file"
    terraform output instance_id >> "$summary_file"
    terraform output public_ip >> "$summary_file"
    terraform output instance_type >> "$summary_file"
    echo '```' >> "$summary_file"
    echo "" >> "$summary_file"
    
    echo "### Application URLs" >> "$summary_file"
    terraform output application_urls | jq -r 'to_entries[] | "- **\(.key):** \(.value)"' >> "$summary_file"
    echo "" >> "$summary_file"
    
    echo "### SSH Access" >> "$summary_file"
    echo '```bash' >> "$summary_file"
    terraform output -raw ssh_command >> "$summary_file"
    echo "" >> "$summary_file"
    echo '```' >> "$summary_file"
    echo "" >> "$summary_file"
    
    cat >> "$summary_file" << EOF
## Next Steps

1. **Upload Application Code:**
   \`\`\`bash
   scp -r -i /path/to/key.pem app server ec2-user@\$(terraform output -raw public_ip):/opt/kg-system/
   \`\`\`

2. **Configure Environment:**
   \`\`\`bash
   ssh -i /path/to/key.pem ec2-user@\$(terraform output -raw public_ip)
   cp /opt/kg-system/.env.template /opt/kg-system/.env
   nano /opt/kg-system/.env  # Add your API keys
   \`\`\`

3. **Start Services:**
   \`\`\`bash
   sudo systemctl start kg-system
   sudo systemctl status kg-system
   \`\`\`

4. **Health Check:**
   \`\`\`bash
   /opt/kg-system/health-check.sh
   \`\`\`

## Checkpointer API Testing

Test the Redis-JSON checkpoint system:

\`\`\`bash
# Health check
curl \$(terraform output -raw public_ip):8000/api/v1/checkpoints/health/status

# Save a checkpoint
curl -X POST \$(terraform output -raw public_ip):8000/api/v1/checkpoints \\
  -H "Content-Type: application/json" \\
  -d '{
    "workflow_id": "test-workflow-001",
    "checkpoint_type": "manual",
    "state_snapshot": {
      "trace_id": "test-trace-001",
      "keyword": "deployment test"
    },
    "metadata": {"deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
  }'

# List checkpoints
curl \$(terraform output -raw public_ip):8000/api/v1/checkpoints/test-workflow-001
\`\`\`

## Management Commands

\`\`\`bash
# Service management
sudo systemctl start|stop|restart|status kg-system

# View logs
sudo journalctl -u kg-system -f

# Health check
/opt/kg-system/health-check.sh

# Destroy infrastructure (when done)
cd $TERRAFORM_DIR && terraform destroy -var-file="terraform.tfvars"
\`\`\`

---
*Generated by AI Knowledge Graph System deployment script*
EOF

    print_success "Deployment summary created: $summary_file"
}

# =============================================================================
# Main Deployment Flow
# =============================================================================

main() {
    print_header "AI Knowledge Graph System Deployment"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -t|--instance-type)
                INSTANCE_TYPE="$2"
                shift 2
                ;;
            -k|--key-pair)
                KEY_PAIR_NAME="$2"
                shift 2
                ;;
            -y|--yes)
                SKIP_CONFIRM="true"
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
        print_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod."
        exit 1
    fi
    
    # Display configuration
    print_info "Configuration:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Region: $REGION"
    echo "  Instance Type: $INSTANCE_TYPE"
    echo "  Key Pair: ${KEY_PAIR_NAME:-"Will be generated"}"
    echo ""
    
    # Confirmation
    if [ "$SKIP_CONFIRM" != "true" ]; then
        echo -n "Continue with deployment? (y/N): "
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            print_warning "Deployment cancelled"
            exit 0
        fi
    fi
    
    # Create keys directory
    mkdir -p "$KEYS_DIR"
    
    # Execute deployment steps
    check_requirements
    create_terraform_vars
    terraform_init
    terraform_plan
    terraform_apply
    show_outputs
    create_deployment_summary
    
    print_header "Deployment Completed Successfully!"
    print_success "Your AI Knowledge Graph System is ready!"
    print_info "See deployment-summary.md for detailed information and next steps."
}

# Run main function
main "$@"