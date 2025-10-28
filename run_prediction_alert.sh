export WORKFLOWS_PLUGINS="care.workflows.care_steps"
export WORKFLOW_DEFINITION="data/workflows/examples/prediction_alarm_demo.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/live.3"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"
export MQTT_TOPIC="care/detections/alerts"
export ALARM_THRESHOLD="1"  # Optional, default: 1
export ALARM_COOLDOWN="5.0" # Optional, default: 5.0 seconds

python examples/run_prediction_alarm.py
