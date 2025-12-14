Deploy the agent service with the following steps:

1. **Pre-deployment checks**:
   - Run tests: `pytest -v`
   - Check code quality: `ruff check src/` and `black --check src/`
   - Verify environment configuration
   - Check for uncommitted changes

2. **Build Docker images**:
   - API image: `docker build -f docker/Dockerfile -t {registry}/agent-service:{version} --target prod .`
   - Worker image: `docker build -f docker/Dockerfile.worker -t {registry}/agent-service-worker:{version} --target worker .`

3. **Push to registry**:
   - `docker push {registry}/agent-service:{version}`
   - `docker push {registry}/agent-service-worker:{version}`

4. **Deploy based on environment**:

   **For Kubernetes**:
   - Update image tags in manifests or Helm values
   - Apply: `kubectl set image deployment/agent-service-api api={registry}/agent-service:{version} -n agent-service`
   - Or Helm: `helm upgrade agent-service ./helm/agent-service --set image.tag={version}`
   - Verify: `kubectl rollout status deployment/agent-service-api -n agent-service`

   **For Docker Compose** (staging/dev):
   - Update image tags in `docker-compose.yml`
   - Deploy: `docker-compose -f docker/docker-compose.yml up -d`

5. **Post-deployment verification**:
   - Check pod/container status
   - Verify health endpoint: `curl https://your-domain/health`
   - Check logs for errors
   - Run smoke tests
   - Verify agents are registered: `curl https://your-domain/api/v1/agents`

6. **Rollback plan** (if needed):
   - Kubernetes: `kubectl rollout undo deployment/agent-service-api -n agent-service`
   - Helm: `helm rollback agent-service -n agent-service`

After deployment:
- Provide deployment summary
- Show verification commands
- Suggest monitoring dashboards to check
- Document the deployed version
