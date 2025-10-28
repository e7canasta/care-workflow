from typing import List, Optional

from care.entities.requests.dynamic_class_base import (
    DynamicClassBaseInferenceRequest,
)
from care.models.defaults import DEFAULT_CONFIDENCE


class YOLOWorldInferenceRequest(DynamicClassBaseInferenceRequest):
    """Request for Grounding DINO zero-shot predictions.

    Attributes:
        text (List[str]): A list of strings.
    """

    yolo_world_version_id: Optional[str] = "l"
    confidence: Optional[float] = DEFAULT_CONFIDENCE
