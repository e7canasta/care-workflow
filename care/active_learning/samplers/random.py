import random
from functools import partial
from typing import Any, Dict

import numpy as np

from care.active_learning.entities import (
    Prediction,
    PredictionType,
    SamplingMethod,
)
from care.exceptions import ActiveLearningConfigurationError


def initialize_random_sampling(strategy_config: Dict[str, Any]) -> SamplingMethod:
    try:
        sample_function = partial(
            sample_randomly,
            traffic_percentage=strategy_config["traffic_percentage"],
        )
        return SamplingMethod(
            name=strategy_config["name"],
            sample=sample_function,
        )
    except KeyError as error:
        raise ActiveLearningConfigurationError(
            f"In configuration of `random_sampling` missing key detected: {error}."
        ) from error


def sample_randomly(
    image: np.ndarray,
    prediction: Prediction,
    prediction_type: PredictionType,
    traffic_percentage: float,
) -> bool:
    return random.random() < traffic_percentage
