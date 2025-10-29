# Guía de Estudio: Arquitectura de Gestión de Modelos Locales

## Cuestionario

1. ¿Cuál era la principal limitación de la arquitectura de gestión de modelos anterior (`IS-A`) y cómo la soluciona el nuevo diseño (`HAS-A`)?
2. Describa la función y las propiedades clave de un archivo `ModelManifest` en la nueva arquitectura para modelos locales.
3. Explique el funcionamiento del `Composite Registry Pattern` y cómo implementa el principio de "Chain of Responsibility".
4. ¿Por qué se decidió evolucionar el `ModelRegistry` en lugar de crear un `Custom Block` para manejar modelos YOLO locales?
5. ¿Qué es el `ModelManager` y cuál es su relación con el `ModelRegistry` y el `InferencePipeline`?
6. ¿Qué rol juega `ONNX Runtime` en la nueva arquitectura y por qué fue elegido sobre la librería `Ultralytics`?
7. Describa el concepto de "lazy loading" y cómo se aplica a la gestión de modelos en el sistema.
8. ¿Qué significa el principio de "Fail-Fast" en este contexto y cómo se logra en la implementación de modelos locales?
9. ¿Cuáles son los dos flujos principales del sistema para ejecutar modelos y qué componente los gestiona?
10. ¿Cómo garantiza la nueva arquitectura la retrocompatibilidad (`backward compatibility`) con los flujos de trabajo existentes que utilizan modelos de Roboflow?

--------------------------------------------------------------------------------

## Clave de Respuestas

1. La principal limitación de la arquitectura anterior era su fuerte acoplamiento al `RoboflowModelRegistry`, lo que requería una llamada obligatoria a la API de Roboflow para determinar el tipo de modelo. El nuevo diseño `HAS-A` soluciona esto introduciendo una abstracción (`ModelRegistry`) y un `CompositeModelRegistry` que desacopla el `InferencePipeline` de una implementación concreta, permitiendo cargar modelos locales sin necesidad de llamadas a la API.
2. El `ModelManifest` es un archivo de configuración declarativo en formato JSON que define un modelo local sin necesidad de modificar el código. Sus propiedades clave incluyen `model_id` (identificador único), `task_type` (detección, pose, etc.), `model_path` (ruta al archivo .onnx) y `class_names` (lista de clases para el post-procesamiento), permitiendo una validación estructural en tiempo de carga.
3. El `Composite Registry Pattern` utiliza una clase `CompositeModelRegistry` que gestiona una lista de registros de modelos individuales (como `LocalModelRegistry` y `RoboflowModelRegistry`). Implementa el "Chain of Responsibility" al intentar resolver un `model_id` secuencialmente en cada registro: primero intenta con el local y, si falla, pasa la solicitud al siguiente (fallback a Roboflow), lo que lo hace extensible y ordenado.
4. Se descartó un `Custom Block` porque duplicaría responsabilidades, como la lógica de inferencia y el manejo del ciclo de vida, que ya existen en `Model.infer_from_request()` y `ModelManager`. La evolución del `ModelRegistry` se consideró arquitectónicamente correcta porque centraliza la responsabilidad de la carga y gestión de modelos, aprovechando características existentes como el caché y el "lazy loading", y manteniendo la consistencia del sistema.
5. El `ModelManager` es el orquestador central que mantiene un diccionario de los modelos cargados y enruta las solicitudes de inferencia al modelo correcto. Para obtener las clases de modelo, utiliza un `ModelRegistry` (como el `CompositeModelRegistry`) que mapea un `model_id` a la clase concreta del modelo. Dentro del `InferencePipeline`, el `ModelManager` es inyectado para cargar dinámicamente los modelos que el flujo de trabajo necesita.
6. `ONNX Runtime` es la librería utilizada para ejecutar la inferencia de los modelos locales en formato ONNX, gestionando automáticamente el uso de CPU o GPU. Fue elegido sobre `Ultralytics` por ser una dependencia más ligera (lightweight), enfocada únicamente en la inferencia, y por ser agnóstica al formato, lo que permite utilizar modelos exportados desde cualquier framework (PyTorch, TensorFlow, etc.) y evita posibles conflictos de versiones.
7. "Lazy loading" (carga perezosa) es una estrategia de optimización donde los modelos no se cargan en la memoria al iniciar el sistema, sino únicamente cuando son requeridos por primera vez por un flujo de trabajo. El `ModelManager` implementa este comportamiento, verificando si un modelo ya está en su caché antes de solicitar su carga, lo que mejora el tiempo de arranque y reduce el consumo de memoria inicial.
8. El principio "Fail-Fast" significa que el sistema está diseñado para fallar lo antes posible si detecta un error de configuración, en lugar de esperar a un fallo en tiempo de ejecución. En la implementación de modelos locales, esto se logra mediante la validación del esquema de los `ModelManifests` JSON utilizando Pydantic en el momento de la carga (`load time`), asegurando que todos los manifiestos son correctos antes de que el pipeline intente usarlos.
9. Los dos flujos principales son el `InferencePipeline` para el procesamiento de video en tiempo real (stream engine) y el `WorkflowRunner` para ejecutar flujos de trabajo declarativos (workflow engine runner). Ambos sistemas se integran con el `ModelManager` para la carga y ejecución de los modelos necesarios en cada frame o paso del workflow.
10. La retrocompatibilidad se garantiza a través del mecanismo de fallback del `CompositeModelRegistry`. Si un `model_id` de un flujo de trabajo existente no corresponde a un manifiesto local, el `LocalModelRegistry` no lo encontrará; entonces, el `CompositeModelRegistry` pasará la solicitud al `RoboflowModelRegistry`, que procederá a cargarlo desde la API de Roboflow como lo hacía en la arquitectura anterior, sin requerir cambios en los archivos JSON de los flujos de trabajo existentes.

--------------------------------------------------------------------------------

## Preguntas de Ensayo

1. Analice en profundidad la decisión de diseño de utilizar manifiestos en formato JSON en lugar de una configuración en código Python para registrar modelos locales. Discuta las ventajas y desventajas de cada enfoque en términos de validación, versionado, usabilidad para perfiles no desarrolladores y mantenibilidad del sistema.
2. Explique cómo la nueva arquitectura aplica los principios SOLID, específicamente el Principio de Responsabilidad Única (SRP), el Principio Abierto/Cerrado (OCP) y el Principio de Inversión de Dependencias (DIP). Proporcione ejemplos concretos de clases y relaciones del sistema para cada principio.
3. Describa el flujo completo de una solicitud de inferencia para un modelo local, desde que se inicializa el `InferencePipeline` con un workflow hasta que se devuelven las detecciones. Detalle la interacción entre `WorkflowRunner`, `ExecutionEngine`, `CompositeModelRegistry`, `LocalModelRegistry`, `ModelManager` y la clase `LocalONNXObjectDetection`.
4. La documentación menciona que el aumento de la complejidad ciclomática en la nueva arquitectura es "complejidad por diseño, no por accidente". Elabore sobre esta afirmación, contrastando la complejidad estructural (bien diseñada) con la complejidad accidental, y justifique por qué el nuevo diseño, aunque más complejo en métricas, es superior en términos de mantenibilidad y extensibilidad.
5. Utilizando el modelo de Vista 4+1 de Kruchten como marco, describa cómo la arquitectura propuesta aborda las perspectivas Lógica, de Procesos, de Desarrollo y Física para el despliegue de modelos en un dispositivo de borde (Edge Device) sin conexión a internet.

--------------------------------------------------------------------------------

## Glosario de Términos Clave

|   |   |
|---|---|
|Término|Definición|
|**Chain of Responsibility**|Un patrón de diseño de comportamiento que permite pasar solicitudes a lo largo de una cadena de manejadores. En este sistema, el `CompositeModelRegistry` lo usa para intentar resolver un modelo localmente primero y, si falla, pasa la solicitud al `RoboflowModelRegistry`.|
|**Composite Registry Pattern**|Un patrón de diseño estructural que permite componer múltiples registros (`LocalModelRegistry`, `RoboflowModelRegistry`) en una única interfaz (`CompositeModelRegistry`), tratándolos de manera uniforme y permitiendo el fallback entre ellos.|
|**ExecutionEngine**|Componente de la librería de inferencia de Roboflow que maneja la ejecución del grafo de bloques definido en un workflow. Es invocado por el `WorkflowRunner`.|
|**Fail-Fast**|Un principio de diseño de sistemas que dicta que un sistema debe reportar cualquier condición de fallo tan pronto como sea posible. Se implementa validando los manifiestos JSON con Pydantic en el momento de la carga.|
|**InferencePipeline**|El componente principal para el procesamiento de streams de video en tiempo real (stream engine). Se encarga de recibir frames, ejecutar workflows sobre ellos y enviar los resultados a un sink.|
|**Lazy Loading**|Estrategia de optimización que consiste en retrasar la carga y la inicialización de un objeto (en este caso, un modelo) hasta el momento en que se necesita por primera vez, reduciendo el consumo inicial de memoria.|
|**LocalModelRegistry**|Un registro de modelos responsable de descubrir y cargar modelos locales. Escanea un directorio en busca de archivos de manifiesto (`ModelManifest`) y mapea los `task_type` a las clases de modelo ONNX correspondientes.|
|**ModelManifest**|Un archivo de configuración declarativo en formato JSON que contiene los metadatos de un modelo local, como su `model_id`, `task_type`, ruta al archivo `.onnx` y nombres de clases.|
|**ModelManager**|El orquestador central que gestiona el ciclo de vida de los modelos. Mantiene un diccionario de modelos activos, utiliza un `ModelRegistry` para obtenerlos y enruta las solicitudes de inferencia.|
|**ModelRegistry**|Una interfaz o clase base que define cómo obtener clases de modelo a partir de un `model_id`. El `CompositeModelRegistry` y el `LocalModelRegistry` son implementaciones de este concepto.|
|**NMS (Non-Maximum Suppression)**|Un paso de post-procesamiento utilizado en modelos de detección de objetos para eliminar cajas delimitadoras (bounding boxes) duplicadas o redundantes que apuntan al mismo objeto.|
|**ONNX Runtime**|Una librería de inferencia de alto rendimiento y multiplataforma para modelos en formato ONNX. Permite ejecutar modelos de manera agnóstica al framework original (PyTorch, TensorFlow) y optimizada para CPU o GPU.|
|**Pydantic**|Una librería de Python para la validación de datos y la gestión de configuraciones mediante anotaciones de tipos. Se utiliza para validar el esquema de los archivos `ModelManifest`.|
|**Retrocompatibilidad**|La capacidad de un nuevo sistema o arquitectura para seguir funcionando con los flujos de trabajo, datos o configuraciones existentes del sistema anterior sin necesidad de modificaciones.|
|**RoboflowInferenceModel**|Una clase base de la cual heredan los modelos, que gestiona la descarga y el almacenamiento en caché de los artefactos del modelo desde fuentes como S3 o la API de Roboflow.|
|**RoboflowModelRegistry**|El registro de modelos original, fuertemente acoplado a la API de Roboflow, que obtiene el tipo de modelo y sus artefactos a través de llamadas de red a dicha API.|
|**Vista 4+1 (Kruchten)**|Un modelo de vista de arquitectura de software que utiliza cinco vistas concurrentes (Lógica, de Procesos, de Desarrollo, Física y de Escenarios) para describir un sistema desde diferentes perspectivas.|
|**WorkflowRunner**|Un componente que actúa como puente entre el `InferencePipeline` y el `ExecutionEngine`. Recibe los frames de video, construye los parámetros de entrada y ejecuta el workflow frame por frame.|