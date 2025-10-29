"""Composite model registry implementing Chain of Responsibility pattern.

This registry tries multiple registries in sequence until one successfully
resolves the model. This enables fallback from local models to Roboflow models
without changing workflow definitions.
"""

from typing import List, Optional, Type

from care.exceptions import ModelNotRecognisedError
from care.logger import logger
from care.models.base import Model
from care.registries.base import ModelRegistry


class CompositeModelRegistry(ModelRegistry):
    """Composite registry that delegates to multiple registries with fallback.

    Architecture: Chain of Responsibility Pattern
        1. Tries each registry in order (registries list)
        2. First registry to successfully return a model wins
        3. If all registries fail, raises ModelNotRecognisedError

    Use Case:
        - Try LocalModelRegistry first (no API call, faster)
        - Fallback to RoboflowModelRegistry if local model not found
        - Extensible: add HuggingFaceModelRegistry, OllamaRegistry, etc.

    Example:
        >>> local_registry = LocalModelRegistry(models_dir="models/local")
        >>> roboflow_registry = RoboflowModelRegistry(ROBOFLOW_MODEL_TYPES)
        >>> composite = CompositeModelRegistry([local_registry, roboflow_registry])
        >>>
        >>> # Will try local first, then Roboflow
        >>> model_class = composite.get_model(model_id="yolov11n-320", api_key="...")

    Attributes:
        registries: Ordered list of registries to try (priority order)
    """

    def __init__(self, registries: List[ModelRegistry]):
        """Initialize composite registry with ordered list of registries.

        Args:
            registries: List of ModelRegistry instances to try in order.
                       First registry has highest priority.

        Raises:
            ValueError: If registries list is empty
        """
        super().__init__(registry_dict={})  # We don't use registry_dict pattern here

        if not registries:
            raise ValueError(
                "CompositeModelRegistry requires at least one registry"
            )

        self.registries = registries
        logger.info(
            f"CompositeModelRegistry initialized with {len(registries)} registries: "
            f"{[r.__class__.__name__ for r in registries]}"
        )

    def get_model(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        **kwargs,
    ) -> Type[Model]:
        """Try to get model from registries in order until one succeeds.

        Args:
            model_id: Model identifier to resolve
            api_key: API key (may be required by some registries like Roboflow)
            **kwargs: Additional arguments passed to registry.get_model()

        Returns:
            Model class from first registry that successfully resolves model_id

        Raises:
            ModelNotRecognisedError: If no registry can resolve the model_id
        """
        errors = []

        for registry in self.registries:
            registry_name = registry.__class__.__name__
            try:
                logger.debug(
                    f"Trying {registry_name}.get_model(model_id='{model_id}')"
                )
                model_class = registry.get_model(
                    model_id=model_id, api_key=api_key, **kwargs
                )
                logger.info(
                    f"✓ {registry_name} resolved model_id '{model_id}' → {model_class.__name__}"
                )
                return model_class

            except ModelNotRecognisedError as e:
                logger.debug(
                    f"✗ {registry_name} could not resolve '{model_id}': {e}"
                )
                errors.append(f"{registry_name}: {e}")
                continue  # Try next registry

            except Exception as e:
                # Unexpected error - log but continue to next registry
                logger.warning(
                    f"✗ {registry_name} raised unexpected error for '{model_id}': {e}"
                )
                errors.append(f"{registry_name}: {type(e).__name__}: {e}")
                continue

        # All registries failed
        error_details = "\n  ".join(errors)
        raise ModelNotRecognisedError(
            f"Model '{model_id}' not found in any registry.\n"
            f"Tried {len(self.registries)} registries:\n  {error_details}"
        )

    def list_registries(self) -> List[str]:
        """Return list of registry class names in priority order.

        Returns:
            List of registry class names
        """
        return [r.__class__.__name__ for r in self.registries]
