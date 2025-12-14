# Agent Service Helm Chart

This Helm chart deploys the Agent Service application with FastAPI API servers and Celery workers to Kubernetes.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.13+
- PV provisioner support in the underlying infrastructure (optional, for persistence)
- Ingress controller (nginx recommended)
- cert-manager (optional, for TLS certificates)

## Installation

### Quick Start

```bash
# Add the repository (if hosted)
helm repo add agent-service https://charts.example.com
helm repo update

# Install with default values (development)
helm install agent-service ./helm/agent-service

# Install for specific environment
helm install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-prod.yaml \
  --namespace production \
  --create-namespace
```

### Development Environment

```bash
helm install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-dev.yaml \
  --namespace dev \
  --create-namespace \
  --set image.tag=latest
```

### Staging Environment

```bash
helm install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-staging.yaml \
  --namespace staging \
  --create-namespace \
  --set image.tag=v1.2.3
```

### Production Environment

```bash
helm install agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-prod.yaml \
  --namespace production \
  --create-namespace \
  --set image.tag=v1.2.3
```

## Upgrading

```bash
# Upgrade with new version
helm upgrade agent-service ./helm/agent-service \
  -f ./helm/agent-service/values-prod.yaml \
  --set image.tag=v1.2.4

# Rollback to previous version
helm rollback agent-service
```

## Uninstallation

```bash
helm uninstall agent-service --namespace production
```

## Configuration

The following table lists the configurable parameters and their default values.

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.environment` | Environment name | `development` |
| `global.domain` | Base domain | `example.com` |
| `global.imageRegistry` | Global Docker registry | `""` |

### Image Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.registry` | Image registry | `docker.io` |
| `image.repository` | Image repository | `your-org/agent-service` |
| `image.tag` | Image tag | `""` (uses appVersion) |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |

### API Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api.enabled` | Enable API deployment | `true` |
| `api.replicaCount` | Number of API replicas | `2` |
| `api.resources.limits.cpu` | CPU limit | `1000m` |
| `api.resources.limits.memory` | Memory limit | `1Gi` |
| `api.autoscaling.enabled` | Enable HPA | `true` |
| `api.autoscaling.minReplicas` | Min replicas | `2` |
| `api.autoscaling.maxReplicas` | Max replicas | `10` |

### Worker Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `worker.enabled` | Enable worker deployment | `true` |
| `worker.replicaCount` | Number of worker replicas | `2` |
| `worker.concurrency` | Celery concurrency | `4` |
| `worker.resources.limits.cpu` | CPU limit | `2000m` |
| `worker.resources.limits.memory` | Memory limit | `2Gi` |
| `worker.autoscaling.enabled` | Enable HPA | `true` |

### Service Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `service.targetPort` | Container port | `8000` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts[0].host` | Hostname | `api.example.com` |
| `ingress.tls` | TLS configuration | See values.yaml |

### Secret Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secret.enabled` | Enable secret creation | `true` |
| `secret.useExisting` | Use existing secret | `false` |
| `secret.data.DATABASE_URL` | Database connection string | See values.yaml |
| `secret.data.REDIS_URL` | Redis connection string | See values.yaml |

### Monitoring Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `serviceMonitor.enabled` | Enable ServiceMonitor | `false` |
| `serviceMonitor.interval` | Scrape interval | `30s` |
| `podDisruptionBudget.enabled` | Enable PDB | `true` |
| `podDisruptionBudget.minAvailable` | Min available pods | `1` |

## Examples

### Using External Secrets Operator

```yaml
externalSecrets:
  enabled: true
  backend: aws-secrets-manager
  backendConfig:
    region: us-east-1
    secretName: agent-service/production
```

### Custom Resource Limits

```yaml
api:
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
    requests:
      cpu: 1000m
      memory: 1Gi
```

### Enable Flower for Development

```yaml
flower:
  enabled: true
  replicaCount: 1
```

### Multi-AZ Deployment

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app.kubernetes.io/name: agent-service
```

## Monitoring

This chart includes built-in support for:

- Prometheus metrics via ServiceMonitor
- Grafana dashboards (see `/monitoring/grafana/dashboards/`)
- Alert rules (see `/monitoring/prometheus/rules.yml`)

## Troubleshooting

### Check deployment status

```bash
kubectl get all -n production -l app.kubernetes.io/name=agent-service
```

### View logs

```bash
# API logs
kubectl logs -n production -l app.kubernetes.io/component=api --tail=100 -f

# Worker logs
kubectl logs -n production -l app.kubernetes.io/component=worker --tail=100 -f
```

### Check pod health

```bash
kubectl describe pod -n production <pod-name>
```

### Test connectivity

```bash
kubectl run test --image=curlimages/curl --rm -i --restart=Never -- \
  curl -v http://agent-service.production.svc.cluster.local/health
```

## Security Considerations

1. **Secrets Management**: Use external-secrets operator or sealed-secrets in production
2. **Network Policies**: Enable network policies to restrict traffic
3. **Pod Security**: Runs as non-root user with read-only root filesystem
4. **RBAC**: Service account with minimal permissions
5. **TLS**: Always use TLS in production via cert-manager

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/agent-service/issues
- Documentation: https://docs.example.com
