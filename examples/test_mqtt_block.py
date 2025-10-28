#!/usr/bin/env python3
"""
Test rápido del MQTT Writer custom block.

Este script verifica que:
1. El plugin se carga correctamente
2. El block está registrado en el execution engine
3. El block puede ejecutarse standalone

Uso:
    # Sin broker MQTT (test de registro)
    python examples/test_mqtt_block.py

    # Con broker MQTT (test completo)
    # Terminal 1:
    mosquitto_sub -h localhost -t "test/care" -v

    # Terminal 2:
    python examples/test_mqtt_block.py --with-broker
"""

import argparse
import os
import sys

# Activar plugin ANTES de cualquier import de inference
os.environ["WORKFLOWS_PLUGINS"] = "care.workflows.care_steps"

from inference.core.workflows.execution_engine.introspection import blocks_loader
from inference.core.workflows.execution_engine.introspection.blocks_loader import (
    describe_available_blocks,
)


def test_plugin_loading():
    """Verifica que el plugin se cargue correctamente."""
    print("=" * 60)
    print("🔍 Test 1: Plugin Loading")
    print("=" * 60)

    plugins = blocks_loader.get_plugin_modules()
    print(f"Plugins configurados: {plugins}")

    if "care.workflows.care_steps" not in plugins:
        print("❌ Plugin 'care.workflows.care_steps' no está en WORKFLOWS_PLUGINS")
        return False

    print("✅ Plugin configurado correctamente\n")
    return True


def test_block_registration():
    """Verifica que el block MQTT esté registrado."""
    print("=" * 60)
    print("🔍 Test 2: Block Registration")
    print("=" * 60)

    try:
        blocks = blocks_loader.load_workflow_blocks()
        custom_blocks = [
            b for b in blocks if b.block_source == "care.workflows.care_steps"
        ]

        print(f"Total blocks cargados: {len(blocks)}")
        print(f"Custom blocks cargados: {len(custom_blocks)}\n")

        if not custom_blocks:
            print("❌ No se encontraron custom blocks")
            return False

        for block in custom_blocks:
            print(f"✅ Block registrado: {block.identifier}")
            manifest = block.manifest_class.model_json_schema()
            block_type = manifest["properties"]["type"]
            print(f"   Type identifier: {block_type}")
            print(f"   Block source: {block.block_source}")

        # Verificar blocks específicos
        mqtt_block = next(
            (b for b in custom_blocks if "MQTTWriterSinkBlock" in b.identifier), None
        )
        count_block = next(
            (b for b in custom_blocks if "DetectionsCountBlock" in b.identifier), None
        )

        if not mqtt_block:
            print("\n❌ Block 'MQTTWriterSinkBlockV1' no encontrado")
            return False

        if not count_block:
            print("\n❌ Block 'DetectionsCountBlockV1' no encontrado")
            return False

        print(f"\n✅ Todos los custom blocks encontrados y registrados correctamente")
        return True

    except Exception as e:
        print(f"❌ Error al cargar blocks: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_block_manifest():
    """Verifica el manifest del block."""
    print("\n" + "=" * 60)
    print("🔍 Test 3: Block Manifest Structure")
    print("=" * 60)

    try:
        blocks_desc = describe_available_blocks(dynamic_blocks=[])

        # Test MQTT Writer
        mqtt_block = next(
            (
                b
                for b in blocks_desc.blocks
                if b.manifest_type_identifier == "care/mqtt_writer@v1"
            ),
            None,
        )

        if not mqtt_block:
            print("❌ Block care/mqtt_writer@v1 no encontrado en registry")
            return False

        print("📋 MQTT Writer Block:")
        schema = mqtt_block.block_schema
        print(f"  Name: {schema.get('title', 'N/A')}")
        print(f"  Type: {mqtt_block.manifest_type_identifier}")
        print(f"  Outputs: {[o.name for o in mqtt_block.outputs_manifest]}")

        # Test Detections Count
        count_block = next(
            (
                b
                for b in blocks_desc.blocks
                if b.manifest_type_identifier == "care/detections_count@v1"
            ),
            None,
        )

        if not count_block:
            print("\n❌ Block care/detections_count@v1 no encontrado en registry")
            return False

        print("\n📋 Detections Count Block:")
        schema = count_block.block_schema
        print(f"  Name: {schema.get('title', 'N/A')}")
        print(f"  Type: {count_block.manifest_type_identifier}")
        print(f"  Outputs: {[o.name for o in count_block.outputs_manifest]}")

        print("\n✅ Manifest estructura correcta para ambos blocks")
        return True

    except Exception as e:
        print(f"❌ Error al verificar manifest: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_block_execution(with_broker: bool = False):
    """Test de ejecución del block (opcional con broker real)."""
    if not with_broker:
        print("\n" + "=" * 60)
        print("⏭️  Test 4: Skipped (use --with-broker para ejecutar)")
        print("=" * 60)
        return True

    print("\n" + "=" * 60)
    print("🔍 Test 4: Block Execution")
    print("=" * 60)

    try:
        from care.workflows.care_steps.sinks.mqtt_writer import MQTTWriterSinkBlockV1

        block = MQTTWriterSinkBlockV1()

        print("Intentando publicar mensaje de test...")
        result = block.run(
            host="localhost",
            port=1883,
            topic="test/care",
            message="Test message from Care Workflow custom block",
            qos=0,
            retain=False,
            timeout=2.0,
        )

        print(f"\nResultado:")
        print(f"  error_status: {result['error_status']}")
        print(f"  message: {result['message']}")

        if result["error_status"]:
            print("\n⚠️  Publish falló (¿broker corriendo?)")
            print("   Para test completo: mosquitto -v")
            return False
        else:
            print("\n✅ Block ejecutado exitosamente")
            print("   Verificá el mensaje en: mosquitto_sub -h localhost -t 'test/care'")
            return True

    except Exception as e:
        print(f"❌ Error al ejecutar block: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test Care Workflow custom MQTT block"
    )
    parser.add_argument(
        "--with-broker",
        action="store_true",
        help="Ejecutar test de publicación MQTT (requiere broker)",
    )
    args = parser.parse_args()

    print("\n🏥 Care Workflow - MQTT Block Test Suite\n")

    results = {
        "Plugin Loading": test_plugin_loading(),
        "Block Registration": test_block_registration(),
        "Manifest Structure": test_block_manifest(),
        "Block Execution": test_block_execution(args.with_broker),
    }

    # Summary
    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(results.values())
    print("=" * 60)

    if all_passed:
        print("\n🎉 Todos los tests pasaron!")
        print(
            "\n💡 Siguiente paso: Probá el workflow completo con 'python examples/run_mqtt_detection.py'"
        )
        return 0
    else:
        print("\n❌ Algunos tests fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
