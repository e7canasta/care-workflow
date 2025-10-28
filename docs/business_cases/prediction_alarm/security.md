# Security - Control de Zonas Restringidas

## Contexto de Negocio

**Vertical**: Security / Seguridad Física
**Desafío**: Detección de intrusiones y accesos no autorizados en zonas críticas
**Impacto**: Prevención de incidentes, respuesta rápida, cumplimiento normativo

## Caso de Uso: Monitoreo de Zona Restringida en Datacenter

### Problema Real

Un datacenter corporativo necesita:
- Detectar presencia no autorizada en sala de servidores
- Alertar inmediatamente cuando alguien entra sin autorización
- Escalar alerta si múltiples personas acceden simultáneamente
- Registrar todos los eventos para auditoría
- Integrar con sistema de control de acceso físico (PACS)

### Solución con Prediction Alarm

```
Cámara → Detección → Conteo en Zona → Prediction Alarm → Sistema de Seguridad
         (personas)   (time_in_zone)   (threshold: 1)     (PACS/VMS/SOC)
```

### Configuración del Block

```json
{
  "type": "care/prediction_alarm@v1",
  "name": "alarma_intrusion",
  "count": "$steps.count_zona_restringida.count",
  "threshold": 1,
  "hysteresis": 0,
  "cooldown_seconds": 2.0,
  "alarm_message_template": "🚨 INTRUSIÓN DETECTADA - Zona: {zone_name} | Personas: {count} | Timestamp: {timestamp}"
}
```

**Parámetros Justificados**:
- `threshold: 1` - **Cero tolerancia**: Cualquier persona dispara alarma
- `hysteresis: 0` - Sin margen, alarma se desactiva inmediatamente al salir
- `cooldown: 2s` - Mínimo para evitar falsos positivos por movimiento en frame boundary

### Escenarios de Seguridad

#### Escenario 1: Sala de Servidores (High Security)

**Objetivo**: Detectar acceso no autorizado 24/7

```json
{
  "steps": [
    {
      "type": "ObjectDetectionModel",
      "name": "detector",
      "model_id": "yolov11n-640",
      "class_filter": ["person"],
      "confidence": 0.7
    },
    {
      "type": "roboflow_core/byte_tracker@v3",
      "name": "tracker",
      "detections": "$steps.detector.predictions",
      "image": "$inputs.image"
    },
    {
      "type": "roboflow_core/time_in_zone@v2",
      "name": "zona_critica",
      "zone": "$inputs.zona_servidor",
      "detections": "$steps.tracker.tracked_detections",
      "image": "$inputs.image",
      "remove_out_of_zone_detections": true
    },
    {
      "type": "care/detections_count@v1",
      "name": "count_intrusos",
      "predictions": "$steps.zona_critica.timed_detections"
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alarma_intrusion",
      "count": "$steps.count_intrusos.count",
      "threshold": 1,
      "cooldown_seconds": 2.0,
      "alarm_message_template": "🚨 INTRUSIÓN - Sala de Servidores: {count} persona(s) no autorizada(s)"
    },
    {
      "type": "roboflow_core/continue_if@v1",
      "name": "check_intrusion",
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
          }
        ]
      },
      "evaluation_parameters": {
        "alarm_active": "$steps.alarma_intrusion.alarm_active"
      },
      "next_steps": ["$steps.notificar_soc", "$steps.guardar_snapshot"]
    },
    {
      "type": "care/mqtt_writer@v1",
      "name": "notificar_soc",
      "host": "soc.company.local",
      "topic": "security/alarms/critical",
      "message": "$steps.alarma_intrusion.alarm_message",
      "qos": 2,
      "retain": false
    },
    {
      "type": "roboflow_core/local_file_sink@v1",
      "name": "guardar_snapshot",
      "content": "$steps.zona_critica.image",
      "file_type": "jpg",
      "output_mode": "append_log",
      "target_directory": "/var/log/security/intrusions",
      "file_name_prefix": "intrusion_datacenter"
    }
  ]
}
```

**Integración con PACS (Physical Access Control System)**:
- Verificar si persona tiene badge activo en ese momento
- Cross-reference con logs de tarjeta de acceso
- Foto del intruso enviada a sistema de reconocimiento facial

#### Escenario 2: Perímetro Externo (After Hours)

**Objetivo**: Detectar presencia fuera de horario laboral

```json
{
  "steps": [
    {
      "type": "roboflow_core/continue_if@v1",
      "name": "check_after_hours",
      "condition_statement": {
        "type": "StatementGroup",
        "statements": [
          {
            "type": "BinaryStatement",
            "left_operand": {
              "type": "DynamicOperand",
              "operand_name": "current_hour"
            },
            "comparator": {"type": "(Number) >"},
            "right_operand": {"type": "StaticOperand", "value": 20}
          }
        ]
      },
      "evaluation_parameters": {
        "current_hour": "$inputs.current_hour"
      },
      "next_steps": ["$steps.detector"]
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alarma_after_hours",
      "count": "$steps.count_perimetro.count",
      "threshold": 1,
      "cooldown_seconds": 30.0,
      "alarm_message_template": "🌙 ACTIVIDAD AFTER-HOURS: {count} persona(s) detectada(s) en perímetro a las {time}"
    }
  ]
}
```

**Lógica de horarios**:
- 06:00-20:00: Modo normal (sin alarmas)
- 20:00-06:00: Modo alta seguridad (threshold = 1)
- Fines de semana: Modo alta seguridad 24/7

#### Escenario 3: Doble Factor - Zona + Tiempo en Zona

**Objetivo**: Alertar solo si persona permanece más de X segundos

```json
{
  "steps": [
    {
      "type": "roboflow_core/time_in_zone@v2",
      "name": "zona_restringida",
      "zone": "$inputs.restricted_zone",
      "detections": "$steps.tracker.tracked_detections",
      "image": "$inputs.image"
    },
    {
      "type": "roboflow_core/property_definition@v1",
      "name": "filtrar_tiempo",
      "operations": [
        {
          "type": "DetectionsFilter",
          "filter_operation": {
            "type": "DetectionsPropertyFilter",
            "property_name": "time_in_zone",
            "operator": ">=",
            "reference_value": 5.0
          }
        }
      ],
      "data": "$steps.zona_restringida.timed_detections"
    },
    {
      "type": "care/detections_count@v1",
      "name": "count_permanencia",
      "predictions": "$steps.filtrar_tiempo.output"
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alarma_permanencia",
      "count": "$steps.count_permanencia.count",
      "threshold": 1,
      "cooldown_seconds": 10.0,
      "alarm_message_template": "⏱️ PERMANENCIA NO AUTORIZADA: {count} persona(s) en zona >5 segundos"
    }
  ]
}
```

**Ventaja**: Evita falsos positivos por paso transitorio (ej: cruzar pasillo adyacente)

### Múltiples Niveles de Amenaza

**Sistema de alertas escalonado según criticidad de zona**:

```json
{
  "steps": [
    {
      "type": "care/prediction_alarm@v1",
      "name": "zona_amarilla",
      "threshold": 1,
      "cooldown_seconds": 60.0,
      "alarm_message_template": "⚠️ ZONA AMARILLA: {count} persona(s). Monitorear."
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "zona_naranja",
      "threshold": 1,
      "cooldown_seconds": 30.0,
      "alarm_message_template": "🟠 ZONA NARANJA: {count} persona(s). Verificar autorización."
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "zona_roja",
      "threshold": 1,
      "cooldown_seconds": 2.0,
      "alarm_message_template": "🔴 ZONA ROJA: {count} persona(s). RESPUESTA INMEDIATA."
    }
  ]
}
```

**Clasificación de zonas**:

| Color | Descripción | Threshold | Response Time SLA |
|-------|-------------|-----------|-------------------|
| 🟢 **Verde** | Áreas públicas | N/A | - |
| 🟡 **Amarilla** | Oficinas restringidas | 1 | 5 min |
| 🟠 **Naranja** | Sala de equipos | 1 | 2 min |
| 🔴 **Roja** | Datacenter/Bóveda | 1 | 30 seg |

### Integración con VMS (Video Management System)

**Milestone/Genetec Integration**:

```json
{
  "type": "roboflow_core/webhook_sink@v1",
  "name": "vms_integration",
  "url": "https://vms.company.local/api/events",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer $inputs.vms_token",
    "Content-Type": "application/json"
  },
  "json_payload": {
    "event_type": "intrusion_detected",
    "camera_id": "$inputs.camera_id",
    "zone_name": "$inputs.zone_name",
    "person_count": "$steps.alarma_intrusion.count_value",
    "alarm_active": "$steps.alarma_intrusion.alarm_active",
    "timestamp": "$inputs.timestamp",
    "snapshot_url": "$steps.guardar_snapshot.file_path"
  },
  "fire_and_forget": false
}
```

**Acciones automáticas en VMS**:
- Iniciar grabación en alta calidad (si estaba en low-res)
- Activar cámaras PTZ para seguimiento
- Enviar snapshot a operador SOC
- Crear caso en sistema de ticketing

### Analytics de Seguridad

**Métricas de incidentes**:

```json
{
  "type": "roboflow_core/data_aggregator@v1",
  "name": "security_metrics",
  "data": {
    "intrusion_events": "$steps.alarma_intrusion.alarm_active",
    "max_intruders": "$steps.count_intrusos.count"
  },
  "aggregation_mode": {
    "intrusion_events": ["sum", "count"],
    "max_intruders": ["max", "avg"]
  },
  "interval": 86400,
  "interval_unit": "seconds"
}
```

**Reporte diario CSV**:

```json
{
  "type": "roboflow_core/csv_formatter@v1",
  "name": "daily_report",
  "columns_data": {
    "date": "$inputs.date",
    "total_intrusions": "$steps.security_metrics.intrusion_events_sum",
    "max_simultaneous": "$steps.security_metrics.max_intruders_max",
    "avg_intruders": "$steps.security_metrics.max_intruders_avg"
  }
}
```

### Workflow Completo

Ver: [`data/workflows/verticals/security_restricted_zone.json`](../../../data/workflows/verticals/security_restricted_zone.json)

### Métricas de Seguridad

**KPIs Obtenidos**:
- **Intrusion Events per Day**: Número de intrusiones detectadas
- **Mean Time to Detect (MTTD)**: Tiempo desde ingreso hasta detección (<5 seg)
- **Mean Time to Respond (MTTR)**: Tiempo desde alarma hasta respuesta de guardia
- **False Positive Rate**: % alarmas sin intrusión real
- **Coverage**: % del tiempo que sistema está operativo (uptime)

**ROI**:
- ✅ Detección automática 24/7 (vs rondas manuales cada 2 horas)
- ✅ Reducción de 90% en MTTD (de 30 min a <5 seg)
- ✅ Evidencia forense automática (snapshots, logs)
- ✅ Cumplimiento normativo (ISO 27001, SOC 2)
- ✅ Reducción de costos de personal (menos guardias nocturnos)

### Caso Real: Datacenter Financiero

**Escenario**:
- Datacenter tier 3 con 500 racks
- Regulación: PCI-DSS, SOX compliance
- 4 zonas de seguridad concéntricas

**Configuración**:
```json
{
  "zones": [
    {"name": "Zona 1 - Lobby", "threshold": null},
    {"name": "Zona 2 - Oficinas IT", "threshold": 5},
    {"name": "Zona 3 - NOC", "threshold": 2},
    {"name": "Zona 4 - Sala Servidores", "threshold": 1}
  ]
}
```

**Resultados después de 6 meses**:
- 127 alarmas verdaderas (intrusiones detectadas)
- 12 incidentes críticos prevenidos (personal sin autorización)
- 3 intentos de sabotaje detectados y detenidos
- 0 brechas de seguridad no detectadas
- Auditoría de seguridad aprobada con puntuación 98/100

### Extensiones Futuras

1. **Reconocimiento facial**: Identificar personas autorizadas vs desconocidos
2. **PPE detection**: Alertar si persona sin casco/chaleco en zona industrial
3. **Behavioral analysis**: Detectar comportamiento sospechoso (merodeando, mirando cámaras)
4. **Multi-zone tracking**: Seguir trayectoria de persona entre zonas
5. **Integration con sistemas de alarma**: Activar sirenas, bloqueo de puertas
6. **License plate recognition**: Control de vehículos en perímetro

### Consideraciones Legales y Éticas

**Cumplimiento Normativo**:
- ✅ Señalización visible: "Área monitoreada 24/7"
- ✅ Política de privacidad documentada
- ✅ Acceso a logs restringido (solo personal autorizado)
- ✅ Retención de evidencia: 90 días según política
- ✅ Cifrado de datos en tránsito y reposo

**Uso Ético**:
- ❌ NO usar para monitoreo de productividad de empleados
- ❌ NO compartir imágenes fuera de investigaciones legítimas
- ✅ Usar solo para prevención de incidentes de seguridad
- ✅ Informar a empleados sobre sistema de monitoreo

### Mejores Prácticas de Implementación

**Hardware**:
- Cámaras con visión nocturna (IR) para zonas 24/7
- Backup power (UPS) para sistema crítico
- Redundancia: 2 cámaras por zona crítica

**Calibración**:
- Ajustar confidence threshold para reducir falsos positivos
- Test en diferentes condiciones de luz
- Validar con penetration testing (equipo de seguridad ingresa intencionalmente)

**Procedimientos**:
- SOP documentado para respuesta a alarmas
- Escalation matrix (guardia → supervisor → gerente seguridad)
- Drill mensual para verificar response time

---

## Referencias

- [Prediction Alarm Block Documentation](../../blocks/prediction_alarm.md)
- [Security Integration Patterns](./security_integration.md) *(TODO)*
- [Compliance Requirements (ISO 27001, SOC 2)](./compliance_security.md) *(TODO)*
