"""
Detections Count Block - Cuenta el número de detecciones.

Block simple que toma predicciones de detección y retorna el conteo.
"""

from typing import List, Literal, Optional, Type, Union

import supervision as sv
from pydantic import ConfigDict, Field

from inference.core.workflows.execution_engine.entities.base import (
    Batch,
    OutputDefinition,
)
from inference.core.workflows.execution_engine.entities.types import (
    INTEGER_KIND,
    INSTANCE_SEGMENTATION_PREDICTION_KIND,
    KEYPOINT_DETECTION_PREDICTION_KIND,
    OBJECT_DETECTION_PREDICTION_KIND,
    Selector,
)
from inference.core.workflows.prototypes.block import (
    BlockResult,
    WorkflowBlock,
    WorkflowBlockManifest,
)

LONG_DESCRIPTION = """
Cuenta el número de detecciones en las predicciones.

Este block toma como entrada predicciones de un modelo de detección
(object detection, instance segmentation, o keypoint detection) y
retorna el número total de detecciones encontradas.

Útil para:
- Alertas basadas en conteo (ej: más de N personas)
- Logging de métricas
- Triggers condicionales
- Mensajes MQTT con conteos
"""


class BlockManifest(WorkflowBlockManifest):
    model_config = ConfigDict(
        json_schema_extra={
            "name": "Detections Count",
            "version": "v1",
            "short_description": "Cuenta el número de detecciones.",
            "long_description": LONG_DESCRIPTION,
            "license": "Apache-2.0",
            "block_type": "transformation",
            "ui_manifest": {
                "section": "analytics",
                "icon": "far fa-hashtag",
            },
        }
    )
    type: Literal["care/detections_count@v1"]

    predictions: Selector(
        kind=[
            OBJECT_DETECTION_PREDICTION_KIND,
            INSTANCE_SEGMENTATION_PREDICTION_KIND,
            KEYPOINT_DETECTION_PREDICTION_KIND,
        ]
    ) = Field(
        description="Predicciones de detección para contar.",
        examples=["$steps.object_detection_model.predictions"],
    )

    @classmethod
    def describe_outputs(cls) -> List[OutputDefinition]:
        return [
            OutputDefinition(name="count", kind=[INTEGER_KIND]),
        ]

    @classmethod
    def get_execution_engine_compatibility(cls) -> Optional[str]:
        return ">=1.0.0,<2.0.0"


class DetectionsCountBlockV1(WorkflowBlock):
    """
    Block que cuenta detecciones.

    Implementación simple: len(detections)
    """

    @classmethod
    def get_manifest(cls) -> Type[WorkflowBlockManifest]:
        return BlockManifest

    def run(
        self,
        predictions: Union[sv.Detections, Batch[sv.Detections]],
    ) -> BlockResult:
        """
        Cuenta las detecciones.

        Args:
            predictions: sv.Detections o lista de sv.Detections

        Returns:
            {"count": int} - Número de detecciones
        """
        # Si es una lista (batch), contar todas
        if isinstance(predictions, list):
            total_count = sum(len(det) for det in predictions if det is not None)
            return {"count": total_count}

        # Si es un solo sv.Detections
        return {"count": len(predictions)}
