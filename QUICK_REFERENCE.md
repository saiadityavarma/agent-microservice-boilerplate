# Quick Reference - Docker & Kubernetes

## Docker Commands

### Development
```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f api

# Stop services
docker-compose -f docker/docker-compose.yml down

# Clean restart
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml up --build
```

### Build Images
```bash
# Production API
docker build -f docker/Dockerfile -t agent-service:latest --target prod .

# Worker
docker build -f docker/Dockerfile.worker -t agent-service-worker:latest --target worker .
```

### Access Services (Docker Compose)
- API: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## Kubernetes Commands

### Deploy
```bash
# All at once
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml  # Configure first!
kubectl apply -f k8s/
```

### Monitor
```bash
# All resources
kubectl get all -n agent-service

# Pods
kubectl get pods -n agent-service

# Logs
kubectl logs -f deployment/agent-service-api -n agent-service

# Events
kubectl get events -n agent-service --sort-by='.lastTimestamp'
```

### Scale
```bash
# Manual scale
kubectl scale deployment agent-service-api --replicas=5 -n agent-service

# Check HPA
kubectl get hpa -n agent-service
```

### Update
```bash
# Rolling update
kubectl set image deployment/agent-service-api \
  api=your-registry/agent-service:v1.1.0 -n agent-service

# Rollback
kubectl rollout undo deployment/agent-service-api -n agent-service
```

### Debug
```bash
# Describe pod
kubectl describe pod <pod-name> -n agent-service

# Shell into pod
kubectl exec -it <pod-name> -n agent-service -- sh

# Port forward
kubectl port-forward svc/agent-service-api 8000:80 -n agent-service
```

## File Locations

### Docker
- /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/docker/Dockerfile
- /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/docker/Dockerfile.worker
- /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/docker/docker-compose.yml

### Kubernetes
- /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/k8s/ (11 manifests)

### Monitoring
- /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/monitoring/prometheus.yml
- /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/monitoring/grafana/

### Documentation
- /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/DEPLOYMENT.md
- /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/DOCKER_K8S_SUMMARY.md
- /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/docker/README.md
- /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/k8s/README.md

## Key Features

### Docker
- Health checks on all services
- Resource limits (CPU, memory)
- Restart policies
- Monitoring (Prometheus + Grafana)
- Celery workers and scheduler

### Kubernetes
- Auto-scaling (2-10 replicas)
- High availability (PDB, anti-affinity)
- Security (non-root, capabilities dropped)
- TLS/Ingress ready
- RBAC configured
- Comprehensive health probes

## Important Notes

1. Never commit secrets - use External Secrets Operator or manual creation
2. Update image references in manifests before deploying
3. Configure proper domain names in ingress.yaml
4. Review and adjust resource limits for your workload
5. Set up monitoring alerts in production
6. Test in staging before production deployment
