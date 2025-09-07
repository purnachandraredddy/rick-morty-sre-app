# Deployment Guide

This guide covers deploying the Rick and Morty SRE Application to various environments.

## Prerequisites

- Docker
- Kubernetes cluster (1.20+)
- Helm 3.x
- kubectl configured for your cluster
- Access to container registry

## Quick Start

### Local Development with Docker Compose

```bash
# Clone the repository
git clone <repository-url>
cd rick-morty-sre-app

# Start services
docker-compose up -d

# Check status
curl http://localhost:8000/healthcheck
```

### Kubernetes Deployment with Helm

```bash
# Add required Helm repositories (if using external dependencies)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Deploy to development
helm install rick-morty-dev ./helm/rick-morty-app \
  --namespace rick-morty-dev --create-namespace \
  --set postgresql.enabled=true \
  --set redis.enabled=true

# Check deployment
kubectl get pods -n rick-morty-dev
```

## Environment-Specific Deployments

### Development Environment

```bash
# Using the deployment script
export ENVIRONMENT=development
export IMAGE_TAG=latest
./scripts/deploy.sh

# Or manually with Helm
helm install rick-morty-dev ./helm/rick-morty-app \
  --namespace rick-morty-dev --create-namespace \
  --values ./helm/rick-morty-app/values-dev.yaml \
  --set image.tag=latest
```

### Staging Environment

```bash
# Using the deployment script
export ENVIRONMENT=staging
export IMAGE_TAG=v1.0.0
./scripts/deploy.sh

# Or manually with Helm
helm install rick-morty-staging ./helm/rick-morty-app \
  --namespace rick-morty-staging --create-namespace \
  --values ./helm/rick-morty-app/values-staging.yaml \
  --set image.tag=v1.0.0
```

### Production Environment

```bash
# Using the deployment script
export ENVIRONMENT=production
export IMAGE_TAG=v1.0.0
./scripts/deploy.sh

# Or manually with Helm
helm install rick-morty-prod ./helm/rick-morty-app \
  --namespace rick-morty-prod --create-namespace \
  --values ./helm/rick-morty-app/values-prod.yaml \
  --set image.tag=v1.0.0 \
  --set secrets.databaseUrl="$DATABASE_URL" \
  --set secrets.redisUrl="$REDIS_URL"
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | See config.py | Yes |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` | Yes |
| `RICK_MORTY_API_URL` | Rick and Morty API base URL | `https://rickandmortyapi.com/api` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `JAEGER_ENDPOINT` | Jaeger tracing endpoint | None | No |

### Helm Values

Key configuration options in `values.yaml`:

```yaml
# Image configuration
image:
  repository: rickmorty/sre-app
  tag: latest
  pullPolicy: Always

# Resource limits
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

# Autoscaling
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

# Database (PostgreSQL)
postgresql:
  enabled: true  # Set to false for external database
  auth:
    database: rickmorty
    username: postgres
    password: postgres

# Cache (Redis)
redis:
  enabled: true  # Set to false for external Redis
  auth:
    enabled: false
```

## Secrets Management

### Kubernetes Secrets

For production deployments, use Kubernetes secrets:

```bash
# Create database secret
kubectl create secret generic rick-morty-db \
  --from-literal=url="postgresql+asyncpg://user:pass@host:5432/db" \
  -n rick-morty-prod

# Create Redis secret
kubectl create secret generic rick-morty-cache \
  --from-literal=url="redis://host:6379/0" \
  -n rick-morty-prod

# Update Helm values to reference secrets
helm upgrade rick-morty-prod ./helm/rick-morty-app \
  --namespace rick-morty-prod \
  --set secrets.databaseUrl="$DATABASE_URL" \
  --set secrets.redisUrl="$REDIS_URL"
```

### External Secret Management

For integration with external secret managers (AWS Secrets Manager, HashiCorp Vault, etc.), use the External Secrets Operator:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: rick-morty-prod
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "rick-morty-app"
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: rick-morty-secrets
  namespace: rick-morty-prod
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: rick-morty-app-secrets
  data:
  - secretKey: database-url
    remoteRef:
      key: rick-morty/database
      property: url
  - secretKey: redis-url
    remoteRef:
      key: rick-morty/cache
      property: url
```

## Database Setup

### Using Built-in PostgreSQL

The Helm chart includes PostgreSQL by default:

```yaml
postgresql:
  enabled: true
  auth:
    database: rickmorty
    username: postgres
    password: postgres
  primary:
    persistence:
      enabled: true
      size: 8Gi
```

### Using External Database

For production, use an external managed database:

```yaml
postgresql:
  enabled: false

secrets:
  databaseUrl: "postgresql+asyncpg://user:pass@rds-host:5432/rickmorty"
```

### Database Migrations

The application automatically creates tables on startup. For production deployments with schema changes, consider using Alembic:

```bash
# Generate migration
alembic revision --autogenerate -m "Add new field"

# Apply migration
alembic upgrade head
```

## Monitoring Setup

### Prometheus

Deploy Prometheus to scrape metrics:

```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    scrape_configs:
    - job_name: 'rick-morty-app'
      kubernetes_sd_configs:
      - role: endpoints
        namespaces:
          names:
          - rick-morty-prod
      relabel_configs:
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
```

### Grafana Dashboard

Import the dashboard from `monitoring/grafana-dashboard.json`:

```bash
# Using Grafana CLI
grafana-cli admin import-dashboard monitoring/grafana-dashboard.json

# Or via API
curl -X POST \
  http://grafana.example.com/api/dashboards/db \
  -H 'Authorization: Bearer <api-key>' \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana-dashboard.json
```

### Alerting

Deploy alerting rules:

```bash
kubectl apply -f monitoring/alerts.yml
```

## Troubleshooting

### Common Issues

1. **Pod Crash Loop**
   ```bash
   # Check pod logs
   kubectl logs -f deployment/rick-morty-app -n rick-morty-prod
   
   # Check events
   kubectl describe pod <pod-name> -n rick-morty-prod
   ```

2. **Database Connection Issues**
   ```bash
   # Test database connectivity
   kubectl run -it --rm debug --image=postgres:15 --restart=Never -- psql $DATABASE_URL
   
   # Check database pod logs
   kubectl logs -f deployment/rick-morty-app-postgresql -n rick-morty-prod
   ```

3. **High Memory Usage**
   ```bash
   # Check resource usage
   kubectl top pods -n rick-morty-prod
   
   # Increase memory limits
   helm upgrade rick-morty-prod ./helm/rick-morty-app \
     --set resources.limits.memory=1Gi
   ```

4. **Ingress Issues**
   ```bash
   # Check ingress status
   kubectl describe ingress rick-morty-app -n rick-morty-prod
   
   # Check ingress controller logs
   kubectl logs -f deployment/nginx-ingress-controller -n ingress-nginx
   ```

### Health Checks

```bash
# Application health
curl https://rick-morty-api.example.com/healthcheck

# Kubernetes health
kubectl get pods -n rick-morty-prod
kubectl get services -n rick-morty-prod
kubectl get ingress -n rick-morty-prod

# Database health
kubectl exec -it deployment/rick-morty-app-postgresql -n rick-morty-prod -- psql -U postgres -c "SELECT 1"

# Cache health
kubectl exec -it deployment/rick-morty-app-redis-master -n rick-morty-prod -- redis-cli ping
```

## Scaling

### Horizontal Pod Autoscaler

HPA is enabled by default:

```yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### Manual Scaling

```bash
# Scale deployment
kubectl scale deployment rick-morty-app --replicas=5 -n rick-morty-prod

# Or using Helm
helm upgrade rick-morty-prod ./helm/rick-morty-app \
  --set replicaCount=5
```

### Cluster Autoscaling

Ensure your cluster has cluster autoscaler configured for automatic node scaling.

## Backup and Recovery

### Database Backup

```bash
# Create backup
kubectl exec deployment/rick-morty-app-postgresql -n rick-morty-prod -- \
  pg_dump -U postgres rickmorty > backup.sql

# Restore backup
kubectl exec -i deployment/rick-morty-app-postgresql -n rick-morty-prod -- \
  psql -U postgres rickmorty < backup.sql
```

### Application State

The application is stateless except for the database. Ensure database backups are automated.

## Security Considerations

1. **Use non-root containers** (implemented in Dockerfile)
2. **Read-only root filesystem** (configured in deployment)
3. **Resource limits** (configured in values.yaml)
4. **Network policies** (implement as needed)
5. **Pod Security Standards** (configure in namespace)
6. **Secret management** (use external secret managers)

## Performance Tuning

### Database Optimization

```sql
-- Add indexes for better performance
CREATE INDEX CONCURRENTLY idx_characters_species ON characters(species);
CREATE INDEX CONCURRENTLY idx_characters_status ON characters(status);
CREATE INDEX CONCURRENTLY idx_characters_origin_name ON characters(origin_name);
```

### Cache Optimization

```yaml
config:
  cacheTtl: 3600  # 1 hour
  cachePrefix: "rickmorty:"
```

### Resource Optimization

```yaml
resources:
  requests:
    cpu: 100m      # Adjust based on load
    memory: 128Mi  # Adjust based on usage
  limits:
    cpu: 500m      # Adjust based on requirements
    memory: 512Mi  # Adjust based on usage
```

## CI/CD Integration

The application includes GitHub Actions workflows for automated deployment. See `.github/workflows/ci-cd.yml` for the complete pipeline.

### Manual Deployment

```bash
# Build and push image
docker build -t rickmorty/sre-app:v1.0.0 .
docker push rickmorty/sre-app:v1.0.0

# Deploy
export IMAGE_TAG=v1.0.0
./scripts/deploy.sh
```

## Support

For deployment issues:

1. Check the troubleshooting section above
2. Review application logs
3. Check Kubernetes events
4. Contact the SRE team
