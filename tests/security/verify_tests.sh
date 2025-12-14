#!/bin/bash
# Security Tests Verification Script

echo "═══════════════════════════════════════════════════════════════"
echo "  Security Tests Implementation Verification"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check files exist
echo "📁 Checking test files..."
files=(
    "test_headers.py"
    "test_cors.py"
    "test_rate_limit.py"
    "test_injection.py"
    "test_auth_bypass.py"
    "conftest.py"
    "README.md"
    "IMPLEMENTATION_SUMMARY.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file")
        echo "  ✓ $file ($lines lines)"
    else
        echo "  ✗ $file (missing)"
    fi
done

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "📊 Test Statistics"
echo "───────────────────────────────────────────────────────────────"

# Count tests
total_tests=$(grep -r "async def test_" *.py 2>/dev/null | wc -l)
echo "  Total test methods: $total_tests"

# Count test classes
total_classes=$(grep -r "^class Test" *.py 2>/dev/null | wc -l)
echo "  Total test classes: $total_classes"

# Line counts
total_lines=$(cat *.py 2>/dev/null | wc -l)
echo "  Total Python code: $total_lines lines"

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "📋 Test Categories"
echo "───────────────────────────────────────────────────────────────"

for file in test_*.py; do
    if [ -f "$file" ]; then
        test_count=$(grep -c "async def test_" "$file")
        class_count=$(grep -c "^class Test" "$file")
        echo "  $file:"
        echo "    - $class_count test classes"
        echo "    - $test_count test methods"
    fi
done

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "✅ Verification Complete"
echo "───────────────────────────────────────────────────────────────"
echo ""
echo "To run security tests:"
echo "  pytest tests/security/ -v"
echo ""
echo "For more information, see:"
echo "  - README.md (comprehensive documentation)"
echo "  - IMPLEMENTATION_SUMMARY.md (implementation details)"
echo ""
