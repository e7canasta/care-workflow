# Conditional Alarm Block (`care/conditional_alarm@v1`)

## Overview

El **Conditional Alarm** block es el miembro más flexible de la familia de alarm blocks. Usa **UQL (Universal Query Language)** para definir condiciones arbitrarias con state machine y hysteresis.

## Type

`transformation` - Produce outputs booleanos y mensajes basados en condiciones UQL

## Arquitectura

Este block usa el **AlarmEngine** core, que también será usado por los wrappers específicos (`prediction_alarm`, `minimum_threshold_alarm`, `range_alarm`).

```
┌─────────────────────────────────────────┐
│     AlarmEngine (core logic)            │
│  - State machine (IDLE/FIRING/COOLDOWN) │
│  - Hysteresis management                │
│  - Cooldown tracking                    │
│  - Condition evaluation                 │
└─────────────────────────────────────────┘
              ▲
              │ uses
              │
    ┌─────────┴──────────┐
    │                    │
┌───▼──────────┐  ┌─────▼────────┐
│conditional   │  │prediction    │
│_alarm        │  │_alarm        │
│(full UQL)    │  │(wrapper)     │
└──────────────┘  └──────────────┘
```

## Key Features

- **UQL Statements**: Define condiciones arbitrarias usando el mismo sistema que `continue_if`
- **State Machine**: IDLE → FIRING → COOLDOWN (evita spam)
- **Hysteresis Global**: Aplica banda muerta a todas las condiciones
- **Cooldown**: Tiempo mínimo entre re-activaciones
- **Message Templating**: Mensajes dinámicos con placeholders
- **Combine Operators**: AND/OR para múltiples condiciones
- **Observable State**: Output del estado para debugging

## Use Cases

### 1. Multi-Condition Alarms

**Healthcare**: Ratio médicos/pacientes crítico

```json
{
  "type": "care/conditional_alarm@v1",
  "condition_statement": {
    "type": "StatementGroup",
    "statements": [
      {
        "type": "BinaryStatement",
        "left_operand": {"type": "DynamicOperand", "operand_name": "doctors"},
        "comparator": {"type": "(Number) >="},
        "right_operand": {"type": "StaticOperand", "value": 2}
      },
      {
        "type": "BinaryStatement",
        "left_operand": {"type": "DynamicOperand", "operand_name": "patients"},
        "comparator": {"type": "(Number) >="},
        "right_operand": {"type": "StaticOperand", "value": 8}
      }
    ]
  },
  "evaluation_parameters": {
    "doctors": "$steps.count_doctors.count",
    "patients": "$steps.count_patients.count"
  },
  "hysteresis_default": 1.0,
  "cooldown_seconds": 30.0,
  "alarm_message_template": "🚨 RATIO CRÍTICO: {doctors} médicos para {patients} pacientes",
  "combine_operator": "AND"
}
```

**Lógica**:
- **Activa**: `doctors >= 2 AND patients >= 8`
- **Desactiva** (con hysteresis=1): `doctors < 1 OR patients < 7`

### 2. Complex OR Conditions

**Manufacturing**: Alarma si defectos altos O temperatura fuera de rango

```json
{
  "type": "care/conditional_alarm@v1",
  "condition_statement": {
    "type": "StatementGroup",
    "statements": [
      {
        "type": "BinaryStatement",
        "left_operand": {"type": "DynamicOperand", "operand_name": "defects"},
        "comparator": {"type": "(Number) >"},
        "right_operand": {"type": "StaticOperand", "value": 5}
      },
      {
        "type": "BinaryStatement",
        "left_operand": {"type": "DynamicOperand", "operand_name": "temp"},
        "comparator": {"type": "(Number) >"},
        "right_operand": {"type": "StaticOperand", "value": 25}
      }
    ]
  },
  "evaluation_parameters": {
    "defects": "$steps.count_defects.count",
    "temp": "$steps.temp_sensor.value"
  },
  "combine_operator": "OR",
  "alarm_message_template": "⚠️ Defectos: {defects}, Temp: {temp}°C"
}
```

### 3. Custom Business Logic

**Retail**: Alarma si ratio cajeros/clientes es inadecuado

```json
{
  "type": "care/conditional_alarm@v1",
  "condition_statement": {
    "type": "StatementGroup",
    "statements": [
      {
        "type": "BinaryStatement",
        "left_operand": {"type": "DynamicOperand", "operand_name": "queue"},
        "comparator": {"type": "(Number) >"},
        "right_operand": {"type": "StaticOperand", "value": 20}
      },
      {
        "type": "BinaryStatement",
        "left_operand": {"type": "DynamicOperand", "operand_name": "cashiers"},
        "comparator": {"type": "(Number) <"},
        "right_operand": {"type": "StaticOperand", "value": 3}
      }
    ]
  },
  "evaluation_parameters": {
    "queue": "$steps.count_queue.count",
    "cashiers": "$steps.count_cashiers.count"
  },
  "combine_operator": "AND",
  "alarm_message_template": "🛒 Cola larga ({queue}) con pocos cajeros ({cashiers})"
}
```

## Inputs

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `condition_statement` | `StatementGroup` | UQL statement group (igual que `continue_if`) | Required |
| `evaluation_parameters` | `Dict[str, Selector]` | Parámetros para evaluar en las condiciones | Required |
| `hysteresis_default` | `float` | Hysteresis global aplicado a todas las condiciones | `1.0` |
| `cooldown_seconds` | `float` | Segundos mínimos entre alarmas | `5.0` |
| `alarm_message_template` | `str` | Template con placeholders `{param_name}` | `"Alarm triggered"` |
| `combine_operator` | `"AND"` \| `"OR"` | Cómo combinar múltiples statements | `"AND"` |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| `alarm_active` | `bool` | `True` cuando alarma está firing |
| `alarm_message` | `str` | Mensaje formateado (vacío si alarm inactivo) |
| `state` | `str` | Estado actual: `"idle"`, `"firing"`, `"cooldown"` |
| `alarm_count` | `int` | Número de veces que alarma se ha disparado |

## State Machine

```
        Conditions no longer met
   ┌──────────────────────────────────┐
   │                                  │
   ▼                                  │
┌──────┐  Conditions met          ┌────────┐
│ IDLE │  AND cooldown elapsed    │ FIRING │
└──────┘ ──────────────────────> └────────┘
                                      │
                                      │ Alarm emitted
                                      ▼
                                 ┌──────────┐
                                 │ COOLDOWN │
                                 └──────────┘
```

### Hysteresis Application

El `hysteresis_default` se aplica **globalmente** a todas las condiciones:

**Para comparadores ">"** (mayor que):
- Activa: `value > threshold`
- Desactiva: `value < (threshold - hysteresis)`

**Para comparadores "<"** (menor que):
- Activa: `value < threshold`
- Desactiva: `value > (threshold + hysteresis)`

**Ejemplo**:
```json
{
  "condition_statement": {
    "statements": [
      {
        "left_operand": {"operand_name": "count"},
        "comparator": {"type": "(Number) >"},
        "right_operand": {"value": 10}
      }
    ]
  },
  "hysteresis_default": 2.0
}
```

**Comportamiento**:
- Activa cuando `count >= 10`
- Desactiva cuando `count < 8` (10 - 2)

## Workflow Completo

Ver: [`data/workflows/examples/conditional_alarm_doctors_patients.json`](../../data/workflows/examples/conditional_alarm_doctors_patients.json)

**Setup**:
```bash
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
export WORKFLOW_DEFINITION="data/workflows/examples/conditional_alarm_doctors_patients.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/hospital_ward"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"

uv run python examples/run_mqtt_detection.py
```

## Comparison con Otros Blocks

| Feature | `conditional_alarm` | `prediction_alarm` | `continue_if` + `rate_limiter` |
|---------|--------------------|--------------------|-------------------------------|
| **UQL Flexibility** | ✅ Full UQL | ❌ Fixed threshold | ✅ Full UQL |
| **State Machine** | ✅ Built-in | ✅ Built-in | ❌ Manual |
| **Hysteresis** | ✅ Global | ✅ Per-condition | ❌ None |
| **Cooldown** | ✅ Built-in | ✅ Built-in | ✅ Via rate_limiter |
| **Message Template** | ✅ Built-in | ✅ Built-in | ❌ Manual |
| **Ease of Use** | ⚠️ Medium (UQL) | ✅ Easy | ⚠️ Verbose (3 blocks) |

## When to Use

### ✅ Use `conditional_alarm` When:

1. **Multiple conditions** that can't be expressed with simple threshold
2. **AND/OR logic** between different metrics
3. **Custom business rules** (ej: ratio médicos/pacientes)
4. **Complex comparisons** que requieren UQL

### ❌ Don't Use (use simpler blocks instead):

1. **Single threshold**: Usa `prediction_alarm` o `minimum_threshold_alarm`
2. **Range check**: Usa `range_alarm`
3. **No hysteresis needed**: Usa `continue_if` + `rate_limiter`

## Troubleshooting

### Alarm fires too often (flapping)

Incrementa `hysteresis_default`:
```json
{"hysteresis_default": 3.0}
```

### Alarm doesn't fire

- Verifica que `condition_statement` es correcto
- Chequea que `evaluation_parameters` tiene los nombres correctos
- Inspecciona output `state` (debería ser "idle" o "firing")
- Verifica que cooldown no está activo (`state` = "cooldown")

### Message template doesn't interpolate

Asegúrate que placeholders coinciden con `evaluation_parameters`:
```json
{
  "evaluation_parameters": {"count": "..."},
  "alarm_message_template": "Value: {count}"  // ✅ Correct
}
```

## Performance

- **State overhead**: O(1) - un engine por block instance
- **CPU**: Leve overhead por UQL evaluation (similar a `continue_if`)
- **Memory**: O(1) - state mínimo (last_alarm_at, alarm_count)

## Related Blocks

- `prediction_alarm@v1` - Threshold superior simple
- `minimum_threshold_alarm@v1` - Threshold inferior simple *(TODO)*
- `range_alarm@v1` - Doble threshold *(TODO)*
- `roboflow_core/continue_if@v1` - Flow control sin state machine
- `roboflow_core/rate_limiter@v1` - Throttling simple

## Version History

- **v1** (2025-10-28): Initial release con AlarmEngine y UQL support

---

## 🎸 Design Philosophy

**"Complejidad por Diseño"**:
- Engine centralizado (DRY)
- UQL reutiliza infraestructura de Roboflow
- State machine explícito

**"Pragmatismo > Purismo"**:
- Hysteresis global (simple) vs per-statement (complejo)
- Solo implementado cuando hay demanda real de casos multi-condición
- Wrappers simples para casos comunes (80% de uso)

**"Patterns con Propósito"**:
- Si tu caso se puede resolver con `prediction_alarm`, úsalo (más simple)
- Si necesitas lógica compleja, aquí está la herramienta
- No over-engineer con UQL si threshold simple funciona
