# ● 🎸 Consultoría: Roboflow Inference Workflows - Design Whiteboard

##  Contexto de la Sesión

  **Cliente**: Visiona (Ernesto)
  **Proyecto**: Care Workflow - Sistema de alertas inteligentes
  **Pregunta Central**: ¿Necesitamos minimum_threshold_alarm o podemos usar blocks existentes de Roboflow?

  ---
##  📋 Inventario de Building Blocks en Roboflow Inference

### 1. **Flow Control Blocks**

* `roboflow_core/continue_if@v1`

    **Propósito**: Ejecución condicional de ramas

    ```json
    {
    "type": "roboflow_core/continue_if@v1",
    "condition_statement": {
        "type": "StatementGroup",
        "statements": [
        {
            "type": "BinaryStatement",
            "left_operand": {"type": "DynamicOperand", "operand_name": "count"},
            "comparator": {"type": "(Number) <"},
            "right_operand": {"type": "StaticOperand", "value": 10}
        }
        ]
    },
    "evaluation_parameters": {"count": "$steps.count.count"},
    "next_steps": ["$steps.alarm"]
    }
    ```

    **✅ Puede resolver**: Threshold inferior con lógica condicional

    **❌ NO tiene**: State machine, cooldown, hysteresis

---

* `roboflow_core/rate_limiter@v1`

    **Propósito**: Throttling temporal de ejecución

    ```json
    {
    "type": "roboflow_core/rate_limiter@v1",
    "cooldown_seconds": 5.0,
    "depends_on": "$steps.detector",
    "next_steps": ["$steps.notification"]
    }
    ```

    **✅ Tiene**: Cooldown period

    **❌ NO tiene**: Threshold logic, state machine

---


* `roboflow_core/delta_filter@v1`

    **Propósito**: Ejecutar solo cuando valor cambia significativamente

    ```json
    {
    "type": "roboflow_core/delta_filter@v1",
    "reference_value": "$steps.count.count",
    "threshold": 5,
    "next_steps": ["$steps.notification"]
    }
    ```

    **✅ Tiene**: Change detection con threshold

    **❌ NO tiene**: State machine, alarma activa/inactiva


---
### 2. Data Transformation Blocks

* `roboflow_core/property_definition@v1`

  **Propósito**: Aplicar operaciones/transformaciones a datos

  ```json
  {
      "type": "roboflow_core/property_definition@v1",
      "name": "check_low_inventory",
      "operations": [
      {
          "type": "LessThan",
          "left": "$steps.count.count",
          "right": 10
      }
      ],
      "data": "$steps.count.count"
  }
  ```

  **Output**: Valor transformado (ej: true/false para comparación)

  ✅ Puede resolver: Comparaciones, cálculos
  ❌ NO tiene: State machine, cooldown, mensaje de alarma

  ---

* `roboflow_core/expression@v1`

  **Propósito**: Evaluar expresiones arbitrarias

  ```json
  {
    "type": "roboflow_core/expression@v1",
    "name": "complex_condition",
    "expression": "($steps.count.count < 10) AND ($steps.count.count > 0)"
  }
  ```

  ✅ Puede resolver: Lógica compleja, rangos
  ❌ NO tiene: State machine, cooldown

---
### 3. Cache/Buffer Blocks

* `roboflow_core/data_aggregator@v1`

    **Propósito**: Agregar datos en ventanas temporales

    ```json
    {
        "type": "roboflow_core/data_aggregator@v1",
        "data": {"count": "$steps.count.count"},
        "aggregation_mode": {"count": ["avg", "min", "max"]},
        "interval": 60,
        "interval_unit": "seconds"
    }
    ```

    **Outputs**:
    - count_avg: Promedio en ventana
    - count_min: Mínimo en ventana
    - count_max: Máximo en ventana

    ✅ Tiene: Ventana temporal, múltiples agregaciones
    ❌ NO tiene: Alarma instantánea (solo reporta cada N segundos)

---

### 4. Formatters

* `roboflow_core/csv_formatter@v1`

Serializa datos a CSV

* `roboflow_core/json_formatter@v1`

Serializa datos a JSON

Propósito: Solo formateo de output, no lógica de negocio

---
## 🔍 Análisis: ¿Podemos Implementar Nuestros Casos de Uso con Blocks Existentes?

### Caso 1: Threshold Superior (count >= threshold)

Con prediction_alarm@v1 (nuestro block) ✅

```json
{
"type": "care/prediction_alarm@v1",
"count": "$steps.count.count",
"threshold": 10,
"hysteresis": 2,
"cooldown_seconds": 60.0
}
```

✅ Completo: State machine + cooldown + hysteresis + mensaje

Con blocks Roboflow

```json
    {
    "steps": [
        {
        "type": "roboflow_core/continue_if@v1",
        "condition_statement": {...},  // count >= 10
        "next_steps": ["$steps.rate_limiter"]
        },
        {
        "type": "roboflow_core/rate_limiter@v1",
        "cooldown_seconds": 60.0,
        "next_steps": ["$steps.mqtt"]
        },
        {
        "type": "care/mqtt_writer@v1",
        "message": "Count: {count}"  // ❌ No hay string interpolation
        }
    ]
    }
```

❌ Problemas:
- Sin hysteresis (oscilará entre 9-11)
- Sin state machine (no sabes si estás en cooldown)
- Sin message templating
- Más verbose (3 blocks vs 1)

---
### Caso 2: Threshold Inferior (count < threshold)

Con minimum_threshold_alarm@v1 (hipotético) ✅

```json
{
"type": "care/minimum_threshold_alarm@v1",
"count": "$steps.count.count",
"min_threshold": 10,
"hysteresis": 2,
"cooldown_seconds": 60.0,
"alarm_message_template": "Inventario bajo: {count}"
}
```

Con blocks Roboflow

```json
{
    "steps": [
        {
        "type": "roboflow_core/property_definition@v1",
        "name": "is_low",
        "operations": [{"type": "LessThan", "left": "$steps.count.count", "right": 10}],
        "data": "$steps.count.count"
        },
        {
        "type": "roboflow_core/continue_if@v1",
        "condition_statement": {...},  // is_low == true
        "next_steps": ["$steps.rate_limiter"]
        },
        {
        "type": "roboflow_core/rate_limiter@v1",
        "cooldown_seconds": 60.0,
        "next_steps": ["$steps.mqtt"]
        }
    ]
}
```

❌ Mismos problemas: Sin hysteresis, sin state machine, verbose


---
### Caso 3: Rango (count NOT IN [min, max])

Con range_alarm@v1 (hipotético) ✅

```json
{
"type": "care/range_alarm@v1",
"count": "$steps.count.count",
"min_threshold": 5,
"max_threshold": 20,
"hysteresis": 2,
"cooldown_seconds": 60.0
}
```

Con blocks Roboflow

```json
{
    "steps": [
        {
        "type": "roboflow_core/expression@v1",
        "name": "out_of_range",
        "expression": "($steps.count.count < 5) OR ($steps.count.count > 20)"
        },
        {
        "type": "roboflow_core/continue_if@v1",
        "condition_statement": {...},  // out_of_range == true
        "next_steps": ["$steps.rate_limiter"]
        },
        {
        "type": "roboflow_core/rate_limiter@v1",
        "cooldown_seconds": 60.0,
        "next_steps": ["$steps.mqtt"]
        }
    ]
}
```

❌ Problemas: Sin hysteresis (oscilará en boundaries), verbose

---
### Caso 4: Propiedades Complejas (ej: time_in_zone > duration)

Con composición de blocks existentes ✅

```json
{
    "steps": [
        {
        "type": "roboflow_core/time_in_zone@v2",
        "name": "zona",
        "zone": "$inputs.zone",
        "detections": "$steps.tracker.tracked_detections"
        },
        {
        "type": "roboflow_core/detections_filter@v1",
        "name": "filtrar_permanencia",
        "filter_operation": {
            "type": "DetectionPropertyBasedFilter",
            "property_name": "time_in_zone",
            "operator": ">=",
            "reference_value": 300.0
        }
        },
        {
        "type": "care/detections_count@v1",
        "name": "count_larga_permanencia"
        },
        {
        "type": "care/prediction_alarm@v1",
        "count": "$steps.count_larga_permanencia.count",
        "threshold": 1
        }
    ]
}

✅ Funciona bien: Composición clara, cada block hace una cosa



---
## 💡 Insight Clave: property_definition vs Custom Blocks

¿Puede property_definition reemplazar detections_count?

Hipótesis de Ernesto: "¿property_definition puede hacer el count?"

```json
{
"type": "roboflow_core/property_definition@v1",
"name": "count_manual",
"operations": [{"type": "SequenceLength"}],
"data": "$steps.detector.predictions"
}
```


Respuesta: SÍ, técnicamente puede

PERO hay una diferencia conceptual importante:

property_definition@v1

- Propósito: Transformación genérica de datos
- Salida: Valor crudo (ej: 5)
- Semántica: "Aplica operación X a dato Y"
- Usuario debe saber: UQL operations disponibles

care/detections_count@v1

- Propósito: Contar detecciones (específico)
- Salida: {"count": 5} (nombrado semánticamente)
- Semántica: "Cuenta cuántas detecciones hay"
- Usuario debe saber: Solo pasar predictions

Analogía con Software Design

# Opción A: Generic (property_definition)
`result = apply_operation(data, operation="length")`

# Opción B: Specific (detections_count)
`count = count_detections(predictions)`

¿Cuál es mejor?

Depende del nivel de abstracción que querés exponer:

- Low-level API (Roboflow): property_definition te da flexibilidad total
- High-level API (Care Workflow): detections_count te da claridad de intención

---
🎯 Matriz de Decisión: ¿Custom Block o Composición?

| Criterio              | Custom Block                  | Composición Roboflow               |
|-----------------------|-------------------------------|------------------------------------|
| State Machine         | ✅ Sí                          | ❌ No (manual con variables)        |
| Hysteresis            | ✅ Built-in                    | ❌ Manual (complejo)                |
| Cooldown              | ✅ Built-in                    | ⚠ Usar rate_limiter (adicional)   |
| Message Templating    | ✅ Built-in                    | ❌ Manual (string concat)           |
| Observable State      | ✅ Output state                | ❌ No (hidden en blocks)            |
| Verbosity             | ✅ 1 block                     | ❌ 3-4 blocks                       |
| Claridad de Intención | ✅ Nombre descriptivo          | ⚠ Requiere leer workflow completo |
| Reusabilidad          | ✅ Alta (parametrizable)       | ⚠ Copy-paste de pattern           |
| Learning Curve        | ✅ Baja (parámetros claros)    | ❌ Alta (UQL, flow control)         |
| Flexibilidad          | ⚠ Limitado a casos diseñados | ✅ Infinita (composición)           |

---
📊 Casos de Uso: ¿Cuándo Usar Qué?

Usar Custom Block Cuando:

1. Patrón repetitivo común
- ✅ Threshold alarm con cooldown (nuestro caso)
- ✅ Inventario bajo con hysteresis
- ✅ Rango de ocupación normal
2. Necesitas state machine
- ✅ IDLE → FIRING → COOLDOWN
- ✅ Estado observable para debugging
- ✅ Hysteresis para evitar flapping
3. User experience importante
- ✅ Workflows más legibles
- ✅ Menos curva de aprendizaje
- ✅ Errores más claros
4. Domain-specific logic
- ✅ "Prediction Alarm" tiene semántica clara en analytics
- ✅ "Minimum Threshold Alarm" es claro para inventario

Usar Composición Cuando:

1. Caso único/específico
- ✅ "Alarma si count > 10 Y temperatura > 25"
- ✅ Lógica específica de un cliente
2. Propiedades complejas de detections
- ✅ Filter por time_in_zone, class_name, confidence
- ✅ Ya hay blocks especializados (detections_filter)
3. Prototipado rápido
- ✅ Testear lógica antes de crear block custom
- ✅ Explorar si vale la pena abstraer
4. Flexibilidad > Simplicidad
- ✅ Power users que dominan UQL
- ✅ Casos que cambian frecuentemente

---
🎸 Recomendación Final: "Family of Alarm Blocks"

Implementar 3 Blocks Complementarios

care/prediction_alarm@v1          → count >= threshold  ✅ DONE
care/minimum_threshold_alarm@v1   → count < threshold   📋 NEXT
care/range_alarm@v1               → count NOT IN [min, max]  📋 FUTURE

Justificación

1. Cohesión Conceptual
- Los 3 resuelven el mismo problema: "Alertar cuando métrica está fuera de rango esperado"
- Comparten infraestructura: state machine, cooldown, hysteresis, message templating

2. User Experience
// ✅ Clear intent
{"type": "care/prediction_alarm@v1", "threshold": 10}

// vs

// ❌ Requires UQL knowledge
{"type": "roboflow_core/continue_if@v1",
"condition_statement": {"type": "StatementGroup", ...}}

3. Reusabilidad
- Healthcare: range_alarm para ocupación normal (5-20)
- Retail: minimum_threshold_alarm para inventario
- Manufacturing: prediction_alarm para defectos

4. Mantenibilidad
- Un lugar para fixear bugs (no distribuido en workflows)
- Tests unitarios en un lugar
- Documentación centralizada

---
🚀 Plan de Implementación

Fase 1: minimum_threshold_alarm@v1 (NOW)

Justificación: Caso simétrico a prediction_alarm, bajo esfuerzo

# State machine (invertido)
IDLE → FIRING: count < min_threshold AND cooldown elapsed
FIRING → COOLDOWN: Alarm emitted
COOLDOWN → IDLE: count >= (min_threshold + hysteresis)

Esfuerzo: ~1 hora (copy de prediction_alarm, invertir lógica)

Casos de uso inmediatos:
- Retail: Inventario bajo
- Security: Equipo faltante
- Manufacturing: Material prima bajo

Fase 2: range_alarm@v1 (NEXT WEEK)

Justificación: Más complejo (2 thresholds), pero casos claros

# State machine
IDLE → FIRING: (count < min OR count > max) AND cooldown elapsed
FIRING → COOLDOWN: Alarm emitted
COOLDOWN → IDLE: count IN [min + hyst, max - hyst]

Esfuerzo: ~2 horas (lógica más compleja)

Casos de uso:
- Healthcare: Ocupación debe estar entre 5-20
- Manufacturing: Temperatura entre 18-22°C
- Data Center: Carga CPU entre 40-80%

Fase 3: Documentar Patterns de Composición (PARALLEL)

Para casos que NO justifican custom block:

## Pattern: Time-based Alarm
time_in_zone → filter (>X) → count → prediction_alarm

## Pattern: Multi-condition Alarm
expression (A AND B) → continue_if → rate_limiter → sink

## Pattern: Aggregated Alarm
data_aggregator (avg) → expression (avg < threshold) → continue_if

---
📝 Casos de Negocio Adicionales

1. Retail: Inventario Bajo

Problema: Detectar cuando productos en estante bajan de nivel crítico

{
"type": "care/minimum_threshold_alarm@v1",
"name": "alerta_restock",
"count": "$steps.count_productos.count",
"min_threshold": 10,
"hysteresis": 3,
"cooldown_seconds": 1800.0,
"alarm_message_template": "📦 RESTOCK NECESARIO: {count}/{min_threshold} productos en estante {shelf_id}"
}

Integración: MQTT → Sistema de inventario → Orden automática a bodega

2. Security: Equipo Faltante

Problema: Detectar cuando equipo crítico desaparece de zona

{
"type": "care/minimum_threshold_alarm@v1",
"name": "alerta_equipo_faltante",
"count": "$steps.count_extintores.count",
"min_threshold": 4,
"hysteresis": 0,
"cooldown_seconds": 60.0,
"alarm_message_template": "🚨 ROBO/PÉRDIDA: Solo {count}/4 extintores en zona {zone_name}"
}

3. Manufacturing: Material Prima Bajo

Problema: Alertar cuando material en tolva baja de nivel

{
"type": "care/minimum_threshold_alarm@v1",
"name": "alerta_material_bajo",
"count": "$steps.count_sacos.count",
"min_threshold": 5,
"hysteresis": 2,
"cooldown_seconds": 300.0,
"alarm_message_template": "⚠ MATERIAL BAJO: {count} sacos restantes. Reabastecer tolva {hopper_id}"
}

4. Healthcare: Ocupación Anormal (Range)

Problema: Sala no debe estar ni vacía ni sobrecargada

{
"type": "care/range_alarm@v1",
"name": "alerta_ocupacion_anormal",
"count": "$steps.count_pacientes.count",
"min_threshold": 3,
"max_threshold": 15,
"hysteresis": 1,
"cooldown_seconds": 120.0,
"alarm_message_template": "⚠ OCUPACIÓN ANORMAL: {count} pacientes (rango esperado: 3-15)"
}

---
🎸 Conclusión: "Patterns con Propósito"

✅ Custom Blocks para Patterns Comunes

- prediction_alarm, minimum_threshold_alarm, range_alarm
- Razón: Claridad, reusabilidad, state machine

✅ Composición para Casos Específicos

- Time-based conditions, multi-property filters
- Razón: Flexibilidad, casos únicos

❌ NO Over-engineer

- No crear generic_conditional_alarm con UQL
- Razón: YAGNI, complejidad innecesaria

---
🤔 Preguntas para Ernesto

1. ¿Te hace sentido la "family of alarms"? (prediction, minimum, range)
2. ¿Qué caso te parece más urgente implementar?
- Inventario bajo (minimum_threshold)
- Ocupación en rango (range)
- Ambos
3. ¿Preferís que documentemos más patterns de composición antes de crear nuevos blocks?
4. ¿Te quedó claro cuándo usar custom block vs composición?
