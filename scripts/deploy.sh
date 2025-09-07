#!/bin/bash
# Deployment script for Rick and Morty SRE Application

set -e  # Exit on any error

# Configuration
NAMESPACE="rick-morty-app"
RELEASE_NAME="rick-morty-app"
CHART_PATH="./helm/rick-morty-app"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ENVIRONMENT="${ENVIRONMENT:-development}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check if we can connect to Kubernetes cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Create namespace if it doesn't exist
create_namespace() {
    log_info "Creating namespace if it doesn't exist..."
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
}

# Deploy the application
deploy_application() {
    log_info "Deploying Rick and Morty SRE Application..."
    
    # Prepare Helm values based on environment
    VALUES_FILE=""
    case ${ENVIRONMENT} in
        "development")
            VALUES_FILE="--values ${CHART_PATH}/values-dev.yaml"
            ;;
        "staging")
            VALUES_FILE="--values ${CHART_PATH}/values-staging.yaml"
            ;;
        "production")
            VALUES_FILE="--values ${CHART_PATH}/values-prod.yaml"
            ;;
        *)
            log_warn "Unknown environment: ${ENVIRONMENT}, using default values"
            ;;
    esac
    
    # Deploy with Helm
    helm upgrade --install ${RELEASE_NAME} ${CHART_PATH} \
        --namespace ${NAMESPACE} \
        --set image.tag=${IMAGE_TAG} \
        ${VALUES_FILE} \
        --wait \
        --timeout=10m \
        --atomic
    
    log_info "Application deployed successfully"
}

# Wait for deployment to be ready
wait_for_deployment() {
    log_info "Waiting for deployment to be ready..."
    
    kubectl rollout status deployment/${RELEASE_NAME} \
        --namespace ${NAMESPACE} \
        --timeout=300s
    
    log_info "Deployment is ready"
}

# Run health check
health_check() {
    log_info "Running health check..."
    
    # Port forward to access the service
    kubectl port-forward -n ${NAMESPACE} svc/${RELEASE_NAME} 8080:80 &
    PF_PID=$!
    
    # Wait for port forward to be ready
    sleep 5
    
    # Health check
    if curl -f http://localhost:8080/healthcheck > /dev/null 2>&1; then
        log_info "Health check passed"
    else
        log_error "Health check failed"
        kill ${PF_PID} 2>/dev/null || true
        exit 1
    fi
    
    # Clean up port forward
    kill ${PF_PID} 2>/dev/null || true
}

# Show deployment information
show_deployment_info() {
    log_info "Deployment Information:"
    echo "========================"
    echo "Namespace: ${NAMESPACE}"
    echo "Release: ${RELEASE_NAME}"
    echo "Image Tag: ${IMAGE_TAG}"
    echo "Environment: ${ENVIRONMENT}"
    echo ""
    
    log_info "Pods:"
    kubectl get pods -n ${NAMESPACE}
    echo ""
    
    log_info "Services:"
    kubectl get services -n ${NAMESPACE}
    echo ""
    
    log_info "Ingress:"
    kubectl get ingress -n ${NAMESPACE}
}

# Rollback function
rollback() {
    log_warn "Rolling back deployment..."
    helm rollback ${RELEASE_NAME} --namespace ${NAMESPACE}
    log_info "Rollback completed"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    helm uninstall ${RELEASE_NAME} --namespace ${NAMESPACE}
    kubectl delete namespace ${NAMESPACE}
    log_info "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting deployment of Rick and Morty SRE Application"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Image Tag: ${IMAGE_TAG}"
    
    check_prerequisites
    create_namespace
    deploy_application
    wait_for_deployment
    health_check
    show_deployment_info
    
    log_info "Deployment completed successfully!"
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        rollback
        ;;
    "cleanup")
        cleanup
        ;;
    "health-check")
        health_check
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|cleanup|health-check}"
        echo ""
        echo "Commands:"
        echo "  deploy      - Deploy the application (default)"
        echo "  rollback    - Rollback to previous version"
        echo "  cleanup     - Remove the application and namespace"
        echo "  health-check - Run health check against deployed application"
        echo ""
        echo "Environment Variables:"
        echo "  IMAGE_TAG   - Docker image tag to deploy (default: latest)"
        echo "  ENVIRONMENT - Deployment environment (development|staging|production)"
        exit 1
        ;;
esac
