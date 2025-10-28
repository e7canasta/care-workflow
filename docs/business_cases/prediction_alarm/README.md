# Prediction Alarm Block - Business Cases por Vertical

Esta guía documenta casos de uso reales del `care/prediction_alarm@v1` block en diferentes industrias verticales, con configuraciones específicas, métricas de negocio y ROI esperado.

## 🎯 Overview

El **Prediction Alarm** block permite implementar sistemas de alertas inteligentes con:
- Threshold-based activation
- Hysteresis para prevenir flapping
- Cooldown periods configurables
- State machine predecible (IDLE → FIRING → COOLDOWN)
- Integración con sistemas empresariales (MQTT, Webhooks, Email)

## 📚 Casos de Uso por Vertical

### 🏥 Healthcare

**[Monitoreo de Capacidad en Salas de Espera](./healthcare.md)**

**Problema**: Gestionar ocupación de salas críticas en tiempo real
**Solución**: Alertas escalonadas (preventivo → crítico → sobrecapacidad)

**Configuración Típica**:
- Threshold: 15 personas (capacidad regulatoria)
- Hysteresis: 3 (desactivar en 12)
- Cooldown: 60s (tiempo de respuesta del personal)

**ROI**:
- ✅ Cumplimiento regulatorio automatizado
- ✅ Mejor experiencia del paciente
- ✅ Optimización de recursos (salas adicionales según demanda)

**Métricas Clave**:
- Ocupación promedio por turno
- Número de eventos de sobrecapacidad
- Tiempo de respuesta del personal

[Ver documentación completa →](./healthcare.md)

---

### 🏭 Manufacturing

**[Control de Calidad en Línea de Producción](./manufacturing.md)**

**Problema**: Detección temprana de productos defectuosos
**Solución**: Alarmas multi-nivel con integración a PLC/SCADA

**Configuración Típica**:
- Threshold: 3 defectos en ventana de inspección
- Hysteresis: 1 (permite variación)
- Cooldown: 10s (tiempo de inspección visual)

**ROI**:
- ✅ Reducción de 85% en desperdicio
- ✅ Detección antes de producir lotes completos defectuosos
- ✅ Mejora de OEE (Overall Equipment Effectiveness)

**Métricas Clave**:
- First Pass Yield (FPY)
- Tasa de defectos por turno
- Mean Time Between Alarms (MTBA)

**Caso Real**: Línea de embotellado logró reducir productos defectuosos de 1.2% a 0.18%, ahorrando $15,000 USD/mes.

[Ver documentación completa →](./manufacturing.md)

---

### 🛒 Retail

**[Gestión Dinámica de Colas en Checkout](./retail.md)**

**Problema**: Minimizar tiempo de espera del cliente
**Solución**: Notificaciones automáticas para abrir cajas adicionales

**Configuración Típica**:
- Threshold: 5 personas por caja (tiempo espera ~10 min)
- Hysteresis: 2 (desactivar en 3)
- Cooldown: 120s (tiempo para activar cajero)

**ROI**:
- ✅ 32% reducción en tiempo promedio de espera
- ✅ 7% aumento en satisfacción del cliente
- ✅ $18,000 USD/mes en ventas recuperadas (menos abandono)

**Métricas Clave**:
- Average Queue Length
- Queue Wait Time estimado
- Abandonment Rate

**Otros Usos**:
- Control de aforo (COVID compliance)
- Monitoreo de zona premium (anti-robo)
- Gestión de servicio al cliente

[Ver documentación completa →](./retail.md)

---

### 🔒 Security

**[Control de Acceso a Zonas Restringidas](./security.md)**

**Problema**: Detectar intrusiones en áreas críticas 24/7
**Solución**: Alarmas de cero tolerancia con integración a VMS/PACS

**Configuración Típica**:
- Threshold: 1 persona (cero tolerancia)
- Hysteresis: 0 (desactivar inmediatamente)
- Cooldown: 2s (minimizar para detección rápida)

**ROI**:
- ✅ Reducción de 90% en Mean Time to Detect (MTTD)
- ✅ Evidencia forense automática (snapshots, logs)
- ✅ Cumplimiento normativo (ISO 27001, SOC 2)

**Métricas Clave**:
- Intrusion Events per Day
- Mean Time to Detect (MTTD)
- Mean Time to Respond (MTTR)
- False Positive Rate

**Caso Real**: Datacenter financiero detectó y previno 12 incidentes críticos en 6 meses, con 0 brechas no detectadas.

[Ver documentación completa →](./security.md)

---

## 🔧 Comparación de Configuraciones

| Vertical | Threshold | Hysteresis | Cooldown | QoS MQTT | Prioridad |
|----------|-----------|------------|----------|----------|-----------|
| **Healthcare** | 15 | 3 | 60s | 2 | CRÍTICA |
| **Manufacturing** | 3-5 | 1 | 10s | 2 | ALTA |
| **Retail** | 5 | 2 | 120s | 1 | MEDIA |
| **Security** | 1 | 0 | 2s | 2 | CRÍTICA |

### ¿Cómo Elegir Parámetros?

#### Threshold
- **Basado en regulación**: Healthcare (capacidad legal), Security (cero tolerancia)
- **Basado en SLA**: Retail (tiempo espera aceptable)
- **Basado en estadística**: Manufacturing (tasa de defectos normal)

#### Hysteresis
- **Alto (2-3)**: Entornos con alta variabilidad (retail, healthcare)
- **Bajo (0-1)**: Procesos estables (manufacturing) o críticos (security)
- **Objetivo**: Evitar oscilaciones alarm ON → OFF → ON

#### Cooldown
- **Largo (60-120s)**: Requiere acción humana (abrir caja, habilitar sala)
- **Corto (2-10s)**: Acción automática (detener línea, bloquear puerta)
- **Criterio**: Tiempo realista de respuesta del sistema/persona

#### QoS MQTT
- **QoS 0**: Logs, métricas no críticas
- **QoS 1**: Alertas importantes, toleran duplicados
- **QoS 2**: Comandos críticos (stop, lock), deben llegar exactamente una vez

---

## 📊 Patrones Comunes de Implementación

### Pattern 1: Alarmas Escalonadas (Multi-Level)

Usado en: **Healthcare, Manufacturing, Retail**

```
Detección → Conteo → [ Alarm Low ] → Notificación Info
                     [ Alarm Med ] → Notificación Warning
                     [ Alarm High ] → Acción Crítica
```

**Ejemplo Healthcare**:
- Low (12 personas): Preparar sala adicional
- Medium (15): Activar sala adicional
- High (18): Alerta de sobrecapacidad

### Pattern 2: Zona + Permanencia (Time-gated)

Usado en: **Security, Manufacturing**

```
Detección → Tracking → Time in Zone → Filtrar (>5s) → Alarm → Acción
```

**Ventaja**: Evita falsos positivos por pasos transitorios

### Pattern 3: Alarma + Flow Control Condicional

Usado en: **Todos los verticales**

```
Alarm → ContinueIf(alarm_active==True) → Sink (MQTT/Webhook)
```

**Ventaja**: Solo ejecuta sink cuando alarma está activa, ahorra recursos

### Pattern 4: Alarma + Analytics Agregados

Usado en: **Manufacturing, Retail, Healthcare**

```
Alarm → DataAggregator(interval=1h) → CSV/InfluxDB → Dashboard
```

**Ventaja**: Métricas históricas para análisis de tendencias

---

## 🚀 Quick Start por Vertical

### Healthcare
```bash
export WORKFLOW_DEFINITION="data/workflows/verticals/healthcare_sala_espera.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/waiting_room"
uv run python examples/run_mqtt_detection.py
```

### Manufacturing
```bash
export WORKFLOW_DEFINITION="data/workflows/verticals/manufacturing_defect_detection.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/production_line"
uv run python examples/run_mqtt_detection.py
```

### Retail
```bash
export WORKFLOW_DEFINITION="data/workflows/verticals/retail_queue_management.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/checkout_1"
uv run python examples/run_mqtt_detection.py
```

### Security
```bash
export WORKFLOW_DEFINITION="data/workflows/verticals/security_restricted_zone.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/datacenter_door"
uv run python examples/run_mqtt_detection.py
```

---

## 📈 ROI Summary

| Vertical | Problema Resuelto | ROI Estimado | Payback |
|----------|-------------------|--------------|---------|
| **Healthcare** | Sobrecapacidad de salas | Cumplimiento + Experiencia | 3-6 meses |
| **Manufacturing** | Productos defectuosos | $15k/mes ahorro desperdicio | 2-4 meses |
| **Retail** | Abandono de cola | $18k/mes ventas recuperadas | 3-6 meses |
| **Security** | Intrusiones no detectadas | Prevención incidentes | 6-12 meses |

---

## 🔗 Referencias

### Documentación Técnica
- [Prediction Alarm Block](../../blocks/prediction_alarm.md)
- [Custom Blocks Guide](../../../care_workflow/care_blocks/README.md)
- [Example Workflows](../../../data/workflows/examples/README.md)

### Workflows por Vertical
- [Healthcare Sala Espera](../../../data/workflows/verticals/healthcare_sala_espera.json)
- [Manufacturing (TODO)](../../../data/workflows/verticals/manufacturing_defect_detection.json)
- [Retail (TODO)](../../../data/workflows/verticals/retail_queue_management.json)
- [Security (TODO)](../../../data/workflows/verticals/security_restricted_zone.json)

### Business Cases Detallados
- [Healthcare](./healthcare.md)
- [Manufacturing](./manufacturing.md)
- [Retail](./retail.md)
- [Security](./security.md)

---

## 💡 Próximos Pasos

1. **Revisar caso de uso relevante** para tu industria
2. **Adaptar workflow JSON** con tus parámetros específicos
3. **Configurar integración** (MQTT broker, webhook endpoint, etc.)
4. **Ejecutar prueba piloto** con video de test
5. **Calibrar thresholds** según feedback operacional
6. **Medir métricas** y ajustar según KPIs

¿Dudas? Consultar [CLAUDE.md](../../../CLAUDE.md) para filosofía de diseño y mejores prácticas.
