#!/usr/bin/env python
"""
Ejemplo de detección de objetos usando modelos ONNX locales sin Roboflow API.

Este script demuestra cómo usar el LocalModelRegistry para cargar y ejecutar
modelos YOLO cuantizados desde manifests JSON locales.

Uso:
    # Configurar variables de entorno
    export LOCAL_MODELS_DIR="./models/local"
    export VIDEO_REFERENCE="rtsp://localhost:8554/live/1"
    export WORKFLOW_DEFINITION="data/workflows/detections/local-yolo-detection.json"

    # Ejecutar
    python examples/run_local_detection.py

Requisitos:
    1. go2rtc ejecutándose (para RTSP stream)
    2. Manifest JSON en models/local/
    3. Modelo ONNX correspondiente

    Ver models/local/README.md para instrucciones de setup.
"""

import os
import signal
import sys
from threading import Thread

import cv2

# Agregar path para imports locales si es necesario
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from care.stream.inference_pipeline import InferencePipeline

# Flag global para terminar pipeline
STOP = False


def signal_handler(sig, frame):
    """Handler para Ctrl+C."""
    global STOP
    print("\n[INFO] Deteniendo pipeline...")
    STOP = True


def command_thread_worker():
    """Thread para manejar comandos interactivos del usuario."""
    global STOP
    print("\n" + "=" * 60)
    print("Comandos disponibles:")
    print("  i - Mostrar info del watchdog")
    print("  t - Terminar pipeline")
    print("  p - Pausar stream")
    print("  m - Mutear stream")
    print("  r - Resumir stream")
    print("=" * 60 + "\n")

    while not STOP:
        try:
            command = input()
            if command == "t":
                print("[INFO] Terminando...")
                STOP = True
            elif command == "i":
                print("[INFO] Watchdog report solicitado (implementar si es necesario)")
            elif command == "p":
                print("[INFO] Pausando stream...")
                # TODO: Implementar pause
            elif command == "m":
                print("[INFO] Muteando stream...")
                # TODO: Implementar mute
            elif command == "r":
                print("[INFO] Resumiendo stream...")
                # TODO: Implementar resume
        except EOFError:
            break


def workflows_sink(predictions: dict, video_frame) -> None:
    """
    Sink para visualizar predicciones.

    Args:
        predictions: Diccionario con predicciones del workflow
        video_frame: Frame de video con metadata
    """
    global STOP

    # Extraer imagen y detections
    image = video_frame.image
    detections = predictions.get("predictions")

    if detections is None:
        # Si no hay detections, mostrar frame sin anotaciones
        cv2.imshow("Local YOLO Detection", image)
    else:
        # Visualizar detections (si supervision está disponible)
        try:
            import supervision as sv

            # Crear annotator
            box_annotator = sv.BoxAnnotator()
            label_annotator = sv.LabelAnnotator()

            # Anotar frame
            annotated_frame = box_annotator.annotate(
                scene=image.copy(), detections=detections
            )

            # Agregar labels si hay class_name
            if hasattr(detections, "data") and "class_name" in detections.data:
                labels = [
                    f"{class_name} {confidence:.2f}"
                    for class_name, confidence in zip(
                        detections.data["class_name"], detections.confidence
                    )
                ]
                annotated_frame = label_annotator.annotate(
                    scene=annotated_frame, detections=detections, labels=labels
                )

            cv2.imshow("Local YOLO Detection", annotated_frame)
        except ImportError:
            # Si supervision no está disponible, dibujar bounding boxes básicos
            for i in range(len(detections.xyxy)):
                x1, y1, x2, y2 = detections.xyxy[i].astype(int)
                conf = detections.confidence[i]
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    image,
                    f"{conf:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2,
                )
            cv2.imshow("Local YOLO Detection", image)

    # Esperar tecla (1ms) para que CV2 actualice ventana
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q") or key == 27:  # 'q' o ESC
        STOP = True


def main():
    """Función principal."""
    global STOP

    # Registrar signal handler para Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Obtener configuración desde variables de entorno
    video_reference = os.getenv("VIDEO_REFERENCE", "rtsp://localhost:8554/live/1")
    workflow_definition = os.getenv(
        "WORKFLOW_DEFINITION",
        "data/workflows/detections/local-yolo-detection.json",
    )
    local_models_dir = os.getenv("LOCAL_MODELS_DIR", "./models/local")

    print("\n" + "=" * 60)
    print("LOCAL ONNX DETECTION EXAMPLE")
    print("=" * 60)
    print(f"Video source:    {video_reference}")
    print(f"Workflow JSON:   {workflow_definition}")
    print(f"Models dir:      {local_models_dir}")
    print("=" * 60 + "\n")

    # Verificar que el workflow existe
    if not os.path.exists(workflow_definition):
        print(f"[ERROR] Workflow definition not found: {workflow_definition}")
        print("\nCreando workflow de ejemplo...")

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(workflow_definition), exist_ok=True)

        # Crear workflow básico
        import json

        example_workflow = {
            "version": "1.0",
            "inputs": [{"type": "InferenceImage", "name": "image"}],
            "steps": [
                {
                    "type": "ObjectDetectionModel",
                    "name": "detector",
                    "image": "$inputs.image",
                    "model_id": "yolov11n-320",  # Usar modelo local
                    "confidence": 0.5,
                }
            ],
            "outputs": [
                {
                    "type": "JsonField",
                    "name": "predictions",
                    "selector": "$steps.detector.predictions",
                }
            ],
        }

        with open(workflow_definition, "w") as f:
            json.dump(example_workflow, f, indent=2)

        print(f"[INFO] Created example workflow at {workflow_definition}")
        print(
            "[INFO] Make sure you have a manifest for 'yolov11n-320' in models/local/"
        )

    # Verificar que models/local existe
    if not os.path.exists(local_models_dir):
        print(f"\n[WARNING] Local models directory not found: {local_models_dir}")
        print("Creating directory...")
        os.makedirs(local_models_dir, exist_ok=True)
        print(
            f"[INFO] Please add model manifests and ONNX files to {local_models_dir}/"
        )
        print("See models/local/README.md for instructions.\n")

    # Crear pipeline con workflow local
    try:
        pipeline = InferencePipeline.init_with_workflow(
            video_reference=video_reference,
            workflow_specification=workflow_definition,
            on_prediction=workflows_sink,
        )
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize pipeline: {e}")
        print("\nPossible issues:")
        print("1. Model manifest not found in LOCAL_MODELS_DIR")
        print("2. ONNX model file missing")
        print("3. Video source not available")
        print("4. Workflow JSON malformed")
        print("\nSee models/local/README.md for setup instructions.")
        sys.exit(1)

    # Iniciar thread de comandos
    command_thread = Thread(target=command_thread_worker, daemon=True)
    command_thread.start()

    print("[INFO] Pipeline started. Press 't' to terminate or 'i' for watchdog info.")
    print("[INFO] Press 'q' or ESC in the video window to quit.\n")

    # Iniciar pipeline
    pipeline.start()

    # Wait loop
    try:
        pipeline.join()
    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt received.")
    finally:
        # Cleanup
        try:
            pipeline.terminate()
        except Exception as e:
            print(f"[WARNING] Error during pipeline termination: {e}")

        cv2.destroyAllWindows()
        print("[INFO] Pipeline terminated. Goodbye!")


if __name__ == "__main__":
    main()
