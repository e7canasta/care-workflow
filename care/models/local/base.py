"""Base class for local ONNX models without Roboflow API dependency.

This module provides common preprocessing, ONNX session management, and utilities
for local model inference.
"""

from pathlib import Path
from typing import Any, List, Optional, Tuple

import cv2
import numpy as np
import onnxruntime as ort

from care.logger import logger
from care.models.base import Model
from care.models.local.manifest import ModelManifest
from care.registries.local import LocalModelRegistry


class LocalONNXModel(Model):
    """Base class for ONNX models loaded from local manifests.

    This class handles:
    - Loading manifest and model metadata
    - ONNX session initialization (CPU/CUDA)
    - Common preprocessing (letterbox, normalization)
    - Error handling

    Subclasses implement:
    - Task-specific postprocessing
    - Task-specific response formatting

    Architecture:
        1. __init__ loads manifest and creates ONNX session
        2. infer_from_request() is main entry point (interface compatibility)
        3. preprocess() → predict() → postprocess() pipeline
        4. Subclasses override postprocess() and response formatting

    Attributes:
        model_id: Model identifier from manifest
        manifest: Loaded ModelManifest instance
        session: ONNX Runtime InferenceSession
        class_names: List of class labels
        input_size: Tuple of (height, width)
        input_name: Name of ONNX input tensor
        output_names: Names of ONNX output tensors
    """

    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        """Initialize local ONNX model from manifest.

        Args:
            model_id: Model identifier (must exist in LocalModelRegistry)
            api_key: Ignored (kept for interface compatibility with Roboflow models)
            **kwargs: Additional arguments (ignored)

        Raises:
            FileNotFoundError: If manifest or ONNX file not found
            ValueError: If model_id not in registry
        """
        super().__init__()
        self.model_id = model_id

        # Load manifest from LocalModelRegistry
        self.manifest = self._load_manifest(model_id)

        # Extract manifest data
        self.class_names = self.manifest.class_names
        self.input_size = tuple(self.manifest.input_size)  # (height, width)
        self.model_path = self.manifest.model_path

        # Validate model file exists
        self.manifest.validate_model_file_exists()

        # Initialize ONNX session
        self.session = self._create_onnx_session(self.model_path)

        # Get input/output names from ONNX model
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]

        logger.info(
            f"LocalONNXModel initialized: {model_id} "
            f"(input_size={self.input_size}, "
            f"num_classes={len(self.class_names)}, "
            f"providers={self.session.get_providers()})"
        )

    def _load_manifest(self, model_id: str) -> ModelManifest:
        """Load manifest for the given model_id.

        This creates a temporary LocalModelRegistry to load the manifest.
        Ideally, the manifest would be passed directly, but for now we
        re-load it to keep initialization simple.

        Args:
            model_id: Model identifier

        Returns:
            Loaded ModelManifest

        Raises:
            ValueError: If model_id not found
        """
        from care.env import LOCAL_MODELS_DIR

        registry = LocalModelRegistry(models_dir=LOCAL_MODELS_DIR)

        if model_id not in registry.manifests:
            raise ValueError(
                f"Model '{model_id}' not found in LocalModelRegistry. "
                f"Available models: {list(registry.manifests.keys())}"
            )

        return registry.manifests[model_id]

    def _create_onnx_session(self, model_path: str) -> ort.InferenceSession:
        """Create ONNX Runtime session with GPU support if available.

        Tries providers in order:
        1. CUDAExecutionProvider (NVIDIA GPU)
        2. CPUExecutionProvider (fallback)

        Args:
            model_path: Path to .onnx model file

        Returns:
            ONNX InferenceSession

        Raises:
            RuntimeError: If model loading fails
        """
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        try:
            session = ort.InferenceSession(model_path, providers=providers)
            logger.info(
                f"ONNX session created with providers: {session.get_providers()}"
            )
            return session
        except Exception as e:
            raise RuntimeError(f"Failed to load ONNX model from {model_path}: {e}")

    def preprocess_image(
        self, image: np.ndarray, target_size: Tuple[int, int]
    ) -> Tuple[np.ndarray, dict]:
        """Preprocess image for ONNX inference.

        Applies letterbox resize and normalization:
        1. Letterbox resize to target_size (preserves aspect ratio)
        2. Convert BGR → RGB
        3. Normalize to [0, 1]
        4. Transpose to CHW format
        5. Add batch dimension

        Args:
            image: Input image as BGR numpy array (H, W, C)
            target_size: Target size as (height, width)

        Returns:
            Tuple of:
            - preprocessed: Preprocessed image ready for ONNX (1, C, H, W), float32
            - metadata: Dict with preprocessing metadata (scale, pad, original_shape)
        """
        original_shape = image.shape[:2]  # (H, W)

        # Letterbox resize (preserves aspect ratio, adds padding)
        resized, scale, pad = self._letterbox_resize(image, target_size)

        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Normalize to [0, 1]
        normalized = rgb.astype(np.float32) / 255.0

        # Transpose HWC → CHW
        transposed = np.transpose(normalized, (2, 0, 1))

        # Add batch dimension: CHW → NCHW
        batched = np.expand_dims(transposed, axis=0)

        metadata = {
            "original_shape": original_shape,
            "scale": scale,
            "pad": pad,
            "target_size": target_size,
        }

        return batched, metadata

    def _letterbox_resize(
        self, image: np.ndarray, target_size: Tuple[int, int]
    ) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Resize image with letterbox (maintain aspect ratio, pad).

        Args:
            image: Input image (H, W, C)
            target_size: Target size (height, width)

        Returns:
            Tuple of:
            - resized: Letterboxed image (target_height, target_width, C)
            - scale: Scale factor applied
            - pad: Padding added as (pad_top, pad_left)
        """
        target_h, target_w = target_size
        img_h, img_w = image.shape[:2]

        # Compute scale to fit image into target size
        scale = min(target_w / img_w, target_h / img_h)

        # Compute new dimensions
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)

        # Resize image
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Compute padding to center image
        pad_w = (target_w - new_w) // 2
        pad_h = (target_h - new_h) // 2

        # Create canvas and paste resized image
        canvas = np.full((target_h, target_w, 3), 114, dtype=np.uint8)  # Gray padding
        canvas[pad_h : pad_h + new_h, pad_w : pad_w + new_w] = resized

        return canvas, scale, (pad_h, pad_w)

    def predict(self, preprocessed_image: np.ndarray) -> List[np.ndarray]:
        """Run ONNX inference on preprocessed image.

        Args:
            preprocessed_image: Preprocessed image (1, C, H, W), float32

        Returns:
            List of output tensors from ONNX model

        Raises:
            RuntimeError: If inference fails
        """
        try:
            outputs = self.session.run(
                self.output_names, {self.input_name: preprocessed_image}
            )
            return outputs
        except Exception as e:
            raise RuntimeError(f"ONNX inference failed: {e}")

    def postprocess(self, outputs: List[np.ndarray], metadata: dict, **kwargs) -> Any:
        """Postprocess ONNX outputs (task-specific, implemented by subclasses).

        Args:
            outputs: Raw ONNX output tensors
            metadata: Preprocessing metadata (scale, pad, original_shape)
            **kwargs: Additional postprocessing parameters

        Returns:
            Task-specific result (e.g., supervision.Detections for object detection)

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.postprocess() must be implemented by subclass"
        )

    def infer_from_request(self, request) -> Any:
        """Main inference entry point (interface compatible with Roboflow models).

        This method provides compatibility with the workflow execution engine,
        which expects models to have an `infer_from_request(request)` method.

        Args:
            request: Inference request object (task-specific, e.g., ObjectDetectionInferenceRequest)

        Returns:
            Inference response object (task-specific, e.g., ObjectDetectionInferenceResponse)

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.infer_from_request() must be implemented by subclass"
        )
