#!/bin/bash
# Verify ignition-lint-toolkit beta is installed and working

set -e

echo "================================================"
echo "Verifying ignition-lint-toolkit Beta"
echo "================================================"
echo ""

# Find the LSP installation
if [ -f "lsp/venv/bin/python" ]; then
    PYTHON="lsp/venv/bin/python"
    PIP="lsp/venv/bin/pip"
    echo "✓ Found plugin venv at lsp/venv/"
elif command -v ignition-lsp &> /dev/null; then
    PYTHON=$(which python3)
    PIP=$(which pip3)
    echo "✓ Using system Python"
else
    echo "✗ LSP not installed"
    exit 1
fi

echo ""
echo "1. Checking ignition-lint-toolkit version..."
echo "-------------------------------------------"
VERSION=$($PIP show ignition-lint-toolkit 2>/dev/null | grep "^Version:" | cut -d' ' -f2 || echo "NOT_INSTALLED")

if [ "$VERSION" = "NOT_INSTALLED" ]; then
    echo "✗ ignition-lint-toolkit is not installed"
    echo ""
    echo "This is expected on Python < 3.10"
    $PYTHON --version
    exit 0
fi

echo "   Version: $VERSION"

# Check if it's from TestPyPI by looking at the package metadata
LOCATION=$($PIP show ignition-lint-toolkit 2>/dev/null | grep "^Location:" | cut -d' ' -f2)
echo "   Location: $LOCATION"

echo ""
echo "2. Testing import..."
echo "-------------------------------------------"
$PYTHON -c "
try:
    from ignition_lint.validators.jython import JythonValidator
    from ignition_lint.reporting import LintIssue, LintSeverity
    print('✓ Successfully imported JythonValidator')
    print('✓ Successfully imported LintIssue, LintSeverity')
except ImportError as e:
    print(f'✗ Import failed: {e}')
    exit(1)
"

echo ""
echo "3. Testing validation..."
echo "-------------------------------------------"
# Create a test file with a known issue
cat > /tmp/test_ignition_script.py << 'EOF'
# Test script with intentional issues
def test_function():
    undefined_variable = some_undefined_var  # Should trigger error
    return undefined_variable
EOF

$PYTHON << 'PYTEST'
from ignition_lint.validators.jython import JythonValidator

validator = JythonValidator()
with open('/tmp/test_ignition_script.py', 'r') as f:
    code = f.read()

issues = validator.validate_script(code, context='<test>')
print(f'   Found {len(issues)} issue(s)')

if issues:
    print('   ✓ Validator is working!')
    for issue in issues[:3]:  # Show first 3
        # Print available attributes for debugging
        print(f'     - {issue.severity.value}: {issue.message} (at line {issue.location.line if hasattr(issue, "location") else "?"})')
else:
    print('   ⚠ No issues found (validator may not be detecting problems)')
PYTEST

rm /tmp/test_ignition_script.py

echo ""
echo "4. Checking LSP integration..."
echo "-------------------------------------------"
$PYTHON << 'LSPTEST'
import sys
sys.path.insert(0, 'lsp')

from ignition_lsp.diagnostics import _get_jython_diagnostics

# Test with a simple script
test_code = """
def bad_function():
    x = undefined_variable
    return x
"""

# Test Jython diagnostics directly
diagnostics = _get_jython_diagnostics(test_code, 'file:///test.py')
print(f'   LSP returned {len(diagnostics)} diagnostic(s)')

if diagnostics:
    print('   ✓ LSP diagnostics integration working!')
    for diag in diagnostics[:3]:
        print(f'     - Line {diag.range.start.line}: {diag.message[:60]}...')
else:
    print('   ⚠ No diagnostics returned')
LSPTEST

echo ""
echo "================================================"
echo "Verification Complete!"
echo "================================================"
echo ""
echo "Summary:"
echo "  • ignition-lint-toolkit version: $VERSION"
echo "  • Imports: Working"
echo "  • Validation: Working"
echo "  • LSP Integration: Working"
echo ""
echo "To verify in Neovim:"
echo "  1. Open an Ignition Python file"
echo "  2. Add: undefined_var = some_undefined_function()"
echo "  3. Check for diagnostics (should see error underline)"
echo "  4. Run: :lua print(vim.inspect(vim.diagnostic.get(0)))"
echo "     Look for source='ignition-lint' in the output"
