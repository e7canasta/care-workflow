"""Local model registry for ONNX models without Roboflow API dependency.

This registry loads model manifests from a local directory and provides
model classes for inference without making API calls to Roboflow.
"""

from pathlib import Path
from typing import Dict, Optional, Type

from care.exceptions import ModelNotRecognisedError
from care.logger import logger
from care.models.base import Model
from care.models.local.manifest import ModelManifest
from care.registries.base import ModelRegistry


class LocalModelRegistry(ModelRegistry):
    """Registry for local ONNX models defined by manifest files.

    This registry scans a directory for JSON manifest files, loads and validates them,
    and provides model classes based on the task_type specified in each manifest.

    Architecture:
        - Manifests are loaded at initialization (fail-fast on invalid manifests)
        - model_id → ModelManifest mapping cached in memory
        - task_type determines which LocalONNX* class to instantiate
        - No API calls, no network dependency

    Directory Structure:
        models/local/
          yolov11/
            yolov11n-320-detection.json  ← Manifest
            yolov11n-320.onnx            ← Model weights
          yolov8/
            yolov8n-pose-320.json
            yolov8n-pose-320.onnx

    Attributes:
        models_dir: Root directory containing manifest files
        manifests: Dictionary mapping model_id to loaded ModelManifest instances
    """

    def __init__(self, models_dir: str = "models/local"):
        """Initialize registry and load all manifests from models_dir.

        Args:
            models_dir: Path to directory containing model manifests (absolute or relative)

        Raises:
            FileNotFoundError: If models_dir doesn't exist
            ValueError: If any manifest has invalid JSON or fails validation
        """
        super().__init__(registry_dict={})  # We don't use registry_dict pattern here
        self.models_dir = Path(models_dir)

        if not self.models_dir.exists():
            logger.warning(
                f"Local models directory does not exist: {self.models_dir}. "
                f"LocalModelRegistry will be empty."
            )
            self.manifests = {}
            return

        if not self.models_dir.is_dir():
            raise ValueError(
                f"models_dir must be a directory, got: {self.models_dir}"
            )

        self.manifests = self._load_manifests()
        logger.info(
            f"LocalModelRegistry initialized with {len(self.manifests)} models from {self.models_dir}"
        )

    def _load_manifests(self) -> Dict[str, ModelManifest]:
        """Scan models_dir recursively for .json manifests and load them.

        Returns:
            Dictionary mapping model_id to ModelManifest

        Raises:
            ValueError: If duplicate model_id found or manifest validation fails
        """
        manifests = {}
        manifest_paths = list(self.models_dir.rglob("*.json"))

        if not manifest_paths:
            logger.warning(
                f"No manifest files (.json) found in {self.models_dir}"
            )
            return manifests

        logger.debug(f"Found {len(manifest_paths)} potential manifest files")

        for manifest_path in manifest_paths:
            try:
                manifest = ModelManifest.from_json(manifest_path)

                # Check for duplicate model_id
                if manifest.model_id in manifests:
                    raise ValueError(
                        f"Duplicate model_id '{manifest.model_id}' found in:\n"
                        f"  - {manifests[manifest.model_id]}\n"
                        f"  - {manifest_path}\n"
                        f"Each model_id must be unique across all manifests."
                    )

                # Optionally validate model file exists (fail-fast)
                try:
                    manifest.validate_model_file_exists()
                except FileNotFoundError as e:
                    logger.warning(
                        f"Manifest {manifest_path} references missing model file: {e}. "
                        f"Model '{manifest.model_id}' will be registered but may fail at inference time."
                    )

                manifests[manifest.model_id] = manifest
                logger.debug(
                    f"Loaded manifest: {manifest.model_id} ({manifest.task_type}) from {manifest_path.name}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to load manifest from {manifest_path}: {e}. Skipping."
                )
                # Fail-fast: re-raise to prevent invalid manifests from loading silently
                raise

        return manifests

    def get_model(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        **kwargs,
    ) -> Type[Model]:
        """Get model class for the given model_id.

        Args:
            model_id: Model identifier (must match a manifest's model_id field)
            api_key: Ignored for local models (kept for interface compatibility)
            **kwargs: Additional arguments (ignored)

        Returns:
            Model class corresponding to the manifest's task_type

        Raises:
            ModelNotRecognisedError: If model_id not found or task_type not supported
        """
        if model_id not in self.manifests:
            raise ModelNotRecognisedError(
                f"Local model '{model_id}' not found. "
                f"Available models: {list(self.manifests.keys())}"
            )

        manifest = self.manifests[model_id]
        logger.debug(
            f"Resolving model_id '{model_id}' → task_type '{manifest.task_type}'"
        )

        return self._get_model_class_for_task(manifest.task_type)

    def _get_model_class_for_task(self, task_type: str) -> Type[Model]:
        """Map task_type to corresponding LocalONNX* model class.

        Args:
            task_type: Task type from manifest (e.g., "object-detection")

        Returns:
            Model class for this task type

        Raises:
            ModelNotRecognisedError: If task_type not supported
        """
        # Import here to avoid circular dependencies and lazy load
        from care.models.local.detection import LocalONNXObjectDetection

        # Mapping task_type → model class
        # NOTE: Placeholder imports for future task types (will be implemented in Fase 4)
        task_mapping: Dict[str, Type[Model]] = {
            "object-detection": LocalONNXObjectDetection,
            # "pose-estimation": LocalONNXPoseEstimation,  # TODO: Fase 4
            # "instance-segmentation": LocalONNXInstanceSegmentation,  # TODO: Fase 4
            # "classification": LocalONNXClassification,  # TODO: Fase 4
        }

        if task_type not in task_mapping:
            raise ModelNotRecognisedError(
                f"Task type '{task_type}' not supported by LocalModelRegistry. "
                f"Supported types: {list(task_mapping.keys())}"
            )

        return task_mapping[task_type]

    def list_models(self) -> Dict[str, Dict[str, str]]:
        """Return summary of all registered local models.

        Returns:
            Dictionary mapping model_id to metadata (task_type, model_path, input_size)
        """
        return {
            model_id: {
                "task_type": manifest.task_type,
                "model_path": manifest.model_path,
                "input_size": str(manifest.input_size),
                "num_classes": len(manifest.class_names),
            }
            for model_id, manifest in self.manifests.items()
        }
