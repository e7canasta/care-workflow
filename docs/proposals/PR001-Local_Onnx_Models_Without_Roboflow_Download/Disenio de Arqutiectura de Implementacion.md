
● Revisando el código y tus documentos, coincido completamente: crear un custom block sería arquitecturalmente incorrecto. El problema que quieres resolver pertenece al dominio del  
 ModelManager/ModelRegistry, no al workflow layer.  
  
## 🎯 Análisis del Problema Real  
  
 Tu Objetivo  
  
 Usar **modelos YOLO locales cuantizados (ONNX)** sin depender de Roboflow API:  
 - YOLOv11 en múltiples tamaños (320, 640, etc.)  
 - Múltiples tareas (detection, pose, segment, classification)  
 - **Modelos propios**, sin download de Roboflow  
  
 Por Qué No Custom Block  
  
 Un custom block tipo `care/local_yolo_inference@v1` sería **duplicar responsabilidades**:  
 - ❌ Reimplementarías lógica de inferencia que ya existe en `Model.infer_from_request()`  
 - ❌ Bypass del `ModelManager` (perdés caché, lazy loading, lifecycle)  
 - ❌ Inconsistencia: algunos modelos via `ObjectDetectionModel` block, otros via custom block  
  
 ## 🏗 Estrategia Recomendada: Evolucionar el ModelRegistry  
  
 Arquitectura Actual (Limitaciones)  

```python
 # care/registries/roboflow.py:68-99  
 def get_model(self, model_id, api_key, ...):  
     model_type = get_model_type(model_id, api_key, ...)  # ← API call obligatoria  
     return self.registry_dict[model_type]  
```
  
**Problemas**:  

  1. `get_model_type()` ***siempre*** llama a Roboflow API para determinar tipo.
  2. `ROBOFLOW_MODEL_TYPES` solo mapea modelos de Roboflow. 
  3.  No hay path para registrar modelos locales.  
  
 Solución Propuesta: Dual Registry Pattern  

---

## ● 📋 Propuesta de Arquitectura  
  
### 1. Composite Registry Pattern  

```python
 # care/registries/composite.py (NUEVO)  
 class CompositeModelRegistry(ModelRegistry):  
     """Registra modelos desde múltiples fuentes con fallback chain."""  
  
     def __init__(self, registries: List[ModelRegistry]):  
         self.registries = registries  # [LocalModelRegistry, RoboflowModelRegistry]  
  
     def get_model(self, model_id, api_key, **kwargs):  
         for registry in self.registries:  
             try:  
                 return registry.get_model(model_id, api_key, **kwargs)  
             except ModelNotRecognisedError:  
                 continue  
         raise ModelNotRecognisedError(f"Model {model_id} not found in any registry")  
```

 **Ventajas**:  

  - ✅ Backward compatible: Roboflow sigue funcionando  
  - ✅ Fallback automático: intenta local primero, luego Roboflow  
  - ✅ Extensible: agregar más registries sin modificar código existente  


### 2. Local Model Registry  

```python

 # care/registries/local.py (NUEVO)  
 class LocalModelRegistry(ModelRegistry):  
     """Registra modelos desde manifests JSON locales."""  
  
     def __init__(self, models_dir: str = "models/local"):  
         self.models_dir = Path(models_dir)  
         self.manifests = self._load_manifests()  
  
     def _load_manifests(self) -> Dict[str, ModelManifest]:  
         """  
         Carga manifests desde models/local/**/*.json  
            
         Estructura esperada:  
         models/local/  
           yolov11/  
             yolov11n-320.json  
             yolov11s-640.json  
           yolov8/  
             yolov8n-pose-320.json  
         """  
         manifests = {}  
         for manifest_path in self.models_dir.rglob("*.json"):  
             manifest = ModelManifest.from_json(manifest_path)  
             manifests[manifest.model_id] = manifest  
         return manifests  
  
     def get_model(self, model_id, api_key=None, **kwargs):  
         if model_id not in self.manifests:  
             raise ModelNotRecognisedError(f"Local model {model_id} not found")  
  
         manifest = self.manifests[model_id]  
         return self._get_model_class_for_task(manifest.task_type)  
  
     def _get_model_class_for_task(self, task_type: str):  
         """  
         Mapea task_type a clase modelo local.  
            
         task_type puede ser:  
         - "object-detection"  
         - "pose-estimation"  
         - "instance-segmentation"  
         - "classification"  
         """  
         mapping = {  
             "object-detection": LocalONNXObjectDetection,  
             "pose-estimation": LocalONNXPoseEstimation,  
             "instance-segmentation": LocalONNXInstanceSegmentation,  
             "classification": LocalONNXClassification,  
         }  
         if task_type not in mapping:  
             raise ModelNotRecognisedError(f"Task {task_type} not supported")  
         return mapping[task_type] 
    
``` 
  
### 3. Model Manifest Schema  

```python
 // models/local/yolov11/yolov11n-320-detection.json  
 {  
   "model_id": "yolov11n-320",  // ← Usado en workflow JSON  
   "task_type": "object-detection",  
   "model_path": "models/local/yolov11/yolov11n-320.onnx",  
   "class_names": ["person", "car", "dog", ...],  // ← 80 clases COCO  
   "input_size": [320, 320],  
   "metadata": {  
     "quantization": "int8",  
     "source": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov11n.pt",  
     "converted_with": "ultralytics export format=onnx imgsz=320 int8=True"  
   }  
 }  
```
  
**Propiedades Clave**:  

 - `model_id`: Identificador único (usado en `model_id` del workflow)  
 - `task_type`: Determina qué clase `LocalONNX*` usar  
 - `model_path`: Ruta absoluta o relativa al `.onnx`  
 - `class_names`: Lista de clases (necesario para post-procesamiento)  


### 4. Local ONNX Model Wrapper  

```python

# care/models/local/onnx_detection.py (NUEVO)  
import onnxruntime as ort  
from care.models.base import Model  

class LocalONNXObjectDetection(Model):  
 """Modelo de detección ONNX local sin dependencia de Roboflow."""  

 def __init__(self, model_id: str, api_key=None, **kwargs):  
	 super().__init__()  
	 self.model_id = model_id  
	 self.manifest = self._load_manifest(model_id)  
	 self.session = ort.InferenceSession(  
		 self.manifest.model_path,  
		 providers=['CUDAExecutionProvider', 'CPUExecutionProvider']  
	 )  
	 self.class_names = self.manifest.class_names  
	 self.input_size = tuple(self.manifest.input_size)  

 def infer_from_request(self, request: ObjectDetectionInferenceRequest):  
	 """Interfaz compatible con Roboflow models."""  
	 # 1. Preprocess image  
	 image = self.preprocess(request.image, self.input_size)  

	 # 2. ONNX inference  
	 outputs = self.session.run(None, {"images": image})  

	 # 3. Post-process (NMS, formato supervision.Detections)  
	 detections = self.postprocess(  
		 outputs,  
		 confidence=request.confidence,  
		 iou_threshold=request.iou_threshold,  
		 class_agnostic_nms=request.class_agnostic_nms  
	 )  

	 return ObjectDetectionInferenceResponse(  
		 predictions=detections,  
		 image=request.image  
	 )  

 def preprocess(self, image, target_size):  
	 """Resize + normalize para ONNX."""  
	 # Similar a YOLOv8 preprocessing  
	 pass  

 def postprocess(self, outputs, confidence, iou_threshold, class_agnostic_nms):  
	 """NMS + conversión a supervision.Detections."""  
	 # Similar a YOLOv8 postprocessing  
	 pass  
```


**Características**:  

 - ✅ **Misma interfaz** que `RoboflowInferenceModel.infer_from_request()`  
 - ✅ **Compatible** con `ModelManager` existente  
 - ✅ **No download**: modelo ya local  
 - ✅ **ONNX Runtime**: GPU/CPU automático  


### 5. Integración con InferencePipeline  

```python

# care/stream/inference_pipeline.py:624-631 (MODIFICADO)  
# Cambiar de:  
model_registry = RoboflowModelRegistry(ROBOFLOW_MODEL_TYPES)  

# A:  
local_registry = LocalModelRegistry(models_dir=LOCAL_MODELS_DIR)  
roboflow_registry = RoboflowModelRegistry(ROBOFLOW_MODEL_TYPES)  
model_registry = CompositeModelRegistry([local_registry, roboflow_registry])  
```

**Flujo**:  

 1. Workflow referencia `model_id: "yolov11n-320"`  
 2. CompositeModelRegistry intenta LocalModelRegistry.get_model("yolov11n-320")  
 3. Si existe manifest → retorna LocalONNXObjectDetection  
 4. Si no existe → fallback a RoboflowModelRegistry  


---

## 🎸 Ventajas de Esta Arquitectura  

Complejidad por Diseño  

 - **Separación de concerns**: Local vs Roboflow son bounded contexts  
 - **Single Responsibility**: Cada registry maneja una fuente  
 - **Extensible**: Agregar `HuggingFaceModelRegistry` en el futuro  

Fail Fast  

 - **Load time validation**: Manifests se cargan en `__init__`  
 - **Clear errors**: `ModelNotRecognisedError` si manifest no existe  
 - **ONNX validation**: `ort.InferenceSession` falla inmediatamente si modelo corrupto  

Backward Compatibility  

 - **Zero breaking changes**: Workflows existentes siguen usando Roboflow  
 - **Opt-in**: Solo usás local models si creás manifests  

Workflow JSON Unchanged  

```json
{  
"steps": [  
 {  
   "type": "ObjectDetectionModel",  
   "name": "detector",  
   "image": "$inputs.image",  
   "model_id": "yolov11n-320"  // ← Puede ser local o Roboflow  
 }  
]  
}  
```

**No cambia nada en el workflow** → el registry resuelve automáticamente.  

## 📁 Estructura de Archivos Propuesta

```python
care-workflow/  
├── care/  
│   ├── models/  
│   │   ├── local/              # NUEVO  
│   │   │   ├── __init__.py  
│   │   │   ├── base.py         # LocalONNXModel base class  
│   │   │   ├── detection.py   # LocalONNXObjectDetection  
│   │   │   ├── pose.py        # LocalONNXPoseEstimation  
│   │   │   ├── segmentation.py  
│   │   │   └── classification.py  
│   │   └── roboflow.py  
│   ├── registries/  
│   │   ├── local.py           # NUEVO: LocalModelRegistry  
│   │   ├── composite.py       # NUEVO: CompositeModelRegistry  
│   │   └── roboflow.py  
│   └── env.py                 # Agregar LOCAL_MODELS_DIR  
├── models/                    # NUEVO: directorio de modelos locales  
│   └── local/  
│       ├── yolov11/  
│       │   ├── yolov11n-320-detection.json  
│       │   ├── yolov11n-320.onnx  
│       │   ├── yolov11s-640-detection.json  
│       │   ├── yolov11s-640.onnx  
│       │   ├── yolov11n-320-pose.json  
│       │   └── yolov11n-320-pose.onnx  
│       └── README.md          # Docs de cómo agregar modelos  
└── examples/  
 └── run_local_detection.py # Ejemplo usando modelo local  
```


## 🚀 Plan de Implementación  

Fase 1: Foundation (2-3 horas)  

 1. ✅ **Crear `ModelManifest` dataclass** (`care/models/local/manifest.py`)  
 
    - Schema validation con pydantic  
    - `from_json()` class method  
 
 2. ✅ **Implementar `LocalModelRegistry`** (`care/registries/local.py`)  
 
	- Scanear manifests en `LOCAL_MODELS_DIR`  
    - Mapeo `task_type` → model class  
 
 3. ✅ **Implementar `CompositeModelRegistry`** (`care/registries/composite.py`)  

	- Chain of responsibility pattern  
    - Tests unitarios  


Fase 2: ONNX Inference (3-4 horas)  

4. ✅ **Base `LocalONNXModel`** (`care/models/local/base.py`)  
    
	- Common preprocessing (letterbox, normalize)  
    - ONNX session setup  
    - Error handling  

5. ✅ **`LocalONNXObjectDetection`** (`care/models/local/detection.py`)  

	- YOLOv11 output parsing  
    - NMS implementation  
    - Conversión a `supervision.Detections`  


Fase 3: Integration (1-2 horas)  

6. ✅ **Modificar `InferencePipeline.init_with_workflow()`  

	- Usar CompositeModelRegistry  
	- Backward compatibility tests  
	
7. ✅ **Variables de entorno** (`care/env.py`)

```bash
LOCAL_MODELS_DIR = os.getenv("LOCAL_MODELS_DIR", "./models/local")  
LOCAL_MODELS_ENABLED = str2bool(os.getenv("LOCAL_MODELS_ENABLED", True))  
```

Fase 4: Tasktypes Adicionales (2 horas cada uno)  

8. ⏸ **Pose Estimation** (`care/models/local/pose.py`)  
9. ⏸ **Instance Segmentation** (`care/models/local/segmentation.py`)  
10. ⏸ **Classification** (`care/models/local/classification.py`)  

Fase 5: Documentation & Examples (1 hora)  

11. ✅ **README de modelos locales** (`models/local/README.md`)  

	- Cómo exportar YOLO a ONNX  
	- Cómo crear manifests  
	- Troubleshooting  

12. ✅ **Ejemplo completo** (`examples/run_local_detection.py`)  



## 🧪 Testing Strategy (Manual Pair-Programming)  


### Test 1: Registry Resolution  

```python

# Dado: manifest yolov11n-320.json existe  
# Cuando: InferencePipeline.init_with_workflow(model_id="yolov11n-320")  
# Entonces: LocalModelRegistry retorna LocalONNXObjectDetection  

Test 2: Fallback to Roboflow  

# Dado: manifest NO existe  
# Cuando: model_id="roboflow-model/3"  
# Entonces: RoboflowModelRegistry maneja el request  

Test 3: ONNX Inference  

# Dado: yolov11n-320.onnx cargado  
# Cuando: infer_from_request(image)  
# Entonces: retorna ObjectDetectionInferenceResponse válido  

Test 4: Workflow End-to-End  

# Dado: workflow JSON con model_id local  
# Cuando: Procesando video RTSP  
# Entonces: Detecciones visibles en ventana CV2
```  


## 🎯 Decisiones de Diseño Clave  

¿Por Qué No Modificar RoboflowModelRegistry?  

- ❌ **Violates OCP**: Open/Closed Principle  
- ❌ **Mixing concerns**: Un registry no debe manejar múltiples fuentes  
- ✅ **Composite es mejor**: Cada registry tiene una responsabilidad  

¿Por Qué Manifest JSON vs Código?  

- ✅ **Declarativo**: No code para agregar modelos  
- ✅ **Validable**: Schema JSON + pydantic  
- ✅ **Versionable**: Git-friendly  
- ✅ **User-friendly**: Data scientists pueden agregar modelos sin tocar código  

¿Por Qué No Usar Ultralytics Directamente?  

- ❌ **Dependency weight**: `ultralytics` trae OpenCV, Pillow, etc.  
- ❌ **Version conflicts**: Puede chocar con `inference` deps  
- ✅ **ONNX Runtime es lightweight**: Solo inferencia, sin training  
- ✅ **Format-agnostic**: Podés usar modelos de cualquier framework  

¿Por Qué No Un Custom Block?  

Ya explicado arriba, pero resumen:  
- ❌ **Duplicación de lógica**: Inferencia ya existe en `Model.infer_from_request()`  
- ❌ **Bypass del ModelManager**: Perdés caché, lazy loading  
- ❌ **Inconsistencia arquitectural**: Dos paths para lo mismo  


## 📊 Comparación: Custom Block vs Registry Evolution  

| Aspecto            | Custom Block                  | Registry Evolution                    |     |
| ------------------ | ----------------------------- | ------------------------------------- | --- |
| **Complejidad**    | Simple corto plazo            | Más upfront, menos deuda              |     |
| **Reusabilidad**   | Solo en workflows             | Cualquier código usando ModelManager  |     |
| **Caché**          | Tendrías que reimplementar    | Gratis via ModelManager               |     |
| **Consistencia**   | Dos caminos (block vs model)  | Un solo camino                        |     |
| **Extensibilidad** | Agregar block por task        | Agregar manifest JSON                 |     |
| **Testing**        | Test el block + workflows     | Test registry + modelos               |     |
| **Mantenimiento**  | Duplicar fixes en block       | Un solo lugar                         |     |

> **Veredicto**: Registry evolution es **complejidad por diseño**, custom block es **complejidad por accidente**.  

> **🎸 "El Blues de la Arquitectura" **
>
> "Un block custom es como tocar siempre en la misma escala pentatónica - funciona, pero te limita. Un registry bien diseñado es conocer todas las escalas y elegir la correcta para cada solo."  

####  Aplicando el Manifiesto:  

- ✅ Pragmatismo > Purismo: Composite pattern es pragmático, no dogma  
- ✅ Patterns con Propósito: Chain of Responsibility resuelve problema real  
- ✅ Simplicidad Estructural: Cada registry es simple, la composición es poderosa  
- ✅ Fail Fast: Manifests validados en load time  

---  

#### ✅ Próximos Pasos Recomendados  

5. **Validar propuesta contigo** antes de codear  
6. **Crear spike** con `LocalModelRegistry` + un manifest de ejemplo  
7. **Probar end-to-end** con YOLOv11n-320 detection  
8. **Iterar** basándonos en lo aprendido  
9. **Extender** a pose, segment, classify  


```
¿Te parece que arrancamos con la Fase 1 (Foundation)? Puedo generar el código de ModelManifest y LocalModelRegistry para que revisemos juntos antes de integrar con el resto del sistema.  

Todos  
☐ Diseñar arquitectura de LocalModelRegistry  
☐ Crear especificación de model manifest JSON  
☐ Implementar LocalONNXModel wrapper  
☐ Integrar con CompositeModelRegistry  
☐ Crear ejemplo de uso con YOLOv11

```