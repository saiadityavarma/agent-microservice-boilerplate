# Helm Deployment Guide for Agent Service

This guide provides step-by-step instructions for deploying the Agent Service to Kubernetes using Helm charts.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Workflows](#deployment-workflows)
- [Environment-Specific Deployments](#environment-specific-deployments)
- [Configuration Management](#configuration-management)
- [Monitoring Setup](#monitoring-setup)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify installations
kubectl version --client
helm version
```

### Kubernetes Cluster

- Kubernetes 1.24+ cluster
- kubectl configured with cluster access
- Sufficient resources:
  - Development: 2 CPU, 4GB RAM
  - Staging: 8 CPU, 16GB RAM
  - Production: 16+ CPU, 32+ GB RAM

### Infrastructure Components

```bash
# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.metrics.enabled=true \
  --set controller.podAnnotations."prometheus\.io/scrape"=true \
  --set controller.podAnnotations."prometheus\.io/port"=10254

# Install cert-manager (for TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/agent-service.git
cd agent-service
```

### 2. Build Docker Image

```bash
# Build image
docker build -t your-org/agent-service:v1.0.0 -f docker/Dockerfile .

# Push to registry
docker push your-org/agent-service:v1.0.0
```

### 3. Deploy to Development

```bash
# Create namespace
kubectl create namespace dev

# Create secrets
kubectl create secret generic agent-service-dev-secrets \
  --from-literal=DATABASE_URL=postgresql://user:pass@postgres:5432/db \
  --from-literal=REDIS_URL=redis://redis:6379/0 \
  --from-literal=SECRET_KEY=dev-secret-key \
  --namespace dev

# Install Helm chart
helm install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-dev.yaml \
  --namespace dev \
  --set image.tag=v1.0.0
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n dev

# Check services
kubectl get svc -n dev

# Check ingress
kubectl get ingress -n dev

# View logs
kubectl logs -n dev -l app.kubernetes.io/name=agent-service --tail=50
```

## Deployment Workflows

### Development Deployment

**Purpose**: Testing and development
**Frequency**: Multiple times per day
**Automation**: Automatic on push to `develop` branch

```bash
# Manual deployment
helm upgrade --install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-dev.yaml \
  --namespace dev \
  --create-namespace \
  --set image.tag=latest \
  --wait
```

### Staging Deployment

**Purpose**: Pre-production testing
**Frequency**: Daily or per release candidate
**Automation**: Automatic on push to `main` branch

```bash
# Create namespace and secrets
kubectl create namespace staging

# Using external secrets (recommended)
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: agent-service-staging-secrets
  namespace: staging
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: agent-service-staging-secrets
  data:
  - secretKey: DATABASE_URL
    remoteRef:
      key: agent-service/staging
      property: database_url
  - secretKey: REDIS_URL
    remoteRef:
      key: agent-service/staging
      property: redis_url
EOF

# Deploy
helm upgrade --install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-staging.yaml \
  --namespace staging \
  --create-namespace \
  --set image.tag=v1.0.0 \
  --wait \
  --timeout 15m
```

### Production Deployment

**Purpose**: Live production environment
**Frequency**: Weekly or per stable release
**Automation**: Manual approval required via GitHub Actions

```bash
# Pre-deployment checklist
# 1. Verify staging tests passed
# 2. Review changes and changelog
# 3. Ensure backup procedures are in place
# 4. Notify team of deployment window

# Create namespace
kubectl create namespace production

# Deploy with production values
helm upgrade --install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-prod.yaml \
  --namespace production \
  --create-namespace \
  --set image.tag=v1.0.0 \
  --wait \
  --timeout 20m \
  --atomic

# Verify deployment
kubectl rollout status deployment/agent-service-api -n production
kubectl rollout status deployment/agent-service-worker -n production

# Run smoke tests
kubectl run smoke-test --image=curlimages/curl --rm -i --restart=Never -n production -- \
  curl -f http://agent-service.production.svc.cluster.local/health

# Monitor for 5-10 minutes
kubectl logs -n production -l app.kubernetes.io/component=api --tail=100 -f
```

## Environment-Specific Deployments

### Development Environment

**Configuration**: `values-dev.yaml`

Features:
- Single replicas for cost savings
- Flower enabled for Celery monitoring
- Debug logging enabled
- Local Redis/PostgreSQL included
- No autoscaling
- Development TLS certificates

```bash
helm upgrade --install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-dev.yaml \
  --namespace dev \
  --set image.tag=latest \
  --set api.replicaCount=1 \
  --set worker.replicaCount=1 \
  --set flower.enabled=true
```

### Staging Environment

**Configuration**: `values-staging.yaml`

Features:
- Multiple replicas
- Autoscaling enabled
- External databases
- Production-like configuration
- Monitoring enabled
- Staging TLS certificates

```bash
helm upgrade --install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-staging.yaml \
  --namespace staging \
  --set image.tag=v1.0.0-rc.1
```

### Production Environment

**Configuration**: `values-prod.yaml`

Features:
- High availability (3+ replicas)
- Aggressive autoscaling
- Pod Disruption Budgets
- Network policies
- External secrets management
- Multi-AZ distribution
- Production TLS certificates
- Enhanced monitoring

```bash
helm upgrade --install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-prod.yaml \
  --namespace production \
  --set image.tag=v1.0.0
```

## Configuration Management

### Using ConfigMaps

Modify `values.yaml`:

```yaml
configMap:
  data:
    APP_NAME: "agent-service"
    LOG_LEVEL: "INFO"
    CUSTOM_CONFIG: "value"
```

### Using Secrets

#### Method 1: Kubernetes Secrets

```bash
kubectl create secret generic agent-service-secrets \
  --from-literal=DATABASE_URL='postgresql://user:pass@host:5432/db' \
  --from-literal=REDIS_URL='redis://redis:6379/0' \
  --from-literal=SECRET_KEY='your-secret-key' \
  --from-literal=ANTHROPIC_API_KEY='your-api-key' \
  --namespace production
```

Update `values.yaml`:
```yaml
secret:
  enabled: true
  useExisting: true
  existingSecretName: "agent-service-secrets"
```

#### Method 2: External Secrets Operator (Recommended)

```yaml
externalSecrets:
  enabled: true
  backend: aws-secrets-manager
  backendConfig:
    region: us-east-1
    secretName: agent-service/production
```

#### Method 3: Sealed Secrets

```bash
# Install sealed-secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret
kubectl create secret generic agent-service-secrets \
  --from-literal=DATABASE_URL='...' \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# Apply
kubectl apply -f sealed-secret.yaml -n production
```

### Environment Variables

Override via Helm:

```bash
helm upgrade agent-service ./helm/agent-service \
  --set api.env[0].name=LOG_LEVEL \
  --set api.env[0].value=DEBUG \
  --set worker.env[0].name=CELERY_CONCURRENCY \
  --set worker.env[0].value=8
```

## Monitoring Setup

### 1. Install Prometheus Stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
```

### 2. Apply Prometheus Rules

```bash
kubectl create configmap agent-service-rules \
  --from-file=monitoring/prometheus/rules.yml \
  -n monitoring

kubectl label configmap agent-service-rules \
  prometheus=kube-prometheus-stack \
  -n monitoring
```

### 3. Configure AlertManager

```bash
# Set environment variables
export SLACK_WEBHOOK_URL="your-webhook-url"
export PAGERDUTY_SERVICE_KEY="your-service-key"

# Create secret
envsubst < monitoring/alertmanager.yml | kubectl create secret generic alertmanager-config \
  --from-file=alertmanager.yml=/dev/stdin \
  -n monitoring
```

### 4. Import Grafana Dashboard

```bash
# Port forward to Grafana
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80

# Access at http://localhost:3000
# Default credentials: admin / prom-operator
# Import dashboard from monitoring/grafana/dashboards/agent-service.json
```

### 5. Enable ServiceMonitor

Update `values.yaml`:
```yaml
serviceMonitor:
  enabled: true
  interval: 30s
  labels:
    release: kube-prometheus-stack
```

## CI/CD Integration

### GitHub Actions Setup

1. **Configure Secrets**:
   - Go to GitHub repository → Settings → Secrets
   - Add secrets:
     - `DOCKER_USERNAME`
     - `DOCKER_PASSWORD`
     - `AWS_ACCESS_KEY_ID`
     - `AWS_SECRET_ACCESS_KEY`
     - `SLACK_WEBHOOK_URL` (optional)

2. **Workflows**:
   - `.github/workflows/build.yml` - Build and push Docker images
   - `.github/workflows/deploy.yml` - Deploy to Kubernetes

3. **Trigger Deployments**:

```bash
# Automatic deployment on push
git push origin develop  # Deploys to dev
git push origin main     # Deploys to staging

# Manual deployment to production
# Go to GitHub Actions → Deploy to Kubernetes → Run workflow
# Select: environment=prod, version=v1.0.0
```

### Deployment Strategies

#### Rolling Update (Default)

```yaml
api:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

#### Blue/Green Deployment

```bash
# Deploy new version with different name
helm install agent-service-green ./helm/agent-service \
  -f ./helm/agent-service/values-prod.yaml \
  --set fullnameOverride=agent-service-green \
  --set image.tag=v2.0.0

# Switch traffic (update ingress)
kubectl patch ingress agent-service -n production \
  -p '{"spec":{"rules":[{"host":"api.example.com","http":{"paths":[{"backend":{"service":{"name":"agent-service-green","port":{"number":80}}}}]}}]}}'

# Remove old version
helm uninstall agent-service -n production
```

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
kubectl get pods -n production

# Describe pod for events
kubectl describe pod <pod-name> -n production

# Check logs
kubectl logs <pod-name> -n production

# Common causes:
# - Image pull errors: Check imagePullSecrets
# - Resource constraints: Check node resources
# - Config errors: Check configmap/secret
```

#### 2. Database Connection Errors

```bash
# Test database connectivity
kubectl run psql-test --image=postgres:15 --rm -i --restart=Never -n production -- \
  psql $DATABASE_URL -c "SELECT 1"

# Check secret
kubectl get secret agent-service-secrets -n production -o yaml
```

#### 3. Ingress Not Working

```bash
# Check ingress
kubectl get ingress -n production
kubectl describe ingress agent-service -n production

# Check ingress controller
kubectl get pods -n ingress-nginx

# Test internal service
kubectl run curl-test --image=curlimages/curl --rm -i --restart=Never -n production -- \
  curl http://agent-service.production.svc.cluster.local/health
```

#### 4. High Memory/CPU Usage

```bash
# Check resource usage
kubectl top pods -n production

# Adjust resources in values.yaml
api:
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
```

#### 5. Autoscaling Not Working

```bash
# Check HPA status
kubectl get hpa -n production

# Check metrics server
kubectl get deployment metrics-server -n kube-system

# View HPA details
kubectl describe hpa agent-service-api -n production
```

### Rollback Procedures

```bash
# List releases
helm history agent-service -n production

# Rollback to previous version
helm rollback agent-service -n production

# Rollback to specific revision
helm rollback agent-service 3 -n production

# Verify rollback
kubectl rollout status deployment/agent-service-api -n production
```

### Debug Mode

```bash
# Enable debug logging
helm upgrade agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-prod.yaml \
  --set configMap.data.LOG_LEVEL=DEBUG \
  --reuse-values

# Port forward for local testing
kubectl port-forward -n production svc/agent-service 8000:80

# Access at http://localhost:8000
```

## Best Practices

1. **Version Control**: Always tag images with semantic versions
2. **Secrets**: Use external secrets management (AWS Secrets Manager, Vault)
3. **Resource Limits**: Always set resource requests and limits
4. **Health Checks**: Configure proper liveness and readiness probes
5. **Monitoring**: Enable ServiceMonitor and set up alerts
6. **Backups**: Implement backup strategy for databases
7. **Testing**: Test in staging before production deployment
8. **Documentation**: Keep deployment documentation up to date
9. **Security**: Run security scans on images (Trivy, Snyk)
10. **Gradual Rollout**: Use canary or blue/green deployments for production

## Additional Resources

- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Agent Service Chart README](./helm/agent-service/README.md)
- [Monitoring Setup Guide](./monitoring/README.md)
- [GitHub Actions Workflows](./.github/workflows/)

## Support

For deployment issues:
- Check logs: `kubectl logs -n <namespace> <pod-name>`
- Review events: `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`
- Contact: platform-team@example.com
