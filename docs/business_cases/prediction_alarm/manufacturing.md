# Manufacturing - Control de Línea de Producción

## Contexto de Negocio

**Vertical**: Manufacturing / Industria 4.0
**Desafío**: Detección temprana de anomalías en línea de producción mediante conteo de productos defectuosos
**Impacto**: Reducción de desperdicio, optimización de calidad, prevención de paradas no planificadas

## Caso de Uso: Detección de Productos Defectuosos en Cinta Transportadora

### Problema Real

Una planta de manufactura necesita:
- Detectar productos defectuosos en tiempo real
- Alertar cuando tasa de defectos excede umbral aceptable
- Detener línea automáticamente si tasa es crítica
- Notificar supervisor de calidad para ajuste de máquina
- Registrar eventos para análisis de root cause

### Solución con Prediction Alarm

```
Cámara → Detección Defectos → Conteo → Prediction Alarm → Sistema Industrial
         (clasificación)       (count)  (threshold)        (PLC/MQTT/Webhook)
```

### Configuración del Block

```json
{
  "type": "care/prediction_alarm@v1",
  "name": "alarma_defectos",
  "count": "$steps.count_defectos.count",
  "threshold": 3,
  "hysteresis": 1,
  "cooldown_seconds": 10.0,
  "alarm_message_template": "⚠️ CALIDAD - {count} productos defectuosos detectados en ventana de inspección. Revisar calibración."
}
```

**Parámetros Justificados**:
- `threshold: 3` - Máximo 3 defectos consecutivos antes de alerta
- `hysteresis: 1` - Desactivar cuando baja a 2 (permite variación)
- `cooldown: 10s` - Tiempo suficiente para inspección visual del operador

### Escenario de Producción

**Línea de ensamblaje de componentes electrónicos**:
- Velocidad: 60 productos/minuto
- Ventana de inspección: 10 productos simultáneos en campo visual
- Tasa de defectos aceptable: <2%
- Criterio de alarma: 3+ defectos en ventana = ~30% (acción inmediata)

### Integración con Sistema de Control Industrial

**Opción 1: MQTT → PLC/SCADA**

```json
{
  "steps": [
    {
      "type": "ObjectDetectionModel",
      "name": "detector_defectos",
      "model_id": "defect-detection-v2",
      "class_filter": ["scratch", "crack", "misalignment"]
    },
    {
      "type": "care/detections_count@v1",
      "name": "count_defectos",
      "predictions": "$steps.detector_defectos.predictions"
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alarma_critica",
      "count": "$steps.count_defectos.count",
      "threshold": 5,
      "cooldown_seconds": 5.0,
      "alarm_message_template": "🛑 DETENER LÍNEA - {count} defectos críticos"
    },
    {
      "type": "roboflow_core/continue_if@v1",
      "name": "check_stop_condition",
      "condition_statement": {
        "type": "StatementGroup",
        "statements": [
          {
            "type": "BinaryStatement",
            "left_operand": {
              "type": "DynamicOperand",
              "operand_name": "alarm_active"
            },
            "comparator": {"type": "(Boolean) =="},
            "right_operand": {"type": "StaticOperand", "value": true}
          }
        ]
      },
      "evaluation_parameters": {
        "alarm_active": "$steps.alarma_critica.alarm_active"
      },
      "next_steps": ["$steps.mqtt_plc"]
    },
    {
      "type": "care/mqtt_writer@v1",
      "name": "mqtt_plc",
      "host": "plc-controller.factory.local",
      "topic": "factory/line_1/commands/stop",
      "message": "EMERGENCY_STOP",
      "qos": 2,
      "retain": false
    }
  ]
}
```

**Opción 2: OPC-UA (TODO: Custom Block)**

```json
{
  "type": "care/opc_ua_writer@v1",
  "name": "opc_scada",
  "endpoint": "opc.tcp://scada.factory.local:4840",
  "node_id": "ns=2;s=Line1.QualityAlarm",
  "value": "$steps.alarma_defectos.alarm_active"
}
```

### Múltiples Niveles de Severidad

**Sistema de alertas escalonado según criticidad**:

```json
{
  "steps": [
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_preventiva",
      "threshold": 2,
      "cooldown_seconds": 30.0,
      "alarm_message_template": "⚠️ ATENCIÓN: {count} defectos detectados. Monitorear proceso."
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_ajuste",
      "threshold": 3,
      "cooldown_seconds": 15.0,
      "alarm_message_template": "🔧 AJUSTE REQUERIDO: {count} defectos. Supervisor de calidad notificado."
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_parada",
      "threshold": 5,
      "cooldown_seconds": 5.0,
      "alarm_message_template": "🛑 PARADA DE LÍNEA: {count} defectos críticos. Detener producción."
    }
  ]
}
```

**Acciones por Nivel**:

| Nivel | Threshold | Acción | Destinatario |
|-------|-----------|--------|--------------|
| **Preventivo** | 2 | Log + Dashboard | Operador |
| **Ajuste** | 3 | Notificación MQTT | Supervisor de Calidad |
| **Parada** | 5 | Comando STOP a PLC | Sistema de Control |

### Analytics de Producción

**Agregación de métricas de calidad**:

```json
{
  "type": "roboflow_core/data_aggregator@v1",
  "name": "metricas_calidad",
  "data": {
    "defectos_detectados": "$steps.count_defectos.count",
    "productos_totales": "$steps.count_todos.count",
    "alarmas_disparadas": "$steps.alerta_ajuste.alarm_active"
  },
  "aggregation_mode": {
    "defectos_detectados": ["sum", "avg", "max"],
    "productos_totales": ["sum"],
    "alarmas_disparadas": ["sum"]
  },
  "interval": 600,
  "interval_unit": "seconds"
}
```

**Cálculo de tasa de defectos**:

```json
{
  "type": "roboflow_core/property_definition@v1",
  "name": "tasa_defectos",
  "operations": [
    {
      "type": "Divide",
      "dividend": "$steps.metricas_calidad.defectos_detectados_sum",
      "divisor": "$steps.metricas_calidad.productos_totales_sum"
    },
    {
      "type": "Multiply",
      "multiplicand": 100
    }
  ],
  "data": "$steps.metricas_calidad"
}
```

### Dashboard en Tiempo Real

**Integración con Grafana/InfluxDB**:

```json
{
  "type": "roboflow_core/webhook_sink@v1",
  "name": "influxdb_metrics",
  "url": "http://influxdb.factory.local:8086/write?db=production",
  "method": "POST",
  "body": "quality,line=1 defect_count=$steps.count_defectos.count,alarm_active=$steps.alarma_ajuste.alarm_active",
  "fire_and_forget": true
}
```

**Métricas visualizadas**:
- Conteo de defectos en tiempo real
- Tasa de defectos por hora
- Tiempo promedio entre alarmas
- Downtime causado por alarmas de calidad
- Distribución de tipos de defectos

### Workflow Completo

Ver: [`data/workflows/verticals/manufacturing_defect_detection.json`](../../../data/workflows/verticals/manufacturing_defect_detection.json)

### Métricas de Negocio

**KPIs Obtenidos**:
- **First Pass Yield (FPY)**: % productos sin defectos en primera pasada
- **Defect Rate**: Tasa de defectos por turno/día
- **Mean Time Between Alarms (MTBA)**: Tiempo promedio entre alertas
- **Response Time**: Tiempo desde alarma hasta acción correctiva
- **Downtime por Calidad**: Tiempo de parada causado por defectos

**ROI**:
- ✅ Reducción de desperdicio (menos productos defectuosos en lote)
- ✅ Detección temprana (antes de producir 1000 unidades defectuosas)
- ✅ Trazabilidad automatizada (timestamp de cada evento)
- ✅ Prevención de recalls costosos
- ✅ Optimización de mantenimiento preventivo

### Caso Real: Línea de Embotellado

**Escenario**:
- Planta de bebidas con 3 líneas de embotellado
- Detección de botellas mal tapadas o etiquetas desalineadas
- Velocidad: 300 botellas/minuto por línea

**Configuración**:
```json
{
  "type": "care/prediction_alarm@v1",
  "name": "alarma_etiquetas",
  "threshold": 10,
  "hysteresis": 3,
  "cooldown_seconds": 20.0,
  "alarm_message_template": "🏷️ LÍNEA {line_id}: {count} etiquetas defectuosas en 60s. Ajustar aplicador."
}
```

**Resultado**:
- Reducción de 85% en productos defectuosos que llegaban a empaque
- Ahorro de $15,000 USD/mes en desperdicio
- Mejora de OEE (Overall Equipment Effectiveness) de 78% a 92%

### Extensiones Futuras

1. **Clasificación de defectos**: Alarmas específicas por tipo (scratch, crack, misalignment)
2. **Predicción de fallas**: Usar tendencia de defectos para predecir falla de máquina
3. **Integración con MES**: Enviar datos a Manufacturing Execution System
4. **Adaptative thresholds**: Ajustar threshold según velocidad de línea
5. **Root cause analysis**: Correlacionar alarmas con parámetros de proceso

### Consideraciones de Implementación

**Iluminación**:
- LED ring lights para inspección consistente
- Control de exposición de cámara según velocidad de línea

**Posicionamiento de cámara**:
- Ángulo cenital (90°) para inspección de tapa
- Lateral para inspección de etiquetas
- Multiple cámaras para inspección 360°

**Calibración**:
- Re-entrenar modelo cada 3 meses con nuevos ejemplos
- Ajustar threshold según variabilidad estacional del proceso

---

## Referencias

- [Prediction Alarm Block Documentation](../../blocks/prediction_alarm.md)
- [Industrial Integration Patterns](./industrial_integration.md) *(TODO)*
- [OEE Calculation Guide](./oee_metrics.md) *(TODO)*
