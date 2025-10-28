#!/bin/bash
# Run MQTT detection workflow

set -e

# Configurar plugin
export WORKFLOWS_PLUGINS="care.workflows.care_steps"

# Configurar workflow y video
export WORKFLOW_DEFINITION="${WORKFLOW_DEFINITION:-data/workflows/examples/mqtt_detection_alert.json}"
export VIDEO_REFERENCE="${VIDEO_REFERENCE:-rtsp://localhost:8554/live/1}"

# Configurar MQTT
export MQTT_HOST="${MQTT_HOST:-localhost}"
export MQTT_PORT="${MQTT_PORT:-1883}"
export MQTT_TOPIC="${MQTT_TOPIC:-care/detections/alerts}"

echo "🏥 Care Workflow - MQTT Detection Alert"
echo "========================================"
echo "Plugin: $WORKFLOWS_PLUGINS"
echo "Workflow: $WORKFLOW_DEFINITION"
echo "Video: $VIDEO_REFERENCE"
echo "MQTT: $MQTT_HOST:$MQTT_PORT/$MQTT_TOPIC"
echo "========================================"
echo ""

uv run python examples/run_mqtt_detection.py
