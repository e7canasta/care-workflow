# Propuesta Técnica: Roadmap de Evolución del Sistema de Gestión de Modelos

## 1. Introducción y Contexto Arquitectural

Tras la exitosa implementación de la arquitectura basada en el `Composite Registry Pattern` para la gestión de modelos ONNX locales, nuestro sistema se encuentra en un punto de inflexión, preparado para una nueva fase de evolución estratégica. Este documento presenta un roadmap detallado de mejoras subsecuentes, diseñadas para incrementar el rendimiento, la flexibilidad y la fiabilidad del sistema. El objetivo es proporcionar una guía clara para el liderazgo técnico y de producto, facilitando la planificación estratégica a corto, mediano y largo plazo.

La reciente refactorización ha sentado una base sólida y extensible, superando las limitaciones de un sistema fuertemente acoplado. Esta refactorización abordó directamente limitaciones críticas de la arquitectura anterior, concretamente la dependencia obligatoria de llamadas a la API para la resolución de modelos y la incapacidad de soportar nativamente modelos locales ajenos a Roboflow. Los logros clave de esta fase inicial incluyen:

- **Soporte para Múltiples Fuentes de Modelos:** La implementación del `Composite Registry Pattern` permite que el sistema obtenga modelos desde diversas fuentes (locales, Roboflow, etc.) de manera transparente y desacoplada.
- **Independencia de la API para Modelos Locales:** El soporte para modelos ONNX locales, definidos mediante manifiestos JSON, elimina la necesidad de realizar llamadas a la API de Roboflow para casos de uso en entornos de borde (_edge_) o sin conexión.
- **Validación Temprana y Robusta:** Se ha establecido un mecanismo de validación "fail-fast" en el momento de la carga, utilizando Pydantic para verificar la integridad de los manifiestos de los modelos y prevenir errores en tiempo de ejecución.
- **Compatibilidad Total con Versiones Anteriores:** La nueva arquitectura mantiene un 100% de compatibilidad con los flujos de trabajo (_workflows_) existentes, garantizando una transición sin interrupciones y sin necesidad de modificar implementaciones previas.

Partiendo de esta base robusta, las siguientes propuestas están diseñadas para construir sobre estos logros, desbloquear nuevas capacidades críticas y preparar el sistema para las exigencias de un entorno de producción a gran escala.

## 2. Roadmap de Mejoras Propuestas

Las propuestas que se describen a continuación están organizadas en grupos lógicos que reflejan su prioridad estratégica y su impacto en el sistema. Este enfoque modular conforma un roadmap coherente que permite una evolución incremental y controlada. Cada propuesta incluye un análisis detallado de sus objetivos, los beneficios estratégicos que aporta, una estimación del esfuerzo requerido y una prioridad recomendada para facilitar la toma de decisiones y la asignación de recursos.

### 2.1. Prioridad Alta: Capacidades Fundamentales para Producción

Estas iniciativas son consideradas críticas para garantizar la estabilidad, mantenibilidad y preparación operativa del sistema en un entorno de producción. Abordan los pilares de calidad y fiabilidad sobre los cuales se construirán todas las capacidades futuras.

#### 2.1.1. Propuesta: Implementación de Pruebas de Integración y CI/CD

El objetivo principal de esta propuesta es desarrollar una suite de pruebas automatizadas de extremo a extremo (_end-to-end_) que validen la arquitectura completa del sistema de gestión de modelos y su integración con los pipelines de inferencia. Estas pruebas se integrarán en un pipeline de Integración Continua y Despliegue Continuo (CI/CD).

**Beneficios Estratégicos:**

- **Fiabilidad:** Garantiza que las nuevas funcionalidades o refactorizaciones no introduzcan regresiones, validando explícitamente tanto la carga exitosa de modelos locales a través de manifiestos como el correcto funcionamiento del mecanismo de _fallback_ a Roboflow cuando un modelo local no es encontrado.
- **Calidad del Código:** Automatiza la validación del sistema, manteniendo un estándar de calidad elevado de forma consistente y previniendo la acumulación de deuda técnica.
- **Agilidad de Desarrollo:** Permite a los equipos de desarrollo desplegar nuevas características y correcciones de errores de manera más rápida y segura, reduciendo el riesgo asociado a cada cambio.

|   |   |
|---|---|
|Parámetro|Valoración|
|**Prioridad Estratégica**|Alta|
|**Esfuerzo Estimado**|6-8 horas|

#### 2.1.2. Propuesta: Versionado de Modelos y Recarga en Caliente (Hot-Reload)

Esta propuesta se centra en implementar un mecanismo que permita actualizar las versiones de los modelos referenciados en los manifiestos JSON sin necesidad de reiniciar el pipeline de inferencia. El sistema detectaría cambios en los manifiestos y recargaría los modelos correspondientes dinámicamente.

**Beneficios Estratégicos:**

1. **Cero Downtime en Despliegues:** Permite la actualización de modelos de inteligencia artificial en producción sin interrumpir el servicio, un requisito fundamental para sistemas de alta disponibilidad.
2. **Experimentación Ágil (A/B Testing):** Facilita que los equipos de producto y ciencia de datos puedan probar rápidamente diferentes versiones de un modelo. Simplemente cambiando un archivo de manifiesto, pueden observar métricas de rendimiento en tiempo real y tomar decisiones basadas en datos. Esto transforma las actualizaciones de modelos de una tarea de ingeniería de alto riesgo a un ciclo de iteración de producto de baja fricción e impulsado por datos.
3. **Rollbacks Instantáneos:** En caso de que una nueva versión del modelo presente un rendimiento inesperado o errores, esta capacidad permite revertir de forma inmediata a una versión anterior y estable restaurando su manifiesto, minimizando el impacto en el usuario final.

|   |   |
|---|---|
|Parámetro|Valoración|
|**Prioridad Estratégica**|Media-Alta|
|**Esfuerzo Estimado**|6-8 horas|

### 2.2. Prioridad Media: Expansión de Capacidades y Rendimiento

Una vez establecida la base de fiabilidad y estabilidad operativa, el siguiente paso lógico es expandir las capacidades del sistema para abordar una gama más amplia de casos de uso y optimizar su rendimiento para escenarios de alta demanda.

#### 2.2.1. Propuesta: Completar Soporte para Tipos de Tareas Adicionales (Fase 4)

El objetivo es extender la arquitectura `LocalONNXModel` para dar soporte nativo a nuevas tareas de visión por computadora más allá de la detección de objetos. La arquitectura actual fue diseñada explícitamente para ser extensible, y esta fase materializa ese diseño. La base arquitectónica ya está en su lugar; esta fase implica implementar la lógica de parseo de salidas y post-procesamiento específica de cada tarea dentro de las subclases de `LocalONNXModel`, tal como se previó originalmente en el plan de implementación. Esta expansión desbloqueará todo el potencial de los modelos locales para un rango mucho más amplio de aplicaciones industriales y comerciales.

|   |   |   |
|---|---|---|
|Tipo de Tarea|Complejidad Estimada|Esfuerzo Estimado (horas)|
|**Pose Estimation**|Media|4-6|
|**Instance Segmentation**|Alta|6-8|
|**Classification**|Baja|2-3|

#### 2.2.2. Propuesta: Soporte para Múltiples Backends de Inferencia

Esta propuesta consiste en abstraer la capa de ejecución de inferencia para permitir el uso de _backends_ alternativos al `ONNX Runtime` por defecto. Esto permitiría al sistema seleccionar dinámicamente el motor de inferencia más optimizado para el hardware subyacente.

**Beneficios Estratégicos:**

- **Optimización por Hardware:** Permite seleccionar el motor de inferencia más eficiente para la plataforma de despliegue, ya sean GPUs NVIDIA, CPUs Intel u otro hardware especializado.
- **Aceleración con TensorRT:** Ofrece una ganancia de velocidad potencial de **2x a 5x** en GPUs NVIDIA, crucial para aplicaciones de baja latencia.
- **Aceleración con OpenVINO:** Proporciona una mejora de rendimiento de **2x a 3x** en CPUs de Intel, optimizando el costo y la eficiencia en despliegues que no cuentan con GPUs dedicadas.

|   |   |
|---|---|
|Parámetro|Valoración|
|**Prioridad Estratégica**|Media|
|**Esfuerzo Estimado**|8-12 horas|

### 2.3. Prioridad Baja: Mejoras Futuras y Ecosistema

Este grupo final de propuestas representa mejoras estratégicas a largo plazo. Aunque no son críticas para el roadmap inmediato, su implementación potenciaría significativamente la extensibilidad, la inteligencia y el ecosistema alrededor de nuestro sistema de gestión de modelos.

#### 2.3.1. Propuesta: Descubrimiento de Registros de Modelos vía Entry Points

El objetivo es evolucionar hacia un sistema de _plugins_ que permita a paquetes externos registrar sus propias implementaciones de `ModelRegistry` sin necesidad de modificar el código base de `care-workflow`. Esto se lograría utilizando el mecanismo de _entry points_ de Python.

**Beneficios Estratégicos:**

- **Extensibilidad Máxima:** Habilita a la comunidad o a otros equipos internos para desarrollar y mantener de forma independiente el soporte para nuevas fuentes de modelos, como `HuggingFaceRegistry` u `OllamaRegistry`, fomentando un ecosistema de contribuciones donde el soporte para nuevas fuentes de modelos puede crecer orgánicamente sin crear un cuello de botella en el equipo central.
- **Desacoplamiento:** Refuerza la separación de responsabilidades, manteniendo el núcleo del sistema más simple, estable y fácil de mantener, mientras que la funcionalidad extendida reside en paquetes externos.

|   |   |
|---|---|
|Parámetro|Valoración|
|**Prioridad Estratégica**|Baja|
|**Esfuerzo Estimado**|4-6 horas|

#### 2.3.2. Propuesta: Benchmarking y Selección Automática de Modelos

Esta propuesta avanzada busca construir un sistema capaz de seleccionar automáticamente el modelo óptimo para ejecutar, basándose en un conjunto de restricciones definidas por el usuario, como la latencia máxima, la precisión deseada y el hardware disponible.

**Beneficios Estratégicos:**

- **Optimización Automática:** El sistema elige de forma inteligente la mejor variante del modelo (p. ej., ONNX, TensorRT, INT8, FP16) para el entorno de despliegue específico, maximizando el rendimiento sin intervención manual.
- **Experiencia de Usuario Simplificada:** Los usuarios pueden definir sus objetivos de negocio (p. ej., "respuesta más rápida" o "máxima precisión") sin necesidad de poseer un conocimiento profundo sobre las especificidades técnicas de cada modelo o backend.

|   |   |
|---|---|
|Parámetro|Valoración|
|**Prioridad Estratégica**|Baja|
|**Esfuerzo Estimado**|10-14 horas|

En conjunto, estas iniciativas conforman un plan de evolución cohesivo, que se resume a continuación para una evaluación estratégica.

## 3. Resumen Estratégico del Roadmap

Esta sección consolida todas las iniciativas propuestas en una vista unificada de alto nivel. El objetivo de este resumen es facilitar la planificación estratégica y la asignación de recursos, presentando una comparación clara del esfuerzo estimado frente al impacto y la prioridad de cada iniciativa.

|   |   |   |   |
|---|---|---|---|
|Propuesta|Objetivo Principal|Prioridad Recomendada|Esfuerzo Estimado (Total Horas)|
|**Implementación de Pruebas de Integración y CI/CD**|Asegurar la fiabilidad y agilidad del sistema para un entorno de producción.|Alta|6-8|
|**Versionado de Modelos y Recarga en Caliente**|Permitir actualizaciones de modelos sin downtime y facilitar la experimentación.|Media-Alta|6-8|
|**Soporte para Tipos de Tareas Adicionales (Fase 4)***|Extender la funcionalidad a nuevas tareas como Pose, Segmentation y Classification.|Media|12-17|
|**Soporte para Múltiples Backends de Inferencia**|Optimizar el rendimiento de la inferencia según el hardware (TensorRT, OpenVINO).|Media|8-12|
|**Descubrimiento de Registros de Modelos vía Entry Points**|Crear un ecosistema de plugins para añadir nuevas fuentes de modelos externamente.|Baja|4-6|
|**Benchmarking y Selección Automática de Modelos**|Seleccionar inteligentemente el mejor modelo según restricciones de rendimiento y precisión.|Baja|10-14|

_La prioridad Media se asigna al conjunto de tareas de la Fase 4 para su planificación agrupada. La implementación de cada tipo de tarea individual puede priorizarse de forma independiente según las necesidades del producto._

Con esta perspectiva consolidada, procedemos a las conclusiones finales y los próximos pasos recomendados para la ejecución.

## 4. Conclusión y Próximos Pasos Recomendados

La adopción de este roadmap transformará nuestro sistema de gestión de modelos de un componente funcional a una plataforma robusta, escalable y preparada para producción. Cada iniciativa propuesta no solo añade una nueva capacidad, sino que refuerza los cimientos arquitectónicos del sistema, aplicando la filosofía de **"complejidad por diseño, no por accidente"**. Esto contrasta directamente con la búsqueda de soluciones más simples a corto plazo, como los bloques de workflow personalizados, que habrían introducido deuda técnica e inconsistencia arquitectónica, lo que denominamos "complejidad por accidente". La ejecución de este plan estratégico generará retornos significativos en términos de rendimiento, eficiencia operativa y capacidad de extensión futura, posicionando nuestra tecnología a la vanguardia.

Para materializar esta visión, recomendamos los siguientes pasos:

1. **Validación de la Propuesta:** Realizar una revisión formal y obtener la aprobación de este roadmap por parte del liderazgo técnico y de producto para alinear las expectativas y asegurar los recursos necesarios.
2. **Planificación de Sprints:** Priorizar la incorporación inmediata del item de **Prioridad Alta** (Pruebas de Integración/CI-CD) en el próximo ciclo de desarrollo. Planificar la iniciativa de **Prioridad Media-Alta** (Recarga en Caliente) para los sprints subsiguientes, alineando su despliegue con la transición del sistema al entorno de producción.
3. **Ejecución Iterativa:** Comenzar la implementación con las iniciativas fundacionales de mayor prioridad para entregar valor de manera incremental y construir sobre una base cada vez más sólida.