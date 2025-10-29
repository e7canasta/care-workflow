"""Model manifest schema for local ONNX models.

This module defines the structure and validation for local model manifests,
which describe ONNX models that can be loaded without Roboflow API calls.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ModelManifest(BaseModel):
    """Schema for local ONNX model manifest files.

    A manifest describes a local ONNX model and provides all metadata needed
    for inference without API calls. Manifests are JSON files stored alongside
    model weights.

    Attributes:
        model_id: Unique identifier used in workflow JSON (e.g., "yolov11n-320")
        task_type: Type of task this model performs. Determines which LocalONNX* class to use.
        model_path: Path to the .onnx model file (absolute or relative to manifest)
        class_names: List of class labels for model outputs (e.g., COCO classes)
        input_size: Model input dimensions as [height, width]
        metadata: Optional additional information (quantization type, source, etc.)

    Example manifest JSON:
        {
          "model_id": "yolov11n-320",
          "task_type": "object-detection",
          "model_path": "models/local/yolov11/yolov11n-320.onnx",
          "class_names": ["person", "car", "dog", ...],
          "input_size": [320, 320],
          "metadata": {
            "quantization": "int8",
            "source": "https://github.com/ultralytics/...",
            "converted_with": "ultralytics export format=onnx imgsz=320 int8=True"
          }
        }
    """

    model_id: str = Field(
        ...,
        description="Unique identifier for this model, used in workflow JSON model_id field",
        min_length=1,
    )

    task_type: Literal[
        "object-detection",
        "pose-estimation",
        "instance-segmentation",
        "classification",
    ] = Field(
        ...,
        description="Task type determines which LocalONNX* model class will handle inference",
    )

    model_path: str = Field(
        ...,
        description="Path to .onnx model file (absolute or relative to manifest location)",
        min_length=1,
    )

    class_names: List[str] = Field(
        ...,
        description="Ordered list of class labels corresponding to model outputs",
        min_length=1,
    )

    input_size: List[int] = Field(
        ...,
        description="Model input dimensions as [height, width]",
        min_length=2,
        max_length=2,
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional metadata (quantization, source URL, conversion details, etc.)",
    )

    @field_validator("input_size")
    @classmethod
    def validate_input_size(cls, v: List[int]) -> List[int]:
        """Ensure input_size contains exactly 2 positive integers."""
        if len(v) != 2:
            raise ValueError("input_size must contain exactly 2 elements [height, width]")
        if any(dim <= 0 for dim in v):
            raise ValueError("input_size dimensions must be positive integers")
        return v

    @field_validator("model_path")
    @classmethod
    def validate_model_path_extension(cls, v: str) -> str:
        """Ensure model_path points to an .onnx file."""
        if not v.endswith(".onnx"):
            raise ValueError(f"model_path must point to an .onnx file, got: {v}")
        return v

    @classmethod
    def from_json(cls, manifest_path: Path) -> "ModelManifest":
        """Load and validate a manifest from a JSON file.

        Args:
            manifest_path: Path to the manifest JSON file

        Returns:
            Validated ModelManifest instance

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            ValueError: If JSON is malformed or validation fails
            pydantic.ValidationError: If manifest doesn't match schema
        """
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in manifest {manifest_path}: {e}")

        # If model_path is relative, resolve it relative to manifest location
        manifest = cls(**data)
        if not Path(manifest.model_path).is_absolute():
            manifest.model_path = str(
                (manifest_path.parent / manifest.model_path).resolve()
            )

        return manifest

    def validate_model_file_exists(self) -> None:
        """Check if the model file specified in model_path exists.

        This is separate from Pydantic validation to support cases where
        manifests are created before model files are downloaded.

        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        model_file = Path(self.model_path)
        if not model_file.exists():
            raise FileNotFoundError(
                f"Model file not found: {self.model_path} (referenced by model_id: {self.model_id})"
            )
