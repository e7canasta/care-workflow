● ¡Excelente pregunta! Estás tocando un punto clave de diseño de abstracciones. Vamos a analizar esto:

  🎸 The Big Picture: ¿Un Block o Múltiples?

  Tu pregunta plantea 4 casos de uso diferentes:

  1. Threshold Superior (implementado): count >= threshold → Alarma
  2. Threshold Inferior: count < threshold → Alarma (ej: inventario bajo, abandono de zona)
  3. Rango: count NOT IN [min, max] → Alarma (ej: ocupación debe estar entre 5-20)
  4. Propiedades complejas: angle > threshold, time_in_zone > duration, etc.

  Filosofía de Diseño: YAGNI vs Extensibilidad

  Opción A: Extender prediction_alarm@v1 ❌

  {
    "type": "care/prediction_alarm@v1",
    "mode": "above_threshold",  // o "below_threshold", "in_range"
    "threshold": 5,
    "threshold_min": 2,  // solo para "in_range"
    "threshold_max": 10
  }

  Problema: Violamos Single Responsibility Principle
  - Block se vuelve complejo con múltiples modos
  - Cada modo tiene parámetros diferentes (threshold vs min/max)
  - Difícil de testear y mantener

  Opción B: Blocks Especializados ✅ (Recomendado)

  care/prediction_alarm@v1           → count >= threshold
  care/minimum_threshold_alarm@v1    → count < threshold
  care/range_alarm@v1                → count NOT IN [min, max]
  care/property_alarm@v1             → custom conditions

  Ventaja:
  - Cada block tiene un propósito claro
  - Parámetros específicos sin ambigüedad
  - Composable: Puedes usar múltiples blocks en paralelo

  Opción C: Block Genérico con UQL (Over-engineering para ahora) 🔧

  {
    "type": "care/conditional_alarm@v1",
    "condition": {
      "type": "BinaryStatement",
      "left_operand": {"type": "DynamicOperand", "operand_name": "count"},
      "comparator": {"type": "(Number) <"},
      "right_operand": {"type": "StaticOperand", "value": 5}
    }
  }

  Ventaja: Máxima flexibilidad
  Problema: Complejidad innecesaria (YAGNI), usuario debe aprender UQL

  ---
  💡 Mi Recomendación: Crear Blocks Específicos

  Caso 1: Threshold Inferior - care/minimum_threshold_alarm@v1

  Use Case: Detectar cuando algo desaparece o baja de nivel

  {
    "type": "care/minimum_threshold_alarm@v1",
    "name": "alerta_inventario_bajo",
    "count": "$steps.count_productos.count",
    "min_threshold": 10,
    "hysteresis": 2,
    "cooldown_seconds": 300.0,
    "alarm_message_template": "⚠ INVENTARIO BAJO: Solo {count} productos (mínimo: {min_threshold})"
  }

  Lógica:
  # State transitions
  IDLE → FIRING: count < min_threshold AND cooldown elapsed
  FIRING → COOLDOWN: Alarm emitted
  COOLDOWN → IDLE: count >= (min_threshold + hysteresis)

  Casos de Negocio:
  - Retail: Productos en estante bajaron de 10 (restock needed)
  - Manufacturing: Material prima bajo en tolva
  - Security: Equipo crítico faltante en zona (robo)
  - Logistics: Pallets en zona de staging < threshold

  Caso 2: Rango - care/range_alarm@v1

  Use Case: Detectar cuando valor está fuera de rango normal

  {
    "type": "care/range_alarm@v1",
    "name": "alerta_ocupacion_anormal",
    "count": "$steps.count_ocupacion.count",
    "min_threshold": 5,
    "max_threshold": 20,
    "hysteresis": 2,
    "cooldown_seconds": 60.0,
    "alarm_message_template": "🚨 OCUPACIÓN ANORMAL: {count} personas (rango normal: {min_threshold}-{max_threshold})"
  }

  Lógica:
  # State transitions
  IDLE → FIRING: (count < min_threshold OR count > max_threshold) AND cooldown elapsed
  FIRING → COOLDOWN: Alarm emitted
  COOLDOWN → IDLE: count IN [min_threshold + hysteresis, max_threshold - hysteresis]

  Casos de Negocio:
  - Healthcare: Sala debe tener entre 5-20 personas (ni vacía ni sobrecargada)
  - Manufacturing: Temperatura debe estar entre 18-22°C
  - Retail: Carritos en zona debe ser 10-50 (ni escasez ni saturación)
  - Data Center: Servidores activos entre 80-95% (ni subutilizado ni sobrecarga)

  Caso 3: Propiedades Complejas - Usar Blocks Existentes + Composition

  Use Case: Alertar cuando time_in_zone > duration o angle > threshold

  No necesitas nuevo block, usa composición:

  {
    "steps": [
      {
        "type": "roboflow_core/time_in_zone@v2",
        "name": "zona_permanencia",
        "zone": "$inputs.zone",
        "detections": "$steps.tracker.tracked_detections",
        "image": "$inputs.image"
      },
      {
        "type": "roboflow_core/detections_filter@v1",
        "name": "filtrar_permanencia_larga",
        "detections": "$steps.zona_permanencia.timed_detections",
        "filter_operation": {
          "type": "DetectionPropertyBasedFilter",
          "property_name": "time_in_zone",
          "operator": ">=",
          "reference_value": 300.0
        }
      },
      {
        "type": "care/detections_count@v1",
        "name": "count_permanencia_larga",
        "predictions": "$steps.filtrar_permanencia_larga.detections"
      },
      {
        "type": "care/prediction_alarm@v1",
        "name": "alerta_permanencia",
        "count": "$steps.count_permanencia_larga.count",
        "threshold": 1,
        "alarm_message_template": "⏱ PERMANENCIA PROLONGADA: {count} persona(s) >5 min en zona"
      }
    ]
  }

  Pattern: Property Extract → Filter → Count → Alarm

  ---
  🎯 Plan de Acción

  Fase 1: Implementar minimum_threshold_alarm@v1 (NOW)

  Justificación:
  - Caso de uso claro y común (inventario, robo, material bajo)
  - Reutiliza lógica de prediction_alarm (misma estructura, lógica invertida)
  - Complementa perfecto el block existente

  Fase 2: Implementar range_alarm@v1 (NEXT)

  Justificación:
  - Casos de uso específicos (temperatura, ocupación normal, etc.)
  - No se puede lograr fácilmente con composición de blocks existentes

  Fase 3: Evaluar property_alarm@v1 (FUTURE)

  Solo si aparecen múltiples casos que no se pueden resolver con composición.

  ---
  📝 Ejemplo Concreto: Retail Anti-Robo

  Problema: Detectar cuando productos desaparecen de estante

  Sin minimum_threshold_alarm:

  {
    "steps": [
      {"type": "ObjectDetectionModel", "name": "det", "class_filter": ["product"]},
      {"type": "care/detections_count@v1", "name": "count", "predictions": "$steps.det.predictions"},

      // ❌ Tengo que usar Expression block + manual logic
      {"type": "roboflow_core/expression@v1",
       "name": "check_low",
       "expression": "$steps.count.count < 10"},

      {"type": "roboflow_core/continue_if@v1", ...}  // más boilerplate
    ]
  }

  Con minimum_threshold_alarm:

  {
    "steps": [
      {"type": "ObjectDetectionModel", "name": "det", "class_filter": ["product"]},
      {"type": "care/detections_count@v1", "name": "count", "predictions": "$steps.det.predictions"},

      // ✅ Clean, composable, tiene state machine
      {"type": "care/minimum_threshold_alarm@v1",
       "name": "alerta_robo",
       "count": "$steps.count.count",
       "min_threshold": 10,
       "cooldown_seconds": 60.0,
       "alarm_message_template": "🚨 POSIBLE ROBO: Solo {count}/10 productos en estante"},

      {"type": "care/mqtt_writer@v1", "message": "$steps.alerta_robo.alarm_message"}
    ]
  }

  ---
  🎸 Pregunta para vos: ¿Qué implementamos?

  Opción A: Implementar minimum_threshold_alarm@v1 ahora (caso inventario bajo / robo)

  Opción B: Implementar range_alarm@v1 ahora (caso ocupación debe estar en rango)

  Opción C: Ambos (tendríamos una "familia" de alarm blocks completa)

  Opción D: Extender prediction_alarm@v1 con parámetro mode (no recomendado pero factible)

  ¿Cuál te parece más útil para tus casos de uso?



● ¡EXCELENTE! Tenés razón, "Complejidad por Diseño" en acción. Vamos a armar el motor de alarmas genérico y los blocks específicos son solo wrappers convenientes.

  🎸 Design: conditional_alarm@v1 + Alarm Engine

  🎯 Arquitectura: Engine + Wrappers

  ┌─────────────────────────────────────────┐
  │     AlarmEngine (core logic)            │
  │  - State machine                        │
  │  - Hysteresis per-condition             │
  │  - Cooldown management                  │
  │  - Condition evaluation with UQL        │
  └─────────────────────────────────────────┘
                ▲
                │ uses (composition)
                │
      ┌─────────┴──────────┬──────────────┬──────────────┐
      │                    │              │              │
  ┌───▼───────┐  ┌────────▼──────┐  ┌────▼─────┐  ┌────▼──────────┐
  │prediction │  │minimum        │  │range     │  │conditional    │
  │_alarm     │  │_threshold     │  │_alarm    │  │_alarm         │
  │           │  │_alarm         │  │          │  │               │
  │(wrapper)  │  │(wrapper)      │  │(wrapper) │  │(full UQL)     │
  └───────────┘  └───────────────┘  └──────────┘  └───────────────┘

  ---
  📦 Estructura de Archivos

  care_workflow/care_blocks/
  ├── core/
  │   ├── __init__.py
  │   └── alarm_engine.py          # 🔥 Motor genérico
  ├── transformations/
  │   ├── conditional_alarm/
  │   │   ├── __init__.py
  │   │   └── v1.py                # 🔥 Block con UQL completo
  │   ├── prediction_alarm/
  │   │   ├── __init__.py
  │   │   └── v1.py                # Wrapper del engine
  │   ├── minimum_threshold_alarm/
  │   │   ├── __init__.py
  │   │   └── v1.py                # Wrapper del engine
  │   └── range_alarm/
  │       ├── __init__.py
  │       └── v1.py                # Wrapper del engine

  ---
  🔧 1. Alarm Engine (Core Logic)




  ---



    # Conditional Alarm Block (`care/conditional_alarm@v1`)

     ## Overview

     El **Conditional Alarm** block es el miembro más flexible de la familia de alarm blocks. Usa **UQL (Universal Query Language)** para definir condiciones arbitrarias con state machine y hysteresis.

     ## Type

     `transformation` - Produce outputs booleanos y mensajes basados en condiciones UQL

     ## Arquitectura

     Este block usa el **AlarmEngine** core, que también será usado por los wrappers específicos (`prediction_alarm`, `minimum_threshold_alarm`, `range_alarm`).

     ```
     ┌─────────────────────────────────────────┐
     │     AlarmEngine (core logic)            │
     │  - State machine (IDLE/FIRING/COOLDOWN) │
     │  - Hysteresis management                │
     │  - Cooldown tracking                    │
     │  - Condition evaluation                 │
     └─────────────────────────────────────────┘
                   ▲
                   │ uses
                   │
         ┌─────────┴──────────┐
         │                    │
     ┌───▼──────────┐  ┌─────▼────────┐
     │conditional   │  │prediction    │
     │_alarm        │  │_alarm        │
     │(full UQL)    │  │(wrapper)     │
     └──────────────┘  └──────────────┘
     ```

     ## Key Features

     - **UQL Statements**: Define condiciones arbitrarias usando el mismo sistema que `continue_if`
     - **State Machine**: IDLE → FIRING → COOLDOWN (evita spam)
     - **Hysteresis Global**: Aplica banda muerta a todas las condiciones
     - **Cooldown**: Tiempo mínimo entre re-activaciones
     - **Message Templating**: Mensajes dinámicos con placeholders
     - **Combine Operators**: AND/OR para múltiples condiciones
     - **Observable State**: Output del estado para debugging

     ## Use Cases

     ### 1. Multi-Condition Alarms

     **Healthcare**: Ratio médicos/pacientes crítico

     ```json
     {
       "type": "care/conditional_alarm@v1",
       "condition_statement": {
         "type": "StatementGroup",
         "statements": [
           {
             "type": "BinaryStatement",
             "left_operand": {"type": "DynamicOperand", "operand_name": "doctors"},
             "comparator": {"type": "(Number) >="},
             "right_operand": {"type": "StaticOperand", "value": 2}
           },
           {
             "type": "BinaryStatement",
             "left_operand": {"type": "DynamicOperand", "operand_name": "patients"},
             "comparator": {"type": "(Number) >="},
             "right_operand": {"type": "StaticOperand", "value": 8}
           }
         ]
       },
       "evaluation_parameters": {
         "doctors": "$steps.count_doctors.count",
         "patients": "$steps.count_patients.count"
       },
       "hysteresis_default": 1.0,
       "cooldown_seconds": 30.0,
       "alarm_message_template": "🚨 RATIO CRÍTICO: {doctors} médicos para {patients} pacientes",
       "combine_operator": "AND"
     }
     ```

     **Lógica**:
     - **Activa**: `doctors >= 2 AND patients >= 8`
     - **Desactiva** (con hysteresis=1): `doctors < 1 OR patients < 7`

     ### 2. Complex OR Conditions

     **Manufacturing**: Alarma si defectos altos O temperatura fuera de rango

     ```json
     {
       "type": "care/conditional_alarm@v1",
       "condition_statement": {
         "type": "StatementGroup",
         "statements": [
           {
             "type": "BinaryStatement",
             "left_operand": {"type": "DynamicOperand", "operand_name": "defects"},
             "comparator": {"type": "(Number) >"},
             "right_operand": {"type": "StaticOperand", "value": 5}
           },
           {
             "type": "BinaryStatement",
             "left_operand": {"type": "DynamicOperand", "operand_name": "temp"},
             "comparator": {"type": "(Number) >"},
             "right_operand": {"type": "StaticOperand", "value": 25}
           }
         ]
       },
       "evaluation_parameters": {
         "defects": "$steps.count_defects.count",
         "temp": "$steps.temp_sensor.value"
       },
       "combine_operator": "OR",
       "alarm_message_template": "⚠ Defectos: {defects}, Temp: {temp}°C"
     }
     ```

     ### 3. Custom Business Logic

     **Retail**: Alarma si ratio cajeros/clientes es inadecuado

     ```json
     {
       "type": "care/conditional_alarm@v1",
       "condition_statement": {
         "type": "StatementGroup",
         "statements": [
           {
             "type": "BinaryStatement",
             "left_operand": {"type": "DynamicOperand", "operand_name": "queue"},
             "comparator": {"type": "(Number) >"},
             "right_operand": {"type": "StaticOperand", "value": 20}
           },
           {
             "type": "BinaryStatement",
             "left_operand": {"type": "DynamicOperand", "operand_name": "cashiers"},
             "comparator": {"type": "(Number) <"},
             "right_operand": {"type": "StaticOperand", "value": 3}
           }
         ]
       },
       "evaluation_parameters": {
         "queue": "$steps.count_queue.count",
         "cashiers": "$steps.count_cashiers.count"
       },
       "combine_operator": "AND",
       "alarm_message_template": "🛒 Cola larga ({queue}) con pocos cajeros ({cashiers})"
     }
     ```

     ## Inputs

     | Name | Type | Description | Default |
     |------|------|-------------|---------|
     | `condition_statement` | `StatementGroup` | UQL statement group (igual que `continue_if`) | Required |
     | `evaluation_parameters` | `Dict[str, Selector]` | Parámetros para evaluar en las condiciones | Required |
     | `hysteresis_default` | `float` | Hysteresis global aplicado a todas las condiciones | `1.0` |
     | `cooldown_seconds` | `float` | Segundos mínimos entre alarmas | `5.0` |
     | `alarm_message_template` | `str` | Template con placeholders `{param_name}` | `"Alarm triggered"` |
     | `combine_operator` | `"AND"` \| `"OR"` | Cómo combinar múltiples statements | `"AND"` |

     ## Outputs

     | Name | Type | Description |
     |------|------|-------------|
     | `alarm_active` | `bool` | `True` cuando alarma está firing |
     | `alarm_message` | `str` | Mensaje formateado (vacío si alarm inactivo) |
     | `state` | `str` | Estado actual: `"idle"`, `"firing"`, `"cooldown"` |
     | `alarm_count` | `int` | Número de veces que alarma se ha disparado |

     ## State Machine

     ```
             Conditions no longer met
        ┌──────────────────────────────────┐
        │                                  │
        ▼                                  │
     ┌──────┐  Conditions met          ┌────────┐
     │ IDLE │  AND cooldown elapsed    │ FIRING │
     └──────┘ ──────────────────────> └────────┘
                                           │
                                           │ Alarm emitted
                                           ▼
                                      ┌──────────┐
                                      │ COOLDOWN │
                                      └──────────┘
     ```

     ### Hysteresis Application

     El `hysteresis_default` se aplica **globalmente** a todas las condiciones:

     **Para comparadores ">"** (mayor que):
     - Activa: `value > threshold`
     - Desactiva: `value < (threshold - hysteresis)`

     **Para comparadores "<"** (menor que):
     - Activa: `value < threshold`
     - Desactiva: `value > (threshold + hysteresis)`

     **Ejemplo**:
     ```json
     {
       "condition_statement": {
         "statements": [
           {
             "left_operand": {"operand_name": "count"},
             "comparator": {"type": "(Number) >"},
             "right_operand": {"value": 10}
           }
         ]
       },
       "hysteresis_default": 2.0
     }
     ```

     **Comportamiento**:
     - Activa cuando `count >= 10`
     - Desactiva cuando `count < 8` (10 - 2)

     ## Workflow Completo

     Ver: [`data/workflows/examples/conditional_alarm_doctors_patients.json`](../../data/workflows/examples/conditional_alarm_doctors_patients.json)

     **Setup**:
     ```bash
     export WORKFLOWS_PLUGINS="care.workflows.care_steps"
     export WORKFLOW_DEFINITION="data/workflows/examples/conditional_alarm_doctors_patients.json"
     export VIDEO_REFERENCE="rtsp://localhost:8554/hospital_ward"
     export MQTT_HOST="localhost"
     export MQTT_PORT="1883"

     uv run python examples/run_mqtt_detection.py
     ```

     ## Comparison con Otros Blocks

     | Feature | `conditional_alarm` | `prediction_alarm` | `continue_if` + `rate_limiter` |
     |---------|--------------------|--------------------|-------------------------------|
     | **UQL Flexibility** | ✅ Full UQL | ❌ Fixed threshold | ✅ Full UQL |
     | **State Machine** | ✅ Built-in | ✅ Built-in | ❌ Manual |
     | **Hysteresis** | ✅ Global | ✅ Per-condition | ❌ None |
     | **Cooldown** | ✅ Built-in | ✅ Built-in | ✅ Via rate_limiter |
     | **Message Template** | ✅ Built-in | ✅ Built-in | ❌ Manual |
     | **Ease of Use** | ⚠ Medium (UQL) | ✅ Easy | ⚠ Verbose (3 blocks) |

     ## When to Use

     ### ✅ Use `conditional_alarm` When:

     1. **Multiple conditions** that can't be expressed with simple threshold
     2. **AND/OR logic** between different metrics
     3. **Custom business rules** (ej: ratio médicos/pacientes)
     4. **Complex comparisons** que requieren UQL

     ### ❌ Don't Use (use simpler blocks instead):

     1. **Single threshold**: Usa `prediction_alarm` o `minimum_threshold_alarm`
     2. **Range check**: Usa `range_alarm`
     3. **No hysteresis needed**: Usa `continue_if` + `rate_limiter`

     ## Troubleshooting

     ### Alarm fires too often (flapping)

     Incrementa `hysteresis_default`:
     ```json
     {"hysteresis_default": 3.0}
     ```

     ### Alarm doesn't fire

     - Verifica que `condition_statement` es correcto
     - Chequea que `evaluation_parameters` tiene los nombres correctos
     - Inspecciona output `state` (debería ser "idle" o "firing")
     - Verifica que cooldown no está activo (`state` = "cooldown")

     ### Message template doesn't interpolate

     Asegúrate que placeholders coinciden con `evaluation_parameters`:
     ```json
     {
       "evaluation_parameters": {"count": "..."},
       "alarm_message_template": "Value: {count}"  // ✅ Correct
     }
     ```

     ## Performance

     - **State overhead**: O(1) - un engine por block instance
     - **CPU**: Leve overhead por UQL evaluation (similar a `continue_if`)
     - **Memory**: O(1) - state mínimo (last_alarm_at, alarm_count)

     ## Related Blocks

     - `prediction_alarm@v1` - Threshold superior simple
     - `minimum_threshold_alarm@v1` - Threshold inferior simple *(TODO)*
     - `range_alarm@v1` - Doble threshold *(TODO)*
     - `roboflow_core/continue_if@v1` - Flow control sin state machine
     - `roboflow_core/rate_limiter@v1` - Throttling simple

     ## Version History

     - **v1** (2025-10-28): Initial release con AlarmEngine y UQL support

     ---

     ## 🎸 Design Philosophy

     **"Complejidad por Diseño"**:
     - Engine centralizado (DRY)
     - UQL reutiliza infraestructura de Roboflow
     - State machine explícito

     **"Pragmatismo > Purismo"**:
     - Hysteresis global (simple) vs per-statement (complejo)
     - Solo implementado cuando hay demanda real de casos multi-condición
     - Wrappers simples para casos comunes (80% de uso)

     **"Patterns con Propósito"**:
     - Si tu caso se puede resolver con `prediction_alarm`, úsalo (más simple)
     - Si necesitas lógica compleja, aquí está la herramienta
     - No over-engineer con UQL si threshold simple funciona


● Perfecto! Ahora creemos un resumen final de lo implementado:

● 🎸 ¡AlarmEngine + conditional_alarm Implementado!

  ✅ Lo que Construimos

  ---
  🔧 1. AlarmEngine - Motor Core Reutilizable

  Ubicación: care_workflow/care_blocks/core/alarm_engine.py

  Características:
  - ✅ State machine genérico (IDLE → FIRING → COOLDOWN)
  - ✅ ConditionWithHysteresis - Clase para condiciones con banda muerta
  - ✅ Cooldown management
  - ✅ Message templating
  - ✅ Composable (no herencia, composition)

  Factory Functions:
  create_threshold_condition(param_name, threshold, hysteresis, direction="above")
  create_range_condition(param_name, min_threshold, max_threshold, hysteresis)

  API:
  engine = AlarmEngine()
  engine.register_condition("main", condition)
  result = engine.evaluate(params, combine_with="AND", cooldown_seconds=5.0)
  # result = {alarm_active, alarm_message, state, alarm_count, condition_states}

  ---
  🎯 2. conditional_alarm@v1 - Block con UQL

  Ubicación: care_workflow/care_blocks/transformations/conditional_alarm/v1.py

  Características:
  - ✅ UQL StatementGroup (igual que continue_if)
  - ✅ Hysteresis global (fallback para todas las condiciones)
  - ✅ AND/OR para combinar statements
  - ✅ Message templating con placeholders dinámicos
  - ✅ Observable state para debugging

  Manifest:
  {
    "type": "care/conditional_alarm@v1",
    "condition_statement": StatementGroup,  // UQL
    "evaluation_parameters": Dict,           // Parámetros
    "hysteresis_default": 1.0,              // Global
    "cooldown_seconds": 5.0,
    "alarm_message_template": str,
    "combine_operator": "AND" | "OR"
  }

  ---
  📝 3. Workflow Ejemplo: Ratio Médicos/Pacientes

  Archivo: data/workflows/examples/conditional_alarm_doctors_patients.json

  Caso de Uso: Detectar cuando 2+ médicos atienden 8+ pacientes (ratio crítico 1:4)

  Pipeline:
  Video → Detector → Tracker → Zona Doctors + Zona Patients
                                ↓              ↓
                            Count Doctors  Count Patients
                                ↓              ↓
                          conditional_alarm (AND)
                                ↓
                          Continue If (si activo)
                                ↓
                            MQTT Writer

  Lógica de Alarma:
  - Activa: doctors >= 2 AND patients >= 8
  - Desactiva: doctors < 1 OR patients < 7 (con hysteresis=1)
  - Cooldown: 30 segundos

  Uso:
  export WORKFLOWS_PLUGINS="care.workflows.care_steps"
  export WORKFLOW_DEFINITION="data/workflows/examples/conditional_alarm_doctors_patients.json"
  export VIDEO_REFERENCE="rtsp://localhost:8554/hospital_ward"

  uv run python examples/run_mqtt_detection.py

  ---
  📚 4. Documentación Completa

  Archivo: docs/blocks/conditional_alarm.md

  Contenido:
  - ✅ Overview y arquitectura
  - ✅ 3 casos de uso detallados (Healthcare, Manufacturing, Retail)
  - ✅ Comparación con otros blocks
  - ✅ When to use / when NOT to use
  - ✅ Troubleshooting
  - ✅ Design philosophy

  ---
  🎯 Arquitectura Final: Engine + Wrappers

  ┌──────────────────────────────────────────────┐
  │         AlarmEngine (core)                   │
  │  - State machine                             │
  │  - Hysteresis per-condition                  │
  │  - Cooldown management                       │
  │  - Condition evaluation                      │
  │  - Message templating                        │
  └──────────────────────────────────────────────┘
                ▲
                │ uses (composition)
                │
      ┌─────────┴──────────┬──────────┬──────────┐
      │                    │          │          │
  ┌───▼──────────┐  ┌─────▼────┐ ┌──▼────┐ ┌───▼────┐
  │conditional   │  │prediction│ │minimum│ │range   │
  │_alarm        │  │_alarm    │ │_alarm │ │_alarm  │
  │              │  │          │ │       │ │        │
  │(UQL full)    │  │(wrapper) │ │(TODO) │ │(TODO)  │
  └──────────────┘  └──────────┘ └───────┘ └────────┘

  Ventaja: Código del engine centralizado, blocks son configuraciones

  ---
  🔍 Verificación

  $ uv run python -c "from care.workflows.care_steps import load_blocks; print(len(load_blocks()))"
  4  # ✅ MQTTWriter, DetectionsCount, PredictionAlarm, ConditionalAlarm

  ---
  📊 Próximos Pasos (Opcionales)

  Opción A: Refactorizar prediction_alarm para usar Engine

  Ventaja: DRY, mismo engine
  Esfuerzo: ~30 min

  Opción B: Implementar Wrappers (minimum_threshold_alarm, range_alarm)

  Ventaja: Completa la familia, casos específicos más simples
  Esfuerzo: ~1 hora cada uno

  Opción C: Casos de uso adicionales de conditional_alarm

  Ejemplos:
  - Retail: queue > 20 AND cashiers < 3
  - Manufacturing: defects > 5 OR temp > 25
  - Security: zone_a > 0 AND zone_b > 0 (personas en 2 zonas simultáneas)

  ---
  🎸 Filosofía Aplicada

  "Complejidad por Diseño" ✅:
  - Motor centralizado (AlarmEngine)
  - State machine explícito
  - Composition over inheritance

  "Pragmatismo > Purismo" ✅:
  - Hysteresis global (simple) en vez de per-statement (complejo)
  - UQL reutiliza infraestructura de Roboflow
  - Implementado conditional_alarm PRIMERO (el más complejo, el que justifica el engine)

  "Patterns con Propósito" ✅:
  - Engine reutilizable
  - Wrappers futuros serán triviales (5-10 líneas)
  - Caso real documentado (médicos/pacientes)

  ---
  ¿Querés que:
  1. Refactoricemos prediction_alarm para usar el engine?
  2. Implementemos los wrappers (minimum_threshold_alarm, range_alarm)?
  3. Creemos más ejemplos de conditional_alarm?
  4. Paremos aquí y dejemos los wrappers como TODO futuro?

