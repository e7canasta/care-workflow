from typing import List, Optional

from care.entities.requests.dynamic_class_base import (
    DynamicClassBaseInferenceRequest,
)
from care.env import CLASS_AGNOSTIC_NMS


class GroundingDINOInferenceRequest(DynamicClassBaseInferenceRequest):
    """Request for Grounding DINO zero-shot predictions.

    Attributes:
        text (List[str]): A list of strings.
    """

    box_threshold: Optional[float] = 0.5
    grounding_dino_version_id: Optional[str] = "default"
    text_threshold: Optional[float] = 0.5
    class_agnostic_nms: Optional[bool] = CLASS_AGNOSTIC_NMS
