# Agent Service Deployment Guide

This guide covers deployment of the Agent Service using Docker and Kubernetes.

## Overview

The Agent Service can be deployed using:
1. **Docker Compose** - For local development and testing
2. **Kubernetes** - For production deployment

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Load Balancer                        │
│                      (Ingress/ALB)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Service (3+ pods)                  │
│  - FastAPI application                                      │
│  - Auto-scaling: 2-10 replicas                             │
│  - Health checks & probes                                   │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
      │  PostgreSQL │  │    Redis    │  │   Celery    │
      │  Database   │  │    Cache    │  │   Workers   │
      │             │  │             │  │  (2-10 pods)│
      └─────────────┘  └─────────────┘  └─────────────┘
                                                │
                                         ┌──────────────┐
                                         │ Celery Beat  │
                                         │  Scheduler   │
                                         │   (1 pod)    │
                                         └──────────────┘
```

## Quick Start

### Option 1: Docker Compose (Development)

```bash
# Start all services
cd /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate
docker-compose -f docker/docker-compose.yml up -d

# Access the API
curl http://localhost:8000/health

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Access monitoring
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### Option 2: Kubernetes (Production)

```bash
# 1. Build and push images
docker build -f docker/Dockerfile -t your-registry/agent-service:v1.0.0 --target prod .
docker push your-registry/agent-service:v1.0.0

docker build -f docker/Dockerfile.worker -t your-registry/agent-service-worker:v1.0.0 --target worker .
docker push your-registry/agent-service-worker:v1.0.0

# 2. Update image references in k8s manifests

# 3. Configure secrets (DO NOT use template values!)
kubectl create secret generic agent-service-secrets \
  --from-literal=DATABASE_PASSWORD='your-secure-password' \
  --from-literal=SECRET_KEY='your-secret-key-min-32-chars' \
  --from-literal=OPENAI_API_KEY='sk-your-key' \
  -n agent-service

# 4. Deploy to Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/ingress.yaml

# 5. Verify deployment
kubectl get all -n agent-service
kubectl logs -f deployment/agent-service-api -n agent-service
```

## File Structure

```
/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/
├── docker/
│   ├── Dockerfile                 # Main API Dockerfile (enhanced)
│   ├── Dockerfile.worker          # Celery worker Dockerfile
│   ├── docker-compose.yml         # Complete dev environment
│   └── README.md                  # Docker documentation
├── k8s/
│   ├── namespace.yaml             # Kubernetes namespace
│   ├── deployment.yaml            # API deployment
│   ├── worker-deployment.yaml     # Worker & beat deployments
│   ├── service.yaml               # ClusterIP service
│   ├── ingress.yaml               # Ingress with TLS
│   ├── configmap.yaml             # Application configuration
│   ├── secret.yaml                # Secrets template
│   ├── serviceaccount.yaml        # RBAC configuration
│   ├── hpa.yaml                   # Horizontal Pod Autoscaler
│   ├── pdb.yaml                   # Pod Disruption Budget
│   └── README.md                  # K8s documentation
└── monitoring/
    ├── prometheus.yml             # Prometheus config
    └── grafana/
        ├── datasources/
        │   └── prometheus.yml     # Grafana datasource
        └── dashboards/
            └── dashboard.yml      # Dashboard provisioning
```

## Docker Enhancements

### Main Dockerfile (`docker/Dockerfile`)

**New Features:**
- Multi-stage build with builder pattern
- Health check instruction (`HEALTHCHECK`)
- Security labels for image scanning
- Production stage uses python:3.11-slim
- Non-root user (UID 1001)
- Read-only root filesystem ready
- Optimized layer caching

**Key Improvements:**
```dockerfile
# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Security labels
LABEL security.scan.enabled="true" \
      security.scan.level="production"

# Non-root user
RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -s /bin/false -d /app appuser
USER appuser
```

### Worker Dockerfile (`docker/Dockerfile.worker`)

**Features:**
- Separate image for Celery workers
- Multi-target: worker and beat
- Same security practices as main Dockerfile
- Optimized for background task processing

### Docker Compose (`docker/docker-compose.yml`)

**New Features:**
- Resource limits (CPU, memory)
- Restart policies (unless-stopped)
- Health checks for all services
- Celery worker service (2 replicas)
- Celery beat service (scheduler)
- Prometheus monitoring
- Grafana dashboards
- Dedicated network (agent-network)

**Services:**
1. **api** - FastAPI application (2 CPU, 2GB)
2. **worker** - Celery workers x2 (2 CPU, 2GB each)
3. **beat** - Celery beat scheduler (0.5 CPU, 512MB)
4. **postgres** - PostgreSQL 16 (1 CPU, 1GB)
5. **redis** - Redis 7 with persistence (0.5 CPU, 512MB)
6. **prometheus** - Metrics collection (1 CPU, 1GB)
7. **grafana** - Dashboards (0.5 CPU, 512MB)

## Kubernetes Manifests

### Core Components

**namespace.yaml**
- Creates `agent-service` namespace
- Labels for organization and governance

**deployment.yaml**
- 3 replicas with rolling updates
- Startup, liveness, and readiness probes
- Security context (non-root, read-only filesystem)
- Resource limits and requests
- Anti-affinity rules for HA
- Init containers for dependency checks

**service.yaml**
- ClusterIP service
- Exposes port 80 (maps to container 8000)
- Metrics port for Prometheus

**ingress.yaml**
- NGINX ingress with TLS
- Rate limiting (100 RPS, 50 connections)
- CORS configuration
- Security headers
- Cert-manager integration
- Separate admin ingress with IP whitelist

### Configuration

**configmap.yaml**
- Non-sensitive configuration
- Database/Redis hosts
- Feature flags
- Observability settings

**secret.yaml**
- Template for secrets (replace values!)
- Database credentials
- API keys
- OAuth credentials
- Examples for External Secrets Operator

### Autoscaling & Availability

**hpa.yaml**
- API: 2-10 replicas
- Worker: 2-10 replicas
- CPU target: 70% (API), 75% (worker)
- Memory target: 80%
- Smart scaling behavior

**pdb.yaml**
- API: minimum 1 pod available
- Worker: maximum 50% unavailable
- Ensures availability during updates

### Workers

**worker-deployment.yaml**
- Celery worker deployment (3 replicas)
- Celery beat deployment (1 replica)
- Security hardening
- Resource limits
- Init containers for Redis check

### RBAC

**serviceaccount.yaml**
- Service account for pods
- Role for accessing ConfigMaps/Secrets
- RoleBinding

## Security Features

### Container Security

1. **Non-root Execution**
   - All containers run as UID 1001
   - Dedicated users (appuser, celeryuser)

2. **Security Context**
   ```yaml
   securityContext:
     runAsNonRoot: true
     runAsUser: 1001
     allowPrivilegeEscalation: false
     capabilities:
       drop: [ALL]
     readOnlyRootFilesystem: true
     seccompProfile:
       type: RuntimeDefault
   ```

3. **Image Security**
   - Slim base images
   - Security scanning labels
   - Regular updates
   - No secrets in images

4. **Network Security**
   - Ingress rate limiting
   - CORS configuration
   - IP whitelisting for admin
   - Security headers

### Secrets Management

**Development:**
```bash
# Use .env file (git-ignored)
cp .env.example .env
```

**Production:**
```bash
# Option 1: Manual secrets
kubectl create secret generic agent-service-secrets \
  --from-literal=DATABASE_PASSWORD='xxx' \
  -n agent-service

# Option 2: External Secrets Operator (recommended)
# See k8s/secret.yaml for examples

# Option 3: Sealed Secrets
kubeseal -f secret.yaml -o yaml > sealed-secret.yaml
```

## Monitoring & Observability

### Metrics (Prometheus)

**Available Metrics:**
- HTTP request rate, latency, errors
- CPU and memory usage
- Database connection pool
- Redis cache hit/miss rate
- Celery task metrics

**Access:**
- Docker Compose: http://localhost:9090
- Kubernetes: Port-forward or via Ingress

### Dashboards (Grafana)

**Pre-configured:**
- API performance dashboard
- Resource utilization
- Database metrics
- Redis metrics

**Access:**
- Docker Compose: http://localhost:3000 (admin/admin)
- Kubernetes: Port-forward or via Ingress

### Logging

**Docker Compose:**
```bash
docker-compose logs -f api
docker-compose logs -f worker
```

**Kubernetes:**
```bash
kubectl logs -f deployment/agent-service-api -n agent-service
kubectl logs -f deployment/agent-service-worker -n agent-service
```

### Health Checks

**API Endpoints:**
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check (includes dependencies)
- `GET /metrics` - Prometheus metrics

## Resource Requirements

### Minimum (Development)
- CPU: 4 cores
- Memory: 8GB
- Storage: 20GB

### Recommended (Production)
- CPU: 8+ cores
- Memory: 16GB+
- Storage: 100GB+ (for logs, database)

### Per-Service Resources

| Service    | CPU Request | CPU Limit | Memory Request | Memory Limit |
|------------|-------------|-----------|----------------|--------------|
| API        | 500m        | 2000m     | 512Mi          | 2Gi          |
| Worker     | 500m        | 2000m     | 512Mi          | 2Gi          |
| Beat       | 100m        | 500m      | 128Mi          | 512Mi        |
| PostgreSQL | 250m        | 1000m     | 256Mi          | 1Gi          |
| Redis      | 100m        | 500m      | 128Mi          | 512Mi        |

## Scaling

### Horizontal Scaling (Kubernetes)

**Automatic (HPA):**
- Based on CPU/memory utilization
- Min: 2 replicas
- Max: 10 replicas

**Manual:**
```bash
kubectl scale deployment agent-service-api --replicas=5 -n agent-service
kubectl scale deployment agent-service-worker --replicas=8 -n agent-service
```

### Vertical Scaling

**Adjust resources:**
```yaml
resources:
  requests:
    cpu: 1000m      # Increase CPU
    memory: 1Gi     # Increase memory
  limits:
    cpu: 4000m
    memory: 4Gi
```

## Troubleshooting

### Common Issues

**1. Pods not starting**
```bash
kubectl describe pod <pod-name> -n agent-service
kubectl logs <pod-name> -n agent-service
```

**2. Database connection failed**
```bash
# Check init container logs
kubectl logs <pod-name> -c wait-for-postgres -n agent-service

# Test connectivity
kubectl exec -it <pod-name> -n agent-service -- sh
pg_isready -h postgres-service -p 5432
```

**3. HPA not scaling**
```bash
# Check metrics server
kubectl top pods -n agent-service
kubectl top nodes

# Check HPA status
kubectl describe hpa agent-service-api-hpa -n agent-service
```

**4. Ingress not working**
```bash
# Check ingress
kubectl describe ingress agent-service-ingress -n agent-service

# Check cert-manager (for TLS)
kubectl get certificate -n agent-service
kubectl describe certificate agent-service-tls -n agent-service
```

## Production Checklist

Before deploying to production:

- [ ] Build and tag Docker images with version
- [ ] Push images to production registry
- [ ] Update image references in K8s manifests
- [ ] Configure production secrets (no template values!)
- [ ] Update ConfigMap with production settings
- [ ] Configure real domain names in Ingress
- [ ] Set up TLS certificates (cert-manager or manual)
- [ ] Configure monitoring alerts
- [ ] Set up log aggregation (ELK, Loki, etc.)
- [ ] Configure backup for PostgreSQL
- [ ] Test disaster recovery procedures
- [ ] Review and adjust resource limits
- [ ] Configure network policies (if required)
- [ ] Set up Pod Security Standards/Policies
- [ ] Document runbooks for common operations
- [ ] Train team on deployment procedures

## Maintenance

### Updates

**Rolling update:**
```bash
# Update image
kubectl set image deployment/agent-service-api \
  api=your-registry/agent-service:v1.1.0 -n agent-service

# Watch rollout
kubectl rollout status deployment/agent-service-api -n agent-service
```

**Rollback:**
```bash
kubectl rollout undo deployment/agent-service-api -n agent-service
```

### Backup

**Database:**
```bash
# Docker Compose
docker-compose exec postgres pg_dump -U postgres agent_db > backup.sql

# Kubernetes
kubectl exec -it postgres-pod -n agent-service -- \
  pg_dump -U postgres agent_db > backup.sql
```

### Monitoring

- Review metrics daily
- Set up alerts for critical metrics
- Monitor resource usage trends
- Plan capacity based on growth

## Support

For detailed documentation:
- Docker: See `docker/README.md`
- Kubernetes: See `k8s/README.md`

For issues:
- Check logs first
- Review health check endpoints
- Consult troubleshooting section
- Check resource utilization
