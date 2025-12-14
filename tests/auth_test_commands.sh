#!/bin/bash
# Authentication Tests - Quick Reference Commands
#
# This script provides quick commands for running authentication tests.
# Make executable: chmod +x tests/auth_test_commands.sh

set -e

echo "=== Authentication Test Suite ==="
echo

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"
if [[ ! "$python_version" =~ ^3\.1[1-9] ]]; then
    echo "WARNING: Python 3.11+ required. Current: $python_version"
    echo "Install Python 3.11+: https://www.python.org/downloads/"
    exit 1
fi

# Install dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo "Installing test dependencies..."
    pip install -e ".[dev]"
fi

echo
echo "Available test commands:"
echo

# 1. Run all auth tests
echo "1. Run ALL auth tests:"
echo "   pytest tests/unit/auth/ tests/integration/auth/ -v"
echo

# 2. Run unit tests only
echo "2. Run UNIT tests only:"
echo "   pytest tests/unit/auth/ -v"
echo

# 3. Run integration tests only
echo "3. Run INTEGRATION tests only:"
echo "   pytest tests/integration/auth/ -v"
echo

# 4. Run specific test files
echo "4. Run SPECIFIC test files:"
echo "   pytest tests/unit/auth/test_api_key.py -v"
echo "   pytest tests/unit/auth/test_rbac.py -v"
echo "   pytest tests/unit/auth/test_providers.py -v"
echo "   pytest tests/integration/auth/test_auth_routes.py -v"
echo

# 5. Run with coverage
echo "5. Run with COVERAGE report:"
echo "   pytest tests/unit/auth/ tests/integration/auth/ --cov=agent_service.auth --cov-report=html"
echo "   # Open htmlcov/index.html to view report"
echo

# 6. Run specific test class
echo "6. Run SPECIFIC test class:"
echo "   pytest tests/unit/auth/test_api_key.py::TestAPIKeyGeneration -v"
echo

# 7. Run specific test
echo "7. Run SINGLE test:"
echo "   pytest tests/unit/auth/test_api_key.py::TestAPIKeyGeneration::test_generate_api_key_produces_valid_format -v"
echo

# 8. Run with markers
echo "8. Run FAST tests only (unit tests):"
echo "   pytest tests/unit/auth/ -v -m 'not slow'"
echo

# 9. Run in parallel
echo "9. Run tests in PARALLEL (faster):"
echo "   pytest tests/unit/auth/ -n auto"
echo

# 10. Run with verbose output
echo "10. Run with VERBOSE output:"
echo "    pytest tests/unit/auth/ -vv -s"
echo

# Interactive menu
echo "Select an option (1-10) or press Enter to run all tests:"
read -r choice

case $choice in
    1|"")
        echo "Running all auth tests..."
        pytest tests/unit/auth/ tests/integration/auth/ -v
        ;;
    2)
        echo "Running unit tests..."
        pytest tests/unit/auth/ -v
        ;;
    3)
        echo "Running integration tests..."
        pytest tests/integration/auth/ -v
        ;;
    4)
        echo "Select test file:"
        echo "  a) test_api_key.py"
        echo "  b) test_rbac.py"
        echo "  c) test_providers.py"
        echo "  d) test_auth_routes.py"
        read -r file_choice
        case $file_choice in
            a) pytest tests/unit/auth/test_api_key.py -v ;;
            b) pytest tests/unit/auth/test_rbac.py -v ;;
            c) pytest tests/unit/auth/test_providers.py -v ;;
            d) pytest tests/integration/auth/test_auth_routes.py -v ;;
            *) echo "Invalid choice" ;;
        esac
        ;;
    5)
        echo "Running tests with coverage..."
        pytest tests/unit/auth/ tests/integration/auth/ \
            --cov=agent_service.auth \
            --cov-report=html \
            --cov-report=term-missing
        echo
        echo "Coverage report generated in htmlcov/index.html"
        ;;
    6)
        echo "Running API key generation tests..."
        pytest tests/unit/auth/test_api_key.py::TestAPIKeyGeneration -v
        ;;
    7)
        echo "Running single test..."
        pytest tests/unit/auth/test_api_key.py::TestAPIKeyGeneration::test_generate_api_key_produces_valid_format -v
        ;;
    8)
        echo "Running fast tests only..."
        pytest tests/unit/auth/ -v -m 'not slow'
        ;;
    9)
        echo "Running tests in parallel..."
        pytest tests/unit/auth/ -n auto
        ;;
    10)
        echo "Running with verbose output..."
        pytest tests/unit/auth/ -vv -s
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo
echo "=== Tests completed ==="
