Los documentos describen la **evolución arquitectónica** de un sistema de gestión de modelos, pasando de una dependencia estricta de la API de Roboflow a una solución **extensible y desacoplada** para manejar modelos ONNX locales y cuantizados. La estrategia central implementada es el **Composite Model Registry**, que utiliza el patrón **Chain of Responsibility** para intentar cargar modelos desde _manifests_ JSON locales primero, y luego recurrir al registro de Roboflow, manteniendo la **compatibilidad regresiva**. Este rediseño, justificado mediante la **Vista 4+1 de Kruchten**, mejora la **latencia** y la **flexibilidad** del sistema al permitir el uso de modelos propios sin necesidad de conectividad de red, adhiriéndose a la filosofía de **"complejidad por diseño"**. Finalmente, se detallan las **fases de implementación** completadas y las **propuestas futuras** para extender el soporte a otros tipos de tareas y optimizar el _deployment_.


La transformación de la arquitectura de gestión de modelos para integrar **modelos locales cuantizados sin depender de la API de Roboflow** se centra en la evolución del componente `ModelRegistry` mediante la implementación de un **Patrón de Registro Compuesto (Composite Registry Pattern)**.

Este cambio arquitectural traslada la responsabilidad de identificación y carga del modelo de una dependencia rígida de la API de Roboflow a un sistema extensible de búsqueda y _fallback_.

Aquí se detalla cómo se transforma la arquitectura:

---

### 1. Evolución del Sistema de Registro (Composite Registry Pattern)

La arquitectura anterior estaba fuertemente acoplada al `RoboflowModelRegistry`. La solución fue introducir dos nuevos componentes y una abstracción superior:

1. **CompositeModelRegistry:** Este es el nuevo orquestador que utiliza el patrón **Chain of Responsibility** (Cadena de Responsabilidad). Su función es intentar resolver la solicitud de un modelo (`model_id`) a través de múltiples registros en orden.
2. **LocalModelRegistry:** Un registro completamente nuevo que se encarga de escanear y cargar la información de los modelos locales. Este registro no requiere llamadas a la API ni autenticación de Roboflow.
3. **Fallback Automático:** La secuencia de búsqueda está diseñada para intentar la carga a través del **`LocalModelRegistry` primero**. Si el modelo local no existe, automáticamente realiza un **fallback** al `RoboflowModelRegistry` existente. Esto asegura una **compatibilidad retroactiva del 100%** con los flujos de trabajo preexistentes.

Esta inversión de dependencia significa que el `InferencePipeline` (o el `ModelManager`) ya no depende de una implementación concreta (como `RoboflowModelRegistry`), sino de una abstracción (`ModelRegistry`).

### 2. Definición y Carga de Modelos Locales (Manifests JSON)

Para manejar modelos locales, la arquitectura introduce un enfoque declarativo utilizando manifiestos, lo que evita la necesidad de modificar código al añadir nuevos modelos:

- **Model Manifest Schema:** Los modelos locales se definen a través de archivos **Manifest JSON**. Estos manifiestos (implementados usando un `dataclass` con validación **Pydantic**) son el mecanismo clave para el registro.
- **Propiedades Clave:** El manifiesto define propiedades esenciales para la carga local, como el `model_id` (utilizado en el workflow), el `task_type` (para determinar la clase envolvente ONNX correcta), `model_path` (la ruta al archivo `.onnx` local) y `class_names`.
- **Validación Fail-Fast:** Al cargarse el sistema, los manifiestos son validados por Pydantic, garantizando una **validación en tiempo de carga** (`load-time validation`) y provocando errores claros si el manifiesto es inválido (estrategia _fail-fast_).

El `LocalModelRegistry` escanea estos manifiestos, típicamente ubicados en un directorio configurado mediante variables de entorno (como `LOCAL_MODELS_DIR`).

### 3. Implementación de Inferencias ONNX Cuantizadas

La inferencia para estos modelos locales se maneja mediante envoltorios (wrappers) dedicados:

- **Clases ONNX Locales:** Se crean clases base como **`LocalONNXModel`** y clases específicas como `LocalONNXObjectDetection` (para modelos como YOLOv11).
- **Interfaz Común:** Estas clases están diseñadas para tener la **misma interfaz** (`infer_from_request()`) que los modelos heredados de Roboflow. Esto asegura que el `ModelManager` (que maneja la caché y el lazy loading) pueda interactuar con ellos sin cambios.
- **ONNX Runtime:** Para la inferencia, se utiliza **ONNX Runtime**. Esto mantiene la solución _lightweight_ (ligera) y evita la carga de dependencias pesadas de _frameworks_ de _training_ como Ultralytics. Permite el uso de aceleración GPU/CPU automática.
- **Soporte a Cuantización:** Dado que los modelos ya están localmente en formato ONNX (que puede ser INT8, FP16, etc.), la nueva arquitectura **soporta directamente modelos cuantizados propios**, lo que resulta en menor latencia y elimina la necesidad de _billing_ (facturación) de uso de la API.

En resumen, la clave de la transformación es mover la decisión de dónde cargar el modelo del flujo de ejecución del `ModelManager` a un **`CompositeModelRegistry` extensible**, permitiendo que modelos cuantizados, locales y sin dependencia de la API sean cargados declarativamente mediante **Manifests JSON**.



---


El patrón **Composite Registry** es una estrategia arquitectónica clave utilizada para la gestión de modelos, cuyo objetivo principal es desacoplar el sistema de una fuente de modelos única (anteriormente, solo Roboflow) y permitir la integración fluida de modelos locales y futuros sin romper la compatibilidad.

A continuación, se detallan los componentes clave de este patrón y cómo garantizan la extensibilidad y la compatibilidad, según los documentos proporcionados:

---

### Componentes Clave del Patrón Composite Registry

El patrón Composite Registry reemplaza el diseño anterior de "Single Registry" con una estructura jerárquica y encadenada, aplicando el patrón **Chain of Responsibility**.

#### 1. CompositeModelRegistry

Este es el orquestador central que maneja la solicitud de un modelo.

- **Función:** Encadena múltiples registros (registries) y determina qué fuente de modelos debe ser consultada.
- **Mecanismo:** Implementa el patrón **Chain of Responsibility** para intentar resolver la solicitud secuencialmente, lo que permite el _fallback_ automático.

#### 2. LocalModelRegistry

Este componente se introdujo específicamente para manejar modelos que no dependen de la API de Roboflow.

- **Función:** Carga modelos definidos en _manifests_ JSON desde rutas locales.
- **Ventaja:** Permite el uso de modelos propios cuantizados (como YOLOv11 ONNX) sin requerir llamadas API ni autenticación de Roboflow.
- **Integración:** Es el primer registro consultado en el flujo de ejecución, logrando la funcionalidad de "local primero".

#### 3. RoboflowModelRegistry (Registro Original)

Aunque es preexistente, su rol dentro del nuevo patrón es crucial para la compatibilidad.

- **Función:** Manejar modelos estándar de detección, clasificación o segmentación que se obtienen, registran y cargan a través de la API de Roboflow.
- **Rol en el Composite:** Sirve como **mecanismo de _fallback_ (reserva)**. Si el `LocalModelRegistry` no puede encontrar el `model_id` solicitado, la solicitud pasa automáticamente al `RoboflowModelRegistry`.

#### 4. Model Manifest Schema (JSON)

Este componente es la clave para la definición declarativa de los modelos locales.

- **Función:** Define las propiedades del modelo (como `model_id`, `task_type`, `model_path` y `class_names`) mediante un esquema JSON.
- **Validación:** Utiliza validación Pydantic, lo que permite una **validación _fail-fast_** (falla rápida) durante el tiempo de carga, en lugar de errores inesperados en tiempo de ejecución.

#### 5. Local ONNX Model Wrapper (e.g., LocalONNXObjectDetection)

Estos son los objetos de modelo concretos que gestionan la inferencia local.

- **Función:** Encapsulan la lógica de inferencia (como ONNX Runtime) y el pre/post-procesamiento (ej. `letterbox`, NMS).
- **Compatibilidad:** Deben exponer la **misma interfaz** (`infer_from_request()`) que los modelos de Roboflow existentes, asegurando que el `ModelManager` pueda interactuar con ellos sin cambios.

---

### Garantía de Extensibilidad y Compatibilidad

El patrón Composite Registry fue elegido específicamente porque resuelve las limitaciones de la arquitectura anterior, que estaba fuertemente acoplada a Roboflow.

#### Extensibilidad

La extensibilidad se garantiza mediante la adhesión a principios de diseño sólidos, principalmente el **Principio Abierto/Cerrado (OCP)**:

1. **Open/Closed Principle (OCP):** El `CompositeModelRegistry` permite que el sistema esté **abierto a la extensión** (agregando nuevos registries) pero **cerrado a la modificación** (sin tener que cambiar el código existente del orquestador o de los registries antiguos).
2. **Arquitectura Modular:** El diseño es inherentemente modular y desacoplado, permitiendo agregar futuras fuentes de modelos, como un `HuggingFaceRegistry` o un `OllamaRegistry`, simplemente uniéndolos a la cadena del Composite.
3. **Registro Declarativo:** La adición de nuevos modelos locales se logra a través de la creación de un nuevo _manifest_ JSON, que es **declarativo** y **amigable para científicos de datos** sin requerir modificaciones en el código base. Esto contribuye a la filosofía de **"Complejidad por diseño, no por accidente"**.

#### Compatibilidad (_Backward Compatibility_)

La compatibilidad se garantiza al aislar la nueva lógica local y utilizando el encadenamiento de manera efectiva:

1. **Abstracción del ModelRegistry:** El `InferencePipeline` (el motor de _stream_) ya no depende de la implementación concreta (`RoboflowModelRegistry`), sino de una abstracción genérica (`ModelRegistry`), lo que reduce el acoplamiento.
2. **Fallback Automático:** La implementación del patrón **Chain of Responsibility** en el `CompositeModelRegistry` asegura que si un `model_id` no se encuentra localmente, el sistema automáticamente hace _fallback_ al `RoboflowModelRegistry`. Esto significa que **los _workflows_ existentes siguen funcionando al 100% sin modificaciones**.
3. **Interfaz Unificada:** El `Local ONNX Model Wrapper` respeta la misma interfaz que el `RoboflowInferenceModel`, lo que permite al `ModelManager` (el orquestador) tratar a los modelos locales y remotos de manera uniforme (polimorfismo). Esto asegura que no hay **duplicación de lógica de inferencia** o _bypass_ del ModelManager (manteniendo caché y _lazy loading_)

---

El **`WorkflowRunner`** tiene el rol de ser el **puente** o **ejecutor** entre el _pipeline_ de procesamiento de video en tiempo real, conocido como **`InferencePipeline` (Stream Engine)**, y el motor de ejecución de flujos de trabajo declarativos, conocido como **`ExecutionEngine`**.

Su función principal dentro de la arquitectura es orquestar la ejecución de los _workflows_ definidos, cuadro por cuadro (frame por frame).

Aquí se detallan sus responsabilidades y proceso:

### Rol y Proceso del `WorkflowRunner`

El `WorkflowRunner` es parte de los dos flujos principales del sistema para ejecutar modelos: el **`WorkflowRunner`** (para _workflows_ declarativos) y el **`InferencePipeline`** (para procesamiento de video en tiempo real).

Cuando se utiliza el método `init_with_workflow()` del `InferencePipeline` para ejecutar _workflows_ declarativos:

1. **Recepción de _Frames_**: El `WorkflowRunner` recibe cuadros (frames) de video provenientes del `InferencePipeline`.
2. **Construcción de Parámetros**: A partir de los _frames_ recibidos, el `WorkflowRunner` construye y prepara los parámetros necesarios para la ejecución del _workflow_, incluyendo la imagen y la metadata asociada.
3. **Invocación del Motor de Ejecución**: El `WorkflowRunner` invoca al **`execution_engine.run()`**, pasándole los parámetros construidos. El `ExecutionEngine` es el componente que realmente maneja la ejecución del grafo de bloques definido en el _workflow_.
4. **Retorno de Resultados**: Finalmente, el `WorkflowRunner` se encarga de retornar los resultados de la ejecución del _workflow_ al _sink_ (destino) del `InferencePipeline`.

En resumen, el `WorkflowRunner` es el componente que toma la lógica del _workflow_ (definida en JSON), la recibe del _pipeline_ de video, la ejecuta cuadro por cuadro a través del `ExecutionEngine`, y devuelve los resultados para continuar el flujo del _stream_.