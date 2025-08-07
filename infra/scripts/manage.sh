#!/bin/bash
set -e

# =============================================================================
# AI Knowledge Graph System - Management Script
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
Usage: $0 COMMAND [OPTIONS]

Manage AI Knowledge Graph System infrastructure

COMMANDS:
    status          Show infrastructure status
    ssh             SSH into the instance
    logs            View application logs
    health          Run health check
    upload          Upload application code
    restart         Restart application services
    destroy         Destroy infrastructure
    backup          Backup data volumes
    restore         Restore data from backup

OPTIONS:
    -e, --environment ENVIRONMENT    Environment (dev, staging, prod) [default: dev]
    -h, --help                      Show this help message

EXAMPLES:
    $0 status                       # Show infrastructure status
    $0 ssh                          # SSH into the instance
    $0 logs                         # View application logs
    $0 upload                       # Upload application code
    $0 destroy -e dev               # Destroy dev environment

EOF
}

get_instance_info() {
    cd "$TERRAFORM_DIR"
    
    if [ ! -f "terraform.tfstate" ]; then
        print_error "No Terraform state found. Please deploy first."
        exit 1
    fi
    
    PUBLIC_IP=$(terraform output -raw public_ip 2>/dev/null || echo "")
    INSTANCE_ID=$(terraform output -raw instance_id 2>/dev/null || echo "")
    KEY_PATH=$(terraform output -raw private_key_path 2>/dev/null || echo "")
    
    if [ -z "$PUBLIC_IP" ]; then
        print_error "Could not get instance information from Terraform state."
        exit 1
    fi
}

cmd_status() {
    print_header "Infrastructure Status"
    
    get_instance_info
    
    echo -e "${BLUE}Instance Information:${NC}"
    echo "  Instance ID: $INSTANCE_ID"
    echo "  Public IP: $PUBLIC_IP"
    echo "  SSH Key: $KEY_PATH"
    echo ""
    
    # Check if instance is reachable
    if ping -c 1 -W 5 "$PUBLIC_IP" &> /dev/null; then
        print_success "Instance is reachable"
        
        # Check if SSH is working
        if ssh -i "$KEY_PATH" -o ConnectTimeout=5 -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" 'echo "SSH working"' &> /dev/null; then
            print_success "SSH connection working"
            
            # Check application status
            print_info "Checking application status..."
            ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" '
                echo "Service Status:"
                if systemctl is-active --quiet kg-system; then
                    echo "  ✅ KG System: Running"
                else
                    echo "  ❌ KG System: Not running"
                fi
                
                echo ""
                echo "Container Status:"
                cd /opt/kg-system && docker-compose ps 2>/dev/null || echo "  ❌ Docker Compose not running"
            '
        else
            print_warning "SSH connection failed"
        fi
    else
        print_error "Instance is not reachable"
    fi
    
    echo ""
    echo -e "${BLUE}Application URLs:${NC}"
    cd "$TERRAFORM_DIR"
    terraform output application_urls | jq -r 'to_entries[] | "  \(.key): \(.value)"'
}

cmd_ssh() {
    print_info "Connecting to instance via SSH..."
    
    get_instance_info
    
    echo "Connecting to ec2-user@$PUBLIC_IP"
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP"
}

cmd_logs() {
    print_info "Viewing application logs..."
    
    get_instance_info
    
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" '
        echo "=== KG System Service Logs ==="
        sudo journalctl -u kg-system -n 50 --no-pager
        
        echo ""
        echo "=== Docker Compose Logs ==="
        cd /opt/kg-system
        docker-compose logs --tail=50 2>/dev/null || echo "Docker Compose not running"
    '
}

cmd_health() {
    print_info "Running health check..."
    
    get_instance_info
    
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" '
        if [ -f /opt/kg-system/health-check.sh ]; then
            /opt/kg-system/health-check.sh
        else
            echo "Health check script not found"
        fi
    '
}

cmd_upload() {
    print_info "Uploading application code..."
    
    get_instance_info
    
    echo "Uploading app and server directories..."
    scp -r -i "$KEY_PATH" -o StrictHostKeyChecking=no \
        "$PROJECT_ROOT/app" "$PROJECT_ROOT/server" \
        ec2-user@"$PUBLIC_IP":/opt/kg-system/
    
    print_success "Code uploaded successfully"
    
    # Restart services
    print_info "Restarting services..."
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" '
        sudo systemctl restart kg-system
    '
    
    print_success "Services restarted"
}

cmd_restart() {
    print_info "Restarting application services..."
    
    get_instance_info
    
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" '
        echo "Stopping services..."
        sudo systemctl stop kg-system
        
        echo "Cleaning up containers..."
        cd /opt/kg-system
        docker-compose down --remove-orphans 2>/dev/null || true
        
        echo "Starting services..."
        sudo systemctl start kg-system
        
        echo "Waiting for services to start..."
        sleep 10
        
        echo "Service status:"
        systemctl status kg-system --no-pager
    '
    
    print_success "Services restarted"
}

cmd_destroy() {
    print_warning "This will destroy ALL infrastructure resources!"
    echo "Environment: $ENVIRONMENT"
    
    echo -n "Are you sure? Type 'destroy' to confirm: "
    read -r confirm
    
    if [ "$confirm" != "destroy" ]; then
        print_info "Destruction cancelled"
        exit 0
    fi
    
    print_info "Destroying infrastructure..."
    
    cd "$TERRAFORM_DIR"
    terraform destroy -var-file="terraform.tfvars" -auto-approve
    
    print_success "Infrastructure destroyed"
}

cmd_backup() {
    print_info "Creating data backup..."
    
    get_instance_info
    
    local backup_dir="$PROJECT_ROOT/backups/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" '
        echo "Creating backup archive..."
        cd /opt/kg-system
        sudo tar -czf /tmp/kg-backup.tar.gz redis-data data app-data .env 2>/dev/null || true
    '
    
    echo "Downloading backup..."
    scp -i "$KEY_PATH" -o StrictHostKeyChecking=no \
        ec2-user@"$PUBLIC_IP":/tmp/kg-backup.tar.gz \
        "$backup_dir/kg-backup.tar.gz"
    
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" '
        rm -f /tmp/kg-backup.tar.gz
    '
    
    print_success "Backup created: $backup_dir/kg-backup.tar.gz"
}

cmd_restore() {
    print_info "Available backups:"
    ls -la "$PROJECT_ROOT/backups/" 2>/dev/null || {
        print_error "No backups found"
        exit 1
    }
    
    echo -n "Enter backup filename to restore: "
    read -r backup_file
    
    if [ ! -f "$PROJECT_ROOT/backups/$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    print_warning "This will overwrite existing data!"
    echo -n "Continue? (y/N): "
    read -r confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_info "Restore cancelled"
        exit 0
    fi
    
    get_instance_info
    
    print_info "Uploading backup..."
    scp -i "$KEY_PATH" -o StrictHostKeyChecking=no \
        "$PROJECT_ROOT/backups/$backup_file" \
        ec2-user@"$PUBLIC_IP":/tmp/kg-backup.tar.gz
    
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" '
        echo "Stopping services..."
        sudo systemctl stop kg-system
        
        echo "Restoring data..."
        cd /opt/kg-system
        sudo tar -xzf /tmp/kg-backup.tar.gz
        sudo chown -R ec2-user:ec2-user /opt/kg-system
        
        echo "Starting services..."
        sudo systemctl start kg-system
        
        rm -f /tmp/kg-backup.tar.gz
    '
    
    print_success "Restore completed"
}

# =============================================================================
# Main Function
# =============================================================================

main() {
    # Default values
    ENVIRONMENT="dev"
    
    # Parse command
    if [ $# -eq 0 ]; then
        usage
        exit 1
    fi
    
    COMMAND="$1"
    shift
    
    # Parse remaining arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
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
    
    # Execute command
    case $COMMAND in
        status)
            cmd_status
            ;;
        ssh)
            cmd_ssh
            ;;
        logs)
            cmd_logs
            ;;
        health)
            cmd_health
            ;;
        upload)
            cmd_upload
            ;;
        restart)
            cmd_restart
            ;;
        destroy)
            cmd_destroy
            ;;
        backup)
            cmd_backup
            ;;
        restore)
            cmd_restore
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"