# Vertical Industry Workflows

Este directorio contiene workflows específicos para diferentes industrias verticales, demostrando la aplicación del `care/prediction_alarm@v1` block en casos de negocio reales.

## 📁 Workflows Disponibles

### Healthcare: `healthcare_sala_espera.json`

**Caso de Uso**: Monitoreo de capacidad en sala de espera de emergencias

**Configuración**:
- ✅ 3 niveles de alerta (Preventivo, Crítico, Sobrecapacidad)
- ✅ Thresholds: 12, 15, 18 personas
- ✅ Hysteresis configurado para evitar oscilaciones
- ✅ MQTT QoS 1 para preventivo, QoS 2 para crítico
- ✅ Aggregation de ocupación por hora

**Variables de Entorno**:
```bash
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
export WORKFLOW_DEFINITION="data/workflows/verticals/healthcare_sala_espera.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"

uv run python examples/run_mqtt_detection.py
```

**MQTT Topics**:
- `hospital/emergencias/capacidad/preventivo` - Alerta al 80% (12/15)
- `hospital/emergencias/capacidad/critico` - Capacidad máxima (15+)

**Métricas**:
- Ocupación promedio por hora
- Número de alarmas críticas por día
- Máxima ocupación registrada

**Documentación Completa**: [docs/business_cases/prediction_alarm/healthcare.md](../../docs/business_cases/prediction_alarm/healthcare.md)

---

### Manufacturing: `manufacturing_defect_detection.json` ✅

**Caso de Uso**: Detección de productos defectuosos en línea de producción

**Configuración**:
- ✅ 3 niveles: Preventivo (2 defectos), Ajuste (3), Parada (5)
- ✅ Integración con PLC/SCADA vía MQTT
- ✅ QoS 2 para comando STOP crítico
- ✅ Snapshot automático de defectos en parada
- ✅ Analytics de calidad (10 min)

**Variables de Entorno**:
```bash
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
export WORKFLOW_DEFINITION="data/workflows/verticals/manufacturing_defect_detection.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/production_line"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"

uv run python examples/run_mqtt_detection.py
```

**MQTT Topics**:
- `factory/quality/warning` - Alerta preventiva (2 defectos)
- `factory/quality/adjustment_required` - Ajuste requerido (3 defectos)
- `factory/line_1/commands/stop` - Comando de parada (5+ defectos)

**Documentación Completa**: [docs/business_cases/prediction_alarm/manufacturing.md](../../docs/business_cases/prediction_alarm/manufacturing.md)

---

### Retail: `retail_queue_management.json` ✅

**Caso de Uso**: Gestión de colas en supermercado

**Configuración**:
- ✅ Threshold: 5 personas (normal), 8 (crítico)
- ✅ Hysteresis: 2 (desactivar en 3)
- ✅ Cooldown: 120s normal, 60s crítico
- ✅ Tracking con ByteTracker
- ✅ Zona de cola configurable (polygon)
- ✅ CSV report cada 30 min

**Variables de Entorno**:
```bash
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
export WORKFLOW_DEFINITION="data/workflows/verticals/retail_queue_management.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/checkout_1"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"

uv run python examples/run_mqtt_detection.py
```

**MQTT Topics**:
- `store/checkout/alerts` - Alerta normal (5+ personas)
- `store/management/alerts` - Alerta crítica (8+ personas)

**Métricas**:
- Longitud promedio de cola (30 min)
- Máxima longitud registrada
- Total de alarmas disparadas
- CSV guardado en `/var/log/retail/queues`

**Documentación Completa**: [docs/business_cases/prediction_alarm/retail.md](../../docs/business_cases/prediction_alarm/retail.md)

---

### Security: `security_restricted_zone.json` ✅

**Caso de Uso**: Control de acceso a zona restringida (datacenter)

**Configuración**:
- ✅ Threshold: 1 persona (cero tolerancia), 2+ (múltiples intrusos)
- ✅ Hysteresis: 0 (desactivar inmediatamente)
- ✅ Cooldown: 2s intrusion, 1s múltiples
- ✅ QoS 2 para máxima confiabilidad
- ✅ Time in zone filtrado (>2s para evitar falsos positivos)
- ✅ Tracking persistente con ByteTracker

**Variables de Entorno**:
```bash
export WORKFLOWS_PLUGINS="care.workflows.care_steps"
export WORKFLOW_DEFINITION="data/workflows/verticals/security_restricted_zone.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/datacenter_door"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"

uv run python examples/run_mqtt_detection.py
```

**MQTT Topics**:
- `security/alarms/critical` - Intrusión detectada (1 persona)
- `security/alarms/emergency` - Múltiples intrusos (2+ personas)

**Acciones Automáticas**:
- ✅ Snapshot de intruso guardado en `/var/log/security/intrusions`
- ✅ Notificación a SOC (Security Operations Center) vía MQTT QoS 2
- ✅ CSV de métricas cada hora en `/var/log/security/reports`
- ✅ Visualización con bounding boxes rojos y zona marcada

**Documentación Completa**: [docs/business_cases/prediction_alarm/security.md](../../docs/business_cases/prediction_alarm/security.md)

---

## 🎯 Comparación de Configuraciones por Vertical

| Vertical | Threshold | Hysteresis | Cooldown | QoS | Prioridad |
|----------|-----------|------------|----------|-----|-----------|
| **Healthcare** | 15 | 3 | 60s | 2 | CRÍTICA |
| **Manufacturing** | 3-5 | 1 | 10s | 2 | ALTA |
| **Retail** | 5 | 2 | 120s | 1 | MEDIA |
| **Security** | 1 | 0 | 2s | 2 | CRÍTICA |

## 📊 Parámetros Clave por Contexto

### Threshold Selection

- **Healthcare**: Basado en capacidad regulatoria (códigos de construcción)
- **Manufacturing**: Basado en tasa de defectos aceptable (1-2% típico)
- **Retail**: Basado en SLA de tiempo de espera (5 min = ~5 personas)
- **Security**: Cero tolerancia (threshold = 1)

### Hysteresis Tuning

- **Alto tráfico variable**: Hysteresis alto (2-3) para evitar flapping
- **Baja variabilidad**: Hysteresis bajo (0-1) para respuesta rápida
- **Seguridad crítica**: Sin hysteresis (0) para máxima sensibilidad

### Cooldown Strategy

- **Acción humana requerida**: Cooldown largo (60-120s) - tiempo para respuesta
- **Acción automática**: Cooldown corto (2-10s) - sistema responde solo
- **Alarmas informativas**: Cooldown muy largo (300s+) - evitar spam

### QoS Levels

- **QoS 0** (at most once): Métricas no críticas, logs
- **QoS 1** (at least once): Alertas importantes pero toleran duplicados
- **QoS 2** (exactly once): Comandos críticos (stop line, lock doors)

## 🚀 Quick Start por Vertical

### Healthcare
```bash
export WORKFLOW_DEFINITION="data/workflows/verticals/healthcare_sala_espera.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"
uv run python examples/run_mqtt_detection.py
```

### Manufacturing
```bash
export WORKFLOW_DEFINITION="data/workflows/verticals/manufacturing_defect_detection.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/production_line"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"
uv run python examples/run_mqtt_detection.py
```

### Retail
```bash
export WORKFLOW_DEFINITION="data/workflows/verticals/retail_queue_management.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/checkout_1"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"
uv run python examples/run_mqtt_detection.py
```

### Security
```bash
export WORKFLOW_DEFINITION="data/workflows/verticals/security_restricted_zone.json"
export VIDEO_REFERENCE="rtsp://localhost:8554/datacenter_door"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"
uv run python examples/run_mqtt_detection.py
```

## 📚 Recursos Adicionales

### Documentación de Business Cases
- [Healthcare](../../docs/business_cases/prediction_alarm/healthcare.md)
- [Manufacturing](../../docs/business_cases/prediction_alarm/manufacturing.md)
- [Retail](../../docs/business_cases/prediction_alarm/retail.md)
- [Security](../../docs/business_cases/prediction_alarm/security.md)

### Documentación Técnica
- [Prediction Alarm Block](../../docs/blocks/prediction_alarm.md)
- [Custom Blocks Guide](../../care_workflow/care_blocks/README.md)
- [Project Architecture](../../CLAUDE.md)

## 🎸 Design Philosophy

Estos workflows demuestran:

**"Complejidad por Diseño"**:
- Cada vertical tiene parámetros justificados por contexto de negocio
- State machine común, configuración específica
- No over-engineering: mismos building blocks, diferentes composiciones

**"Patterns con Propósito"**:
- Múltiples niveles de alarma (preventivo → crítico)
- Flow control con `continue_if` para evitar spam
- Analytics agregados para métricas de negocio

**"Pragmatismo > Purismo"**:
- Thresholds empíricos (ajustar según feedback real)
- Cooldowns basados en tiempos de respuesta humanos
- QoS según criticidad del negocio, no "best practices" rígidas

---

## ✅ Workflows Completados

Todos los workflows verticales están implementados y listos para usar:

- ✅ `healthcare_sala_espera.json` - Monitoreo de capacidad en sala de espera
- ✅ `manufacturing_defect_detection.json` - Detección de productos defectuosos
- ✅ `retail_queue_management.json` - Gestión de colas en checkout
- ✅ `security_restricted_zone.json` - Control de zonas restringidas

## TODO (Extensiones Futuras)

- [ ] Agregar scripts de ejemplo específicos por vertical (alternativas a run_mqtt_detection.py)
- [ ] Documentar troubleshooting común por vertical
- [ ] Crear dashboard templates (Grafana) por vertical
- [ ] Agregar más verticales (Transportation, Agriculture, Energy)
- [ ] Implementar OPC-UA writer para Manufacturing
- [ ] Integración con VMS específicos (Milestone, Genetec) para Security
