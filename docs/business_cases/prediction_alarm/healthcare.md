# Healthcare - Monitoreo de Capacidad en Salas

## Contexto de Negocio

**Vertical**: Healthcare / Hospitales
**Desafío**: Gestionar ocupación de salas de espera, consultorios y áreas críticas en tiempo real
**Regulación**: Cumplimiento de normativas de capacidad máxima y distanciamiento

## Caso de Uso: Sala de Espera de Emergencias

### Problema Real

Un hospital necesita:
- Monitorear ocupación de sala de espera en tiempo real
- Alertar cuando se excede capacidad máxima (ej: 15 personas)
- Notificar al personal para habilitar sala adicional
- Prevenir saturación y mejorar experiencia del paciente
- Registrar histórico de ocupación para análisis

### Solución con Prediction Alarm

```
Cámara → Detección → Conteo → Prediction Alarm → Sistema de Alertas
         (personas)   (count)   (threshold: 15)    (MQTT/Webhook)
```

### Configuración del Block

```json
{
  "type": "care/prediction_alarm@v1",
  "name": "capacidad_sala_espera",
  "count": "$steps.count.count",
  "threshold": 15,
  "hysteresis": 3,
  "cooldown_seconds": 60.0,
  "alarm_message_template": "🏥 CAPACIDAD EXCEDIDA - Sala de Espera: {count}/15 personas. Habilitar sala adicional."
}
```

**Parámetros Justificados**:
- `threshold: 15` - Capacidad máxima según regulación local
- `hysteresis: 3` - Desactivar cuando baja a 12 (evita oscilaciones)
- `cooldown: 60s` - Evitar spam, tiempo suficiente para respuesta del personal

### Estados del Sistema

| Estado | Count | Acción | Notificación |
|--------|-------|--------|--------------|
| **IDLE** | 0-14 | Operación normal | - |
| **FIRING** | 15+ | Alarma activa | ✅ Notificar enfermera de triaje |
| **COOLDOWN** | 12-14 | Esperando resolución | - |
| **IDLE** | <12 | Capacidad normalizada | ✅ Capacidad normalizada |

### Integración con Sistema Hospitalario

**Opción 1: MQTT → Sistema de Gestión**
```json
{
  "type": "care/mqtt_writer@v1",
  "host": "hospital-mqtt.local",
  "topic": "hospital/emergencias/sala_espera/capacidad",
  "message": "$steps.capacidad_sala_espera.alarm_message"
}
```

**Opción 2: Webhook → Sistema HIS (Hospital Information System)**
```json
{
  "type": "roboflow_core/webhook_sink@v1",
  "url": "https://his.hospital.local/api/alerts",
  "json_payload": {
    "area": "emergencias_sala_espera",
    "alarm_active": "$steps.capacidad_sala_espera.alarm_active",
    "current_occupancy": "$steps.capacidad_sala_espera.count_value",
    "max_capacity": 15,
    "timestamp": "$inputs.timestamp",
    "message": "$steps.capacidad_sala_espera.alarm_message"
  }
}
```

**Opción 3: Email → Personal Administrativo**
```json
{
  "type": "roboflow_core/email_notification@v1",
  "receiver_email": "triaje@hospital.local",
  "subject": "⚠️ Alerta de Capacidad - Emergencias",
  "message": "$steps.capacidad_sala_espera.alarm_message"
}
```

### Múltiples Niveles de Severidad

Implementar alertas escalonadas:

```json
{
  "steps": [
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_preventiva",
      "threshold": 12,
      "cooldown_seconds": 120.0,
      "alarm_message_template": "⚠️ PREVENTIVO: Sala al 80% ({count}/15). Preparar sala adicional."
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_critica",
      "threshold": 15,
      "cooldown_seconds": 60.0,
      "alarm_message_template": "🚨 CRÍTICO: Capacidad máxima alcanzada ({count}/15). Acción inmediata."
    },
    {
      "type": "care/prediction_alarm@v1",
      "name": "alerta_sobrecapacidad",
      "threshold": 18,
      "cooldown_seconds": 30.0,
      "alarm_message_template": "🆘 SOBRECAPACIDAD: {count}/15 personas. Riesgo de seguridad."
    }
  ]
}
```

### Analytics para Gestión

Combinar con `data_aggregator` para reportes:

```json
{
  "type": "roboflow_core/data_aggregator@v1",
  "name": "stats_ocupacion",
  "data": {
    "ocupacion_actual": "$steps.count.count",
    "alarmas_disparadas": "$steps.alerta_critica.alarm_active"
  },
  "aggregation_mode": {
    "ocupacion_actual": ["avg", "max"],
    "alarmas_disparadas": ["sum"]
  },
  "interval": 3600,
  "interval_unit": "seconds"
}
```

### Métricas de Negocio

**KPIs Obtenidos**:
- Ocupación promedio por hora
- Número de eventos de sobrecapacidad por día
- Tiempo promedio en estado FIRING (tiempo de respuesta del personal)
- Picos de demanda (horas críticas)

**ROI**:
- ✅ Reducción de tiempo de espera (mejor experiencia)
- ✅ Cumplimiento regulatorio automatizado
- ✅ Optimización de recursos (abrir salas según demanda)
- ✅ Datos para planificación de turnos

### Workflow Completo

Ver: [`data/workflows/verticals/healthcare_sala_espera.json`](../../../data/workflows/verticals/healthcare_sala_espera.json)

### Consideraciones de Privacidad

**Cumplimiento HIPAA/GDPR**:
- ✅ Solo se cuenta personas, no se identifica
- ✅ No se almacenan imágenes (solo metadata)
- ✅ Datos anonimizados en aggregator
- ✅ Retention policy en logs MQTT

### Variantes del Caso de Uso

**Otras Áreas del Hospital**:
1. **UCI/CTI**: Monitoreo de personal médico en zona crítica
2. **Quirófanos**: Control de personas en área estéril
3. **Farmacia**: Gestión de cola de pacientes
4. **Cafetería**: Control de aforo durante pandemia
5. **Estacionamiento**: Disponibilidad de espacios

### Extensiones Futuras

1. **Clasificación por tipo**: Pacientes vs Personal vs Visitas
2. **Tracking temporal**: Tiempo promedio de permanencia
3. **Integración con turnos**: Predicción de ocupación futura
4. **Zonas múltiples**: Alarmas por área dentro de la sala

---

## Referencias

- [Prediction Alarm Block Documentation](../../blocks/prediction_alarm.md)
- [Healthcare Compliance Guide](./compliance_healthcare.md) *(TODO)*
- [Privacy & HIPAA Considerations](./privacy_guidelines.md) *(TODO)*
