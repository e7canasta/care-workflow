# Guía de Custom Blocks

## Quick Start

### 1️⃣ Activar Plugin

```bash
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
```

### 2️⃣ Verificar Instalación

```bash
python examples/test_mqtt_block.py
```

Deberías ver:
```
✅ PASS - Plugin Loading
✅ PASS - Block Registration
✅ PASS - Manifest Structure
⏭️  PASS - Block Execution (skipped)
```

### 3️⃣ Test con Broker MQTT (Opcional)

**Terminal 1** - Broker:
```bash
mosquitto -v
```

**Terminal 2** - Subscriber:
```bash
mosquitto_sub -h localhost -t "test/care" -v
```

**Terminal 3** - Test:
```bash
python examples/test_mqtt_block.py --with-broker
```

Deberías ver el mensaje en Terminal 2.

### 4️⃣ Ejecutar Workflow Completo

```bash
# Setup
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
export WORKFLOW_DEFINITION="data/workflows/examples/mqtt_detection_alert.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"
export MQTT_TOPIC="care/detections/alerts"

# Ejecutar
python examples/run_mqtt_detection.py
```

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                   Care Workflow System                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐         ┌─────────────────┐               │
│  │ Video Source │────────▶│ InferencePipeline│               │
│  │ (RTSP/File)  │         └────────┬─────────┘               │
│  └──────────────┘                  │                         │
│                                    │                         │
│                           ┌────────▼─────────┐               │
│                           │ Workflow Engine   │               │
│                           └────────┬─────────┘               │
│                                    │                         │
│              ┌─────────────────────┴──────────────────┐      │
│              │                                         │      │
│     ┌────────▼────────┐                     ┌─────────▼──────┐
│     │  Core Blocks     │                     │ Custom Blocks  │
│     │  (Roboflow)      │                     │ (care_blocks/) │
│     ├─────────────────┤                     ├────────────────┤
│     │ • Detection     │                     │ • MQTT Writer  │
│     │ • Classification│                     │ • PLC Modbus   │
│     │ • Tracking      │                     │ • OPC Writer   │
│     │ • Visualization │                     │ • SQL Server   │
│     └─────────────────┘                     └────────────────┘
│              │                                         │      │
│              └─────────────────┬────────────────────┘      │
│                                │                              │
│                       ┌────────▼─────────┐                   │
│                       │  Outputs/Sinks    │                   │
│                       │ • CV2 Display     │                   │
│                       │ • MQTT Publish    │                   │
│                       │ • Industrial I/O  │                   │
│                       └──────────────────┘                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Flujo de Datos: MQTT Detection Alert

```
┌────────┐    ┌──────────┐    ┌─────────┐    ┌──────┐    ┌──────────┐
│ Video  │───▶│ Detector │───▶│ Counter │───▶│ MQTT │───▶│  Broker  │
│ Frame  │    │ (YOLOv11)│    │         │    │Writer│    │(mosquitto)│
└────────┘    └──────────┘    └─────────┘    └──────┘    └──────────┘
                    │                            │
                    │                            │
                    ▼                            ▼
              ┌──────────┐              ┌──────────────┐
              │Detections│              │error_status  │
              │  (N bbox)│              │message       │
              └──────────┘              └──────────────┘
```

## Estructura del Plugin

```
care_workflow/care_blocks/
│
├── __init__.py                    # Plugin entry point
│   └── load_blocks() → List[WorkflowBlock]
│
└── sinks/
    ├── __init__.py
    │
    ├── mqtt_writer/
    │   ├── __init__.py
    │   └── v1.py                   # MQTTWriterSinkBlockV1
    │       ├── BlockManifest       # Pydantic schema
    │       │   ├── type: Literal["care/mqtt_writer@v1"]
    │       │   ├── host, port, topic, message
    │       │   └── describe_outputs()
    │       │
    │       └── MQTTWriterSinkBlockV1
    │           ├── get_manifest()
    │           └── run() → BlockResult
    │
    ├── opc_writer/
    ├── PLC_modbus/
    └── microsoft_sql_server/
```

## Ciclo de Vida del Plugin

### Load Time (Startup)

```python
# 1. Environment Setup
os.environ["WORKFLOWS_PLUGINS"] = "care.workflows.care_steps"

# 2. InferencePipeline Init
pipeline = InferencePipeline.init_with_workflow(...)

# 3. Plugin Discovery
blocks_loader.get_plugin_modules()
# → ["care.workflows.care_steps"]

# 4. Dynamic Import
importlib.import_module("care.workflows.care_steps")

# 5. Load Blocks
module.load_blocks()
# → [MQTTWriterSinkBlockV1, ...]

# 6. Registration
for block in blocks:
    validate_manifest(block.get_manifest())
    register(block)
```

### Run Time (Cada Frame)

```python
# 1. Frame llega al pipeline
video_frame = capture_frame()

# 2. Workflow execution
for step in workflow["steps"]:
    if step["type"] == "care/mqtt_writer@v1":
        # 3. Resolve inputs
        host = resolve_selector(step["host"])
        message = resolve_selector(step["message"])

        # 4. Execute block
        block = get_registered_block("care/mqtt_writer@v1")
        result = block.run(host=host, message=message, ...)

        # 5. Store outputs
        outputs["mqtt_pub.error_status"] = result["error_status"]
```

## Troubleshooting

### ❌ Plugin no carga

**Síntoma**:
```
PluginLoadingError: It is not possible to load workflow plugin
```

**Debug**:
```bash
# Verificar instalación
python -c "import care.workflows.care_steps; print(care.workflows.care_steps.__file__)"

# Verificar load_blocks()
python -c "from care.workflows.care_steps import load_blocks; print(load_blocks())"
```

**Solución**:
```bash
pip install -e .
```

---

### ❌ Block no aparece en workflow

**Síntoma**:
```
Workflow execution failed: Unknown block type 'care/mqtt_writer@v1'
```

**Debug**:
```python
import os
os.environ["WORKFLOWS_PLUGINS"] = "care.workflows.care_steps"

from inference.core.workflows.execution_engine.introspection import describe_available_blocks

blocks = describe_available_blocks(dynamic_blocks=[])
mqtt = [b for b in blocks.blocks if "mqtt" in b.manifest_type_identifier]
print(mqtt)
```

**Solución**: Verificar que `type: Literal["care/mqtt_writer@v1"]` en manifest coincide con el usado en JSON.

---

### ❌ MQTT timeout

**Síntoma**:
```
error_status: True
message: Failed to connect to MQTT broker: Connection timeout
```

**Debug**:
```bash
# Test broker
telnet localhost 1883

# Test publish manual
mosquitto_pub -h localhost -t "test" -m "hello"
```

**Solución**:
- Verificar broker corriendo: `mosquitto -v`
- Aumentar timeout en workflow: `"timeout": 2.0`
- Verificar firewall/network

---

### ⚠️ Blocking en publish

**Síntoma**: Pipeline se congela en frames con muchas detecciones.

**Contexto**: `care/mqtt_writer@v1` usa blocking I/O (línea 181 de v1.py):
```python
res.wait_for_publish(timeout=timeout)  # TODO: blocking
```

**Workaround temporal**:
1. Aumentar timeout: `"timeout": 0.1`
2. Reducir QoS: `"qos": 0`
3. Usar throttling: Agregar step de rate limiting antes del MQTT block

**Fix futuro**: Implementar fire-and-forget pattern (ver TODOs en código).

## Ejemplos de Workflows

### 1. Alert Simple

```json
{
    "steps": [
        {"type": "ObjectDetectionModel", "name": "det", ...},
        {
            "type": "care/mqtt_writer@v1",
            "name": "alert",
            "host": "localhost",
            "port": 1883,
            "topic": "alerts",
            "message": "Detection!"
        }
    ]
}
```

### 2. Alert con Conteo

```json
{
    "steps": [
        {"type": "ObjectDetectionModel", "name": "det", ...},
        {"type": "roboflow_core/detections_number@v1", "name": "count", ...},
        {
            "type": "care/mqtt_writer@v1",
            "name": "alert",
            "message": "Count: $steps.count.count"
        }
    ]
}
```

### 3. Alert Condicional (con Continue If)

```json
{
    "steps": [
        {"type": "ObjectDetectionModel", "name": "det", ...},
        {"type": "roboflow_core/detections_number@v1", "name": "count", ...},
        {
            "type": "roboflow_core/continue_if@v1",
            "name": "gate",
            "condition_statement": {
                "type": "StatementGroup",
                "operator": "and",
                "statements": [
                    {
                        "type": "BinaryStatement",
                        "left_operand": {"type": "DynamicOperand", "operand_name": "$steps.count.count"},
                        "comparator": {"type": "(Number) >"},
                        "right_operand": {"type": "StaticOperand", "value": 5}
                    }
                ]
            },
            "next_steps": ["$steps.alert"]
        },
        {
            "type": "care/mqtt_writer@v1",
            "name": "alert",
            "message": "ALERT: More than 5 detections!"
        }
    ]
}
```

## Próximos Pasos

1. **Testing**: Ejecutar `python examples/test_mqtt_block.py --with-broker`
2. **Integration**: Probar workflow completo con video real
3. **Custom Blocks**: Implementar otros sinks (OPC, PLC, SQL)
4. **Optimization**: Evaluar fire-and-forget para reducir latencia

## Referencias

- README completo: `care_workflow/care_blocks/README.md`
- Ejemplo ejecutable: `examples/run_mqtt_detection.py`
- Test suite: `examples/test_mqtt_block.py`
- Workflow JSON: `data/workflows/examples/mqtt_detection_alert.json`
