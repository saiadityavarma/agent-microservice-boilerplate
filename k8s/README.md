# Kubernetes Manifests for Agent Service

This directory contains production-ready Kubernetes manifests for deploying the AI Agent Service.

## Overview

The deployment includes:
- Main API deployment with health checks and auto-scaling
- Celery worker deployment for background tasks
- Celery beat scheduler for periodic tasks
- Horizontal Pod Autoscaler (HPA) for dynamic scaling
- Pod Disruption Budget (PDB) for high availability
- Ingress with TLS support
- ConfigMap for application configuration
- Secrets management (template)
- RBAC configuration

## Prerequisites

1. **Kubernetes Cluster** (v1.24+)
   - GKE, EKS, AKS, or self-managed cluster
   - Metrics Server installed for HPA

2. **Ingress Controller**
   - NGINX Ingress Controller, or
   - AWS ALB Controller, or
   - Other ingress controller

3. **Cert Manager** (for TLS certificates)
   ```bash
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

4. **Container Registry**
   - Docker Hub, GCR, ECR, ACR, or private registry
   - Images must be built and pushed before deployment

## Quick Start

### 1. Build and Push Docker Images

```bash
# Build API image
docker build -f docker/Dockerfile -t your-registry/agent-service:latest --target prod .
docker push your-registry/agent-service:latest

# Build worker image
docker build -f docker/Dockerfile.worker -t your-registry/agent-service-worker:latest --target worker .
docker push your-registry/agent-service-worker:latest
```

### 2. Update Image References

Edit the deployment files to use your registry:
- `k8s/deployment.yaml` - Update `image: agent-service:latest`
- `k8s/worker-deployment.yaml` - Update `image: agent-service-worker:latest`

### 3. Configure Secrets

**IMPORTANT**: Never commit actual secrets to version control!

Choose one of these methods:

#### Option A: Manual Secret Creation
```bash
kubectl create secret generic agent-service-secrets \
  --from-literal=DATABASE_PASSWORD='your-password' \
  --from-literal=SECRET_KEY='your-secret-key' \
  --from-literal=OPENAI_API_KEY='sk-...' \
  -n agent-service
```

#### Option B: External Secrets Operator (Recommended)
1. Install External Secrets Operator
2. Configure SecretStore (AWS Secrets Manager, Azure Key Vault, etc.)
3. Apply ExternalSecret manifest (see `secret.yaml` for examples)

#### Option C: Sealed Secrets
```bash
# Install Sealed Secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret
kubectl create secret generic agent-service-secrets \
  --from-literal=DATABASE_PASSWORD='xxx' \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

kubectl apply -f sealed-secret.yaml
```

### 4. Update ConfigMap

Edit `k8s/configmap.yaml` to match your environment:
- Database hosts
- Redis hosts
- CORS origins
- Domain names

### 5. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply RBAC
kubectl apply -f k8s/serviceaccount.yaml

# Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# Apply Secrets (or use external secrets)
kubectl apply -f k8s/secret.yaml  # Only if using template with replaced values

# Deploy applications
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml

# Create services
kubectl apply -f k8s/service.yaml

# Apply autoscaling
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml

# Configure ingress (update domains first!)
kubectl apply -f k8s/ingress.yaml
```

### 6. Verify Deployment

```bash
# Check namespace
kubectl get all -n agent-service

# Check pod status
kubectl get pods -n agent-service

# Check logs
kubectl logs -f deployment/agent-service-api -n agent-service
kubectl logs -f deployment/agent-service-worker -n agent-service

# Check HPA status
kubectl get hpa -n agent-service

# Check ingress
kubectl get ingress -n agent-service
kubectl describe ingress agent-service-ingress -n agent-service
```

## Configuration Details

### Resource Limits

**API Pods:**
- Requests: 500m CPU, 512Mi memory
- Limits: 2 CPU, 2Gi memory

**Worker Pods:**
- Requests: 500m CPU, 512Mi memory
- Limits: 2 CPU, 2Gi memory

**Beat Scheduler:**
- Requests: 100m CPU, 128Mi memory
- Limits: 500m CPU, 512Mi memory

### Autoscaling

**API HPA:**
- Min replicas: 2
- Max replicas: 10
- Target CPU: 70%
- Target Memory: 80%

**Worker HPA:**
- Min replicas: 2
- Max replicas: 10
- Target CPU: 75%
- Target Memory: 80%

### Security Features

1. **Non-root containers**: All containers run as UID 1001
2. **Read-only root filesystem**: Enhanced security
3. **Security context**: Drop all capabilities, seccomp profile
4. **Network policies**: (Add network-policy.yaml if needed)
5. **Pod security standards**: Restricted profile compatible

### Health Checks

**API:**
- Startup probe: `/health` (30 attempts, 5s intervals)
- Liveness probe: `/health` (every 10s)
- Readiness probe: `/health/ready` (every 5s)

**Workers:**
- Liveness probe: Celery inspect ping (every 30s)

## Updating Deployments

### Rolling Update
```bash
# Update image version
kubectl set image deployment/agent-service-api api=your-registry/agent-service:v1.1.0 -n agent-service

# Or apply updated manifest
kubectl apply -f k8s/deployment.yaml
```

### Rollback
```bash
# View rollout history
kubectl rollout history deployment/agent-service-api -n agent-service

# Rollback to previous version
kubectl rollout undo deployment/agent-service-api -n agent-service

# Rollback to specific revision
kubectl rollout undo deployment/agent-service-api --to-revision=2 -n agent-service
```

## Monitoring and Observability

### Prometheus Metrics

All pods expose metrics at `/metrics`:
- API: Port 8000
- Workers: Via Celery metrics exporter

### Logs

```bash
# Stream API logs
kubectl logs -f -l app=agent-service,component=api -n agent-service

# Stream worker logs
kubectl logs -f -l app=agent-service,component=worker -n agent-service

# Stream beat logs
kubectl logs -f -l app=agent-service,component=beat -n agent-service
```

### Port Forwarding (for testing)

```bash
# Forward API port
kubectl port-forward svc/agent-service-api 8000:80 -n agent-service

# Access at http://localhost:8000
```

## Troubleshooting

### Pods not starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n agent-service

# Check init container logs
kubectl logs <pod-name> -c wait-for-postgres -n agent-service
```

### Database connection issues

```bash
# Verify database service
kubectl get svc -n agent-service

# Test connectivity from pod
kubectl exec -it <pod-name> -n agent-service -- sh
# Inside pod:
pg_isready -h postgres-service -p 5432 -U agent_service
```

### HPA not scaling

```bash
# Check metrics server
kubectl top pods -n agent-service
kubectl top nodes

# Check HPA status
kubectl describe hpa agent-service-api-hpa -n agent-service
```

### TLS certificate issues

```bash
# Check cert-manager
kubectl get certificaterequest -n agent-service
kubectl get certificate -n agent-service
kubectl describe certificate agent-service-tls -n agent-service

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

## Production Checklist

- [ ] Docker images built and pushed to registry
- [ ] Secrets configured (not using template values)
- [ ] ConfigMap updated with correct hosts/domains
- [ ] Ingress updated with actual domain names
- [ ] TLS certificates configured
- [ ] Resource limits appropriate for workload
- [ ] HPA min/max replicas set correctly
- [ ] Monitoring and alerting configured
- [ ] Backup strategy for database
- [ ] Log aggregation configured
- [ ] Network policies defined (if required)
- [ ] Pod security policies/admission controller configured
- [ ] Disaster recovery plan documented

## Additional Resources

### Network Policy (Optional)

Create `network-policy.yaml` to restrict pod communication:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent-service-netpol
  namespace: agent-service
spec:
  podSelector:
    matchLabels:
      app: agent-service
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
        - podSelector:
            matchLabels:
              app: redis
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 443  # HTTPS for external APIs
        - protocol: TCP
          port: 53   # DNS
```

### Database Migration Job

Create a Kubernetes Job to run migrations:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: agent-service-migrate
  namespace: agent-service
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: your-registry/agent-service:latest
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - configMapRef:
                name: agent-service-config
            - secretRef:
                name: agent-service-secrets
      restartPolicy: Never
  backoffLimit: 3
```

## Support

For issues or questions:
- Check logs: `kubectl logs -n agent-service <pod-name>`
- Review events: `kubectl get events -n agent-service --sort-by='.lastTimestamp'`
- Check pod status: `kubectl describe pod -n agent-service <pod-name>`
