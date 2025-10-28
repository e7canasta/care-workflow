from typing import List

from care.camera.entities import VideoFrame
from care.stream.entities import ModelConfig
from care.stream.utils import wrap_in_list
from care.models.roboflow import OnnxRoboflowInferenceModel


def default_process_frame(
    video_frame: List[VideoFrame],
    model: OnnxRoboflowInferenceModel,
    inference_config: ModelConfig,
) -> List[dict]:
    postprocessing_args = inference_config.to_postprocessing_params()
    # TODO: handle batch input in usage
    fps = video_frame[0].fps
    if video_frame[0].measured_fps:
        fps = video_frame[0].measured_fps
    if not fps:
        fps = 0
    predictions = wrap_in_list(
        model.infer(
            [f.image for f in video_frame],
            usage_fps=fps,
            usage_api_key=model.api_key,
            **postprocessing_args,
        )
    )
    return [
        p.dict(
            by_alias=True,
            exclude_none=True,
        )
        for p in predictions
    ]
