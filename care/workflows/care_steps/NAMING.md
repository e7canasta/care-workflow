# Care Workflow Blocks - Naming Convention

## 📛 Prefijo `care/`

Todos los custom blocks de Care Workflow usan el prefijo `care/` para distinguirlos de los blocks core de Roboflow.

### ✅ Correcto

```json
{
    "type": "care/detections_count@v1",
    "type": "care/mqtt_writer@v1",
    "type": "care/plc_modbus_writer@v1",
    "type": "care/opc_writer@v1"
}
```

### ❌ Incorrecto

```json
{
    "type": "detections_count@v1",           // Falta prefijo
    "type": "mqtt_writer_sink@v1",           // Falta prefijo
    "type": "roboflow_core/mqtt_writer@v1"   // Prefijo incorrecto (reservado)
}
```

---

## 🏷️ Estructura del Type

```
care/<block_name>@<version>
 │      │            │
 │      │            └─ Versión (v1, v2, ...)
 │      └─ Nombre descriptivo (snake_case)
 └─ Namespace de Care Workflow
```

**Ejemplos**:
- `care/detections_count@v1` - Cuenta detecciones
- `care/mqtt_writer@v1` - Publica a MQTT
- `care/plc_modbus_writer@v2` - Escribe a PLC (versión 2)

---

## 📦 Categorías

### Transformations
Blocks que transforman o procesan datos sin side-effects.

```
care/<transformation_name>@v1
```

**Ejemplos**:
- `care/detections_count@v1`
- `care/detections_filter@v1` (futuro)
- `care/roi_classifier@v1` (futuro)

### Sinks
Blocks con side-effects (I/O, networking, storage).

```
care/<destination>_writer@v1
```

**Ejemplos**:
- `care/mqtt_writer@v1`
- `care/plc_modbus_writer@v1`
- `care/opc_writer@v1`
- `care/sql_server_writer@v1`

### Analytics
Blocks de análisis de video/datos.

```
care/<analytics_type>@v1
```

**Ejemplos** (futuros):
- `care/dwell_time_tracker@v1`
- `care/zone_counter@v1`
- `care/anomaly_detector@v1`

---

## 🔄 Versionado

### Cuándo incrementar versión

**v1 → v2**:
- Breaking change en inputs/outputs
- Cambio de comportamiento incompatible
- Deprecación de campos

**Mantener v1**:
- Agregar campos opcionales
- Bug fixes
- Performance improvements
- Cambios internos sin afectar API

### Ejemplo

```python
# v1 - Original
type: Literal["care/mqtt_writer@v1"]
host: str
port: int

# v2 - Breaking change (agrega campo requerido)
type: Literal["care/mqtt_writer@v2"]
host: str
port: int
client_id: str  # ← Nuevo campo REQUERIDO

# v1 - Compatible (campo opcional)
type: Literal["care/mqtt_writer@v1"]
host: str
port: int
client_id: Optional[str] = None  # ← Nuevo campo OPCIONAL
```

---

## 📁 Estructura de Archivos

```
care_workflow/care_blocks/
├── transformations/
│   └── <block_name>/
│       ├── __init__.py
│       ├── v1.py          # type: "care/<block_name>@v1"
│       └── v2.py          # type: "care/<block_name>@v2"
│
├── sinks/
│   └── <destination>_writer/
│       ├── __init__.py
│       └── v1.py          # type: "care/<destination>_writer@v1"
│
└── analytics/
    └── <analytics_name>/
        ├── __init__.py
        └── v1.py          # type: "care/<analytics_name>@v1"
```

---

## 🎯 Registrar en Plugin

```python
# care_workflow/care_blocks/__init__.py

def load_blocks():
    return [
        # Transformations
        DetectionsCountBlockV1,      # care/detections_count@v1
        DetectionsCountBlockV2,      # care/detections_count@v2 (futuro)

        # Sinks
        MQTTWriterBlockV1,           # care/mqtt_writer@v1
        PLCModbusWriterBlockV1,      # care/plc_modbus_writer@v1
        OPCWriterBlockV1,            # care/opc_writer@v1

        # Analytics
        DwellTimeTrackerBlockV1,     # care/dwell_time_tracker@v1 (futuro)
    ]
```

---

## 🚫 Nombres Reservados

**NO usar estos prefijos** (reservados por Roboflow):
- `roboflow_core/...`
- `roboflow_enterprise/...`
- `ObjectDetectionModel`
- `ClassificationModel`
- Cualquier block sin namespace

---

## ✅ Checklist para Nuevo Block

- [ ] Nombre usa prefijo `care/`
- [ ] Versión especificada (`@v1`)
- [ ] Type en manifest usa `Literal["care/...@v1"]`
- [ ] Agregado a `load_blocks()` en `__init__.py`
- [ ] Documentado en `README.md`
- [ ] Test suite actualizado

---

## 📚 Referencias

- **Blocks existentes**: `care_workflow/care_blocks/`
- **Examples**: `data/workflows/examples/`
- **Tests**: `examples/test_mqtt_block.py`
