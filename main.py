#!/usr/bin/env python3
"""
Punto de entrada principal para Care Workflow.
"""

from care_workflow import WorkflowManager
from care_workflow.core import WorkflowStep, WorkflowStatus


def main():
    """Función principal de demostración."""
    print("🏥 Bienvenido a Care Workflow!")
    print("=" * 50)
    
    # Crear el gestor de flujos de trabajo
    manager = WorkflowManager()
    
    # Crear pasos de ejemplo para un flujo de cuidados
    steps = [
        WorkflowStep(
            id="step_1",
            name="Evaluación inicial",
            description="Evaluación inicial del paciente"
        ),
        WorkflowStep(
            id="step_2", 
            name="Plan de cuidados",
            description="Crear plan personalizado de cuidados"
        ),
        WorkflowStep(
            id="step_3",
            name="Seguimiento",
            description="Seguimiento y monitoreo del progreso"
        )
    ]
    
    # Crear un flujo de trabajo de ejemplo
    workflow = manager.create_workflow(
        workflow_id="care_001",
        name="Flujo de Cuidados Básico",
        description="Flujo estándar para nuevos pacientes",
        steps=steps
    )
    
    print(f"✅ Flujo de trabajo creado: {workflow.name}")
    print(f"📋 Descripción: {workflow.description}")
    print(f"🔢 Número de pasos: {len(workflow.steps)}")
    
    # Listar todos los workflows
    workflows = manager.list_workflows()
    print(f"\n📊 Total de workflows: {len(workflows)}")
    
    # Iniciar el workflow
    if manager.start_workflow("care_001"):
        print("🚀 Workflow iniciado exitosamente")
        
        # Mostrar estado actual
        status = manager.get_workflow_status("care_001")
        print(f"📈 Estado actual: {status.value}")
    
    print("\n" + "=" * 50)
    print("💡 Para más información, consulta el README.md")


if __name__ == "__main__":
    main()
