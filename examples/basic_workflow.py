#!/usr/bin/env python3
"""
Ejemplo básico de uso de Care Workflow.
"""

from care_workflow import WorkflowManager
from care_workflow.core import WorkflowStep, WorkflowStatus


def create_patient_care_workflow():
    """Crea un flujo de trabajo para cuidado de pacientes."""
    
    # Inicializar el gestor
    manager = WorkflowManager()
    
    # Definir los pasos del cuidado
    care_steps = [
        WorkflowStep(
            id="admission",
            name="Admisión del Paciente",
            description="Registro y admisión inicial del paciente",
            metadata={"priority": "high", "estimated_duration": 15}
        ),
        WorkflowStep(
            id="assessment",
            name="Evaluación Médica",
            description="Evaluación completa del estado del paciente",
            metadata={"priority": "critical", "estimated_duration": 45}
        ),
        WorkflowStep(
            id="care_plan",
            name="Plan de Cuidados",
            description="Desarrollo del plan personalizado de cuidados",
            metadata={"priority": "high", "estimated_duration": 30}
        ),
        WorkflowStep(
            id="treatment",
            name="Tratamiento",
            description="Implementación del tratamiento prescrito",
            metadata={"priority": "critical", "estimated_duration": 120}
        ),
        WorkflowStep(
            id="monitoring",
            name="Monitoreo",
            description="Seguimiento del progreso del paciente",
            metadata={"priority": "medium", "estimated_duration": 60}
        ),
        WorkflowStep(
            id="discharge",
            name="Alta del Paciente",
            description="Proceso de alta y instrucciones de seguimiento",
            metadata={"priority": "medium", "estimated_duration": 20}
        )
    ]
    
    # Crear el workflow
    workflow = manager.create_workflow(
        workflow_id="patient_care_001",
        name="Cuidado Integral del Paciente",
        description="Flujo completo desde admisión hasta alta del paciente",
        steps=care_steps
    )
    
    return manager, workflow


def demonstrate_workflow():
    """Demuestra el uso del workflow."""
    print("🏥 Ejemplo: Flujo de Cuidado del Paciente")
    print("=" * 60)
    
    # Crear el workflow
    manager, workflow = create_patient_care_workflow()
    
    print(f"✅ Workflow creado: {workflow.name}")
    print(f"📋 ID: {workflow.id}")
    print(f"📝 Descripción: {workflow.description}")
    print(f"🔢 Pasos totales: {len(workflow.steps)}")
    print()
    
    # Mostrar todos los pasos
    print("📋 Pasos del workflow:")
    for i, step in enumerate(workflow.steps, 1):
        duration = step.metadata.get("estimated_duration", "N/A")
        priority = step.metadata.get("priority", "normal")
        print(f"  {i}. {step.name}")
        print(f"     📝 {step.description}")
        print(f"     ⏱️  Duración estimada: {duration} min")
        print(f"     🔥 Prioridad: {priority}")
        print(f"     📊 Estado: {step.status.value}")
        print()
    
    # Iniciar el workflow
    print("🚀 Iniciando workflow...")
    if manager.start_workflow(workflow.id):
        status = manager.get_workflow_status(workflow.id)
        print(f"✅ Workflow iniciado exitosamente - Estado: {status.value}")
    else:
        print("❌ Error al iniciar el workflow")
    
    # Simular progreso
    print("\n⏳ Simulando progreso del workflow...")
    
    # En un caso real, aquí habría lógica para ejecutar cada paso
    # Por ahora solo cambiamos algunos estados para demostrar
    workflow.steps[0].status = WorkflowStatus.COMPLETED
    workflow.steps[1].status = WorkflowStatus.RUNNING
    
    print("📊 Estado actualizado de los pasos:")
    for step in workflow.steps[:3]:  # Mostrar solo los primeros 3
        print(f"  • {step.name}: {step.status.value}")
    
    print("\n" + "=" * 60)
    print("💡 Este es un ejemplo básico. En producción, cada paso")
    print("   tendría lógica específica para su ejecución.")


if __name__ == "__main__":
    demonstrate_workflow()