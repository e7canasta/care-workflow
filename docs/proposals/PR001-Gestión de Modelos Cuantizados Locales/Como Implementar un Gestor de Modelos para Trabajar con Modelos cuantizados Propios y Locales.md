Entiendo que estás preguntando sobre cómo implementar un gestor de modelos para trabajar con modelos cuantizados propios y locales en el codebase de `care-workflow`.<cite />

## Arquitectura Actual del Gestor de Modelos

El sistema ya cuenta con una arquitectura de gestión de modelos basada en la clase `ModelManager` en `care/managers/base.py`. [1](#0-0)  Esta clase mantiene un diccionario de objetos `Model` y es responsable de enrutar las solicitudes de inferencia al modelo correcto.<cite />

## Estrategia para Modelos Locales Cuantizados

### 1. Registro de Modelos

El sistema utiliza un `ModelRegistry` para registrar y obtener clases de modelos. [2](#0-1)  Para modelos locales cuantizados, podrías:

- Extender el registro existente para soportar modelos locales sin necesidad de API keys de Roboflow<cite />
- El método `add_model` ya soporta la carga de modelos con autenticación opcional [3](#0-2) 

### 2. Soporte de Cuantización Existente

El codebase ya tiene soporte para cuantización en algunos modelos. Por ejemplo, `Qwen25VL` acepta un parámetro `use_quantization`: [4](#0-3) 

### 3. Implementación Recomendada

Para implementar un gestor de modelos locales cuantizados:

**a) Crear un ModelRegistry personalizado** que no requiera autenticación de Roboflow:<cite />
- Deshabilitar la verificación de API key configurando `MODELS_CACHE_AUTH_ENABLED=False` [5](#0-4) 

**b) Usar StubLoaderManager** para carga simplificada sin pesos iniciales: [6](#0-5) 

**c) Gestión de caché** con tamaño fijo usando `WithFixedSizeCache` decorator: [7](#0-6) 

### 4. Variables de Entorno

Puedes habilitar/deshabilitar modelos específicos mediante variables de entorno como `QWEN_2_5_ENABLED`, `FLORENCE2_ENABLED`, etc. [8](#0-7) 

## Notas

El sistema está diseñado principalmente para modelos de Roboflow, pero la arquitectura es extensible.<cite /> Para modelos completamente locales, necesitarías crear tu propio `ModelRegistry` que cargue modelos desde rutas locales en lugar de descargarlos de la API de Roboflow.<cite /> El parámetro `MODEL_CACHE_DIR` define dónde se almacenan los artefactos del modelo localmente.<cite />

### Citations

**File:** care/managers/base.py (L39-48)
```python
class ModelManager:
    """Model managers keep track of a dictionary of Model objects and is responsible for passing requests to the right model using the infer method."""

    def __init__(self, model_registry: ModelRegistry, models: Optional[dict] = None):
        self.model_registry = model_registry
        self._models: Dict[str, Model] = models if models is not None else {}
        self.pingback = None
        self._state_lock = Lock()
        self._models_state_locks: Dict[str, Lock] = {}

```

**File:** care/managers/base.py (L57-84)
```python
    def add_model(
        self,
        model_id: str,
        api_key: str,
        model_id_alias: Optional[str] = None,
        endpoint_type: ModelEndpointType = ModelEndpointType.ORT,
        countinference: Optional[bool] = None,
        service_secret: Optional[str] = None,
    ) -> None:
        """Adds a new model to the manager.

        Args:
            model_id (str): The identifier of the model.
            model (Model): The model instance.
            endpoint_type (ModelEndpointType, optional): The endpoint type to use for the model.
        """
        if MODELS_CACHE_AUTH_ENABLED:
            if not _check_if_api_key_has_access_to_model(
                api_key=api_key,
                model_id=model_id,
                endpoint_type=endpoint_type,
                countinference=countinference,
                service_secret=service_secret,
            ):
                raise RoboflowAPINotAuthorizedError(
                    f"API key {api_key} does not have access to model {model_id}"
                )

```

**File:** care/models/hub/qwen25vl/qwen25vl.py (L64-86)
```python
    def __init__(
        self,
        model_id,
        *args,
        dtype=None,
        huggingface_token=HUGGINGFACE_TOKEN,
        use_quantization=True,
        **kwargs,
    ):
        super().__init__(model_id, *args, **kwargs)
        self.huggingface_token = huggingface_token
        if self.needs_hf_token and self.huggingface_token is None:
            raise RuntimeError(
                "Must set environment variable HUGGINGFACE_TOKEN to load LoRA "
                "(or pass huggingface_token to this __init__)"
            )
        self.dtype = dtype
        if self.dtype is None:
            self.dtype = self.default_dtype
        self.cache_model_artefacts(**kwargs)

        self.cache_dir = os.path.join(MODEL_CACHE_DIR, self.endpoint + "/")
        self.use_quantization = use_quantization
```

**File:** care/managers/stub_loader.py (L7-30)
```python
class StubLoaderManager(ModelManager):
    def add_model(
        self,
        model_id: str,
        api_key: str,
        model_id_alias=None,
        endpoint_type: ModelEndpointType = ModelEndpointType.ORT,
        countinference: Optional[bool] = None,
        service_secret: Optional[str] = None,
    ) -> None:
        """Adds a new model to the manager.

        Args:
            model_id (str): The identifier of the model.
            model (Model): The model instance.
            endpoint_type (ModelEndpointType, optional): The endpoint type to use for the model.
        """
        if model_id in self._models:
            return
        model_class = self.model_registry.get_model(
            model_id_alias if model_id_alias is not None else model_id, api_key
        )
        model = model_class(model_id=model_id, api_key=api_key, load_weights=False)
        self._models[model_id] = model
```

**File:** care/managers/decorators/fixed_size_cache.py (L138-147)
```python
    def remove(self, model_id: str, delete_from_disk: bool = True) -> Model:
        with acquire_with_timeout(
            lock=self._queue_lock, timeout=HOT_MODELS_QUEUE_LOCK_ACQUIRE_TIMEOUT
        ) as acquired:
            if not acquired:
                raise ModelManagerLockAcquisitionError(
                    "Could not acquire lock on Model Manager state to remove model from active models queue."
                )
            self._safe_remove_model_from_queue(model_id=model_id)
        return super().remove(model_id, delete_from_disk=delete_from_disk)
```

**File:** care/env.py (L180-192)
```python
LMM_ENABLED = str2bool(os.getenv("LMM_ENABLED", False))

QWEN_2_5_ENABLED = str2bool(os.getenv("QWEN_2_5_ENABLED", True))

DEPTH_ESTIMATION_ENABLED = str2bool(os.getenv("DEPTH_ESTIMATION_ENABLED", True))

SMOLVLM2_ENABLED = str2bool(os.getenv("SMOLVLM2_ENABLED", True))

MOONDREAM2_ENABLED = str2bool(os.getenv("MOONDREAM2_ENABLED", True))

PALIGEMMA_ENABLED = str2bool(os.getenv("PALIGEMMA_ENABLED", True))

FLORENCE2_ENABLED = str2bool(os.getenv("FLORENCE2_ENABLED", True))
```
