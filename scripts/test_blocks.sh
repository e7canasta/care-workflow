#!/bin/bash
# Test Care Workflow custom blocks

set -e

export WORKFLOWS_PLUGINS="care.workflows.care_steps"

echo "🧪 Testing Care Workflow Custom Blocks"
echo "========================================"
echo ""

uv run python examples/test_mqtt_block.py "$@"
