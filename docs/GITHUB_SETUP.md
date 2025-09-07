# GitHub Repository Setup Guide

This guide walks you through setting up the GitHub repository with all required secrets and configurations for the CI/CD pipeline.

## Step 1: Create GitHub Repository

1. **Create a new repository** on GitHub:
   ```
   Repository name: rick-morty-sre-app
   Description: Production-grade SRE application integrating with Rick and Morty API
   Visibility: Private (recommended) or Public
   ```

2. **Initialize the repository** with the code:
   ```bash
   cd /Users/purnachandrareddypeddasura/Desktop/Akamai
   git init
   git add .
   git commit -m "Initial commit: Complete SRE application"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/rick-morty-sre-app.git
   git push -u origin main
   ```

3. **Create develop branch**:
   ```bash
   git checkout -b develop
   git push -u origin develop
   ```

## Step 2: Configure Repository Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

### Required Secrets

#### Docker Hub Secrets
```
DOCKERHUB_USERNAME = your-dockerhub-username
DOCKERHUB_TOKEN = your-dockerhub-access-token
```

**How to get Docker Hub token:**
1. Go to [Docker Hub](https://hub.docker.com/)
2. Sign in → Account Settings → Security
3. Create "New Access Token"
4. Copy the token (save it securely)

#### Production Kubernetes Secrets
```
KUBE_CONFIG = base64-encoded-kubeconfig-file
DATABASE_URL = postgresql+asyncpg://user:pass@host:5432/rickmorty
REDIS_URL = redis://host:6379/0
JAEGER_ENDPOINT = http://jaeger:14268/api/traces
PRODUCTION_DOMAIN = rick-morty-api.yourdomain.com
```

**How to get KUBE_CONFIG:**
```bash
# For your Kubernetes cluster, encode the kubeconfig
cat ~/.kube/config | base64 | tr -d '\n'
```

## Step 3: Configure Environments

Go to your GitHub repository → Settings → Environments

### Create Staging Environment
1. Click "New environment"
2. Name: `staging`
3. Configure protection rules (optional):
   - Required reviewers: Add team members
   - Wait timer: 0 minutes
   - Deployment branches: Only `develop` branch

### Create Production Environment
1. Click "New environment" 
2. Name: `production`
3. Configure protection rules (recommended):
   - Required reviewers: Add senior team members
   - Wait timer: 5 minutes (for review)
   - Deployment branches: Only `main` branch and release tags

## Step 4: Set Up Container Registry

### Option A: Docker Hub (Free)
1. Create account at [Docker Hub](https://hub.docker.com/)
2. Create repository: `your-username/rick-morty-sre-app`
3. Set visibility to Public or Private
4. Update the image name in workflows if needed

### Option B: GitHub Container Registry (Free)
Update the workflow to use GitHub Container Registry:

```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
```

And update the login step:
```yaml
- name: Log in to Container Registry
  uses: docker/login-action@v3
  with:
    registry: ${{ env.REGISTRY }}
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

## Step 5: Grant Repository Access

Add `abregman@akamai.com` (bregmanx) as a collaborator:

1. Go to your repository → Settings → Manage access
2. Click "Invite a collaborator"
3. Enter: `bregmanx` or `abregman@akamai.com`
4. Select role: "Admin" or "Write" (as required)
5. Send invitation

## Step 6: Test the Pipeline

### Test CI Pipeline
1. **Create a feature branch**:
   ```bash
   git checkout -b feature/test-ci
   echo "# Test" >> test.md
   git add test.md
   git commit -m "Test CI pipeline"
   git push origin feature/test-ci
   ```

2. **Create Pull Request** to `main` branch
3. **Verify** that CI tests run successfully

### Test Staging Deployment
1. **Merge to develop branch**:
   ```bash
   git checkout develop
   git merge feature/test-ci
   git push origin develop
   ```

2. **Check Actions tab** for staging deployment

### Test Production Deployment
1. **Merge to main branch**:
   ```bash
   git checkout main
   git merge develop
   git push origin main
   ```

2. **Check Actions tab** for production deployment

## Step 7: Configure Branch Protection

Go to Settings → Branches → Add rule

### Protect `main` branch:
- Branch name pattern: `main`
- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging
- ✅ Include administrators
- ✅ Allow force pushes (uncheck)
- ✅ Allow deletions (uncheck)

### Protect `develop` branch:
- Branch name pattern: `develop`  
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging

## Step 8: Set Up Notifications (Optional)

### Slack Integration
1. Install GitHub app in Slack workspace
2. Configure notifications for:
   - Failed deployments
   - Successful production deployments
   - Security alerts

### Email Notifications
Go to Settings → Notifications to configure email alerts for:
- Actions workflow failures
- Security advisories
- Dependency alerts

## Troubleshooting

### Common Issues

1. **"Secret not found" error**
   - Verify secret names match exactly (case-sensitive)
   - Check if secrets are set in the correct repository
   - Ensure environment names match workflow configuration

2. **Docker push fails**
   - Verify DOCKERHUB_USERNAME and DOCKERHUB_TOKEN
   - Check Docker Hub repository exists and is accessible
   - Ensure token has push permissions

3. **Kubernetes deployment fails**
   - Verify KUBE_CONFIG is properly base64 encoded
   - Check if cluster is accessible
   - Verify namespace permissions

4. **Environment not found**
   - Ensure environment names in workflow match GitHub settings
   - Check if environments are created in repository settings

### Validation Commands

```bash
# Test Docker credentials locally
echo $DOCKERHUB_TOKEN | docker login --username $DOCKERHUB_USERNAME --password-stdin

# Test Kubernetes config
kubectl --kubeconfig=<(echo $KUBE_CONFIG | base64 -d) get nodes

# Test database connection
psql $DATABASE_URL -c "SELECT 1"

# Test Redis connection
redis-cli -u $REDIS_URL ping
```

## Next Steps

After setup is complete:

1. **Monitor first deployment** in Actions tab
2. **Verify application** is accessible at configured domain
3. **Set up monitoring** dashboards and alerts
4. **Configure log aggregation** if using external logging
5. **Schedule regular security scans** and dependency updates

## Security Best Practices

1. **Rotate secrets regularly** (quarterly recommended)
2. **Use least-privilege access** for service accounts
3. **Enable branch protection** rules
4. **Monitor failed login attempts** and unusual activity
5. **Keep dependencies updated** with Dependabot
6. **Review access logs** regularly

---

**Need Help?**
- GitHub Actions Documentation: https://docs.github.com/en/actions
- Kubernetes Documentation: https://kubernetes.io/docs/
- Docker Documentation: https://docs.docker.com/
