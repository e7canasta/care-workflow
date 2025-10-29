# Local ONNX Models

Este directorio contiene modelos ONNX locales que pueden ser cargados sin hacer llamadas a la API de Roboflow.

## Arquitectura

Los modelos locales se definen mediante **manifests JSON** que describen:
- Identificador del modelo (`model_id`)
- Tipo de tarea (`task_type`: object-detection, pose-estimation, etc.)
- Ruta al archivo ONNX
- Nombres de clases
- Dimensiones de entrada
- Metadata adicional (opcional)

### Ventajas

- ✅ **Sin dependencia de API**: No requiere conexión a Roboflow
- ✅ **Modelos cuantizados**: Soporta INT8, FP16 para menor latencia
- ✅ **Múltiples tamaños**: YOLOv11n-320, YOLOv11s-640, etc.
- ✅ **Fallback automático**: Si el modelo local no existe, usa Roboflow
- ✅ **Backward compatible**: Workflows existentes siguen funcionando

## Estructura de Directorios

```
models/local/
├── README.md                      # Este archivo
├── yolov11/
│   ├── yolov11n-320-detection.json    # Manifest
│   ├── yolov11n-320.onnx              # Modelo ONNX
│   ├── yolov11s-640-detection.json
│   └── yolov11s-640.onnx
└── yolov8/
    ├── yolov8n-pose-320.json
    └── yolov8n-pose-320.onnx
```

## Schema de Manifest

Un manifest es un archivo JSON que describe el modelo:

```json
{
  "model_id": "yolov11n-320",
  "task_type": "object-detection",
  "model_path": "models/local/yolov11/yolov11n-320.onnx",
  "class_names": ["person", "bicycle", "car", ...],
  "input_size": [320, 320],
  "metadata": {
    "quantization": "int8",
    "source": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov11n.pt",
    "converted_with": "ultralytics export format=onnx imgsz=320 int8=True"
  }
}
```

### Campos Requeridos

- **`model_id`** (string): Identificador único usado en workflow JSON
- **`task_type`** (string): Uno de:
  - `"object-detection"`
  - `"pose-estimation"` (TODO: Fase 4)
  - `"instance-segmentation"` (TODO: Fase 4)
  - `"classification"` (TODO: Fase 4)
- **`model_path`** (string): Ruta al archivo `.onnx` (absoluta o relativa al manifest)
- **`class_names`** (array): Lista de nombres de clases en orden
- **`input_size`** (array): `[altura, ancho]` de entrada del modelo

### Campos Opcionales

- **`metadata`** (object): Información adicional (quantization, source URL, etc.)

## Cómo Agregar un Modelo Local

### Paso 1: Exportar Modelo a ONNX

Usando Ultralytics (YOLOv8/v11):

```bash
# Instalar ultralytics
pip install ultralytics

# Exportar modelo a ONNX con cuantización INT8 y tamaño 320
yolo export model=yolov11n.pt format=onnx imgsz=320 int8=True

# Esto genera yolov11n.onnx
```

Otros tamaños:
```bash
# YOLOv11s con 640x640
yolo export model=yolov11s.pt format=onnx imgsz=640 int8=True

# YOLOv11n pose estimation
yolo export model=yolov11n-pose.pt format=onnx imgsz=320 int8=True
```

### Paso 2: Crear Manifest JSON

Crea un archivo JSON con el schema descrito arriba. Ejemplo:

**`models/local/yolov11/yolov11n-320-detection.json`**:
```json
{
  "model_id": "yolov11n-320",
  "task_type": "object-detection",
  "model_path": "yolov11n-320.onnx",
  "class_names": [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush"
  ],
  "input_size": [320, 320],
  "metadata": {
    "quantization": "int8",
    "source": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov11n.pt",
    "converted_with": "yolo export model=yolov11n.pt format=onnx imgsz=320 int8=True",
    "coco_dataset": true
  }
}
```

### Paso 3: Copiar Modelo al Directorio

```bash
# Copiar modelo ONNX
cp yolov11n.onnx models/local/yolov11/yolov11n-320.onnx

# Verificar estructura
ls -lh models/local/yolov11/
# yolov11n-320-detection.json
# yolov11n-320.onnx
```

### Paso 4: Usar en Workflow JSON

Referencia el `model_id` del manifest en tu workflow:

```json
{
  "version": "1.0",
  "inputs": [
    {"type": "InferenceImage", "name": "image"}
  ],
  "steps": [
    {
      "type": "ObjectDetectionModel",
      "name": "detector",
      "image": "$inputs.image",
      "model_id": "yolov11n-320",
      "confidence": 0.5
    }
  ],
  "outputs": [
    {"type": "JsonField", "name": "predictions", "selector": "$steps.detector.predictions"}
  ]
}
```

**El sistema automáticamente**:
1. Intenta cargar `yolov11n-320` desde LocalModelRegistry
2. Si existe manifest → usa `LocalONNXObjectDetection`
3. Si no existe → fallback a RoboflowModelRegistry

## Variables de Entorno

```bash
# Habilitar/deshabilitar local models
export LOCAL_MODELS_ENABLED=true  # default: true

# Directorio de modelos locales
export LOCAL_MODELS_DIR="./models/local"  # default: ./models/local
```

## Troubleshooting

### Error: "Manifest file not found"
- Verifica que el archivo JSON exista en `LOCAL_MODELS_DIR`
- Usa rutas absolutas si es necesario

### Error: "Model file not found"
- Verifica que `model_path` en el manifest apunte al archivo `.onnx` correcto
- Si usas ruta relativa, debe ser relativa a la ubicación del manifest

### Warning: "LocalModelRegistry will be empty"
- El directorio `LOCAL_MODELS_DIR` no existe
- Crea el directorio: `mkdir -p models/local`

### Error: "Duplicate model_id"
- Dos manifests tienen el mismo `model_id`
- Usa IDs únicos (ej: `yolov11n-320`, `yolov11n-640`)

### Model class not implemented yet
- El `task_type` del manifest no tiene clase implementada
- Actualmente solo `object-detection` está implementado
- Pose, segmentation, classification vienen en Fase 4

## Roadmap

### ✅ Fase 1-3 (Completado)
- ModelManifest con validación Pydantic
- LocalModelRegistry con scaneo de manifests
- CompositeModelRegistry con fallback chain
- Integración en InferencePipeline

### 🚧 Fase 2 (En Progreso)
- LocalONNXModel base class
- LocalONNXObjectDetection con YOLOv11 inference

### 📋 Fase 4 (Futuro)
- LocalONNXPoseEstimation
- LocalONNXInstanceSegmentation
- LocalONNXClassification

## Ejemplos

Ver `examples/run_local_detection.py` para un ejemplo completo de uso.

## Contribuir

Para agregar soporte a nuevos tipos de modelos:

1. Implementar clase en `care/models/local/{task_type}.py`
2. Heredar de `Model` base class
3. Implementar `infer_from_request()` compatible con Roboflow interface
4. Agregar al mapping en `LocalModelRegistry._get_model_class_for_task()`
5. Documentar formato de salida esperado
