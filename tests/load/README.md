# Load Testing Guide

This directory contains load testing configurations using [Locust](https://locust.io/).

## Prerequisites

Install Locust:

```bash
pip install locust
# or
uv pip install locust
```

## Quick Start

### 1. Start your Agent Service

```bash
# Start the service locally
uvicorn agent_service.main:app --host 0.0.0.0 --port 8000
```

### 2. Run Load Tests

#### Web UI Mode (Recommended for initial testing)

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

Then open http://localhost:8089 in your browser to:
- Set number of users
- Set spawn rate
- View real-time metrics
- See charts and statistics

#### Headless Mode (CI/CD)

```bash
# Run for 5 minutes with 100 users, spawning 10 users/second
locust -f tests/load/locustfile.py \
       --host=http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless
```

## User Classes

The load tests include different user classes simulating various usage patterns:

### 1. AgentInvocationUser
Simulates users invoking agents with different message types.

```bash
locust -f tests/load/locustfile.py AgentInvocationUser \
       --host=http://localhost:8000 \
       --users 50 --spawn-rate 5
```

**Load pattern:**
- 60% simple invocations
- 40% invocations with context
- Average 1-3 second wait between requests

### 2. StreamingUser
Tests streaming endpoints with SSE.

```bash
locust -f tests/load/locustfile.py StreamingUser \
       --host=http://localhost:8000 \
       --users 20 --spawn-rate 2
```

**Use case:** Testing streaming response handling

### 3. AsyncJobUser
Submits async jobs and polls for completion.

```bash
locust -f tests/load/locustfile.py AsyncJobUser \
       --host=http://localhost:8000 \
       --users 30 --spawn-rate 3
```

**Load pattern:**
- 60% job submission
- 40% status polling

### 4. ProtocolUser
Tests different protocol endpoints (MCP, A2A, AG-UI).

```bash
locust -f tests/load/locustfile.py ProtocolUser \
       --host=http://localhost:8000 \
       --users 40 --spawn-rate 4
```

### 5. MixedWorkloadUser
Realistic mixed workload with various operations.

```bash
locust -f tests/load/locustfile.py MixedWorkloadUser \
       --host=http://localhost:8000 \
       --users 100 --spawn-rate 10
```

**Load pattern:**
- 50% quick invocations
- 20% streaming
- 10% async jobs
- 20% health checks

### 6. BurstTrafficUser
Simulates burst traffic patterns.

```bash
locust -f tests/load/locustfile.py BurstTrafficUser \
       --host=http://localhost:8000 \
       --users 50 --spawn-rate 25
```

**Use case:** Testing system resilience under sudden traffic spikes

## Test Scenarios

### Baseline Performance Test

Test basic throughput with moderate load:

```bash
locust -f tests/load/locustfile.py MixedWorkloadUser \
       --host=http://localhost:8000 \
       --users 50 \
       --spawn-rate 5 \
       --run-time 10m \
       --headless \
       --html report-baseline.html
```

### Stress Test

Push the system to its limits:

```bash
locust -f tests/load/locustfile.py MixedWorkloadUser \
       --host=http://localhost:8000 \
       --users 500 \
       --spawn-rate 50 \
       --run-time 15m \
       --headless \
       --html report-stress.html
```

### Endurance Test

Test system stability over extended period:

```bash
locust -f tests/load/locustfile.py MixedWorkloadUser \
       --host=http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 2h \
       --headless \
       --html report-endurance.html
```

### Spike Test

Test system response to sudden traffic spikes:

```bash
locust -f tests/load/locustfile.py BurstTrafficUser \
       --host=http://localhost:8000 \
       --users 200 \
       --spawn-rate 100 \
       --run-time 5m \
       --headless \
       --html report-spike.html
```

## Advanced Usage

### Custom User Distribution

Create a custom test with multiple user types:

```bash
# Run with multiple user classes
locust -f tests/load/locustfile.py \
       AgentInvocationUser StreamingUser AsyncJobUser \
       --host=http://localhost:8000 \
       --users 100 \
       --spawn-rate 10
```

### Remote Load Testing

Run load from multiple machines:

```bash
# Master node
locust -f tests/load/locustfile.py \
       --master \
       --host=http://production-api.example.com

# Worker nodes (on separate machines)
locust -f tests/load/locustfile.py \
       --worker \
       --master-host=<master-ip>
```

### Export Results

```bash
# Generate HTML report
locust -f tests/load/locustfile.py \
       --headless \
       --html report.html \
       --csv results

# CSV files: results_stats.csv, results_stats_history.csv, results_failures.csv
```

## Performance Metrics

Key metrics to monitor:

- **RPS (Requests Per Second)**: Target > 100 RPS for production
- **Response Time (P95)**: Should be < 500ms for sync endpoints
- **Response Time (P99)**: Should be < 1000ms for sync endpoints
- **Failure Rate**: Should be < 1% under normal load
- **Concurrent Users**: Target capacity (e.g., 1000 users)

## Testing Production

**IMPORTANT:** Always get approval before load testing production!

```bash
# Production load test (with rate limiting)
locust -f tests/load/locustfile.py MixedWorkloadUser \
       --host=https://api.production.example.com \
       --users 10 \
       --spawn-rate 1 \
       --run-time 5m \
       --headless
```

## Monitoring During Load Tests

While running load tests, monitor:

1. **Application Metrics**
   - Response times
   - Error rates
   - Request throughput

2. **System Metrics**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network I/O

3. **Database Metrics**
   - Query performance
   - Connection pool usage
   - Lock contention

4. **External Services**
   - API rate limits
   - Response times
   - Error rates

## Troubleshooting

### High Failure Rate

```bash
# Reduce load to find breaking point
locust -f tests/load/locustfile.py \
       --users 10 --spawn-rate 1
```

### Slow Response Times

- Check database query performance
- Verify external API response times
- Monitor CPU/memory usage
- Check for N+1 queries

### Connection Errors

- Increase connection pool size
- Check network limits
- Verify firewall settings
- Increase file descriptor limits

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Load Test

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install locust
      - name: Run load test
        run: |
          locust -f tests/load/locustfile.py \
                 --host=http://staging-api.example.com \
                 --users 50 \
                 --spawn-rate 5 \
                 --run-time 10m \
                 --headless \
                 --html report.html
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: load-test-report
          path: report.html
```

## Best Practices

1. **Start Small**: Begin with low load and gradually increase
2. **Monitor Everything**: Watch system metrics while testing
3. **Use Realistic Data**: Match production usage patterns
4. **Test Regularly**: Include in CI/CD pipeline
5. **Document Results**: Keep history of performance metrics
6. **Test Edge Cases**: Include error scenarios and edge cases
7. **Cleanup**: Remove test data after completion
8. **Coordinate**: Notify team before production load tests

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [Load Testing Best Practices](https://docs.locust.io/en/stable/writing-a-locustfile.html)
- [Interpreting Results](https://docs.locust.io/en/stable/running-locust-distributed.html)
