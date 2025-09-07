#!/bin/bash
# GitHub Repository Setup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "app" ]; then
    log_error "Please run this script from the rick-morty-sre-app root directory"
    exit 1
fi

log_info "GitHub Repository Setup Script"
echo "================================"

# Step 1: Initialize Git Repository
log_step "1. Initializing Git repository..."

if [ ! -d ".git" ]; then
    git init
    log_info "Git repository initialized"
else
    log_info "Git repository already exists"
fi

# Step 2: Get GitHub repository URL
echo ""
log_step "2. GitHub Repository Configuration"
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter repository name [rick-morty-sre-app]: " REPO_NAME
REPO_NAME=${REPO_NAME:-rick-morty-sre-app}

GITHUB_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
log_info "Repository URL: $GITHUB_URL"

# Step 3: Configure Git
log_step "3. Configuring Git..."
git config user.name "$GITHUB_USERNAME" 2>/dev/null || true
git config user.email "${GITHUB_USERNAME}@users.noreply.github.com" 2>/dev/null || true

# Step 4: Add files and create initial commit
log_step "4. Creating initial commit..."
git add .
git commit -m "Initial commit: Complete SRE application

- Production-grade FastAPI application with Rick and Morty API integration
- Kubernetes deployment with Helm charts
- Comprehensive CI/CD pipeline with GitHub Actions
- Full observability stack with metrics, tracing, and alerting
- Complete test suite with unit, integration, and load tests
- Security hardened containers and configurations
- Comprehensive documentation and deployment guides" || log_info "No changes to commit"

# Step 5: Set up branches
log_step "5. Setting up branches..."
git branch -M main

if ! git ls-remote --heads origin develop | grep -q develop; then
    git checkout -b develop
    git checkout main
    log_info "Created develop branch"
else
    log_info "Develop branch already exists"
fi

# Step 6: Add remote and push
log_step "6. Adding remote and pushing to GitHub..."
git remote remove origin 2>/dev/null || true
git remote add origin "$GITHUB_URL"

echo ""
log_warn "About to push to GitHub. Make sure you have:"
log_warn "1. Created the repository on GitHub: $GITHUB_URL"
log_warn "2. Have push access to the repository"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

git push -u origin main
git push -u origin develop

log_info "Code pushed to GitHub successfully!"

# Step 7: Display next steps
echo ""
log_step "7. Next Steps - GitHub Configuration"
echo "=================================="
echo ""
echo "🔐 REQUIRED SECRETS (GitHub → Settings → Secrets and variables → Actions):"
echo ""
echo "   DOCKERHUB_USERNAME     = your-dockerhub-username"
echo "   DOCKERHUB_TOKEN        = your-dockerhub-access-token"
echo "   KUBE_CONFIG           = \$(cat ~/.kube/config | base64 | tr -d '\\n')"
echo "   DATABASE_URL          = postgresql+asyncpg://user:pass@host:5432/rickmorty"
echo "   REDIS_URL             = redis://host:6379/0"
echo "   JAEGER_ENDPOINT       = http://jaeger:14268/api/traces"
echo "   PRODUCTION_DOMAIN     = rick-morty-api.yourdomain.com"
echo ""
echo "🌍 REQUIRED ENVIRONMENTS (GitHub → Settings → Environments):"
echo ""
echo "   staging     - For develop branch deployments"
echo "   production  - For main branch deployments (add protection rules)"
echo ""
echo "👥 GRANT ACCESS:"
echo ""
echo "   Add 'bregmanx' (abregman@akamai.com) as collaborator"
echo "   Repository → Settings → Manage access → Invite collaborator"
echo ""
echo "🔒 BRANCH PROTECTION (GitHub → Settings → Branches):"
echo ""
echo "   Protect 'main' branch with PR requirements and status checks"
echo "   Protect 'develop' branch with status checks"
echo ""
echo "📋 DETAILED INSTRUCTIONS:"
echo ""
echo "   See docs/GITHUB_SETUP.md for complete step-by-step guide"
echo ""

# Step 8: Test Docker Hub credentials (optional)
echo ""
read -p "Do you want to test Docker Hub credentials now? (y/n): " TEST_DOCKER
if [[ $TEST_DOCKER =~ ^[Yy]$ ]]; then
    log_step "8. Testing Docker Hub credentials..."
    read -p "Enter Docker Hub username: " DOCKER_USER
    read -s -p "Enter Docker Hub token: " DOCKER_TOKEN
    echo ""
    
    if echo "$DOCKER_TOKEN" | docker login --username "$DOCKER_USER" --password-stdin; then
        log_info "Docker Hub login successful!"
        docker logout
    else
        log_error "Docker Hub login failed. Please check your credentials."
    fi
fi

echo ""
log_info "Setup completed! 🎉"
log_info "Repository URL: $GITHUB_URL"
log_info "Next: Configure GitHub secrets and environments as shown above"
