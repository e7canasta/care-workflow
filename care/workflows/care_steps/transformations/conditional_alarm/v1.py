from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Type, Union

from pydantic import ConfigDict, Field

from inference.core.logger import logger
from inference.core.workflows.core_steps.common.query_language.entities.operations import (
    StatementGroup,
)
from inference.core.workflows.core_steps.common.query_language.evaluation_engine.core import (
    build_eval_function,
)
from inference.core.workflows.execution_engine.entities.base import OutputDefinition
from inference.core.workflows.execution_engine.entities.types import (
    BOOLEAN_KIND,
    FLOAT_KIND,
    INTEGER_KIND,
    STRING_KIND,
    Selector,
)
from inference.core.workflows.prototypes.block import (
    BlockResult,
    WorkflowBlock,
    WorkflowBlockManifest,
)

from care.workflows.care_steps.core.alarm_engine import (
    AlarmEngine,
    ConditionWithHysteresis,
)

LONG_DESCRIPTION = """
Conditional Alarm block for flexible alert triggering based on UQL statements.

Este block usa el AlarmEngine core con soporte completo de UQL (Universal Query Language)
para definir condiciones arbitrarias. Cada statement puede tener su propio hysteresis
para evitar flapping.

Características:
- Condiciones flexibles usando UQL StatementGroup
- Hysteresis per-statement (opcional, con fallback a default)
- State machine (IDLE → FIRING → COOLDOWN)
- Cooldown period configurable
- Message templating con valores dinámicos

Casos de Uso:
- Múltiples condiciones: "count > 10 AND temp > 25"
- Condiciones complejas: "(count > 10 OR pressure < 5) AND temp > 25"
- Lógica de negocio específica: "doctors >= 2 AND patients >= 8"

State Machine:
    IDLE → FIRING: Condiciones se cumplen AND cooldown elapsed
    FIRING → COOLDOWN: Alarm emitido
    COOLDOWN → IDLE: Condiciones dejan de cumplirse (con hysteresis) OR cooldown elapsed

Outputs:
    - alarm_active (bool): TRUE cuando alarm está firing
    - alarm_message (str): Mensaje formateado
    - state (str): Estado actual ("idle", "firing", "cooldown")
    - alarm_count (int): Número de veces que alarm se ha disparado
    - condition_states (dict): Estado de cada condición (para debugging)
"""

SHORT_DESCRIPTION = "Trigger alarms based on flexible UQL conditions with hysteresis."

LONG_DESCRIPTION = """
Conditional Alarm - Alarmas basadas en condiciones UQL flexibles.

Este block permite definir alarmas con lógica arbitraria usando UQL (Universal Query Language),
similar a `roboflow_core/continue_if@v1` pero con state machine y hysteresis.

**Diferencias con continue_if**:
- ✅ State machine (IDLE → FIRING → COOLDOWN)
- ✅ Hysteresis per-statement para evitar flapping
- ✅ Cooldown automático
- ✅ Message templating
- ✅ Observable state

**Ejemplo básico** (equivalente a prediction_alarm):
```json
{
  "type": "care/conditional_alarm@v1",
  "condition_statement": {
    "type": "StatementGroup",
    "statements": [
      {
        "type": "BinaryStatement",
        "left_operand": {"type": "DynamicOperand", "operand_name": "count"},
        "comparator": {"type": "(Number) >"},
        "right_operand": {"type": "StaticOperand", "value": 10},
        "hysteresis": 2
      }
    ]
  },
  "evaluation_parameters": {"count": "$steps.count.count"},
  "cooldown_seconds": 5.0,
  "alarm_message_template": "Count is {count}"
}
```

**Ejemplo multi-condición** (2 médicos Y 8 pacientes):
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
        "right_operand": {"type": "StaticOperand", "value": 2},
        "hysteresis": 1
      },
      {
        "type": "BinaryStatement",
        "left_operand": {"type": "DynamicOperand", "operand_name": "patients"},
        "comparator": {"type": "(Number) >="},
        "right_operand": {"type": "StaticOperand", "value": 8},
        "hysteresis": 2
      }
    ],
    "operator": "AND"
  },
  "evaluation_parameters": {
    "doctors": "$steps.count_doctors.count",
    "patients": "$steps.count_patients.count"
  },
  "alarm_message_template": "Ratio crítico: {doctors} médicos para {patients} pacientes"
}
```

**Hysteresis per-statement**:
- Si statement tiene `hysteresis` explícito, usa ese valor
- Si no, usa `hysteresis_default` del block
- Permite ajuste fino por condición

**Note**: Este block es más complejo que los wrappers específicos (prediction_alarm, etc.).
Úsalo solo cuando necesites lógica condicional que no se pueda expresar con los blocks simples.
"""


class BlockManifest(WorkflowBlockManifest):
    model_config = ConfigDict(
        json_schema_extra={
            "name": "Conditional Alarm",
            "version": "v1",
            "short_description": SHORT_DESCRIPTION,
            "long_description": LONG_DESCRIPTION,
            "license": "Apache-2.0",
            "block_type": "transformation",
            "ui_manifest": {
                "section": "analytics",
                "icon": "far fa-bell-exclamation",
                "blockPriority": 2,
            },
        }
    )
    type: Literal["care/conditional_alarm@v1"]

    condition_statement: StatementGroup = Field(
        title="Conditional Statement",
        description="UQL statement group defining alarm conditions. Each statement can have optional 'hysteresis' field.",
        examples=[
            {
                "type": "StatementGroup",
                "statements": [
                    {
                        "type": "BinaryStatement",
                        "left_operand": {"type": "DynamicOperand", "operand_name": "count"},
                        "comparator": {"type": "(Number) >"},
                        "right_operand": {"type": "StaticOperand", "value": 10},
                        "hysteresis": 2,
                    }
                ],
            }
        ],
    )

    evaluation_parameters: Dict[str, Selector()] = Field(
        description="Parameters to be used in the conditional logic.",
        examples=[{"count": "$steps.count.count", "temp": "$steps.temp.value"}],
        default_factory=lambda: {},
    )

    hysteresis_default: Union[float, Selector(kind=[FLOAT_KIND, INTEGER_KIND])] = Field(
        default=1.0,
        description="Default hysteresis for statements without explicit hysteresis field.",
        examples=[1.0, 2.0, 5.0],
    )

    cooldown_seconds: Union[float, Selector(kind=[FLOAT_KIND, INTEGER_KIND])] = Field(
        default=5.0,
        description="Minimum seconds between alarm activations.",
        examples=[5.0, 10.0, 60.0],
    )

    alarm_message_template: Union[str, Selector(kind=[STRING_KIND])] = Field(
        default="Alarm triggered",
        description="Message template with placeholders matching evaluation_parameters keys.",
        examples=[
            "Alert: count={count}",
            "Ratio crítico: {doctors} médicos, {patients} pacientes",
        ],
    )

    combine_operator: Literal["AND", "OR"] = Field(
        default="AND",
        description="How to combine multiple statements: 'AND' (all must be true) or 'OR' (at least one true).",
        examples=["AND", "OR"],
    )

    @classmethod
    def describe_outputs(cls) -> List[OutputDefinition]:
        return [
            OutputDefinition(name="alarm_active", kind=[BOOLEAN_KIND]),
            OutputDefinition(name="alarm_message", kind=[STRING_KIND]),
            OutputDefinition(name="state", kind=[STRING_KIND]),
            OutputDefinition(name="alarm_count", kind=[INTEGER_KIND]),
        ]

    @classmethod
    def get_execution_engine_compatibility(cls) -> Optional[str]:
        return ">=1.3.0,<2.0.0"


class ConditionalAlarmBlockV1(WorkflowBlock):
    """
    Conditional Alarm block usando AlarmEngine con UQL.

    Este block es el más flexible de la familia de alarmas, permitiendo
    lógica arbitraria usando UQL statements.

    NOTA: Este block NO soporta hysteresis per-statement en UQL nativo
    porque StatementGroup de Roboflow no tiene campo hysteresis.

    Alternativa: Usar hysteresis_default global para todas las condiciones.
    """

    def __init__(self):
        super().__init__()
        self._engine = AlarmEngine()
        self._eval_function = None

    @classmethod
    def get_manifest(cls) -> Type[WorkflowBlockManifest]:
        return BlockManifest

    def run(
        self,
        condition_statement: StatementGroup,
        evaluation_parameters: Dict[str, Any],
        hysteresis_default: float = 1.0,
        cooldown_seconds: float = 5.0,
        alarm_message_template: str = "Alarm triggered",
        combine_operator: str = "AND",
    ) -> BlockResult:
        """
        Evalúa condiciones UQL y actualiza state machine.

        Args:
            condition_statement: StatementGroup con condiciones UQL
            evaluation_parameters: Parámetros para evaluar
            hysteresis_default: Hysteresis global
            cooldown_seconds: Cooldown period
            alarm_message_template: Template de mensaje
            combine_operator: "AND" o "OR"

        Returns:
            BlockResult con alarm_active, alarm_message, state, alarm_count
        """
        # Runtime validation
        if hysteresis_default < 0:
            raise ValueError(f"hysteresis_default must be >= 0, got {hysteresis_default}")
        if cooldown_seconds < 0:
            raise ValueError(f"cooldown_seconds must be >= 0, got {cooldown_seconds}")
        
        # Build evaluation function (cache en primera ejecución)
        if self._eval_function is None:
            self._eval_function = build_eval_function(definition=condition_statement)

        # Evaluar condición actual (sin hysteresis, evaluación cruda)
        current_condition_met = self._eval_function(evaluation_parameters)

        # Registrar condición con hysteresis en el engine (si es primera vez)
        if "main_condition" not in self._engine._conditions:
            # Crear ConditionWithHysteresis que encapsula la evaluación UQL
            condition = ConditionWithHysteresis(
                evaluate_activation=lambda params: self._eval_function(params),
                evaluate_deactivation=lambda params: not self._eval_function(params),
                hysteresis=hysteresis_default,
            )
            self._engine.register_condition("main_condition", condition)

        # Evaluar engine (aplica state machine + hysteresis + cooldown)
        result = self._engine.evaluate(
            params=evaluation_parameters,
            combine_with=combine_operator,
            cooldown_seconds=cooldown_seconds,
            message_template=alarm_message_template,
        )

        # Log cuando alarma dispara
        if result["alarm_active"]:
            logger.info(
                f"Conditional Alarm FIRED: {result['alarm_message']} "
                f"(count: {result['alarm_count']}, state: {result['state']})"
            )

        return {
            "alarm_active": result["alarm_active"],
            "alarm_message": result["alarm_message"],
            "state": result["state"],
            "alarm_count": result["alarm_count"],
        }
