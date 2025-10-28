# Prediction Alarm Block (`care/prediction_alarm@v1`)

## Overview

The **Prediction Alarm** block provides intelligent threshold-based alerting for detection counts. It implements a state machine with cooldown periods to prevent alarm spam while ensuring critical events are captured.

## Type

`transformation` - Produces boolean and string outputs for downstream consumption

## Key Features

- **Threshold-based activation**: Triggers when detection count exceeds configurable threshold
- **Hysteresis control**: Prevents oscillating alarms with configurable deactivation threshold
- **Cooldown management**: Enforces minimum time between alarm activations
- **Message templating**: Dynamic message generation with value interpolation
- **State machine**: Clean state transitions (IDLE → FIRING → COOLDOWN)
- **Observable state**: Outputs current state for debugging and monitoring

## Use Cases

- **Occupancy monitoring**: Alert when room capacity exceeds limit
- **Safety zones**: Trigger alarms when unauthorized persons enter restricted areas
- **Production line**: Alert when defect count exceeds threshold
- **Healthcare**: Notify staff when patient count in zone changes
- **Retail**: Track when customer queue length exceeds capacity

## Inputs

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `count` | `int` | Detection count to monitor (typically from `care/detections_count@v1`) | Required |
| `threshold` | `int` | Activation threshold. Alarm triggers when `count >= threshold` | Required |
| `hysteresis` | `int` | Deactivation offset. Alarm resets when `count < (threshold - hysteresis)` | `0` |
| `cooldown_seconds` | `float` | Minimum seconds between alarm activations | `5.0` |
| `alarm_message_template` | `str` | Message template with placeholders: `{count}`, `{threshold}`, `{hysteresis}` | See below |

**Default message template**:
```
"Alert: {count} detection(s) (threshold: {threshold})"
```

## Outputs

| Name | Type | Description |
|------|------|-------------|
| `alarm_active` | `bool` | `True` when alarm is firing, `False` otherwise |
| `alarm_message` | `str` | Formatted alarm message (empty string when alarm inactive) |
| `count_value` | `int` | Pass-through of input count value |
| `state` | `str` | Current state: `"idle"`, `"firing"`, or `"cooldown"` |

## State Machine

```
        count < (threshold - hysteresis)
   ┌────────────────────────────────────┐
   │                                    │
   ▼                                    │
┌──────┐  count >= threshold       ┌────────┐
│ IDLE │  AND cooldown elapsed     │ FIRING │
└──────┘ ────────────────────────> └────────┘
                                        │
                                        │ alarm emitted
                                        ▼
                                   ┌──────────┐
                                   │ COOLDOWN │
                                   └──────────┘
```

### State Transitions

1. **IDLE → FIRING**: `count >= threshold` AND cooldown period elapsed
2. **FIRING → COOLDOWN**: Alarm emitted, cooldown timer starts
3. **COOLDOWN → IDLE**:
   - `count < (threshold - hysteresis)` (immediate reset), OR
   - Cooldown elapsed AND `count < threshold`
4. **COOLDOWN → FIRING**: Cooldown elapsed AND `count >= threshold`

## Example Usage

### Basic Alarm with MQTT

```json
{
  "steps": [
    {
      "type": "ObjectDetectionModel",
      "name": "detector",
      "image": "$inputs.image",
      "model_id": "yolov11n-640",
      "class_filter": ["person"]
    },
    {
      "type": "care/detections_count@v1",
      "name": "count",
      "predictions": "$steps.detector.predictions"
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alarm",
      "count": "$steps.count.count",
      "threshold": 1,
      "cooldown_seconds": 5.0,
      "alarm_message_template": "⚠️ {count} person(s) detected"
    },
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
    },
    {
      "type": "care/mqtt_writer@v1",
      "name": "mqtt_publisher",
      "host": "$inputs.mqtt_host",
      "port": "$inputs.mqtt_port",
      "topic": "$inputs.mqtt_topic",
      "message": "$steps.alarm.alarm_message"
    }
  ]
}
```

### Occupancy Limit with Hysteresis

```json
{
  "type": "care/prediction_alarm@v1",
  "name": "occupancy_alarm",
  "count": "$steps.count.count",
  "threshold": 10,
  "hysteresis": 2,
  "cooldown_seconds": 30.0,
  "alarm_message_template": "🚨 Capacity exceeded: {count}/{threshold} persons"
}
```

**Behavior**:
- Alarm activates when count reaches 10
- Alarm stays active while count >= 10
- Alarm deactivates when count drops below 8 (threshold - hysteresis)
- Minimum 30 seconds between alarms

### Multiple Thresholds

Use multiple alarm blocks for different severity levels:

```json
{
  "steps": [
    {
      "type": "care/prediction_alarm@v1",
      "name": "warning",
      "count": "$steps.count.count",
      "threshold": 5,
      "alarm_message_template": "⚠️ WARNING: {count} persons"
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "critical",
      "count": "$steps.count.count",
      "threshold": 10,
      "alarm_message_template": "🚨 CRITICAL: {count} persons"
    }
  ]
}
```

## Integration Patterns

### With MQTT (recommended)

Combine with `roboflow_core/continue_if@v1` to conditionally trigger MQTT:

```
detections → count → alarm → continue_if → mqtt_writer
                              (if active)
```

### With Webhooks

```json
{
  "type": "roboflow_core/webhook_sink@v1",
  "name": "webhook",
  "url": "$inputs.webhook_url",
  "json_payload": {
    "alarm": "$steps.alarm.alarm_active",
    "message": "$steps.alarm.alarm_message",
    "count": "$steps.alarm.count_value"
  }
}
```

### With Email Notifications

```json
{
  "type": "roboflow_core/email_notification@v1",
  "name": "email",
  "subject": "Detection Alarm",
  "message": "$steps.alarm.alarm_message"
}
```

## Design Philosophy

### Complejidad por Diseño

This block follows the "Complexity by Design" principle:

- **State machine**: Explicit states prevent ambiguous behavior
- **Fail-fast validation**: Threshold constraints enforced at manifest level
- **Single Responsibility**: Only handles alarm logic, not communication
- **Composable**: Outputs designed for integration with any sink
- **Observable**: State output enables debugging and monitoring

### Why Not a Sink?

The block is a **transformation**, not a sink, to maintain:

- **Decoupling**: Alarm logic independent of notification mechanism
- **Reusability**: Same alarm can trigger MQTT, webhook, email, etc.
- **Testability**: Pure logic without I/O side effects
- **Flexibility**: Downstream blocks control when/how to act on alarms

## Troubleshooting

### Alarm fires too frequently

Increase `cooldown_seconds`:

```json
{"cooldown_seconds": 30.0}
```

### Alarm oscillates (on/off/on/off)

Add hysteresis:

```json
{
  "threshold": 5,
  "hysteresis": 2
}
```

This creates a "dead zone" between activation (5) and deactivation (3).

### Alarm never fires

Check:
1. `count` value is reaching threshold (inspect workflow outputs)
2. Cooldown hasn't expired yet
3. State is not stuck in COOLDOWN (check `state` output)

### Messages show literal template

Ensure message template uses correct syntax:

```json
// ✓ Correct
{"alarm_message_template": "Alert: {count} persons"}

// ✗ Wrong (selector syntax)
{"alarm_message_template": "Alert: $steps.count.count persons"}
```

## Performance

- **State overhead**: Minimal (3 variables per block instance)
- **CPU**: Negligible (simple comparisons and string formatting)
- **Memory**: O(1) per video stream
- **Thread-safe**: No shared mutable state between streams

## Related Blocks

- `care/detections_count@v1` - Count detections (typical input)
- `roboflow_core/continue_if@v1` - Conditional flow control
- `care/mqtt_writer@v1` - MQTT notifications
- `roboflow_core/rate_limiter@v1` - Time-based throttling (alternative approach)
- `roboflow_core/data_aggregator@v1` - Analytics over time windows

## Version History

- **v1** (2025-10-28): Initial release with state machine implementation
