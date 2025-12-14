# Installation Guide

Complete guide for installing and configuring the Agent Service in different environments.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker Setup](#docker-setup)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Configuration Reference](#configuration-reference)

---

## Local Development Setup

### Prerequisites

- Python 3.12 or higher
- PostgreSQL 16 (optional, can use Docker)
- Redis 7 (optional, can use Docker)
- Git

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd agents_boiler_plate
```

### Step 2: Install Python Dependencies

Using uv (recommended):
```bash
# Install uv
pip install uv

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

Using pip:
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements/base.txt
pip install -r requirements/dev.txt  # For development
```

### Step 3: Start Infrastructure Services

**Option A: Use Docker for PostgreSQL and Redis**
```bash
# Start only PostgreSQL and Redis
docker-compose -f docker/docker-compose.yml up -d postgres redis

# Verify they're running
docker-compose -f docker/docker-compose.yml ps
```

**Option B: Install Locally**

PostgreSQL:
```bash
# macOS with Homebrew
brew install postgresql@16
brew services start postgresql@16

# Ubuntu/Debian
sudo apt-get install postgresql-16
sudo systemctl start postgresql

# Create database
psql -U postgres -c "CREATE DATABASE agent_db;"
```

Redis:
```bash
# macOS with Homebrew
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server
```

### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

Minimum required configuration for local development:
```bash
# .env
ENVIRONMENT=local
DEBUG=true
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agent_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-local-secret-key-min-32-characters
```

### Step 5: Run Database Migrations

```bash
# Run migrations
alembic upgrade head

# Verify migration
alembic current
```

### Step 6: Start the API Server

```bash
# Development mode with auto-reload
uvicorn agent_service.main:app --reload --host 0.0.0.0 --port 8000

# Or using the script
python -m agent_service.main
```

### Step 7: Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs  # macOS
# or visit http://localhost:8000/docs in your browser
```

### Step 8: Start Celery Workers (Optional)

If you need background task processing:

```bash
# In a new terminal, start worker
celery -A agent_service.workers.celery_app worker --loglevel=info

# In another terminal, start beat scheduler
celery -A agent_service.workers.celery_app beat --loglevel=info
```

---

## Docker Setup

### Prerequisites

- Docker 24.0 or higher
- Docker Compose 2.0 or higher

### Quick Start

```bash
# Clone repository
git clone <your-repo-url>
cd agents_boiler_plate

# Copy and configure environment
cp .env.example .env

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Check status
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f api
```

### Services Included

- **api**: FastAPI application (port 8000)
- **worker**: Celery worker for background tasks
- **beat**: Celery beat scheduler
- **postgres**: PostgreSQL database (port 5432)
- **redis**: Redis cache/broker (port 6379)
- **prometheus**: Metrics collection (port 9090)
- **grafana**: Metrics visualization (port 3000)

### Custom Docker Build

```bash
# Build production image
docker build -f docker/Dockerfile -t agent-service:latest --target prod .

# Build development image
docker build -f docker/Dockerfile -t agent-service:dev --target dev .

# Build worker image
docker build -f docker/Dockerfile.worker -t agent-service-worker:latest --target worker .

# Run production container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379/0 \
  agent-service:latest
```

### Docker Compose Customization

Create `docker-compose.override.yml` for local customizations:

```yaml
# docker-compose.override.yml
version: "3.9"

services:
  api:
    ports:
      - "8001:8000"  # Use different port
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./custom-config:/app/config
```

Then run:
```bash
docker-compose -f docker/docker-compose.yml -f docker-compose.override.yml up -d
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Container registry access
- Helm 3 (optional, for Helm deployment)

### Step 1: Build and Push Images

```bash
# Set your registry
export REGISTRY=your-registry.com
export VERSION=v1.0.0

# Build and push API image
docker build -f docker/Dockerfile -t $REGISTRY/agent-service:$VERSION --target prod .
docker push $REGISTRY/agent-service:$VERSION

# Build and push worker image
docker build -f docker/Dockerfile.worker -t $REGISTRY/agent-service-worker:$VERSION --target worker .
docker push $REGISTRY/agent-service-worker:$VERSION
```

### Step 2: Create Namespace

```bash
kubectl create namespace agent-service
```

### Step 3: Configure Secrets

```bash
# Create secrets for sensitive data
kubectl create secret generic agent-service-secrets \
  --from-literal=DATABASE_URL='postgresql://user:password@postgres:5432/agent_db' \
  --from-literal=SECRET_KEY='your-production-secret-key-min-32-chars' \
  --from-literal=OPENAI_API_KEY='sk-your-api-key' \
  --from-literal=REDIS_URL='redis://redis:6379/0' \
  -n agent-service

# For Azure AD authentication
kubectl create secret generic auth-secrets \
  --from-literal=AZURE_CLIENT_SECRET='your-azure-client-secret' \
  --from-literal=AWS_COGNITO_CLIENT_SECRET='your-cognito-secret' \
  -n agent-service
```

### Step 4: Update ConfigMap

Edit `k8s/configmap.yaml` with your configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-service-config
  namespace: agent-service
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  AUTH_PROVIDER: "azure_ad"
  AZURE_TENANT_ID: "your-tenant-id"
  AZURE_CLIENT_ID: "your-client-id"
  # Add other non-sensitive config
```

### Step 5: Deploy with kubectl

```bash
# Update image references in k8s/deployment.yaml and k8s/worker-deployment.yaml
# Replace 'your-registry/agent-service:latest' with your actual image

# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/ingress.yaml

# Verify deployment
kubectl get all -n agent-service

# Check pod status
kubectl get pods -n agent-service

# View logs
kubectl logs -f deployment/agent-service-api -n agent-service
```

### Step 6: Deploy with Helm (Alternative)

```bash
# Install with Helm
helm install agent-service ./helm/agent-service \
  --namespace agent-service \
  --create-namespace \
  --values helm/agent-service/values.yaml \
  --set image.tag=$VERSION

# Upgrade deployment
helm upgrade agent-service ./helm/agent-service \
  --namespace agent-service \
  --values helm/agent-service/values.yaml

# View status
helm status agent-service -n agent-service

# Uninstall
helm uninstall agent-service -n agent-service
```

### Step 7: Configure Ingress

Update `k8s/ingress.yaml` or Helm values with your domain:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agent-service-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: agent-service-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: agent-service
            port:
              number: 8000
```

Apply:
```bash
kubectl apply -f k8s/ingress.yaml
```

### Step 8: Verify Deployment

```bash
# Check all resources
kubectl get all -n agent-service

# Check pod health
kubectl get pods -n agent-service
kubectl describe pod <pod-name> -n agent-service

# Check logs
kubectl logs -f deployment/agent-service-api -n agent-service

# Test health endpoint
kubectl port-forward -n agent-service svc/agent-service 8000:8000
curl http://localhost:8000/health

# Or test via ingress (if configured)
curl https://api.yourdomain.com/health
```

### Monitoring Setup

Deploy Prometheus and Grafana:

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Import dashboards from monitoring/grafana/dashboards/
```

---

## Configuration Reference

### Environment Variables

#### Application Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | No | "Agent Service" | Application name |
| `ENVIRONMENT` | Yes | - | Environment: local, development, staging, production |
| `DEBUG` | No | false | Enable debug mode |
| `HOST` | No | 0.0.0.0 | Server host |
| `PORT` | No | 8000 | Server port |
| `LOG_LEVEL` | No | INFO | Logging level: DEBUG, INFO, WARNING, ERROR |

#### Database Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `DB_POOL_SIZE` | No | 20 | Database connection pool size |
| `DB_MAX_OVERFLOW` | No | 10 | Max overflow connections |

#### Redis Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | - | Redis connection string |
| `REDIS_MAX_CONNECTIONS` | No | 50 | Max Redis connections |

#### Authentication Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_PROVIDER` | Yes | none | Auth provider: azure_ad, aws_cognito, none |
| `SECRET_KEY` | Yes | - | Secret key for JWT signing (min 32 chars) |
| `AZURE_TENANT_ID` | If Azure | - | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | If Azure | - | Azure AD client ID |
| `AZURE_CLIENT_SECRET` | If Azure | - | Azure AD client secret |
| `AWS_REGION` | If Cognito | - | AWS region |
| `AWS_COGNITO_USER_POOL_ID` | If Cognito | - | Cognito user pool ID |
| `AWS_COGNITO_CLIENT_ID` | If Cognito | - | Cognito client ID |

#### Feature Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENABLE_MCP` | No | true | Enable MCP protocol |
| `ENABLE_A2A` | No | true | Enable Agent-to-Agent protocol |
| `ENABLE_AGUI` | No | true | Enable AG-UI protocol |

#### Observability Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | No | - | Sentry DSN for error tracking |
| `OTLP_ENDPOINT` | No | - | OpenTelemetry endpoint |
| `ENABLE_METRICS` | No | true | Enable Prometheus metrics |

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current version
alembic current

# View migration history
alembic history
```

### Health Checks

The service exposes health check endpoints:

- `/health` - Overall health status
- `/health/live` - Liveness probe (for K8s)
- `/health/ready` - Readiness probe (for K8s)

### Security Considerations

1. **Secrets Management**: Never commit secrets to version control
2. **Use strong SECRET_KEY**: Minimum 32 characters, cryptographically random
3. **Enable HTTPS**: Always use TLS in production
4. **Database Credentials**: Use strong passwords, rotate regularly
5. **API Keys**: Store in Kubernetes secrets or cloud secret managers
6. **CORS**: Configure `CORS_ORIGINS` appropriately for your frontend
7. **Rate Limiting**: Configure rate limits in production

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure strong `SECRET_KEY`
- [ ] Use managed database (RDS, Cloud SQL, etc.)
- [ ] Use managed Redis (ElastiCache, MemoryStore, etc.)
- [ ] Configure authentication provider
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS origins
- [ ] Enable rate limiting
- [ ] Set up monitoring (Sentry, Prometheus, Grafana)
- [ ] Configure log aggregation
- [ ] Set resource limits (CPU, memory)
- [ ] Configure auto-scaling
- [ ] Set up backup strategy
- [ ] Configure alerting
- [ ] Review security settings
- [ ] Test disaster recovery

## Troubleshooting

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql $DATABASE_URL -c "SELECT version();"

# Check if database exists
psql $DATABASE_URL -c "\l"

# Check migrations
alembic current
```

### Redis Connection Issues

```bash
# Test Redis connection
redis-cli -u $REDIS_URL ping

# Check Redis info
redis-cli -u $REDIS_URL info
```

### Container Issues

```bash
# Check container logs
docker logs <container-id>

# Enter container for debugging
docker exec -it <container-id> /bin/bash

# Check container resource usage
docker stats
```

### Kubernetes Issues

```bash
# Check pod events
kubectl describe pod <pod-name> -n agent-service

# Check logs
kubectl logs <pod-name> -n agent-service --previous

# Check resource usage
kubectl top pods -n agent-service

# Debug with ephemeral container
kubectl debug -it <pod-name> -n agent-service --image=busybox
```

## Next Steps

- [Quick Start Guide](./quickstart.md) - Get running quickly
- [Build Your First Agent](./first-agent.md) - Create custom agents
- [Authentication Guide](./api/authentication.md) - Set up auth
- [API Reference](./api/agents.md) - Full API documentation
