# Production Deployment Guide

## T-1001-T-1035: Production Deployment

This guide covers deploying EDGP to production using Docker and Kubernetes.

### Prerequisites

- Docker & Docker Compose
- Kubernetes cluster (1.24+)
- kubectl configured
- helm (optional)
- AWS S3 or Azure Blob Storage for production
- PostgreSQL 16+ database
- Redis 7+ cache

### Option 1: Docker Compose Deployment

#### Quick Start

```bash
# Clone repository
git clone https://github.com/manishjnv/DocumentGovernancePlatform.git
cd DocumentGovernancePlatform

# Create production environment file
cp .env.production .env

# Edit secrets
vim .env
# Set: DB_PASSWORD, REDIS_PASSWORD, SECRET_KEY, ANTHROPIC_API_KEY, etc.

# Build and start
docker-compose -f docker-compose.prod.yml up -d

# Verify
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f api
```

#### Access Application

```
Web:  http://localhost:3000
API:  http://localhost:8000
Docs: http://localhost:8000/docs
```

#### Scaling

```bash
# Scale API service
docker-compose -f docker-compose.prod.yml up -d --scale api=5
```

---

### Option 2: Kubernetes Deployment

#### Prerequisites Setup

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Create secrets
kubectl create secret generic edgp-db-secret \
  --from-literal=connection-string="postgresql+asyncpg://edgp_user:PASSWORD@postgres:5432/edgp_prod" \
  -n edgp-prod

kubectl create secret generic edgp-redis-secret \
  --from-literal=connection-string="redis://:PASSWORD@redis:6379/0" \
  -n edgp-prod

kubectl create secret generic edgp-api-keys \
  --from-literal=anthropic-key="sk-ant-..." \
  -n edgp-prod

kubectl create secret generic edgp-app-secret \
  --from-literal=secret-key="your-secret-key-here" \
  -n edgp-prod

# 3. Create namespace and apply configs
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
```

#### Deploy EDGP

```bash
# Deploy all components
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/web-deployment.yaml
kubectl apply -f k8s/nginx-ingress.yaml

# Verify deployment
kubectl get pods -n edgp-prod
kubectl get svc -n edgp-prod

# Watch rollout
kubectl rollout status deployment/edgp-api -n edgp-prod
```

#### Check Logs

```bash
# API logs
kubectl logs -n edgp-prod -l app=edgp-api -f

# Database logs
kubectl logs -n edgp-prod -l app=postgres -f

# Redis logs
kubectl logs -n edgp-prod -l app=redis -f
```

#### Port Forwarding (for debugging)

```bash
# Access API
kubectl port-forward -n edgp-prod svc/edgp-api 8000:8000

# Access Web
kubectl port-forward -n edgp-prod svc/edgp-web 3000:3000

# Access Database
kubectl port-forward -n edgp-prod svc/postgres 5432:5432
```

---

### Security Considerations

#### 1. Secrets Management

**❌ DON'T:**
```bash
# Don't commit secrets
git add .env
echo "SECRET_KEY=123456" >> .env
```

**✅ DO:**
```bash
# Use secure secret management
# AWS Secrets Manager
# HashiCorp Vault
# Kubernetes Secrets
# GitHub Actions Secrets

# For local dev only:
cp .env.example .env
# Edit with actual secrets
chmod 600 .env
echo ".env" >> .gitignore
```

#### 2. TLS/SSL Configuration

```bash
# Generate self-signed cert (for testing)
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Production: Use Let's Encrypt
# Kubernetes: Use cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

#### 3. Network Policies

```bash
# Apply K8s network policies
kubectl apply -f k8s/network-policies.yaml
```

---

### Monitoring & Logging

#### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
kubectl exec -n edgp-prod postgres-0 -- pg_isready

# Redis health
kubectl exec -n edgp-prod redis-0 -- redis-cli ping
```

#### Logging Aggregation

```bash
# View structured logs
kubectl logs -n edgp-prod deployment/edgp-api --timestamps=true
```

#### Metrics

```bash
# Install Prometheus (optional)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring

# View API metrics
curl http://localhost:8000/metrics
```

---

### Backup & Recovery

#### Database Backup

```bash
# Backup PostgreSQL
kubectl exec -n edgp-prod postgres-0 -- pg_dump -U edgp_user edgp_prod > backup.sql

# Restore
kubectl exec -n edgp-prod postgres-0 -- psql -U edgp_user edgp_prod < backup.sql
```

#### Redis Backup

```bash
# Manual backup
kubectl exec -n edgp-prod redis-0 -- redis-cli BGSAVE

# Copy snapshot
kubectl cp edgp-prod/redis-0:/data/dump.rdb ./redis-backup.rdb
```

---

### CI/CD Pipeline

EDGP includes GitHub Actions workflow (`.github/workflows/ci-cd.yml`) that:

1. **Tests** on every push
2. **Builds** Docker images
3. **Pushes** to container registry
4. **Deploys** to Kubernetes (main branch only)
5. **Runs smoke tests**
6. **Scans security** with Trivy

#### Setup CI/CD

```bash
# 1. Set GitHub secrets
# Settings → Secrets and variables → Actions

KUBECONFIG=<base64-encoded-kubeconfig>
API_URL=https://api.edgp.example.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
REGISTRY=ghcr.io
```

---

### Troubleshooting

#### Pod not starting

```bash
kubectl describe pod edgp-api-xxx -n edgp-prod
kubectl logs edgp-api-xxx -n edgp-prod
```

#### Database connection issues

```bash
# Test database connection
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n edgp-prod -- \
  psql -h postgres -U edgp_user -d edgp_prod -c "SELECT 1;"
```

#### Memory/CPU issues

```bash
# Check resource usage
kubectl top pods -n edgp-prod
kubectl top nodes

# Increase limits in deployment
kubectl set resources deployment edgp-api -n edgp-prod \
  --limits=cpu=2000m,memory=2Gi \
  --requests=cpu=500m,memory=512Mi
```

---

### Performance Tuning

1. **Database**: Increase `max_connections`, tune shared_buffers
2. **Redis**: Increase `maxmemory`, optimize eviction policy
3. **API**: Increase worker processes, tune connection pools
4. **Nginx**: Enable caching, optimize worker connections

---

### Disaster Recovery Plan

1. **RTO** (Recovery Time Objective): < 1 hour
2. **RPO** (Recovery Point Objective): < 15 minutes

- Daily database backups to S3
- Point-in-time recovery capability
- Multi-region deployment (optional)

---

### Support

For issues or questions:
- GitHub Issues: https://github.com/manishjnv/DocumentGovernancePlatform/issues
- Email: support@example.com
