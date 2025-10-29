# Glosario de Términos Clave de Arquitectura

Este glosario define el vocabulario fundamental de la arquitectura de software del proyecto. Su objetivo es ayudar a los nuevos miembros del equipo y a estudiantes a comprender rápidamente los conceptos esenciales que sustentan nuestro sistema.

--------------------------------------------------------------------------------

### 1. Componentes Centrales de Gestión de Modelos

En esta sección, se definen los dos componentes que forman el núcleo del sistema de gestión de modelos.

#### 1.1. ModelManager

**El** `**ModelManager**` **es el orquestador central que gestiona el ciclo de vida de los modelos y dirige las solicitudes de inferencia.**

Sus responsabilidades principales son:

- Mantener un diccionario interno de todos los modelos que han sido cargados.
- Enrutar las solicitudes de inferencia entrantes hacia la instancia del modelo correcto.
- Gestionar un caché de modelos de tamaño fijo para controlar y limitar el uso de la memoria RAM.

**💡 Insight Clave:** La estrategia de _lazy loading_ (carga diferida) que utiliza es crucial, ya que garantiza que un modelo solo se cargue en memoria en el momento exacto en que se necesita por primera vez, optimizando el rendimiento y el uso de recursos.

#### 1.2. ModelRegistry

**El** `**ModelRegistry**` **(Registro de Modelos) es el componente responsable de mapear un tipo de modelo a su clase de implementación específica.**

Actúa como un catálogo que le indica al `ModelManager` qué "plano" de código usar para construir un modelo. En el sistema coexisten dos implementaciones principales:

- `RoboflowModelRegistry`: Utiliza la API de Roboflow para determinar el tipo de modelo y obtener su clase correspondiente.
- `LocalModelRegistry`: Utiliza archivos _manifest_ locales en formato JSON para registrar modelos locales sin depender de una API externa.

**💡 Insight Clave:** Esta abstracción desacopla al sistema de una única fuente de modelos, permitiendo que sea fácilmente extensible en el futuro para soportar nuevos registros (por ejemplo, un `HuggingFaceModelRegistry`) sin modificar el código existente.

Estos core components no existen en un vacío; su poder y flexibilidad se derivan de patrones arquitectónicos probados que aseguran que el sistema sea tanto robusto como extensible.

--------------------------------------------------------------------------------

### 2. Patrones Arquitectónicos y Tecnologías Habilitadoras

En esta sección, se explican los patrones de diseño y las tecnologías clave que sustentan la arquitectura de modelos.

#### 2.1. Patrones y Formatos Clave

|   |   |
|---|---|
|Término|Descripción y Propósito en el Proyecto|
|**Composite Pattern**|Este patrón de diseño se utiliza para crear el `CompositeModelRegistry`, que combina múltiples registros (`LocalModelRegistry` y `RoboflowModelRegistry`) bajo una única interfaz. Su propósito es implementar el patrón **Chain of Responsibility** a través de un sistema de _fallback_ automático: primero intenta resolver un modelo localmente y, si falla, pasa la solicitud al siguiente registro. Este diseño adhiere al **Principio de Abierto/Cerrado (Open/Closed Principle)**, permitiendo agregar nuevas fuentes de modelos (como `HuggingFaceModelRegistry`) sin modificar el código existente.|
|**ONNX**|Es un formato de modelo de estándar abierto que permite al proyecto ejecutar **modelos propios y locales** de forma altamente eficiente, especialmente en sus versiones cuantizadas (INT8, FP16). En el proyecto, se utiliza la librería `ONNX Runtime` como un motor de inferencia ligero, lo cual reduce la latencia y evita la necesidad de instalar dependencias más pesadas como `ultralytics`.|
|**Pydantic**|Es la librería utilizada para la validación del esquema de los archivos `ModelManifest`. Su propósito clave es asegurar que los manifiestos JSON tengan la estructura y los tipos de datos correctos en el momento de la carga. Esto aplica el principio de _Fail Fast_ (fallar rápido) para detectar errores de configuración de inmediato, en lugar de permitir que causen fallos inesperados durante la ejecución.|

Con estos patrones fundamentales en mente, podemos ahora examinar cómo se orquestan dentro de los flujos de ejecución principales del sistema.

--------------------------------------------------------------------------------

### 3. Flujos de Ejecución y Motores

En esta sección, se definen los componentes responsables de ejecutar los modelos en los diferentes contextos del sistema.

#### 3.1. InferencePipeline

**El** `**InferencePipeline**` **es el flujo de ejecución principal diseñado para el procesamiento de video en tiempo real.**

Es el componente de alto nivel que inicializa el `ModelManager` y lo configura para usar el `CompositeModelRegistry`. De esta manera, cuando procesa un stream de video, puede cargar dinámicamente cualquier modelo requerido, ya sea desde una fuente local (manifest) o remota (Roboflow API).

#### 3.2. WorkflowRunner y ExecutionEngine

**El** `**WorkflowRunner**` **actúa como el puente entre el** `**InferencePipeline**` **y el motor de ejecución de workflows (**`**ExecutionEngine**`**) para procesar flujos de trabajo declarativos definidos en JSON.**

Su función es invocar al `**ExecutionEngine**`, que es el motor de bajo nivel responsable de interpretar y ejecutar el grafo de pasos definido en un workflow, utilizando los fotogramas y parámetros que el `WorkflowRunner` le proporciona.

La capacidad de ejecutar workflows complejos de manera dinámica condujo a una evolución arquitectónica crítica: el soporte para modelos locales de alto rendimiento. Esto introdujo un nuevo conjunto de conceptos fundamentales para la potencia actual del sistema.

--------------------------------------------------------------------------------

### 4. Conceptos de la Arquitectura de Modelos Locales

En esta sección, se definen los términos clave introducidos por la arquitectura para soportar modelos locales.

#### 4.1. ModelManifest

**Un** `**ModelManifest**` **es un archivo de configuración declarativo en formato JSON que describe un modelo local y cómo debe ser cargado.**

Contiene metadatos esenciales para que el `LocalModelRegistry` pueda registrar y construir una instancia del modelo. Sus propiedades más importantes son:

- `model_id`: Un identificador único que se utiliza en los workflows para referenciar el modelo.
- `task_type`: Define la tarea del modelo (p. ej., `object-detection`, `pose-estimation`), lo que permite al registro seleccionar la clase de implementación correcta.
- `model_path`: La ruta en el sistema de archivos donde se encuentra el archivo del modelo (p. ej., el archivo `.onnx`).

**💡 Decisión de Diseño:** Se eligió un manifiesto JSON en lugar de una configuración en código para que **científicos de datos y otros roles no centrados en la ingeniería de software** puedan agregar nuevos modelos sin tocar el código fuente, habilitando una validación de esquema robusta con Pydantic y un versionado sencillo a través de Git.

#### 4.2. Custom Block (Como Anti-Patrón)

**Un** `**Custom Block**` **fue una alternativa de diseño considerada para implementar modelos locales, pero fue rechazada por ser un anti-patrón arquitectónico.**

La idea era crear un bloque de workflow específico para ejecutar un modelo local. Esta opción fue descartada porque violaba principios fundamentales de diseño, como la **Separación de Responsabilidades (Single Responsibility Principle)**:

- **Duplicación de responsabilidades:** Requeriría reimplementar la lógica de inferencia, que ya es una responsabilidad de las clases de modelo.
- **Bypass del** `**ModelManager**`**:** Ignoraría por completo al `ModelManager`, perdiendo funcionalidades críticas como el caché centralizado y la carga diferida (_lazy loading_).
- **Inconsistencia arquitectónica:** Crearía dos formas completamente diferentes de ejecutar modelos en el sistema, aumentando la complejidad y la deuda técnica.

Finalmente, evolucionar el `ModelRegistry` representa **complejidad por diseño** —una elección deliberada para una arquitectura robusta y escalable— mientras que el `Custom Block` habría introducido **complejidad por accidente**, conduciendo a una deuda técnica inevitable. En resumen, el `Custom Block` era una solución tácticamente simple pero estratégicamente limitante; la evolución del `ModelRegistry` fue la decisión arquitectónica que nos da la flexibilidad para adaptarnos a cualquier "música" que el futuro requiera.