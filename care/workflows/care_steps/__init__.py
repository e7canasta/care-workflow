"""
Care Workflow Custom Blocks Plugin.

This module provides custom workflow blocks for Roboflow Inference workflows.
To use these blocks, set the WORKFLOWS_PLUGINS environment variable:

    export WORKFLOWS_PLUGINS="care.workflows.care_steps"

"""
from typing import List, Type

from care.workflows.care_steps.prototypes.block import WorkflowBlock
from care.workflows.care_steps.sinks import MQTTWriterSinkBlockV1
from care.workflows.care_steps.transformations import (
    DetectionsCountBlockV1,
    PredictionAlarmBlockV1,
    ConditionalAlarmBlockV1,
)


def load_blocks() -> List[Type[WorkflowBlock]]:
    """
    Load all custom Care Workflow blocks.

    This function is called by Roboflow Inference's plugin system to discover
    and register custom blocks.

    Returns:
        List of WorkflowBlock classes to be registered.
    """
    return [
        # Sinks
        MQTTWriterSinkBlockV1,

        # Transformations
        DetectionsCountBlockV1,
        PredictionAlarmBlockV1,
        ConditionalAlarmBlockV1,

        # Agregar otros blocks aquí cuando los implementes:
        # PLCModbusSinkBlockV1,
        # PLCEthernetIPSinkBlockV1,
        # etc.
    ]


__all__ = [
    "load_blocks",
    "MQTTWriterSinkBlockV1",
    "DetectionsCountBlockV1",
    "PredictionAlarmBlockV1",
    "ConditionalAlarmBlockV1",
]
