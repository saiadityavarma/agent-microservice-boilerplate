#!/bin/bash
# verify_test_suite.sh
# Verify that the comprehensive test suite is properly set up

set -e

echo "==================================="
echo "Test Suite Verification"
echo "==================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

# Function to check directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

echo "1. Checking Test Directory Structure..."
check_dir "tests/unit/api"
check_dir "tests/unit/agents"
check_dir "tests/unit/tools"
check_dir "tests/unit/protocols"
check_dir "tests/integration"
check_dir "tests/e2e"
check_dir "tests/load"
echo ""

echo "2. Checking Unit Test Files..."
check_file "tests/unit/api/test_agents_routes.py"
check_file "tests/unit/api/test_protocols_routes.py"
check_file "tests/unit/agents/test_agent_implementations.py"
check_file "tests/unit/tools/test_tool_registry.py"
check_file "tests/unit/protocols/test_protocol_handlers.py"
echo ""

echo "3. Checking Integration Test Files..."
check_file "tests/integration/test_auth_flow.py"
check_file "tests/integration/test_agent_invocation.py"
check_file "tests/integration/test_protocol_handlers.py"
check_file "tests/integration/test_database.py"
echo ""

echo "4. Checking E2E Test Files..."
check_file "tests/e2e/test_full_agent_flow.py"
check_file "tests/e2e/test_api_workflow.py"
echo ""

echo "5. Checking Load Test Files..."
check_file "tests/load/locustfile.py"
check_file "tests/load/README.md"
echo ""

echo "6. Checking Configuration Files..."
check_file "pytest.ini"
check_file "tests/conftest.py"
echo ""

echo "7. Checking Documentation..."
check_file "tests/TEST_GUIDE.md"
check_file "tests/TEST_SUITE_SUMMARY.md"
check_file "tests/QUICK_START.md"
check_file "COMPREHENSIVE_TEST_SUITE.md"
echo ""

echo "8. Counting Test Files..."
TEST_COUNT=$(find tests -type f -name "test_*.py" | wc -l | tr -d ' ')
echo -e "${YELLOW}Total test files: $TEST_COUNT${NC}"
echo ""

echo "9. Running Quick Test Collection..."
if command -v pytest &> /dev/null; then
    echo "Collecting tests (without running)..."
    pytest --collect-only -q 2>/dev/null | tail -5 || echo -e "${YELLOW}Note: Some tests may need dependencies${NC}"
else
    echo -e "${YELLOW}pytest not installed - skipping collection${NC}"
fi
echo ""

echo "==================================="
echo "Verification Complete!"
echo "==================================="
echo ""
echo "Next Steps:"
echo "  1. Install dependencies: pip install pytest pytest-asyncio pytest-cov httpx"
echo "  2. Run unit tests: pytest -m unit"
echo "  3. Run with coverage: pytest --cov=src/agent_service --cov-report=html"
echo "  4. View coverage: open htmlcov/index.html"
echo "  5. Read guide: cat tests/TEST_GUIDE.md"
echo ""
echo "For load testing:"
echo "  1. Install Locust: pip install locust"
echo "  2. Run: locust -f tests/load/locustfile.py --host=http://localhost:8000"
echo "  3. Open: http://localhost:8089"
echo ""
