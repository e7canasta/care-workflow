# Custom Blocks Quick Start

## 🚀 Setup Rápido

```bash
# 1. Test que el plugin funciona
./scripts/test_blocks.sh

# Deberías ver:
# ✅ PASS - Plugin Loading
# ✅ PASS - Block Registration
# ✅ PASS - Manifest Structure
```

## 📦 Blocks Disponibles

### 1. `care/detections_count@v1`
Cuenta detecciones → Retorna número

```json
{
    "type": "care/detections_count@v1",
    "name": "count",
    "predictions": "$steps.detector.predictions"
}
```

**Output**: `$steps.count.count` (integer)

---

### 2. `care/mqtt_writer@v1`
Publica mensajes a MQTT broker

```json
{
    "type": "care/mqtt_writer@v1",
    "name": "mqtt",
    "host": "localhost",
    "port": 1883,
    "topic": "care/alerts",
    "message": "Detected $steps.count.count persons"
}
```

**Outputs**:
- `$steps.mqtt.error_status` (bool)
- `$steps.mqtt.message` (string)

---

## 🎯 Workflow Ejemplo Completo

Ver: `data/workflows/examples/mqtt_detection_alert.json`

**Flujo**:
```
Video → YOLOv11 Detector → Count Detections → MQTT Alert
```

**Ejecutar**:
```bash
# Opción 1: Con script helper
./scripts/run_mqtt_detection.sh

# Opción 2: Manual
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
export WORKFLOW_DEFINITION="data/workflows/examples/mqtt_detection_alert.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"
export MQTT_TOPIC="care/detections/alerts"

uv run python examples/run_mqtt_detection.py
```

---

## 🧪 Testing

### Test Básico (sin broker MQTT)
```bash
./scripts/test_blocks.sh
```

### Test con Broker MQTT
```bash
# Terminal 1: Broker
mosquitto -v

# Terminal 2: Subscriber (ver mensajes)
mosquitto_sub -h localhost -t "test/care" -v

# Terminal 3: Test
./scripts/test_blocks.sh --with-broker
```

---

## 📚 Documentación Completa

- **Guía detallada**: `docs/CUSTOM_BLOCKS_GUIDE.md`
- **API Reference**: `care_workflow/care_blocks/README.md`
- **Architecture**: `CLAUDE.md` → sección "Custom Workflow Blocks"

---

## 🛠️ Agregar Nuevos Blocks

1. **Crear block** en `care_workflow/care_blocks/<category>/<block_name>/v1.py`

2. **Registrar** en `care_workflow/care_blocks/__init__.py`:
   ```python
   def load_blocks():
       return [
           MQTTWriterSinkBlockV1,
           DetectionsCountBlockV1,
           YourNewBlock,  # ← Agregar aquí
       ]
   ```

3. **Test**: `./scripts/test_blocks.sh`

**Template**: Ver `care_workflow/care_blocks/README.md` → "Desarrollo de Nuevos Blocks"

---

## 🎨 Naming Convention

**Nuestros blocks usan prefijo `care/`**:
- ✅ `care/detections_count@v1`
- ✅ `care/plc_modbus_writer@v1`
- ❌ `roboflow_core/...` (reservado para Roboflow)

**Versionado**: Siempre `@v1`, `@v2`, etc.

---

## 🔧 Files Creados

```
care_workflow/care_blocks/
├── __init__.py                           # Plugin loader (load_blocks())
├── README.md                             # API docs
├── sinks/
│   └── mqtt_writer/
│       └── v1.py                         # care/mqtt_writer@v1
└── transformations/
    └── detections_count/
        └── v1.py                         # care/detections_count@v1

data/workflows/examples/
└── mqtt_detection_alert.json             # Workflow ejemplo

examples/
├── run_mqtt_detection.py                 # Ejecutable
└── test_mqtt_block.py                    # Test suite

scripts/
├── test_blocks.sh                        # Helper test
└── run_mqtt_detection.sh                 # Helper run

docs/
└── CUSTOM_BLOCKS_GUIDE.md                # Guía completa
```

---

## ⚡ Troubleshooting

### Block no se carga

```bash
# Debug
uv run python -c "
import os
os.environ['WORKFLOWS_PLUGINS'] = 'care.workflows.care_steps'
from care.workflows.care_steps import load_blocks
print([b.__name__ for b in load_blocks()])
"

# Debería mostrar:
# ['MQTTWriterSinkBlockV1', 'DetectionsCountBlockV1']
```

### Workflow no reconoce block

**Error común**:
```
Input tag 'care/detections_count@v1' found using 'type' does not match...
```

**Fix**: Verificar que `WORKFLOWS_PLUGINS="care.workflows.care_steps"` está configurado ANTES de ejecutar.

---

## 📞 Support

- **Issues**: Ver `CONTRIBUTING.md`
- **Ejemplos**: `examples/run_mqtt_detection.py`
- **Docs**: `care_workflow/care_blocks/README.md`
