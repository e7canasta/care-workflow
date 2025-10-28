from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional, Type, Union

from pydantic import ConfigDict, Field

from inference.core.logger import logger
from inference.core.workflows.execution_engine.entities.base import OutputDefinition
from inference.core.workflows.execution_engine.entities.types import (
    BOOLEAN_KIND,
    INTEGER_KIND,
    STRING_KIND,
    Selector,
)
from inference.core.workflows.prototypes.block import (
    BlockResult,
    WorkflowBlock,
    WorkflowBlockManifest,
)

LONG_DESCRIPTION = """
Prediction Alarm block for intelligent alert triggering based on detection counts.

This block implements a state machine to control alarm firing with:
- Threshold-based activation
- Hysteresis to prevent flapping
- Cooldown period between repeated alarms
- Message templating with dynamic values

State Machine:
    IDLE → FIRING: count >= threshold AND cooldown elapsed
    FIRING → COOLDOWN: Alarm emitted, cooldown timer starts
    COOLDOWN → IDLE: count < (threshold - hysteresis) OR cooldown elapsed

Outputs:
    - alarm_active (bool): TRUE when alarm is firing
    - alarm_message (str): Formatted message (only when alarm_active=True)
    - count_value (int): Pass-through of the input count
    - state (str): Current state for debugging ("idle", "firing", "cooldown")
"""

SHORT_DESCRIPTION = "Monitor and trigger alarms based on detection counts."


class AlarmState(str, Enum):
    """States for the alarm state machine."""

    IDLE = "idle"
    FIRING = "firing"
    COOLDOWN = "cooldown"


class BlockManifest(WorkflowBlockManifest):
    model_config = ConfigDict(
        json_schema_extra={
            "name": "Prediction Alarm",
            "version": "v1",
            "short_description": SHORT_DESCRIPTION,
            "long_description": LONG_DESCRIPTION,
            "license": "Apache-2.0",
            "block_type": "transformation",
            "ui_manifest": {
                "section": "analytics",
                "icon": "far fa-bell",
                "blockPriority": 3,
            },
        }
    )
    type: Literal["care/prediction_alarm@v1"]
    count: Union[int, Selector(kind=[INTEGER_KIND])] = Field(
        description="Detection count to monitor (typically from detections_count block).",
        examples=[0, "$steps.count.count"],
    )
    threshold: Union[int, Selector(kind=[INTEGER_KIND])] = Field(
        description="Threshold value to trigger alarm. Alarm activates when count >= threshold.",
        examples=[1, 5, "$inputs.alarm_threshold"],
    )
    hysteresis: Union[int, Selector(kind=[INTEGER_KIND])] = Field(
        default=0,
        description="Hysteresis offset for deactivation. Alarm deactivates when count < (threshold - hysteresis).",
        examples=[0, 1, 2],
    )
    cooldown_seconds: Union[float, Selector(kind=[INTEGER_KIND])] = Field(
        default=5.0,
        description="Minimum seconds between alarm activations. Prevents alarm spam.",
        examples=[5.0, 10.0, 30.0],
    )
    alarm_message_template: Union[str, Selector(kind=[STRING_KIND])] = Field(
        default="Alert: {count} detection(s) (threshold: {threshold})",
        description="Message template with placeholders: {count}, {threshold}, {hysteresis}.",
        examples=[
            "Alert: {count} person(s) detected!",
            "Warning: {count} objects exceed threshold {threshold}",
        ],
    )

    @classmethod
    def describe_outputs(cls) -> List[OutputDefinition]:
        return [
            OutputDefinition(name="alarm_active", kind=[BOOLEAN_KIND]),
            OutputDefinition(name="alarm_message", kind=[STRING_KIND]),
            OutputDefinition(name="count_value", kind=[INTEGER_KIND]),
            OutputDefinition(name="state", kind=[STRING_KIND]),
        ]

    @classmethod
    def get_execution_engine_compatibility(cls) -> Optional[str]:
        return ">=1.3.0,<2.0.0"


class PredictionAlarmBlockV1(WorkflowBlock):
    """
    Prediction Alarm block implementing intelligent threshold-based alerting.

    Maintains internal state for cooldown timing and state machine tracking.
    """

    def __init__(self):
        super().__init__()
        self._current_state: AlarmState = AlarmState.IDLE
        self._last_alarm_at: Optional[datetime] = None
        self._alarm_count: int = 0

    @classmethod
    def get_manifest(cls) -> Type[WorkflowBlockManifest]:
        return BlockManifest

    def run(
        self,
        count: int,
        threshold: int,
        hysteresis: int = 0,
        cooldown_seconds: float = 5.0,
        alarm_message_template: str = "Alert: {count} detection(s) (threshold: {threshold})",
    ) -> BlockResult:
        """
        Execute alarm logic based on current count and state.

        Args:
            count: Current detection count
            threshold: Activation threshold
            hysteresis: Deactivation offset
            cooldown_seconds: Minimum time between alarms
            alarm_message_template: Message template with placeholders

        Returns:
            BlockResult with alarm_active, alarm_message, count_value, state
        """
        # Runtime validation
        if threshold <= 0:
            raise ValueError(f"threshold must be greater than 0, got {threshold}")
        if hysteresis < 0:
            raise ValueError(f"hysteresis must be >= 0, got {hysteresis}")
        if cooldown_seconds < 0:
            raise ValueError(f"cooldown_seconds must be >= 0, got {cooldown_seconds}")
        
        current_time = datetime.now()

        # Calculate thresholds
        activation_threshold = threshold
        deactivation_threshold = max(0, threshold - hysteresis)

        # Check if cooldown period has elapsed
        cooldown_elapsed = True
        if self._last_alarm_at is not None:
            time_since_last_alarm = (current_time - self._last_alarm_at).total_seconds()
            cooldown_elapsed = time_since_last_alarm >= cooldown_seconds

        # State machine logic
        alarm_active = False
        alarm_message = ""

        if self._current_state == AlarmState.IDLE:
            # Transition: IDLE → FIRING
            if count >= activation_threshold and cooldown_elapsed:
                self._current_state = AlarmState.FIRING
                self._last_alarm_at = current_time
                self._alarm_count += 1
                alarm_active = True
                alarm_message = alarm_message_template.format(
                    count=count, threshold=threshold, hysteresis=hysteresis
                )
                logger.info(
                    f"Alarm FIRED: count={count}, threshold={threshold}, "
                    f"alarm_count={self._alarm_count}"
                )

        elif self._current_state == AlarmState.FIRING:
            # Stay in FIRING state (alarm remains active)
            alarm_active = True
            alarm_message = alarm_message_template.format(
                count=count, threshold=threshold, hysteresis=hysteresis
            )

            # Transition: FIRING → COOLDOWN (after emitting alarm)
            self._current_state = AlarmState.COOLDOWN

        elif self._current_state == AlarmState.COOLDOWN:
            # Transition: COOLDOWN → IDLE
            if count < deactivation_threshold:
                self._current_state = AlarmState.IDLE
                logger.info(
                    f"Alarm RESET: count={count} < deactivation_threshold={deactivation_threshold}"
                )
            elif cooldown_elapsed:
                # Cooldown expired, check if we should fire again
                if count >= activation_threshold:
                    self._current_state = AlarmState.FIRING
                    self._last_alarm_at = current_time
                    self._alarm_count += 1
                    alarm_active = True
                    alarm_message = alarm_message_template.format(
                        count=count, threshold=threshold, hysteresis=hysteresis
                    )
                    logger.info(
                        f"Alarm RE-FIRED: count={count}, threshold={threshold}, "
                        f"alarm_count={self._alarm_count}"
                    )
                else:
                    self._current_state = AlarmState.IDLE

        return {
            "alarm_active": alarm_active,
            "alarm_message": alarm_message,
            "count_value": count,
            "state": self._current_state.value,
        }
