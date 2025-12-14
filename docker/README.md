# Docker Configuration

This directory contains Docker and Docker Compose configuration for the Agent Service.

## Files

- `Dockerfile` - Multi-stage Dockerfile for API service
- `Dockerfile.worker` - Dockerfile for Celery workers and beat scheduler
- `docker-compose.yml` - Complete local development environment

## Quick Start

### Development

```bash
# Start all services
docker-compose up

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f worker

# Stop all services
docker-compose down

# Remove volumes (clean start)
docker-compose down -v
```

### Building Images

```bash
# Build production API image
docker build -f docker/Dockerfile -t agent-service:latest --target prod .

# Build development image
docker build -f docker/Dockerfile -t agent-service:dev --target dev .

# Build worker image
docker build -f docker/Dockerfile.worker -t agent-service-worker:latest --target worker .

# Build beat scheduler image
docker build -f docker/Dockerfile.worker -t agent-service-beat:latest --target beat .
```

### Production Build

```bash
# Build and tag for registry
docker build -f docker/Dockerfile -t your-registry/agent-service:v1.0.0 --target prod .
docker push your-registry/agent-service:v1.0.0

# Build worker
docker build -f docker/Dockerfile.worker -t your-registry/agent-service-worker:v1.0.0 --target worker .
docker push your-registry/agent-service-worker:v1.0.0
```

## Docker Compose Services

### Core Services

1. **api** - FastAPI application
   - Port: 8000
   - Health check: http://localhost:8000/health
   - Auto-reloads on code changes

2. **worker** - Celery workers (2 replicas)
   - Processes background tasks
   - Concurrency: 4 workers per container

3. **beat** - Celery beat scheduler
   - Manages periodic tasks
   - Single instance only

### Infrastructure Services

4. **postgres** - PostgreSQL 16
   - Port: 5432
   - Database: agent_db
   - Credentials: postgres/postgres (dev only!)

5. **redis** - Redis 7
   - Port: 6379
   - Used for cache and Celery broker

### Monitoring Services

6. **prometheus** - Metrics collection
   - Port: 9090
   - UI: http://localhost:9090

7. **grafana** - Metrics visualization
   - Port: 3000
   - UI: http://localhost:3000
   - Credentials: admin/admin

## Resource Limits

### API Service
- Memory: 512M - 2G
- CPU: 0.5 - 2 cores

### Worker Service
- Memory: 512M - 2G per replica
- CPU: 0.5 - 2 cores per replica

### PostgreSQL
- Memory: 256M - 1G
- CPU: 0.25 - 1 core

### Redis
- Memory: 128M - 512M
- CPU: 0.1 - 0.5 cores

### Prometheus
- Memory: 256M - 1G
- CPU: 0.25 - 1 core

### Grafana
- Memory: 128M - 512M
- CPU: 0.1 - 0.5 cores

## Environment Variables

See `.env` file for configuration. Key variables:

```bash
# Application
ENVIRONMENT=local
DEBUG=true
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/agent_db

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Security (change in production!)
SECRET_KEY=dev-secret-not-for-production
```

## Health Checks

All services include health checks:

- **API**: `curl -f http://localhost:8000/health`
- **PostgreSQL**: `pg_isready -U postgres`
- **Redis**: `redis-cli ping`

Services won't start until dependencies are healthy.

## Dockerfile Features

### Production Dockerfile

1. **Multi-stage build** - Separate builder and runtime stages
2. **Slim base image** - python:3.11-slim for small size
3. **Security labels** - OCI image labels for scanning
4. **Non-root user** - Runs as UID 1001
5. **Health check** - Built-in container health monitoring
6. **Layer optimization** - Efficient caching and small image size

### Worker Dockerfile

1. **Separate entrypoint** - Worker and beat targets
2. **Non-root execution** - celeryuser (UID 1001)
3. **Optimized for tasks** - Appropriate concurrency settings

## Monitoring

### Prometheus Metrics

Access Prometheus at http://localhost:9090

Example queries:
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Grafana Dashboards

Access Grafana at http://localhost:3000

Pre-configured dashboards for:
- API performance
- Resource utilization
- Database metrics
- Redis metrics

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs api

# Check specific container
docker-compose logs postgres

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Database connection issues

```bash
# Verify postgres is healthy
docker-compose ps postgres

# Check postgres logs
docker-compose logs postgres

# Connect to postgres directly
docker-compose exec postgres psql -U postgres -d agent_db
```

### Worker not processing tasks

```bash
# Check worker logs
docker-compose logs worker

# Verify Redis connection
docker-compose exec worker redis-cli -h redis ping

# Check Celery status
docker-compose exec worker celery -A agent_service.tasks.celery_app inspect active
```

### Out of resources

```bash
# Check resource usage
docker stats

# Adjust limits in docker-compose.yml
# Restart with new limits
docker-compose up -d --force-recreate
```

### Clean slate

```bash
# Stop and remove everything
docker-compose down -v

# Remove all images
docker-compose down --rmi all -v

# Rebuild and start
docker-compose up --build
```

## Production Deployment

For production deployment:

1. Use production Dockerfile target
2. Change all default passwords
3. Use secrets management (not .env files)
4. Enable TLS/SSL
5. Configure proper resource limits
6. Set up external monitoring
7. Use managed databases (RDS, Cloud SQL, etc.)
8. Configure backup strategy
9. Set up log aggregation

See the `k8s/` directory for Kubernetes deployment.

## Security Considerations

1. **Non-root containers** - All containers run as unprivileged users
2. **No secrets in images** - All secrets via environment variables
3. **Security scanning** - Use `docker scan` or Trivy
4. **Regular updates** - Keep base images updated
5. **Read-only filesystem** - Where possible
6. **Resource limits** - Prevent DoS

## Best Practices

1. **Use specific tags** - Don't use `latest` in production
2. **Multi-stage builds** - Keep images small
3. **Health checks** - Always include health checks
4. **Logging** - Log to stdout/stderr
5. **Graceful shutdown** - Handle SIGTERM properly
6. **Secrets** - Never commit secrets to git
