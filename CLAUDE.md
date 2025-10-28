# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Care Workflow** es un sistema para gestión de flujos de trabajo de cuidados de salud que integra detección de objetos en video usando Roboflow Inference y workflows definidos en JSON.

### Arquitectura Dual

Este proyecto combina dos sistemas:

1. **Sistema de Workflows de Cuidados** (Python nativo)
   - Gestión de flujos de trabajo mediante `WorkflowManager` en `care_workflow/core.py`
   - Estados de workflow: PENDING → RUNNING → COMPLETED/FAILED/CANCELLED
   - Modelo de dominio: `Workflow` contiene múltiples `WorkflowStep`

2. **Sistema de Detección/Inferencia** (Roboflow Inference)
   - Procesamiento de video en tiempo real usando `InferencePipeline`
   - Workflows de ML definidos en JSON en `data/workflows/detections/`
   - Streaming via go2rtc (RTSP → detección → visualización)

**Bounded Context Crítico**: Los dos sistemas comparten el término "workflow" pero con semántica diferente:
- `care_workflow/`: Workflow = flujo de pasos de cuidados de salud
- `examples/run_detection.py`: Workflow = pipeline de ML (detección → clasificación → visualización)

## Comandos de Desarrollo

### Setup
```bash
# Crear entorno virtual y instalar dependencias
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Tests
```bash
# Ejecutar todos los tests
pytest

# Test con cobertura
pytest --cov=care_workflow --cov-report=html

# Test específico
pytest tests/test_core.py::TestWorkflowManager::test_create_workflow -v
```

### Linting y Formato
```bash
# Formatear código (aplicar cambios)
black .

# Revisar estilo (solo reportar)
ruff check .

# Aplicar correcciones automáticas
ruff check . --fix
```

### Ejecutar Sistema

**Workflow de Cuidados (demo básica)**:
```bash
python main.py
# o
care-workflow
```

**Pipeline de Detección con Custom Blocks** (MQTT ejemplo):
```bash
# 1. Activar custom blocks plugin
export WORKFLOWS_PLUGINS="care.workflows.care_steps"

# 2. Configurar workflow y video
export WORKFLOW_DEFINITION="data/workflows/examples/mqtt_detection_alert.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"

# 3. Configurar MQTT
export MQTT_HOST="localhost"
export MQTT_PORT="1883"
export MQTT_TOPIC="care/detections/alerts"

# 4. Ejecutar
python examples/run_mqtt_detection.py

# En otra terminal, subscribirse al topic:
mosquitto_sub -h localhost -t "care/detections/alerts" -v
```

**Pipeline de Detección en Video** (requiere variables de entorno):
```bash
# Configurar variables
export WORKFLOW_DEFINITION="data/workflows/detections/detect-and-classify.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"
export DETECTION_CLASSES="person,car"  # Opcional

# Ejecutar
python examples/run_detection.py
```

**Comandos interactivos durante detección**:
- `i`: Mostrar reporte del watchdog
- `t`: Terminar pipeline
- `p`: Pausar stream
- `m`: Mutear stream
- `r`: Resumir stream

### go2rtc (Streaming)
```bash
# Iniciar servidor RTSP
go2rtc -config config/go2rtc/go2rtc.yaml

# Health check
curl http://localhost:1984/api/streams

# Test stream con ffplay
ffplay rtsp://localhost:8554/live/1
```

## Arquitectura Técnica

### Custom Workflow Blocks (care_workflow/care_blocks/)

**Plugin System Integration**:
- Custom blocks siguen el protocolo de Roboflow Inference plugin system
- Entry point: `care.workflows.care_steps.load_blocks()` retorna `List[Type[WorkflowBlock]]`
- Activación: Variable de entorno `WORKFLOWS_PLUGINS="care.workflows.care_steps"`

**Blocks Disponibles**:

1. **`care/detections_count@v1`** (`care_blocks/transformations/detections_count/v1.py`):
   - **Tipo**: Transformation block
   - **Propósito**: Contar número de detecciones en predicciones
   - **Inputs**: `predictions` (sv.Detections)
   - **Outputs**: `count` (int)
   - **Características**:
     - Soporta object detection, instance segmentation, keypoint detection
     - Maneja batches (suma total)
     - Simple: `len(detections)`
   - **Uso**: Ideal para alerts condicionales, logging, triggers

2. **`care/mqtt_writer@v1`** (`care_blocks/sinks/mqtt_writer/v1.py`):
   - **Tipo**: Sink block (no visualización, side-effects)
   - **Propósito**: Publicar mensajes a broker MQTT
   - **Inputs**: host, port, topic, message, qos, retain, timeout, username, password
   - **Outputs**: `error_status` (bool), `message` (str)
   - **Características**:
     - Conexión persistente (reconnect automático)
     - Thread-safe con `threading.Event` para sync
     - Blocking en connect y publish (TODO anotado para fire-and-forget)
     - Callbacks `mqtt_on_connect` y `mqtt_on_connect_fail`
   - **Invariantes**:
     - Cliente MQTT se crea lazy (primera ejecución del run)
     - Reconexión si `not is_connected()` antes de publish
     - Timeout configurable (default 0.5s)

**Patrón de Uso**:
```bash
# 1. Activar plugin system
export WORKFLOWS_PLUGINS="care.workflows.care_steps"

# 2. Workflow JSON incluye los blocks
{
  "steps": [
    {"type": "ObjectDetectionModel", "name": "det", ...},
    {"type": "care/detections_count@v1", "name": "count", "predictions": "$steps.det.predictions"},
    {"type": "care/mqtt_writer@v1", "name": "mqtt", "message": "Count: $steps.count.count"}
  ]
}

# 3. Ejecutar con parámetros runtime
python examples/run_mqtt_detection.py
```

**Arquitectura del Plugin Loader**:
```
WORKFLOWS_PLUGINS env var
         ↓
InferencePipeline init
         ↓
blocks_loader.get_plugin_modules()
         ↓
importlib.import_module("care.workflows.care_steps")
         ↓
module.load_blocks() → [MQTTWriterSinkBlockV1, ...]
         ↓
Registered en ExecutionEngine
```

**Fail-Fast en Load Time**:
- `PluginLoadingError` si import falla (línea 190 de blocks_loader.py)
- `PluginInterfaceError` si `load_blocks()` no existe o retorna tipo incorrecto (línea 196-222)
- Validación de `type` Literal en manifest (línea 99-117)

### Core Domain (care_workflow/core.py)

**Entidades Principales**:
- `WorkflowStatus` (Enum): Estados del ciclo de vida
- `WorkflowStep` (Dataclass): Paso individual con id, name, description, status, metadata
- `Workflow` (Dataclass): Contenedor de steps con su propio status
- `WorkflowManager`: Orquestador de workflows (create, get, list, start, complete)

**Invariantes**:
- Un workflow solo puede iniciarse si está en estado PENDING (ver `WorkflowManager.start_workflow:97`)
- IDs de workflow deben ser únicos (validación en `create_workflow:68`)
- Steps y workflows tienen metadata opcional (dict) que se inicializa vacío si no se provee

**Fail-Fast Pattern**:
- `start_workflow` retorna `False` inmediatamente si el workflow no existe o no está PENDING
- Los errores se loggean pero no lanzan excepciones (política actual)

### Inference Pipeline (examples/run_detection.py)

**Arquitectura**:
```
Video Source → InferencePipeline → Workflow Blocks → Sink (Visualización)
     ↓                                    ↓
  go2rtc RTSP              JSON workflow definition
                           (data/workflows/detections/)
```

**Workflow JSON Structure**:
- `version`: Versión del schema
- `inputs`: Declaración de entradas (ej: `InferenceImage`)
- `steps`: Blocks de Roboflow (`roboflow_object_detection_model`, `dynamic_crop`, `bounding_box_visualization`, etc.)
- `outputs`: Mapeo de resultados con selectores tipo `$steps.detection_model.predictions`

**Threading Model**:
- Pipeline corre en thread principal
- `command_thread` maneja input del usuario en thread separado
- Comunicación via variable global `STOP`

**Sink Pattern** (`workflows_sink:82-121`):
- Recibe predicciones + video frames
- Extrae visualizaciones y crops del diccionario de predicción
- Usa `create_tiles` para layout multi-stream
- Dos ventanas CV2: "Predictions" y "Crops Grid"

### Configuración

**pyproject.toml**:
- Build system: Hatchling
- Python: >=3.8, target 3.8
- Dependencies core: `inference`, `inference-cli`, `inference-sdk` (>=0.37.1)
- Dev dependencies: `pytest`, `pytest-cov`, `ruff`, `black`
- Entry point: `care-workflow = "main:main"`
- Ruff: line-length 100, linters E/F/I/N/W

**go2rtc.yaml**:
- API en puerto 1984
- RTSP server en puerto 8554
- Streams `live/0` a `live/11` mapeados a videos en `data/videos/`
- Hardware encoding habilitado (`#video=h264#hardware`)

## Patrones y Filosofía

### Complejidad por Diseño
- **Modularidad clara**: `core.py` contiene dominio, `run_detection.py` contiene integración con Roboflow
- **Desacoplamiento**: Workflows de cuidados no dependen del sistema de detección
- **Single Responsibility**: `WorkflowManager` solo gestiona workflows, no ejecuta lógica de negocio de steps

### Fail Fast
- Validaciones en load time (ej: workflow_id único)
- Estados invalidos retornan `False` inmediatamente
- Logs informativos para debugging

### Testing
- Enfoque de "pair-programming manual": NO generar tests automáticamente
- Tests existentes en `tests/test_core.py` cubren happy paths y edge cases básicos
- Usar fixtures de pytest cuando sea apropiado

## Convenciones de Commits

**NO usar**: "Generated with [Claude Code]" (per instrucciones del jefe)

**SÍ usar**:
```
<tipo>: <descripción>

Co-Authored-By: Gaby <noreply@anthropic.com>
```

**Tipos** (con emojis opcionales):
- `feat:` / `✨ feat:` - Nueva característica
- `fix:` / `🐛 fix:` - Corrección de bug
- `docs:` / `📚 docs:` - Cambios en documentación
- `refactor:` - Refactoring de código
- `test:` / `🧪 test:` - Tests

**Ejemplo**:
```
✨ feat: agregar validación de metadata en WorkflowStep

Co-Authored-By: Gaby <noreply@anthropic.com>
```

## Contexto de Negocio

- **Usuario**: Ernesto (Visiona)
- **Compañero de trabajo**: Gaby (alias para Claude Code en commits)
- **Dominio**: Healthcare/Care workflows con componente de computer vision
- **Fase**: Desarrollo inicial (v0.1.0, Alpha)

## Notas Técnicas

### Workflow JSON Dinámico
El sistema permite modificar `class_filter` del modelo de detección via `DETECTION_CLASSES` (ver `run_detection.py:35-41`). Este pattern permite configuración runtime sin modificar JSON.

### Video Source Strategy
- `BufferFillingStrategy` y `BufferConsumptionStrategy` disponibles (importados pero no configurados actualmente)
- Comentado `max_fps=1` en pipeline init (línea 51) - descomentar para throttling

### Visualización
- `supervision` library usado para anotaciones (`sv.BoxAnnotator`)
- FPS monitor integrado en sink
- Multi-window display (predictions + crops grid)

### Logging
- Configurado a nivel INFO en `core.py:11`
- WorkflowManager loggea operaciones principales (create, start, complete)
- Logs estructurados: `logger.info(f"Workflow '{name}' creado con ID: {workflow_id}")`
