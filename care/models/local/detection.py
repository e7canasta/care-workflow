"""Local ONNX Object Detection model for YOLOv8/v11 inference.

This module implements object detection using local ONNX models (YOLOv8, YOLOv11)
without Roboflow API dependency. Outputs are compatible with supervision.Detections
format expected by workflow blocks.
"""

from typing import Any, List, Optional, Tuple

import numpy as np

try:
    import supervision as sv
except ImportError:
    sv = None

from care.logger import logger
from care.models.local.base import LocalONNXModel


class LocalONNXObjectDetection(LocalONNXModel):
    """ONNX-based object detection model for YOLOv8/v11.

    This class implements:
    - YOLOv8/v11 output parsing (detection format: x, y, w, h, conf, class_scores...)
    - Non-Maximum Suppression (NMS)
    - Conversion to supervision.Detections format
    - Coordinate rescaling to original image dimensions

    YOLOv8/v11 ONNX Output Format:
        - Shape: (batch_size, 84 + num_classes, num_anchors)
        - First 4 channels: bounding box coords (x_center, y_center, width, height)
        - Next 80 channels: class scores (for COCO)
        - Note: Some models use (batch_size, num_anchors, 84 + num_classes)

    Workflow Compatibility:
        - Input: Image as numpy array or workflow image object
        - Output: supervision.Detections object with:
            - xyxy: Bounding boxes in (x1, y1, x2, y2) format
            - confidence: Detection confidences
            - class_id: Class IDs
            - data: Additional data dict with class_name

    Architecture:
        1. preprocess_image() → letterbox + normalize
        2. predict() → ONNX inference
        3. postprocess() → parse YOLO output, NMS, rescale coords
        4. infer() → full pipeline returning supervision.Detections
    """

    task_type = "object-detection"

    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        """Initialize LocalONNXObjectDetection.

        Args:
            model_id: Model identifier from manifest
            api_key: Ignored (kept for interface compatibility)
            **kwargs: Additional arguments
        """
        super().__init__(model_id=model_id, api_key=api_key, **kwargs)

        if sv is None:
            raise ImportError(
                "supervision package is required for LocalONNXObjectDetection. "
                "Install with: pip install supervision"
            )

    def infer(
        self,
        image: np.ndarray,
        confidence: float = 0.5,
        iou_threshold: float = 0.45,
        class_agnostic_nms: bool = False,
        **kwargs,
    ) -> sv.Detections:
        """Run object detection inference on an image.

        Args:
            image: Input image as BGR numpy array (H, W, C)
            confidence: Confidence threshold for detections (default: 0.5)
            iou_threshold: IoU threshold for NMS (default: 0.45)
            class_agnostic_nms: Whether to perform class-agnostic NMS (default: False)
            **kwargs: Additional arguments (ignored)

        Returns:
            supervision.Detections object with detections

        Raises:
            RuntimeError: If inference fails
        """
        # 1. Preprocess image
        preprocessed, metadata = self.preprocess_image(image, self.input_size)

        # 2. ONNX inference
        outputs = self.predict(preprocessed)

        # 3. Postprocess outputs
        detections = self.postprocess(
            outputs,
            metadata,
            confidence=confidence,
            iou_threshold=iou_threshold,
            class_agnostic_nms=class_agnostic_nms,
        )

        return detections

    def postprocess(
        self,
        outputs: List[np.ndarray],
        metadata: dict,
        confidence: float = 0.5,
        iou_threshold: float = 0.45,
        class_agnostic_nms: bool = False,
    ) -> sv.Detections:
        """Postprocess YOLO outputs into supervision.Detections.

        Args:
            outputs: Raw ONNX output tensors [output_tensor]
            metadata: Preprocessing metadata (scale, pad, original_shape)
            confidence: Confidence threshold
            iou_threshold: IoU threshold for NMS
            class_agnostic_nms: Whether to perform class-agnostic NMS

        Returns:
            supervision.Detections object
        """
        # Extract output tensor (YOLOv8/v11 has single output)
        output = outputs[0]  # Shape: (batch_size, 84+num_classes, num_anchors) or (batch_size, num_anchors, 84+num_classes)

        # Handle different output shapes
        if len(output.shape) == 3:
            # Check which format: (batch, features, anchors) or (batch, anchors, features)
            if output.shape[1] > output.shape[2]:
                # Format: (batch, anchors, features) - transpose to (batch, features, anchors)
                output = np.transpose(output, (0, 2, 1))

        # Process batch (we only handle single image for now)
        batch_idx = 0
        predictions = output[batch_idx]  # Shape: (84+num_classes, num_anchors)

        # Parse predictions
        boxes, scores, class_ids = self._parse_yolo_output(
            predictions, confidence_threshold=confidence
        )

        if len(boxes) == 0:
            # No detections above confidence threshold
            return sv.Detections.empty()

        # Apply NMS
        keep_indices = self._non_max_suppression(
            boxes, scores, class_ids, iou_threshold, class_agnostic_nms
        )

        boxes = boxes[keep_indices]
        scores = scores[keep_indices]
        class_ids = class_ids[keep_indices]

        # Rescale boxes to original image coordinates
        boxes = self._rescale_boxes(boxes, metadata)

        # Convert to supervision.Detections format
        detections = sv.Detections(
            xyxy=boxes,
            confidence=scores,
            class_id=class_ids,
        )

        # Add class names to data dict
        detections.data = {
            "class_name": np.array([self.class_names[int(cid)] for cid in class_ids])
        }

        return detections

    def _parse_yolo_output(
        self, predictions: np.ndarray, confidence_threshold: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Parse YOLO output tensor into boxes, scores, and class IDs.

        YOLOv8/v11 format:
        - predictions shape: (84+num_classes, num_anchors)
        - First 4 rows: x_center, y_center, width, height
        - Remaining rows: class scores

        Args:
            predictions: YOLO output (features, num_anchors)
            confidence_threshold: Minimum confidence to keep detection

        Returns:
            Tuple of:
            - boxes: (N, 4) array of [x1, y1, x2, y2] in input image coords
            - scores: (N,) array of confidence scores
            - class_ids: (N,) array of class IDs
        """
        # Extract box coordinates (first 4 rows)
        box_coords = predictions[:4, :]  # (4, num_anchors)

        # Extract class scores (remaining rows)
        class_scores = predictions[4:, :]  # (num_classes, num_anchors)

        # Get best class score and ID for each anchor
        max_scores = np.max(class_scores, axis=0)  # (num_anchors,)
        class_ids = np.argmax(class_scores, axis=0)  # (num_anchors,)

        # Filter by confidence threshold
        mask = max_scores >= confidence_threshold
        filtered_boxes = box_coords[:, mask]  # (4, N)
        filtered_scores = max_scores[mask]  # (N,)
        filtered_class_ids = class_ids[mask]  # (N,)

        if filtered_boxes.shape[1] == 0:
            # No detections above threshold
            return (
                np.empty((0, 4), dtype=np.float32),
                np.empty((0,), dtype=np.float32),
                np.empty((0,), dtype=np.int32),
            )

        # Convert from (x_center, y_center, w, h) to (x1, y1, x2, y2)
        x_center = filtered_boxes[0, :]
        y_center = filtered_boxes[1, :]
        width = filtered_boxes[2, :]
        height = filtered_boxes[3, :]

        x1 = x_center - width / 2
        y1 = y_center - height / 2
        x2 = x_center + width / 2
        y2 = y_center + height / 2

        boxes = np.stack([x1, y1, x2, y2], axis=1)  # (N, 4)

        return boxes, filtered_scores, filtered_class_ids

    def _non_max_suppression(
        self,
        boxes: np.ndarray,
        scores: np.ndarray,
        class_ids: np.ndarray,
        iou_threshold: float,
        class_agnostic: bool = False,
    ) -> np.ndarray:
        """Apply Non-Maximum Suppression to remove overlapping boxes.

        Args:
            boxes: (N, 4) array of [x1, y1, x2, y2]
            scores: (N,) array of confidence scores
            class_ids: (N,) array of class IDs
            iou_threshold: IoU threshold for NMS
            class_agnostic: If True, ignore class when computing NMS

        Returns:
            Array of indices to keep
        """
        if len(boxes) == 0:
            return np.array([], dtype=np.int32)

        # Sort by confidence (descending)
        sorted_indices = np.argsort(scores)[::-1]

        keep = []

        if class_agnostic:
            # Class-agnostic NMS (simpler)
            keep = self._nms_single_class(
                boxes[sorted_indices], scores[sorted_indices], iou_threshold
            )
            return sorted_indices[keep]
        else:
            # Per-class NMS
            unique_classes = np.unique(class_ids)
            for class_id in unique_classes:
                # Get indices for this class
                class_mask = class_ids == class_id
                class_indices = np.where(class_mask)[0]

                if len(class_indices) == 0:
                    continue

                # Apply NMS to this class
                class_boxes = boxes[class_indices]
                class_scores = scores[class_indices]

                # Sort by score within class
                class_sorted = np.argsort(class_scores)[::-1]
                class_keep = self._nms_single_class(
                    class_boxes[class_sorted],
                    class_scores[class_sorted],
                    iou_threshold,
                )

                # Map back to original indices
                keep.extend(class_indices[class_sorted[class_keep]])

            return np.array(keep, dtype=np.int32)

    def _nms_single_class(
        self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float
    ) -> List[int]:
        """NMS for a single class (or class-agnostic).

        Args:
            boxes: (N, 4) sorted by score descending
            scores: (N,) sorted descending
            iou_threshold: IoU threshold

        Returns:
            List of indices to keep
        """
        keep = []

        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

        for i in range(len(boxes)):
            if i in keep:
                continue

            # Check IoU with all previously kept boxes
            should_keep = True
            for j in keep:
                iou = self._compute_iou(boxes[i], boxes[j], areas[i], areas[j])
                if iou > iou_threshold:
                    should_keep = False
                    break

            if should_keep:
                keep.append(i)

        return keep

    def _compute_iou(
        self, box1: np.ndarray, box2: np.ndarray, area1: float, area2: float
    ) -> float:
        """Compute IoU between two boxes.

        Args:
            box1: [x1, y1, x2, y2]
            box2: [x1, y1, x2, y2]
            area1: Precomputed area of box1
            area2: Precomputed area of box2

        Returns:
            IoU value
        """
        # Intersection coordinates
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        # Intersection area
        intersection = max(0, x2 - x1) * max(0, y2 - y1)

        # Union area
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _rescale_boxes(self, boxes: np.ndarray, metadata: dict) -> np.ndarray:
        """Rescale boxes from input image coordinates to original image coordinates.

        Reverses the letterbox transformation applied during preprocessing.

        Args:
            boxes: (N, 4) array of [x1, y1, x2, y2] in input image coords
            metadata: Preprocessing metadata (scale, pad, original_shape)

        Returns:
            Rescaled boxes in original image coordinates
        """
        scale = metadata["scale"]
        pad_h, pad_w = metadata["pad"]
        original_h, original_w = metadata["original_shape"]

        # Remove padding
        boxes[:, [0, 2]] -= pad_w  # x coordinates
        boxes[:, [1, 3]] -= pad_h  # y coordinates

        # Rescale to original size
        boxes /= scale

        # Clip to image bounds
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, original_w)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, original_h)

        return boxes

    def infer_from_request(self, request: Any) -> sv.Detections:
        """Inference entry point compatible with workflow execution engine.

        The workflow engine may pass different request types. We extract
        the image and parameters, then call infer().

        Args:
            request: Inference request (may have .image, .confidence, etc.)

        Returns:
            supervision.Detections object

        Raises:
            ValueError: If request is invalid
        """
        # Extract image from request
        if hasattr(request, "image"):
            image = request.image
        elif isinstance(request, np.ndarray):
            image = request
        else:
            raise ValueError(
                f"Invalid request type: {type(request)}. Expected object with .image or numpy array."
            )

        # Handle image loading if it's not already a numpy array
        if not isinstance(image, np.ndarray):
            # Try to load image (may be PIL, path, etc.)
            try:
                from care.utils.image import load_image_rgb

                image = load_image_rgb(image)
                # Convert RGB to BGR for OpenCV
                import cv2

                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            except Exception as e:
                raise ValueError(f"Failed to load image from request: {e}")

        # Extract parameters from request
        confidence = getattr(request, "confidence", 0.5)
        iou_threshold = getattr(request, "iou_threshold", 0.45)
        class_agnostic_nms = getattr(request, "class_agnostic_nms", False)

        # Run inference
        detections = self.infer(
            image=image,
            confidence=confidence,
            iou_threshold=iou_threshold,
            class_agnostic_nms=class_agnostic_nms,
        )

        return detections
