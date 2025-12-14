# Agent Service Monitoring Stack

This directory contains the monitoring configuration for the Agent Service, including Prometheus alert rules, Grafana dashboards, and AlertManager configuration.

## Overview

The monitoring stack provides comprehensive observability for:

- **API Performance**: Request rates, latency, error rates
- **Celery Workers**: Queue depth, task processing, worker health
- **Resource Usage**: CPU, memory, disk, network
- **Business Metrics**: Agent invocations, tool usage, external API calls
- **Infrastructure**: Pod health, replica status, node resources

## Components

### 1. Prometheus Alert Rules (`prometheus/rules.yml`)

Alert rules are organized into groups:

#### agent-service-alerts
- Service availability and health
- Error rate thresholds
- Latency monitoring
- Resource usage (CPU, memory)
- Pod health and restarts

#### celery-worker-alerts
- Worker availability
- Queue depth monitoring
- Task failure rates
- Task processing times
- Worker resource usage

#### database-alerts
- Connection pool health
- Query latency
- Connection errors

#### redis-alerts
- Redis availability
- Memory usage
- Connection exhaustion

#### agent-business-logic-alerts
- Agent invocation success/failure
- Response time monitoring
- Tool invocation patterns
- External API rate limits

### 2. Grafana Dashboard (`grafana/dashboards/agent-service.json`)

The main dashboard includes:

#### Overview Section
- Service status indicator
- Current request rate
- Error rate trending
- Requests per minute

#### Latency Metrics
- Request latency (p50, p95, p99) by endpoint
- Agent response time by agent type

#### Resource Usage
- CPU utilization by pod
- Memory usage by pod
- Resource limits visualization

#### Celery Workers
- Active worker count
- Queue depth by queue
- Task success/failure rates
- Total queue depth

#### Agent Invocations
- Invocation rate by agent type
- Tool invocation rate by tool

### 3. AlertManager Configuration (`alertmanager.yml`)

Routing and notification setup:

- **Critical alerts** → PagerDuty + Slack
- **Warning alerts** → Slack
- **Info alerts** → Slack (low priority)
- Component-specific routing for teams
- Inhibition rules to prevent alert fatigue
- Maintenance window support

## Setup

### Prerequisites

Install monitoring stack components:

```bash
# Install Prometheus Operator
kubectl create namespace monitoring
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values monitoring-values.yaml
```

### Deploy Alert Rules

```bash
kubectl apply -f monitoring/prometheus/rules.yml -n monitoring
```

### Import Grafana Dashboard

1. Access Grafana UI:
```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
```

2. Navigate to http://localhost:3000 (default credentials: admin/prom-operator)

3. Go to Dashboards → Import → Upload JSON file
   - Select `monitoring/grafana/dashboards/agent-service.json`

4. Configure data source (select Prometheus)

### Configure AlertManager

1. Create secret with AlertManager configuration:

```bash
kubectl create secret generic alertmanager-config \
  --from-file=alertmanager.yml=monitoring/alertmanager.yml \
  -n monitoring
```

2. Set environment variables for sensitive values:

```bash
# Slack webhook
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# PagerDuty integration keys
export PAGERDUTY_SERVICE_KEY="your-pagerduty-integration-key"
export PAGERDUTY_DATABASE_SERVICE_KEY="your-database-pagerduty-key"
```

3. Update the AlertManager configuration:

```bash
kubectl create secret generic additional-scrape-configs \
  --from-literal=slack-webhook=$SLACK_WEBHOOK_URL \
  --from-literal=pagerduty-key=$PAGERDUTY_SERVICE_KEY \
  -n monitoring
```

## Alert Severity Levels

### Critical (severity: critical)
- Service completely down
- Very high error rates (>5%)
- Database connection failures
- All workers down
- OOM kills

**Response**: Immediate action required, PagerDuty alerts triggered

### Warning (severity: warning)
- High resource usage (>80%)
- Elevated error rates (2-5%)
- High latency (>2s)
- Frequent pod restarts
- High queue depth

**Response**: Investigate within 1 hour, Slack notification

### Info (severity: info)
- High load indicators
- Usage pattern changes
- Non-critical metrics

**Response**: For awareness, no immediate action needed

## Customizing Alerts

### Adjust Thresholds

Edit `prometheus/rules.yml` to modify alert thresholds:

```yaml
# Example: Change error rate threshold
- alert: AgentServiceHighErrorRate
  expr: |
    (
      sum(rate(http_requests_total{job="agent-service",status=~"5.."}[5m])) /
      sum(rate(http_requests_total{job="agent-service"}[5m]))
    ) > 0.05  # Change this value
  for: 5m     # Change alert delay
```

### Add Custom Alerts

Add new alert rules to the appropriate group:

```yaml
- alert: CustomMetricAlert
  expr: your_metric > threshold
  for: 5m
  labels:
    severity: warning
    component: custom
  annotations:
    summary: "Custom alert summary"
    description: "Detailed description with {{ $labels.label_name }}"
```

## Notification Channels

### Slack Configuration

Update channel names in `alertmanager.yml`:

```yaml
receivers:
  - name: 'slack-critical'
    slack_configs:
      - channel: '#your-critical-channel'  # Change channel
```

### PagerDuty Configuration

1. Create integration in PagerDuty
2. Get integration key
3. Update AlertManager secret:

```bash
kubectl create secret generic alertmanager-pagerduty \
  --from-literal=service-key=YOUR_KEY \
  -n monitoring
```

### Adding Email Notifications

```yaml
receivers:
  - name: 'email-alerts'
    email_configs:
      - to: 'team@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alertmanager@example.com'
        auth_password: 'password'
```

## Dashboard Customization

### Adding Panels

1. Open dashboard in Grafana
2. Click "Add panel"
3. Configure query:
   ```promql
   # Example: Add request duration by status code
   histogram_quantile(0.95,
     sum(rate(http_request_duration_seconds_bucket[5m])) by (le, status)
   )
   ```
4. Save dashboard
5. Export as JSON and commit to repository

### Template Variables

The dashboard supports namespace selection:
- Variable name: `namespace`
- Options: dev, staging, production

Add more variables:
```json
{
  "name": "pod",
  "query": "label_values(up{namespace=\"$namespace\"}, pod)",
  "type": "query"
}
```

## Troubleshooting

### Alerts Not Firing

1. Check Prometheus targets:
```bash
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090
# Visit http://localhost:9090/targets
```

2. Verify alert rules loaded:
```bash
# Visit http://localhost:9090/alerts
```

3. Check AlertManager:
```bash
kubectl logs -n monitoring alertmanager-kube-prometheus-stack-0
```

### Missing Metrics

1. Verify ServiceMonitor is created:
```bash
kubectl get servicemonitor -n production agent-service
```

2. Check Prometheus scrape config:
```bash
kubectl get secret -n monitoring prometheus-kube-prometheus-stack-prometheus -o yaml
```

3. Verify application exposes metrics:
```bash
kubectl port-forward -n production svc/agent-service 8000:80
curl http://localhost:8000/metrics
```

### Dashboard Not Loading

1. Check Prometheus data source:
   - Grafana → Configuration → Data Sources
   - Test connection

2. Verify metrics exist:
   - Use Prometheus query browser
   - Run sample queries from dashboard

3. Check time range and refresh settings

## Metrics Reference

### HTTP Metrics
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request duration histogram
- `http_requests_in_progress` - Current requests being processed

### Celery Metrics
- `celery_workers_active` - Number of active workers
- `celery_queue_length` - Queue depth by queue name
- `celery_task_total` - Total tasks processed
- `celery_task_failed_total` - Failed tasks
- `celery_task_runtime_seconds` - Task execution time

### Resource Metrics (from cAdvisor)
- `container_cpu_usage_seconds_total` - CPU usage
- `container_memory_working_set_bytes` - Memory usage
- `container_network_receive_bytes_total` - Network RX
- `container_network_transmit_bytes_total` - Network TX

### Business Metrics
- `agent_invocation_total` - Agent invocations
- `agent_invocation_failed_total` - Failed invocations
- `agent_response_time_seconds` - Agent response time
- `tool_invocation_total` - Tool usage
- `rate_limit_remaining` - External API rate limits

## Best Practices

1. **Alert Fatigue**: Use appropriate thresholds and durations
2. **Runbooks**: Document response procedures for each alert
3. **Regular Review**: Review and tune alerts monthly
4. **Test Alerts**: Periodically test alert routing
5. **Dashboard Organization**: Keep dashboards focused and organized
6. **Retention**: Configure appropriate metric retention periods
7. **High Availability**: Run multiple AlertManager replicas

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AlertManager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [PromQL Guide](https://prometheus.io/docs/prometheus/latest/querying/basics/)
