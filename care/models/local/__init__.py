"""Local ONNX models package for inference without Roboflow API dependency."""

from care.models.local.base import LocalONNXModel
from care.models.local.detection import LocalONNXObjectDetection
from care.models.local.manifest import ModelManifest

__all__ = ["ModelManifest", "LocalONNXModel", "LocalONNXObjectDetection"]
