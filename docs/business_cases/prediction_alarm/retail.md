# Retail - Gestión de Colas y Ocupación

## Contexto de Negocio

**Vertical**: Retail / Comercio
**Desafío**: Optimizar experiencia del cliente mediante gestión inteligente de colas y ocupación de tienda
**Impacto**: Reducción de abandono, mejora de conversión, optimización de personal

## Caso de Uso: Gestión Dinámica de Cajas en Supermercado

### Problema Real

Una cadena de supermercados necesita:
- Monitorear longitud de colas en tiempo real
- Alertar cuando cola excede umbral aceptable (ej: 5 personas)
- Notificar gerente para abrir caja adicional
- Reducir tiempo de espera del cliente
- Medir impacto en satisfacción y ventas

### Solución con Prediction Alarm

```
Cámara → Detección → Conteo → Prediction Alarm → Sistema de Gestión
         (personas)   (cola)   (threshold: 5)     (Staff App/Display)
```

### Configuración del Block

```json
{
  "type": "care/prediction_alarm@v1",
  "name": "alarma_cola_checkout",
  "count": "$steps.count_cola.count",
  "threshold": 5,
  "hysteresis": 2,
  "cooldown_seconds": 120.0,
  "alarm_message_template": "🛒 CHECKOUT - Cola de {count} personas en Caja {checkout_id}. Abrir caja adicional."
}
```

**Parámetros Justificados**:
- `threshold: 5` - Máximo 5 personas en cola (tiempo espera ~10 min)
- `hysteresis: 2` - Desactivar en 3 personas (permite cerrar caja extra)
- `cooldown: 120s` - Tiempo para que cajero adicional se active

### Escenarios de Implementación

#### Escenario 1: Checkout Lines (Cajas Registradoras)

**Objetivo**: Minimizar tiempo de espera en cajas

```json
{
  "steps": [
    {
      "type": "ObjectDetectionModel",
      "name": "detector",
      "model_id": "yolov11n-640",
      "class_filter": ["person"]
    },
    {
      "type": "roboflow_core/line_counter@v2",
      "name": "contador_cola",
      "detections": "$steps.byte_tracker.tracked_detections",
      "line_segment": [[100, 500], [900, 500]],
      "image": "$inputs.image"
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_cola_larga",
      "count": "$steps.contador_cola.count_in",
      "threshold": 5,
      "alarm_message_template": "⚠️ Cola larga: {count} clientes esperando"
    },
    {
      "type": "roboflow_core/continue_if@v1",
      "name": "check_alert",
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
        "alarm_active": "$steps.alerta_cola_larga.alarm_active"
      },
      "next_steps": ["$steps.notificar_staff"]
    },
    {
      "type": "care/mqtt_writer@v1",
      "name": "notificar_staff",
      "host": "store-mqtt.local",
      "topic": "store/checkout/alerts",
      "message": "$steps.alerta_cola_larga.alarm_message"
    }
  ]
}
```

**Integración con Staff App**:
- App móvil para gerente recibe notificación push
- Display en sala de descanso muestra estado de colas
- Sistema de turnos asigna cajero disponible automáticamente

#### Escenario 2: Ocupación de Tienda (Límite COVID/Black Friday)

**Objetivo**: Control de aforo según normativa

```json
{
  "type": "care/prediction_alarm@v1",
  "name": "alarma_aforo",
  "count": "$steps.count_personas_tienda.count",
  "threshold": 200,
  "hysteresis": 10,
  "cooldown_seconds": 60.0,
  "alarm_message_template": "🚪 AFORO COMPLETO: {count}/200 personas. Controlar acceso."
}
```

**Configuración específica**:
- `threshold: 200` - Aforo máximo según regulación
- `hysteresis: 10` - Desactivar en 190 (margen para salida natural)
- Integración con semáforo en entrada (verde/amarillo/rojo)

#### Escenario 3: Sección de Productos Premium (Anti-Robo)

**Objetivo**: Alertar cuando múltiples personas en zona de alto valor

```json
{
  "steps": [
    {
      "type": "roboflow_core/time_in_zone@v2",
      "name": "zona_premium",
      "zone": [[100, 100], [500, 100], [500, 400], [100, 400]],
      "detections": "$steps.byte_tracker.tracked_detections",
      "image": "$inputs.image"
    },
    {
      "type": "care/detections_count@v1",
      "name": "count_zona",
      "predictions": "$steps.zona_premium.timed_detections"
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_seguridad",
      "count": "$steps.count_zona.count",
      "threshold": 3,
      "cooldown_seconds": 30.0,
      "alarm_message_template": "🔒 SEGURIDAD: {count} personas en zona premium. Monitorear."
    }
  ]
}
```

### Múltiples Prioridades de Atención

**Sistema de alertas por prioridad de cliente**:

```json
{
  "steps": [
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_caja_rapida",
      "count": "$steps.count_cola_rapida.count",
      "threshold": 3,
      "cooldown_seconds": 60.0,
      "alarm_message_template": "⚡ CAJA RÁPIDA: {count} clientes (máx 3). Asignar cajero."
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_caja_normal",
      "count": "$steps.count_cola_normal.count",
      "threshold": 5,
      "cooldown_seconds": 120.0,
      "alarm_message_template": "🛒 CAJA NORMAL: {count} clientes. Considerar caja adicional."
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_servicio_cliente",
      "count": "$steps.count_cola_servicio.count",
      "threshold": 4,
      "cooldown_seconds": 180.0,
      "alarm_message_template": "💁 SERVICIO AL CLIENTE: {count} personas esperando."
    }
  ]
}
```

### Analytics de Retail

**Métricas de operación**:

```json
{
  "type": "roboflow_core/data_aggregator@v1",
  "name": "retail_analytics",
  "data": {
    "longitud_cola": "$steps.count_cola.count",
    "alarmas_cola": "$steps.alerta_cola_larga.alarm_active",
    "ocupacion_tienda": "$steps.count_personas_tienda.count"
  },
  "aggregation_mode": {
    "longitud_cola": ["avg", "max", "values_counts"],
    "alarmas_cola": ["sum"],
    "ocupacion_tienda": ["avg", "max"]
  },
  "interval": 1800,
  "interval_unit": "seconds"
}
```

**CSV para análisis histórico**:

```json
{
  "type": "roboflow_core/csv_formatter@v1",
  "name": "reporte_colas",
  "columns_data": {
    "timestamp": "$inputs.timestamp",
    "longitud_cola_avg": "$steps.retail_analytics.longitud_cola_avg",
    "longitud_cola_max": "$steps.retail_analytics.longitud_cola_max",
    "total_alarmas": "$steps.retail_analytics.alarmas_cola_sum",
    "ocupacion_avg": "$steps.retail_analytics.ocupacion_tienda_avg"
  }
}
```

### Dashboard para Gerente de Tienda

**Visualización en tiempo real**:

```
┌─────────────────────────────────────────┐
│  🏪 Dashboard de Operaciones            │
├─────────────────────────────────────────┤
│  Ocupación: 156/200 (78%)        🟢     │
│  Cola Caja 1: 3 personas         🟢     │
│  Cola Caja 2: 7 personas         🔴     │
│  Cola Caja 3: 2 personas         🟢     │
│                                          │
│  ⚠️ ALERTA ACTIVA - Caja 2              │
│     Abrir caja adicional                │
│                                          │
│  Alarmas hoy: 12                        │
│  Tiempo promedio espera: 4.2 min        │
└─────────────────────────────────────────┘
```

### Workflow Completo

Ver: [`data/workflows/verticals/retail_queue_management.json`](../../../data/workflows/verticals/retail_queue_management.json)

### Métricas de Negocio

**KPIs Obtenidos**:
- **Average Queue Length**: Longitud promedio de cola
- **Queue Wait Time**: Tiempo promedio de espera (estimado)
- **Checkout Utilization**: % tiempo que cada caja está activa
- **Peak Hours**: Horas de mayor demanda
- **Abandonment Rate**: % clientes que abandonan cola (requiere tracking)
- **Staff Response Time**: Tiempo desde alarma hasta apertura de caja

**ROI**:
- ✅ Reducción de abandono de cola (5-10% mejora en conversión)
- ✅ Optimización de personal (abrir cajas solo cuando necesario)
- ✅ Mejora en NPS (Net Promoter Score)
- ✅ Cumplimiento de SLA de tiempo de espera (<5 min)
- ✅ Reducción de horas extras innecesarias

### Caso Real: Supermercado Mediano

**Escenario**:
- Supermercado de 1,500 m² con 8 cajas
- Horario: 8:00-22:00 (14 horas)
- Promedio: 2,000 clientes/día

**Configuración**:
- Threshold: 5 personas por caja
- Cooldown: 120 segundos
- Hysteresis: 2

**Resultados después de 3 meses**:
- ⬇️ 32% reducción en tiempo promedio de espera (de 8 min a 5.4 min)
- ⬆️ 7% aumento en satisfacción del cliente (encuestas)
- ⬇️ 15% reducción en abandono de compra estimado
- ⬆️ $18,000 USD/mes en ventas recuperadas
- ⬇️ 10% reducción en horas extra (mejor planificación)

### Extensiones Futuras

1. **Predicción de demanda**: ML para predecir picos 15 min antes
2. **Self-checkout monitoring**: Detectar clientes confundidos que necesitan ayuda
3. **Cart tracking**: Contar productos en carrito para estimar tiempo de checkout
4. **Heat maps**: Zonas de mayor tráfico para optimizar layout
5. **Integración con inventario**: Alertas si producto popular se agota
6. **A/B testing**: Probar diferentes thresholds según día/hora

### Consideraciones de Privacidad

**Cumplimiento GDPR/Ley de Protección de Datos**:
- ✅ Solo conteo, sin identificación facial
- ✅ No almacenamiento de video
- ✅ Señalización visible: "Área monitoreada para mejorar servicio"
- ✅ Política de retención: logs 30 días, analytics agregados 1 año
- ✅ Derecho de acceso: Clientes pueden solicitar eliminación de datos

### Mejores Prácticas de Implementación

**Posicionamiento de cámaras**:
- Ángulo cenital (bird's eye view) para mejor conteo
- Evitar contraluz de puertas/ventanas
- Cubrir zona de cola completa (10-15 metros)

**Calibración**:
- Ajustar threshold según día de semana (lunes vs sábado)
- Considerar festivos y eventos especiales
- Re-calibrar cada 6 meses según cambios en layout

**Change Management**:
- Capacitar staff en interpretación de alertas
- Establecer SLA de respuesta (ej: 2 min para abrir caja)
- Gamificación: Premiar cajeros con mejor response time

---

## Referencias

- [Prediction Alarm Block Documentation](../../blocks/prediction_alarm.md)
- [Retail Analytics Best Practices](./retail_analytics.md) *(TODO)*
- [Privacy Compliance for Retail](./privacy_retail.md) *(TODO)*
