#!/usr/bin/env python3
"""
Ejemplo de uso del custom block MQTT Writer con InferencePipeline.

Este ejemplo demuestra cómo:
1. Registrar custom blocks mediante WORKFLOWS_PLUGINS
2. Usar el block mqtt_writer_sink@v1 en un workflow
3. Publicar detecciones en tiempo real a un broker MQTT

Requisitos:
    - Broker MQTT corriendo (ej: mosquitto en localhost:1883)
    - Video source configurado (RTSP, webcam, o archivo)
    - Workflow definition con mqtt_writer_sink

Setup:
    # Instalar mosquitto (opcional, para testing local)
    sudo apt-get install mosquitto mosquitto-clients

    # Subscribirse al topic para ver mensajes (en otra terminal)
    mosquitto_sub -h localhost -t "care/detections/alerts" -v

Uso:
    export WORKFLOWS_PLUGINS="care.workflows.care_steps"
    export WORKFLOW_DEFINITION="data/workflows/examples/mqtt_detection_alert.json"
    export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"
    export MQTT_HOST="localhost"
    export MQTT_PORT="1883"
    export MQTT_TOPIC="care/detections/alerts"

    python examples/run_mqtt_detection.py
"""

import json
import os
from threading import Thread
from typing import List, Optional, Union

import cv2
from inference import InferencePipeline
from inference.core.interfaces.camera.entities import VideoFrame
from inference.core.interfaces.stream.watchdog import BasePipelineWatchDog


STOP = False

# Load workflow definition
with open(os.environ["WORKFLOW_DEFINITION"], 'r') as f:
    workflow_definition = json.load(f)

# Get MQTT configuration from environment
mqtt_config = {
    "mqtt_host": os.environ.get("MQTT_HOST", "localhost"),
    "mqtt_port": int(os.environ.get("MQTT_PORT", "1883")),
    "mqtt_topic": os.environ.get("MQTT_TOPIC", "care/detections/alerts"),
}


def main() -> None:
    """
    Inicia el pipeline con custom MQTT block.

    El workflow detectará personas y publicará alertas en MQTT
    cuando se detecten objetos.
    """
    global STOP

    print("=" * 60)
    print("🏥 Care Workflow - MQTT Detection Alert")
    print("=" * 60)
    print(f"📡 MQTT Broker: {mqtt_config['mqtt_host']}:{mqtt_config['mqtt_port']}")
    print(f"📢 Topic: {mqtt_config['mqtt_topic']}")
    print(f"🎥 Video: {os.environ['VIDEO_REFERENCE']}")
    print("=" * 60)
    print("\nComandos interactivos:")
    print("  i - Mostrar reporte del watchdog")
    print("  t - Terminar pipeline")
    print("  p - Pausar stream")
    print("  r - Resumir stream")
    print("=" * 60)

    watchdog = BasePipelineWatchDog()

    # Inicializar pipeline con workflow que incluye MQTT block
    pipeline = InferencePipeline.init_with_workflow(
        video_reference=[os.environ["VIDEO_REFERENCE"]],
        workflow_specification=workflow_definition,
        watchdog=watchdog,
        on_prediction=workflow_sink,
        workflows_parameters=mqtt_config,  # Pasar config MQTT como parámetros
    )

    control_thread = Thread(target=command_thread, args=(pipeline, watchdog))
    control_thread.start()

    pipeline.start()
    STOP = True
    pipeline.join()

    print("\n✅ Pipeline terminado")


def command_thread(pipeline: InferencePipeline, watchdog: BasePipelineWatchDog) -> None:
    """Maneja comandos interactivos del usuario."""
    global STOP
    while not STOP:
        key = input()
        if key == "i":
            print(watchdog.get_report())
        elif key == "t":
            pipeline.terminate()
            STOP = True
        elif key == "p":
            pipeline.pause_stream()
            print("⏸️  Stream pausado")
        elif key == "r":
            pipeline.resume_stream()
            print("▶️  Stream resumido")


def workflow_sink(
    predictions: Union[Optional[dict], List[Optional[dict]]],
    video_frames: Union[Optional[VideoFrame], List[Optional[VideoFrame]]],
) -> None:
    """
    Procesa predicciones del workflow.

    El workflow ya envía mensajes MQTT internamente via mqtt_writer_sink block.
    Este sink solo muestra status en consola.
    """
    if not isinstance(predictions, list):
        predictions = [predictions]

    for prediction in predictions:
        if prediction is None:
            continue

        # Mostrar status de MQTT publish
        if "mqtt_status" in prediction and "mqtt_message" in prediction:
            error = prediction["mqtt_status"]
            message = prediction["mqtt_message"]

            if error:
                print(f"❌ MQTT Error: {message}")
            else:
                person_count = prediction.get("person_count", 0)
                print(f"✅ MQTT: Publicado - {person_count} persona(s) detectada(s)")

        # Visualizar detecciones (opcional)
        if "visualization" in prediction:
            cv2.imshow("Detections", prediction["visualization"].numpy_image)
            cv2.waitKey(1)


if __name__ == '__main__':
    # Configurar el plugin de workflows si no está establecido
    if "WORKFLOWS_PLUGINS" not in os.environ:
        os.environ["WORKFLOWS_PLUGINS"] = "care.workflows.care_steps"

    main()
