# tests/load/locustfile.py
"""
Locust load testing configuration for Agent Service.

Usage:
    # Run with web UI
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # Run headless with specific users
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 5m --headless

    # Run with custom user class
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
           AgentInvocationUser --users 50 --spawn-rate 5
"""

import random
import json
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser


class AgentServiceUser(HttpUser):
    """Base user class for Agent Service load testing."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a user starts. Set up authentication."""
        # In production, you'd authenticate here and get a token
        self.api_key = "test-api-key-for-load-testing"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Create a session ID for this user
        self.session_id = f"load-test-session-{random.randint(1000, 9999)}"


class AgentInvocationUser(AgentServiceUser):
    """User that performs agent invocations."""

    @task(3)
    def invoke_agent_simple(self):
        """Invoke agent with simple message."""
        messages = [
            "What is the weather today?",
            "Tell me a joke",
            "Explain quantum computing",
            "What is Python?",
            "How do I make coffee?"
        ]

        payload = {
            "message": random.choice(messages),
            "session_id": self.session_id
        }

        with self.client.post(
            "/api/v1/agents/invoke",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(2)
    def invoke_agent_with_context(self):
        """Invoke agent with additional context."""
        payload = {
            "message": "Process this request with context",
            "session_id": self.session_id,
            "metadata": {
                "source": "load_test",
                "priority": random.choice(["low", "medium", "high"]),
                "user_tier": random.choice(["free", "pro", "enterprise"])
            }
        }

        with self.client.post(
            "/api/v1/agents/invoke",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(1)
    def health_check(self):
        """Check health endpoint."""
        self.client.get("/api/v1/health")


class StreamingUser(AgentServiceUser):
    """User that tests streaming endpoints."""

    @task
    def stream_agent_response(self):
        """Test streaming agent responses."""
        payload = {
            "message": "Stream a long response",
            "session_id": self.session_id
        }

        with self.client.post(
            "/api/v1/agents/stream",
            json=payload,
            headers=self.headers,
            stream=True,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                # Consume the stream
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        pass  # Process chunk
                response.success()
            else:
                response.failure(f"Stream failed with status {response.status_code}")


class AsyncJobUser(AgentServiceUser):
    """User that submits async jobs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_ids = []

    @task(3)
    def submit_async_job(self):
        """Submit async agent invocation."""
        payload = {
            "message": "Long running async task",
            "session_id": self.session_id,
            "metadata": {"async": True}
        }

        with self.client.post(
            "/api/v1/agents/test-agent/invoke-async",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 202:
                data = response.json()
                if "task_id" in data:
                    self.task_ids.append(data["task_id"])
                response.success()
            else:
                response.failure(f"Async submit failed: {response.status_code}")

    @task(2)
    def check_task_status(self):
        """Check status of submitted tasks."""
        if not self.task_ids:
            return

        task_id = random.choice(self.task_ids)

        with self.client.get(
            f"/api/v1/agents/tasks/{task_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("state") == "SUCCESS":
                    # Remove completed task
                    self.task_ids.remove(task_id)
                response.success()
            else:
                response.failure(f"Status check failed: {response.status_code}")


class ProtocolUser(AgentServiceUser):
    """User that tests different protocols."""

    @task(2)
    def test_mcp_tools(self):
        """Test MCP tool listing."""
        self.client.get("/api/v1/protocols/mcp/tools", headers=self.headers)

    @task(3)
    def test_mcp_invoke(self):
        """Test MCP invocation."""
        payload = {"message": "MCP test message"}

        self.client.post(
            "/api/v1/protocols/mcp/invoke",
            json=payload,
            headers=self.headers
        )

    @task(1)
    def test_a2a_create_task(self):
        """Test A2A task creation."""
        payload = {"message": "Create A2A task"}

        self.client.post(
            "/api/v1/protocols/a2a/tasks",
            json=payload,
            headers=self.headers
        )

    @task(1)
    def test_a2a_list_tasks(self):
        """Test A2A task listing."""
        self.client.get(
            "/api/v1/protocols/a2a/tasks?limit=10",
            headers=self.headers
        )


class MixedWorkloadUser(AgentServiceUser):
    """User with mixed workload patterns."""

    @task(5)
    def quick_invoke(self):
        """Quick agent invocation."""
        payload = {"message": "Quick question"}
        self.client.post(
            "/api/v1/agents/invoke",
            json=payload,
            headers=self.headers
        )

    @task(2)
    def stream_response(self):
        """Streaming response."""
        payload = {"message": "Stream response"}
        self.client.post(
            "/api/v1/agents/stream",
            json=payload,
            headers=self.headers,
            stream=True
        )

    @task(1)
    def async_job(self):
        """Async job submission."""
        payload = {"message": "Async task"}
        self.client.post(
            "/api/v1/agents/test-agent/invoke-async",
            json=payload,
            headers=self.headers
        )

    @task(3)
    def health_checks(self):
        """Health check."""
        self.client.get("/api/v1/health")


# Fast HTTP User for better performance
class FastAgentUser(FastHttpUser):
    """High-performance user using FastHttpUser."""

    wait_time = between(0.5, 2)

    def on_start(self):
        self.api_key = "test-api-key"
        self.headers = {"X-API-Key": self.api_key}
        self.session_id = f"fast-session-{random.randint(1000, 9999)}"

    @task
    def fast_invoke(self):
        """Fast agent invocation."""
        payload = {
            "message": "Fast request",
            "session_id": self.session_id
        }

        self.client.post(
            "/api/v1/agents/invoke",
            json=json.dumps(payload),
            headers=self.headers
        )


# Event handlers for metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("Load test starting...")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("Load test completed!")
    stats = environment.stats

    print(f"\nTotal requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"RPS: {stats.total.total_rps:.2f}")


# Custom test scenarios
class BurstTrafficUser(AgentServiceUser):
    """User that simulates burst traffic patterns."""

    wait_time = between(0.1, 0.5)  # Very short wait time for bursts

    @task
    def burst_invoke(self):
        """Rapid fire invocations."""
        for _ in range(5):  # Send 5 requests in quick succession
            payload = {"message": f"Burst request {random.randint(1, 1000)}"}
            self.client.post(
                "/api/v1/agents/invoke",
                json=payload,
                headers=self.headers
            )


class LongRunningUser(AgentServiceUser):
    """User that simulates long-running sessions."""

    wait_time = between(5, 10)  # Longer wait time

    @task
    def long_session(self):
        """Long running session with multiple invocations."""
        # Simulate conversation with multiple turns
        messages = [
            "Start of conversation",
            "Follow up question",
            "More details please",
            "Final question"
        ]

        for msg in messages:
            payload = {
                "message": msg,
                "session_id": self.session_id
            }

            self.client.post(
                "/api/v1/agents/invoke",
                json=payload,
                headers=self.headers
            )
