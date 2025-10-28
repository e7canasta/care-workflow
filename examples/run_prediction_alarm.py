"""
Example script demonstrating the Prediction Alarm block with MQTT integration.

This example shows intelligent alarm triggering with:
- Threshold-based activation
- Cooldown period to prevent spam
- State machine control (IDLE → FIRING → COOLDOWN)
- Integration with MQTT for notifications

Usage:
    export WORKFLOWS_PLUGINS="care.workflows.care_steps"
    export WORKFLOW_DEFINITION="data/workflows/examples/prediction_alarm_demo.json"
    export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"
    export MQTT_HOST="localhost"
    export MQTT_PORT="1883"
    export MQTT_TOPIC="care/detections/alerts"
    export ALARM_THRESHOLD="1"  # Optional, default: 1
    export ALARM_COOLDOWN="5.0"  # Optional, default: 5.0 seconds

    python examples/run_prediction_alarm.py

Monitor MQTT messages:
    mosquitto_sub -h localhost -t "care/detections/alerts" -v
"""

import json
import os
from threading import Thread
from typing import List, Optional, Union

import cv2
import supervision as sv

from inference import InferencePipeline
from inference.core.interfaces.camera.entities import VideoFrame
from inference.core.interfaces.stream.watchdog import BasePipelineWatchDog

# Global control flag
STOP = False
fps_monitor = sv.FPSMonitor()
frame_counter = 0


def main() -> None:
    """Run the prediction alarm pipeline."""
    global STOP

    # Validate required environment variables
    required_vars = ["VIDEO_REFERENCE", "MQTT_HOST", "MQTT_PORT", "MQTT_TOPIC"]
    missing_vars = [var for var in required_vars if var not in os.environ]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    # Optional parameters with defaults
    alarm_threshold = int(os.environ.get("ALARM_THRESHOLD", "1"))
    alarm_cooldown = float(os.environ.get("ALARM_COOLDOWN", "5.0"))

    workflow_path = os.environ.get(
        "WORKFLOW_DEFINITION", "data/workflows/examples/prediction_alarm_demo.json"
    )

    # Load workflow definition from JSON file
    with open(workflow_path, "r") as f:
        workflow_specification = json.load(f)

    print("=" * 60)
    print("🚨 Prediction Alarm Pipeline")
    print("=" * 60)
    print(f"Workflow: {workflow_path}")
    print(f"Video: {os.environ['VIDEO_REFERENCE']}")
    print(f"MQTT Broker: {os.environ['MQTT_HOST']}:{os.environ['MQTT_PORT']}")
    print(f"MQTT Topic: {os.environ['MQTT_TOPIC']}")
    print(f"Alarm Threshold: {alarm_threshold}")
    print(f"Alarm Cooldown: {alarm_cooldown}s")
    print("=" * 60)
    print("\nCommands:")
    print("  i - Show watchdog report")
    print("  t - Terminate pipeline")
    print("  p - Pause stream")
    print("  m - Mute stream")
    print("  r - Resume stream")
    print("=" * 60)

    watchdog = BasePipelineWatchDog()
    pipeline = InferencePipeline.init_with_workflow(
        video_reference=[os.environ["VIDEO_REFERENCE"]],
        workflow_specification=workflow_specification,
        watchdog=watchdog,
        on_prediction=workflows_sink,
        workflows_parameters={
            "mqtt_host": os.environ["MQTT_HOST"],
            "mqtt_port": int(os.environ["MQTT_PORT"]),
            "mqtt_topic": os.environ["MQTT_TOPIC"],
            "alarm_threshold": alarm_threshold,
            "alarm_cooldown": alarm_cooldown,
        },
    )

    control_thread = Thread(target=command_thread, args=(pipeline, watchdog))
    control_thread.start()
    pipeline.start()
    STOP = True
    pipeline.join()


def command_thread(pipeline: InferencePipeline, watchdog: BasePipelineWatchDog) -> None:
    """Handle user commands in a separate thread."""
    global STOP
    while not STOP:
        key = input()
        if key == "i":
            print(watchdog.get_report())
        if key == "t":
            pipeline.terminate()
            STOP = True
        elif key == "p":
            pipeline.pause_stream()
        elif key == "m":
            pipeline.mute_stream()
        elif key == "r":
            pipeline.resume_stream()


def workflows_sink(
    predictions: Union[Optional[dict], List[Optional[dict]]],
    video_frames: Union[Optional[VideoFrame], List[Optional[VideoFrame]]],
) -> None:
    """
    Process workflow predictions and display status.

    Args:
        predictions: Workflow output predictions
        video_frames: Video frames (not used in this example)
    """
    global frame_counter
    
    fps_monitor.tick()
    frame_counter += 1

    if not isinstance(predictions, list):
        predictions = [predictions]

    for prediction in predictions:
        if prediction is None:
            continue

        # Extract alarm state information
        count = prediction.get("person_count", 0)
        alarm_active = prediction.get("alarm_active", False)
        alarm_state = prediction.get("alarm_state", "unknown")

        # Display status based on alarm state
        if alarm_active:
            print(f"🔥 ALARM FIRING! Count: {count}, State: {alarm_state}")
        else:
            # Only print status every ~30 frames to reduce noise
            if frame_counter % 30 == 0:
                print(f"✓ Monitoring... Count: {count}, State: {alarm_state}")

    # Display FPS
    if hasattr(fps_monitor, "fps"):
        fps_value = fps_monitor.fps
    else:
        fps_value = fps_monitor()

    if frame_counter % 30 == 0:
        print(f"FPS: {fps_value:.2f}")


if __name__ == "__main__":
    main()
