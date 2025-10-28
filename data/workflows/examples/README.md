# Example Workflows

This directory contains example workflow definitions demonstrating Care Workflow custom blocks.

## Available Workflows

### `mqtt_detection_alert.json`

**Purpose**: Intelligent alarm system with detection counting, threshold-based triggering, and MQTT notifications.

**Custom Blocks Used**:
- `care/detections_count@v1` - Count detected persons
- `care/prediction_alarm@v1` - Trigger alarms with cooldown and hysteresis
- `care/mqtt_writer@v1` - Publish alerts to MQTT broker

**Features**:
- ✅ Prevents alarm spam with 5-second cooldown
- ✅ Only publishes when alarm is active (not every frame)
- ✅ State machine control (IDLE → FIRING → COOLDOWN)
- ✅ Formatted alarm messages

**Usage**:
```bash
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
export WORKFLOW_DEFINITION="data/workflows/examples/mqtt_detection_alert.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"
export MQTT_TOPIC="care/detections/alerts"

uv run python examples/run_mqtt_detection.py
```

**Monitor alerts**:
```bash
mosquitto_sub -h localhost -t "care/detections/alerts" -v
```

**Expected behavior**:
- When person detected: Publishes "⚠️ 1 persona(s) detectada(s)"
- Cooldown: 5 seconds minimum between alerts
- When no persons: No MQTT messages (alarm stays idle)

---

### `prediction_alarm_demo.json`

**Purpose**: Full demonstration of the Prediction Alarm block with configurable parameters.

**Custom Blocks Used**:
- `care/detections_count@v1` - Count detections
- `care/prediction_alarm@v1` - Intelligent alarm triggering
- `care/mqtt_writer@v1` - MQTT notifications

**Features**:
- ✅ Runtime-configurable threshold via `ALARM_THRESHOLD`
- ✅ Runtime-configurable cooldown via `ALARM_COOLDOWN`
- ✅ Flow control with `roboflow_core/continue_if@v1`
- ✅ State visibility in outputs

**Usage**:
```bash
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
export WORKFLOW_DEFINITION="data/workflows/examples/prediction_alarm_demo.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"
export MQTT_TOPIC="care/detections/alerts"
export ALARM_THRESHOLD="2"      # Alert when ≥2 persons
export ALARM_COOLDOWN="10.0"    # 10 seconds between alarms

uv run python examples/run_prediction_alarm.py
```

**Workflow parameters**:
- `alarm_threshold` (default: 1): Minimum detections to trigger alarm
- `alarm_cooldown` (default: 5.0): Seconds between alarm activations

**Outputs**:
- `person_count`: Current detection count
- `alarm_active`: Boolean indicating if alarm is firing
- `alarm_state`: State machine state ("idle", "firing", "cooldown")
- `alarm_message`: Formatted alarm message

---

## Workflow Architecture

### Basic Detection → Count → MQTT

```
Video → ObjectDetectionModel → DetectionsCount → MQTT
                 (person)           (count)      (every frame)
```

**Problem**: Spams MQTT with messages every frame, even when count is 0.

### Intelligent Alarm System (Recommended)

```
Video → ObjectDetectionModel → DetectionsCount → PredictionAlarm → ContinueIf → MQTT
                 (person)           (count)      (state machine)   (if active)
```

**Benefits**:
- ✅ Only publishes when alarm is active
- ✅ Cooldown prevents spam
- ✅ Hysteresis prevents flapping
- ✅ Observable state for debugging

---

## Custom Blocks Reference

### `care/detections_count@v1`

Counts number of detections in predictions.

**Inputs**:
- `predictions` (sv.Detections): Model predictions

**Outputs**:
- `count` (int): Number of detections

### `care/prediction_alarm@v1`

Intelligent threshold-based alarm with state machine.

**Inputs**:
- `count` (int): Detection count
- `threshold` (int): Activation threshold
- `hysteresis` (int): Deactivation offset (default: 0)
- `cooldown_seconds` (float): Minimum time between alarms (default: 5.0)
- `alarm_message_template` (str): Message template with `{count}`, `{threshold}` placeholders

**Outputs**:
- `alarm_active` (bool): TRUE when alarm is firing
- `alarm_message` (str): Formatted message
- `count_value` (int): Pass-through count
- `state` (str): Current state ("idle", "firing", "cooldown")

**State Machine**:
```
IDLE → FIRING: count >= threshold AND cooldown elapsed
FIRING → COOLDOWN: Alarm emitted
COOLDOWN → IDLE: count < (threshold - hysteresis) OR cooldown elapsed
```

### `care/mqtt_writer@v1`

Publishes messages to MQTT broker.

**Inputs**:
- `host` (str): MQTT broker host
- `port` (int): MQTT broker port
- `topic` (str): MQTT topic
- `message` (str): Message to publish
- `qos` (int): Quality of Service (default: 0)
- `retain` (bool): Retain flag (default: false)
- `timeout` (float): Connection timeout (default: 0.5)

**Outputs**:
- `error_status` (bool): TRUE if error occurred
- `message` (str): Status message

---

## Integration Patterns

### With Flow Control

Use `roboflow_core/continue_if@v1` to conditionally execute downstream blocks:

```json
{
  "type": "roboflow_core/continue_if@v1",
  "name": "check_alarm",
  "condition_statement": {
    "type": "StatementGroup",
    "statements": [
      {
        "type": "BinaryStatement",
        "left_operand": {
          "type": "DynamicOperand",
          "operand_name": "alarm_active"
        },
        "comparator": {"type": "(Boolean) =="},
        "right_operand": {"type": "StaticOperand", "value": true}
      }
    ]
  },
  "evaluation_parameters": {
    "alarm_active": "$steps.alarm.alarm_active"
  },
  "next_steps": ["$steps.mqtt_publisher"]
}
```

### Multiple Severity Levels

Create multiple alarm blocks with different thresholds:

```json
{
  "steps": [
    {"type": "care/prediction_alarm@v1", "name": "warning", "threshold": 5},
    {"type": "care/prediction_alarm@v1", "name": "critical", "threshold": 10}
  ]
}
```

### With Data Aggregation

Combine with `roboflow_core/data_aggregator@v1` for analytics:

```json
{
  "type": "roboflow_core/data_aggregator@v1",
  "name": "stats",
  "data": {
    "alarm_count": "$steps.alarm.alarm_active"
  },
  "aggregation_mode": {
    "alarm_count": ["sum", "count"]
  },
  "interval": 60,
  "interval_unit": "seconds"
}
```

---

## Troubleshooting

### No MQTT messages received

Check:
1. MQTT broker is running: `systemctl status mosquitto` or `docker ps`
2. Environment variables are set correctly
3. Alarm threshold is appropriate (try threshold=0 for testing)
4. Check logs for connection errors

### Too many alerts

Increase `cooldown_seconds` or adjust `threshold`:

```bash
export ALARM_COOLDOWN="30.0"
export ALARM_THRESHOLD="3"
```

### Alarm oscillates

Add hysteresis in the workflow JSON:

```json
{
  "type": "care/prediction_alarm@v1",
  "threshold": 5,
  "hysteresis": 2
}
```

Alarm activates at 5, deactivates at 3 (5-2).

---

## Related Documentation

- [Prediction Alarm Block Documentation](../../docs/blocks/prediction_alarm.md)
- [CLAUDE.md](../../CLAUDE.md) - Project architecture and conventions
- [Custom Blocks README](../../care_workflow/care_blocks/README.md)
