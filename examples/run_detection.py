import json
import os

from threading import Thread
from typing import List, Optional, Union


import cv2
import supervision as sv
from inference.core.utils.drawing import create_tiles


# from care import InferencePipeline
from care.stream.inference_pipeline import InferencePipeline
from care.camera.entities import VideoFrame


from care.stream.watchdog import (
    BasePipelineWatchDog,
    PipelineWatchDog
)


STOP = False
ANNOTATOR = sv.BoxAnnotator()
fps_monitor = sv.FPSMonitor()

# Load workflow definition from JSON file
with open(os.environ["WORKFLOW_DEFINITION"], 'r') as f:
    workflow_definition = json.load(f)

# Update class filter from environment variable if provided
if "DETECTION_CLASSES" in os.environ:
    classes = [cls.strip() for cls in os.environ["DETECTION_CLASSES"].split(",")]
    # Find the ObjectDetectionModel step and update its class_filter
    for step in workflow_definition.get("steps", []):
        if step.get("type") == "ObjectDetectionModel":
            step["class_filter"] = classes
            break

# Update model_id from environment variable if provided
if "MODEL_ID" in os.environ:
    model_id = os.environ["MODEL_ID"]
    # Find the ObjectDetectionModel step and update its model_id
    for step in workflow_definition.get("steps", []):
        if step.get("type") == "ObjectDetectionModel":
            step["model_id"] = model_id
            break

def main() -> None:
    global STOP
    watchdog = BasePipelineWatchDog()
    pipeline = InferencePipeline.init_with_workflow(
        video_reference=[os.environ["VIDEO_REFERENCE"]],
        workflow_specification=workflow_definition,
        watchdog=watchdog,
        on_prediction=workflows_sink,
        max_fps= int(os.environ["MAX_FPS"])
    )
    control_thread = Thread(
        target=command_thread,
        args=(pipeline, watchdog)
    )
    control_thread.start()
    pipeline.start()
    STOP = True
    pipeline.join()
    pass



def command_thread(pipeline: InferencePipeline, watchdog: PipelineWatchDog) -> None:
    global STOP
    while not STOP:
        key = input()
        if key == "i":
            print(watchdog.get_report())
        if key == "t":
            pipeline.terminate()
            STOP = True
        if key == "p":
            pipeline.pause_stream()
        if key == "m":
            pipeline.mute_stream()
        elif key == "r":
            pipeline.resume_stream()


def workflows_sink(
    predictions: Union[Optional[dict], List[Optional[dict]]],
    video_frames: Union[Optional[VideoFrame], List[Optional[VideoFrame]]],
) -> None:
    fps_monitor.tick()
    if not isinstance(predictions, list):
        predictions = [predictions]

    images_to_show = []
    crops_grid_images = []
    
    for prediction in predictions:
        if prediction is None:
            continue
        
        # Show main visualization
        if "visualization" in prediction:
            images_to_show.append(prediction["visualization"].numpy_image)
        
        # Check if crops_grid exists and collect them
        if "crops_grid" in prediction and prediction["crops_grid"] is not None:
            crops_grid_images.append(prediction["crops_grid"].numpy_image)
    
    # Display main predictions window
    if images_to_show:
        tiles = create_tiles(images=images_to_show)
        cv2.imshow("Predictions", tiles)
    
    # Display crops grid window if available
    if crops_grid_images:
        crops_tiles = create_tiles(images=crops_grid_images)
        cv2.imshow("Crops Grid", crops_tiles)
    
    cv2.waitKey(1)
    
    if hasattr(fps_monitor, "fps"):
        print(f"FPS: {fps_monitor.fps}")
    else:
        sv.FPSMonitor()





if __name__ == '__main__':
    main()