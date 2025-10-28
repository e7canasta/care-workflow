# Care Workflow Custom Blocks

Custom workflow blocks para Roboflow Inference workflows, especializados en integraciones industriales y healthcare.

## Instalación y Activación

### 1. Instalar Care Workflow

```bash
pip install -e .
```

### 2. Activar Plugin

**Método 1: Variable de entorno** (recomendado para desarrollo)
```bash
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
```

**Método 2: Dentro del script Python**
```python
import os
os.environ["WORKFLOWS_PLUGINS"] = "care.workflows.care_steps"

from inference import InferencePipeline
# ... resto del código
```

## Blocks Disponibles

### Transformation Blocks

#### `care/detections_count@v1`

Cuenta el número de detecciones en predicciones de modelos.

**Inputs**:
- `predictions` (sv.Detections): Predicciones de object detection, instance segmentation o keypoint detection

**Outputs**:
- `count` (int): Número total de detecciones

**Ejemplo en Workflow JSON**:
```json
{
    "type": "care/detections_count@v1",
    "name": "counter",
    "predictions": "$steps.detector.predictions"
}
```

**Uso con Continue If (Conditional)**:
```json
{
    "steps": [
        {"type": "ObjectDetectionModel", "name": "det", ...},
        {"type": "care/detections_count@v1", "name": "count", "predictions": "$steps.det.predictions"},
        {
            "type": "roboflow_core/continue_if@v1",
            "name": "threshold",
            "condition_statement": {
                "type": "BinaryStatement",
                "left_operand": {"type": "DynamicOperand", "operand_name": "$steps.count.count"},
                "comparator": {"type": "(Number) >"},
                "right_operand": {"type": "StaticOperand", "value": 5}
            },
            "next_steps": ["$steps.alert"]
        }
    ]
}
```

**Características**:
- ✅ Soporta múltiples tipos de predicciones
- ✅ Maneja batches automáticamente
- ✅ Performance: O(1) - solo `len()`

---

### Sink Blocks

#### `care/mqtt_writer@v1`

Publica mensajes a un broker MQTT.

**Inputs**:
- `host` (str): Host del broker MQTT
- `port` (int): Puerto del broker (default: 1883)
- `topic` (str): Topic MQTT donde publicar
- `message` (str): Mensaje a publicar (puede incluir selectores)
- `qos` (int): Quality of Service (0, 1, o 2) - default: 0
- `retain` (bool): Retener mensaje en broker - default: False
- `timeout` (float): Timeout para conexión y publish - default: 0.5
- `username` (str, opcional): Usuario para autenticación
- `password` (str, opcional): Contraseña para autenticación

**Outputs**:
- `error_status` (bool): True si hubo error, False si exitoso
- `message` (str): Mensaje de status/error

**Ejemplo en Workflow JSON**:
```json
{
    "type": "care/mqtt_writer@v1",
    "name": "mqtt_publisher",
    "host": "$inputs.mqtt_host",
    "port": 1883,
    "topic": "care/alerts/detections",
    "message": "Alert: Detected $steps.counter.count persons",
    "qos": 1
}
```

**Características**:
- ✅ Conexión persistente con reconnect automático
- ✅ Thread-safe
- ⚠️ Blocking en connect y publish (ver TODOs para fire-and-forget futuro)
- ✅ Timeout configurable

## Uso en InferencePipeline

### Ejemplo Completo

```python
import os
import json
from inference import InferencePipeline

# Activar plugin
os.environ["WORKFLOWS_PLUGINS"] = "care.workflows.care_steps"

# Definir workflow con custom block
workflow = {
    "version": "1.0",
    "inputs": [
        {"type": "WorkflowImage", "name": "image"},
        {"type": "WorkflowParameter", "name": "mqtt_host"}
    ],
    "steps": [
        {
            "type": "ObjectDetectionModel",
            "name": "detector",
            "image": "$inputs.image",
            "model_id": "yolov11n-640"
        },
        {
            "type": "care/mqtt_writer@v1",
            "name": "mqtt_pub",
            "host": "$inputs.mqtt_host",
            "port": 1883,
            "topic": "detections",
            "message": "Detection count: $steps.detector.predictions"
        }
    ],
    "outputs": [
        {
            "type": "JsonField",
            "name": "mqtt_status",
            "selector": "$steps.mqtt_pub.error_status"
        }
    ]
}

# Inicializar pipeline
pipeline = InferencePipeline.init_with_workflow(
    video_reference="rtsp://localhost:8554/live/1",
    workflow_specification=workflow,
    workflows_parameters={"mqtt_host": "localhost"},
    on_prediction=lambda pred, frame: print(pred)
)

pipeline.start()
pipeline.join()
```

## Testing de Custom Blocks

### Test Manual con Mosquitto

```bash
# 1. Instalar mosquitto
sudo apt-get install mosquitto mosquitto-clients

# 2. Subscribirse al topic (terminal 1)
mosquitto_sub -h localhost -t "care/alerts/#" -v

# 3. Ejecutar workflow (terminal 2)
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
python examples/run_mqtt_detection.py
```

### Verificar Block Cargado

```python
import os
os.environ["WORKFLOWS_PLUGINS"] = "care.workflows.care_steps"

from inference.core.workflows.execution_engine.introspection import blocks_loader

# Listar todos los blocks
blocks = blocks_loader.load_workflow_blocks()
custom_blocks = [b for b in blocks if b.block_source == "care.workflows.care_steps"]

for block in custom_blocks:
    print(f"✅ {block.identifier}")
    manifest = block.manifest_class.model_json_schema()
    print(f"   Type: {manifest['properties']['type']}")
```

## Desarrollo de Nuevos Blocks

### Template Básico

```python
from typing import List, Literal, Type
from pydantic import ConfigDict, Field
from inference.core.workflows.execution_engine.entities.base import OutputDefinition
from inference.core.workflows.execution_engine.entities.types import STRING_KIND
from inference.core.workflows.prototypes.block import (
    BlockResult,
    WorkflowBlock,
    WorkflowBlockManifest,
)

class MyCustomBlockManifest(WorkflowBlockManifest):
    model_config = ConfigDict(
        json_schema_extra={
            "name": "My Custom Block",
            "version": "v1",
            "short_description": "Does something useful",
            "block_type": "sink",  # o "transformation", "visualization", etc.
        }
    )
    type: Literal["my_custom_block@v1"]

    # Inputs aquí
    input_param: str = Field(description="Example input")

    @classmethod
    def describe_outputs(cls) -> List[OutputDefinition]:
        return [
            OutputDefinition(name="result", kind=[STRING_KIND])
        ]

class MyCustomBlock(WorkflowBlock):
    @classmethod
    def get_manifest(cls) -> Type[WorkflowBlockManifest]:
        return MyCustomBlockManifest

    def run(self, input_param: str) -> BlockResult:
        # Tu lógica aquí
        return {"result": f"Processed: {input_param}"}
```

### Registrar en Plugin

```python
# En care_workflow/care_blocks/__init__.py
from care.workflows.care_steps.my_module import MyCustomBlock

def load_blocks():
    return [
        MQTTWriterSinkBlockV1,
        MyCustomBlock,  # Agregar aquí
    ]
```

## Troubleshooting

### Error: "Could not load plugin"

```
PluginLoadingError: It is not possible to load workflow plugin `care.workflows.care_steps`
```

**Solución**: Verificar que `care_workflow` esté instalado
```bash
pip install -e .
```

### Error: "Plugin does not implement load_blocks"

```
PluginInterfaceError: Provided workflow plugin ... do not implement blocks loading interface
```

**Solución**: Verificar que `care_workflow/care_blocks/__init__.py` tiene función `load_blocks()`.

### Block no aparece en workflow

**Verificar**:
1. ✅ `WORKFLOWS_PLUGINS` está configurado
2. ✅ `type` en manifest usa `Literal` correcto
3. ✅ Block está en lista retornada por `load_blocks()`

**Debug**:
```python
import os
os.environ["WORKFLOWS_PLUGINS"] = "care.workflows.care_steps"

from inference.core.workflows.execution_engine.introspection import describe_available_blocks

blocks = describe_available_blocks(dynamic_blocks=[])
custom = [b for b in blocks.blocks if "mqtt_writer" in b.fully_qualified_block_class_name]
print(custom)
```

## Estructura de Archivos

```
care_workflow/care_blocks/
├── __init__.py              # Plugin entry point con load_blocks()
├── README.md                # Esta documentación
└── sinks/
    ├── __init__.py
    └── mqtt_writer/
        ├── __init__.py      # Exports del block
        └── v1.py            # Implementación MQTTWriterSinkBlockV1
```

## Referencias

- [Roboflow Workflows Docs](https://docs.roboflow.com/workflows)
- [Plugin System](https://github.com/roboflow/inference/tree/main/inference/core/workflows)
- Ejemplos: `examples/run_mqtt_detection.py`
- Workflow JSON: `data/workflows/examples/mqtt_detection_alert.json`
