# IMPORTANT: Unset any old environment variable
unset WORKFLOWS_PLUGINS

# Run with the CORRECT plugin path
WORKFLOWS_PLUGINS="care.workflows.care_steps" \
  WORKFLOW_DEFINITION="data/workflows/examples/mqtt_detection_alert.json" \
  VIDEO_REFERENCE="rtsp://localhost:8554/live.3" \
  MQTT_HOST="localhost" \
  MQTT_PORT="1883" \
  MQTT_TOPIC="care/detections/alerts" \
  uv run python examples/run_mqtt_detection.py
