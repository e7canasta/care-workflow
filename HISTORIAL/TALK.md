
 🎉 Resumen - Custom Blocks Integrados  
  
 Implementé un plugin system completo para usar tu custom block mqtt_writer_sink@v1 con Roboflow Inference workflows.  
  
 ---  
 📦 Estructura Creada  
  
 1. Plugin Loader (`care_workflow/care_blocks/)  
  
```python
 # care_workflow/care_blocks/__init__.py  
 def load_blocks() -> List[Type[WorkflowBlock]]:  
     return [MQTTWriterSinkBlockV1]  
```
  
**Patrón**: Entry point que Roboflow Inference importa dinámicamente via WORKFLOWS_PLUGINS env var.  
  
 ---  
 
 2. Workflow JSON de Ejemplo  
  
`data/workflows/examples/mqtt_detection_alert.json`:  
 - Detecta personas con YOLOv11  
 - Cuenta detecciones  
 - Publica alertas a MQTT broker  
 - Retorna status de publicación  
  
 Flujo:  
 
 ```python
 Video → Detector → Counter → MQTT Writer → Broker  
                                     ↓  
                             error_status, message  
```
 
 
 ---  
 
 3. Script de Ejecución  
  
 `examples/run_mqtt_detection.py`:  
 - Configura pipeline con custom blocks  
 - Maneja comandos interactivos (pause/resume/terminate)  
 - Muestra status de MQTT en consola  
 - Visualiza detecciones (opcional)  
  
 Usage:  
 ```bash
 export WORKFLOWS_PLUGINS="care.workflows.care_steps"  
 export WORKFLOW_DEFINITION="data/workflows/examples/mqtt_detection_alert.json"  
 export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"  
 export MQTT_HOST="localhost"  
 export MQTT_PORT="1883"  
 export MQTT_TOPIC="care/detections/alerts"  
  
 python examples/run_mqtt_detection.py  
  ```

 ```bash
 WORKFLOWS_PLUGINS="care.workflows.care_steps" WORKFLOW_DEFINITION="data/workflows/examples/mqtt_detection_alert.json"  VIDEO_REFERENCE="rtsp://localhost:8554/live/1"  MQTT_HOST="localhost"  MQTT_PORT="1883"  MQTT_TOPIC="care/detections/alerts"  uv run python examples/run_mqtt_detection.py  
```
  
 ---  
 4. Test Suite  
  
 `examples/test_mqtt_block.py`:  
 - ✅ Verifica plugin loading  
 - ✅ Verifica block registration  
 - ✅ Valida manifest structure  
 - ✅ Test de ejecución (opcional con broker)  
  
 Usage:  
 ```bash
 # Test básico (sin broker)  
 python examples/test_mqtt_block.py  
  
 # Test completo (con broker)  
 python examples/test_mqtt_block.py --with-broker  
```

 ---  
 5. Documentación  
  
	 1. `care_workflow/care_blocks/README.md`:  
	   - Instalación y activación  
	   - Referencia de blocks disponibles  
	   - Ejemplos de uso  
	   - Template para nuevos blocks  
	   - Troubleshooting  
	 2. `docs/CUSTOM_BLOCKS_GUIDE.md`:  
	   - Quick start  
	   - Arquitectura visual (diagramas ASCII)  
	   - Ciclo de vida del plugin  
	   - Ejemplos de workflows  
	   - Debug guide  
	 3. `CLAUDE.md (actualizado)`:  
	   - Sección nueva: "Custom Workflow Blocks"  
	   - Arquitectura del plugin loader  
	   - Patrón de uso  
	   - Fail-fast en load time  
	 4. `.env.example`:  
	   - Template de configuración  
	   - Todas las variables documentadas  
  
 ---  
 🚀 Cómo Empezar  
  
 Quick Test (Sin Video)  
  
 # 1. Activar plugin  
 
```
export WORKFLOWS_PLUGINS="care.workflows.care_steps"  
```  
 
 # 2. Test  
 
```
 python examples/test_mqtt_block.py  
```
 
 Output esperado:  
 
 ✅ PASS - Plugin Loading  
 ✅ PASS - Block Registration  
 ✅ PASS - Manifest Structure  
  
 ---  
 Test con MQTT (Sin Video)  
  
 Terminal 1 - Broker:  
 ```
 mosquitto -v  
 ``` 
 
 Terminal 2 - Test:  
 
 ```
 python examples/test_mqtt_block.py --with-broker  
 ```
  
 Output esperado: Mensaje publicado exitosamente.  
  
 ---  
 Workflow Completo (Con Video)  
  
 Terminal 1 - go2rtc:  

```
 go2rtc -config config/go2rtc/go2rtc.yaml  
```
  
 Terminal 2 - MQTT subscriber:  

```
 mosquitto_sub -h localhost -t "care/detections/alerts" -v  
```
  
 Terminal 3 - Pipeline:  

 ```
 export WORKFLOWS_PLUGINS="care.workflows.care_steps"  
 export WORKFLOW_DEFINITION="data/workflows/examples/mqtt_detection_alert.json"  
 export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"  
 export MQTT_HOST="localhost"  
 export MQTT_PORT="1883"  
 export MQTT_TOPIC="care/detections/alerts"  
  
 python examples/run_mqtt_detection.py  
 ```
  
 Output esperado:  
 - Video con bboxes en ventana CV2  
 - Alertas en Terminal 2 cuando detecta personas  
 - Status en Terminal 3  
  
 ---  
 🏗 Arquitectura Clave  
  
 Plugin Loading Flow  

  ```
  
 WORKFLOWS_PLUGINS="care.workflows.care_steps"  
          ↓  
 InferencePipeline.init_with_workflow()  
          ↓  
 blocks_loader.get_plugin_modules()  
          ↓  
 importlib.import_module("care.workflows.care_steps")  
          ↓  
 module.load_blocks() → [MQTTWriterSinkBlockV1]  
          ↓  
 ExecutionEngine.register(blocks)  
  
 Workflow Execution (Por Frame)  
  
 Frame → Detector → Predictions  
               ↓  
           Counter → count  
               ↓  
       Resolve selectors:  
         host = "$inputs.mqtt_host"  
         message = "Count: {count}"  
               ↓  
       MQTT Writer Block:  
         - Connect (lazy, persistent)  
         - Publish(topic, message)  
         - Return {error_status, message}  
               ↓  
           Sink callback:  
             - Display status  
             - Visualize (opcional) 

```
  
 ---  
 🎯 Beneficios del Diseño  
  
 1. Fail-Fast en Load Time  
  
 - Plugin inválido → `PluginLoadingError` al inicio  
 - Manifest incorrecto → `luginInterfaceError` al inicio  
 - NO fallos silenciosos en runtime  
  
 2. Desacoplamiento  
  
 - `are_workflow.care_blocks` es módulo independiente  
 - Mismo protocolo que plugins de Roboflow  
 - Puedes distribuirlo como package separado  
  
 3. Extensibilidad  
  
 - Template claro para nuevos blocks  
 - Solo agregar a `load_blocks()` para registrar  
 - Sin modificar código de Roboflow  
  
 4. Complejidad por Diseño  
  
 - No crear nuevo framework  
 - SÍ usar plugin system existente  
 - Arquitectura emergente de Roboflow, no re-inventada  
  
 ---  
 📝 Próximos Pasos  
  
 Inmediato  
  
 1. ✅ Ejecutar python `examples/test_mqtt_block.py`  
 2. ✅ Probar workflow completo con video  
  
 Corto Plazo  
  
 1. Implementar otros sinks:  
   - `opc_writer_sink@v1` (ya tenés el código base)  
   - `plc_modbus_sink@v1`  
   - `sql_server_sink@v1`  
   
   2. Agregar al load_blocks():  
 
 ```python
 
 def load_blocks():  
     return [  
         MQTTWriterSinkBlockV1,  
         OPCWriterSinkBlockV1,      # ← Agregar  
         PLCModbusSinkBlockV1,      # ← Agregar  
         SQLServerSinkBlockV1,      # ← Agregar  
     ]  
 ```
  
 Medio Plazo  
  
 3. Optimizar MQTT block (fire-and-forget)  
 4. Agregar tests unitarios para blocks  
 5. CI/CD para validar plugin loading  
  
 ---  
 🔧 Files Modificados/Creados  
  
 ✅ care_workflow/care_blocks/__init__.py           (nuevo - plugin loader)  
 ✅ care_workflow/care_blocks/sinks/__init__.py     (nuevo)  
 ✅ care_workflow/care_blocks/sinks/mqtt_writer/__init__.py  (nuevo)  
 ✅ care_workflow/care_blocks/README.md             (nuevo - docs)  
  
 ✅ data/workflows/examples/mqtt_detection_alert.json  (nuevo - workflow)  
  
 ✅ examples/run_mqtt_detection.py                  (nuevo - ejecutable)  
 ✅ examples/test_mqtt_block.py                     (nuevo - test suite)  
  
 ✅ docs/CUSTOM_BLOCKS_GUIDE.md                     (nuevo - guía)  
  
 ✅ .env.example                                    (nuevo - template)  
  
 ✅ CLAUDE.md                                       (actualizado)  
  
 ---  
 💡 Lecciones de Diseño  
  
 6. "Plugin protocol > Custom implementation"  
   - Usar sistema existente de Roboflow  
   - NO crear nuestro propio registry  
 2. "Fail fast en load time, no runtime"  
   - Validar manifest structure al cargar  
   - Errores de config antes de procesar video  
 3. "Simplicidad estructural ≠ Simplicidad ingenua"  
   - load_blocks() retorna lista simple  
   - Pero protocolo complejo manejado por Roboflow  
   - KISS aplicado correctamente  
 4. "Documentation as architecture"  
   - Diagramas ASCII muestran bounded contexts  
   - Quick start enfocado en uso, no implementación  
   - Troubleshooting basado en errores reales



● Tenés razón, no tiene sentido enviar la misma alerta constantemente. Lo que necesitamos es lógica condicional en el workflow para que solo publique cuando:  
  
 1. Hay detecciones (count > 0)  
 2. Cambió el estado (transición de sin personas → con personas)  
  
 Además, veo que el mensaje está mostrando el selector literal $steps.count.count en vez del valor real.  
  
 Opciones de Solución  
  
 Opción 1: Usar DetectionsConsensus Block (Built-in)  
  
 Roboflow tiene un block roboflow_core/DetectionsConsensus que puede ayudar con debouncing de detecciones.  
  
 Opción 2: Custom Block ConditionalMQTTWriter  
  
 Crear un block que:  
 - Mantenga estado interno (último count publicado)  
 - Solo publique cuando count > threshold Y cambió desde último estado  
 - Formatee correctamente el mensaje con el valor real  
  
 Opción 3: Usar Condition Block (Built-in)  
  
 Roboflow tiene un block roboflow_core/Condition para evaluar expresiones y rutear el workflow.  
  
 ---  
 Propuesta: Usar Condition Block + Mejorar Mensaje  
  
 Ventaja: No requiere custom code, usa infraestructura existente.  
  
 {  
   "steps": [  
     {"type": "roboflow_object_detection_model", "name": "det", ...},  
     {"type": "care/detections_count@v1", "name": "count", "predictions": "$steps.det.predictions"},  
     {  
       "type": "roboflow_core/Condition@v1",  
       "name": "check_alert",  
       "condition": "$steps.count.count > 0"  
     },  
     {  
       "type": "care/mqtt_writer@v1",  
       "name": "mqtt",  
       "message": "¡Persona detectada! Total: {count}",  // Interpolación  
       "condition": "$steps.check_alert.result"  
     }  
   ]  
 }  
  
 Problema: Esto todavía publicaría en cada frame que tenga count > 0.  
  
 ---  
 ¿Qué preferís?  
  
 1. Opción A: Custom block care/conditional_mqtt@v1 con lógica de debouncing (cooldown period)  
 2. Opción B: Agregar parámetro throttle_seconds al MQTT block actual  
 3. Opción C: Usar DetectionsConsensus para suavizar detecciones + fix del mensaje