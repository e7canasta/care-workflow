"""
Módulo principal del sistema de gestión de flujos de trabajo.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Estados posibles de un flujo de trabajo."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """Representa un paso individual en el flujo de trabajo."""
    id: str
    name: str
    description: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Workflow:
    """Representa un flujo de trabajo completo."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class WorkflowManager:
    """Gestor principal para flujos de trabajo de cuidados."""
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        logger.info("WorkflowManager inicializado")

    def create_workflow(
        self, 
        workflow_id: str, 
        name: str, 
        description: str,
        steps: List[WorkflowStep]
    ) -> Workflow:
        """Crea un nuevo flujo de trabajo."""
        if workflow_id in self.workflows:
            raise ValueError(f"El workflow con ID '{workflow_id}' ya existe")
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=steps
        )
        
        self.workflows[workflow_id] = workflow
        logger.info(f"Workflow '{name}' creado con ID: {workflow_id}")
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Obtiene un flujo de trabajo por su ID."""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[Workflow]:
        """Lista todos los flujos de trabajo."""
        return list(self.workflows.values())

    def start_workflow(self, workflow_id: str) -> bool:
        """Inicia la ejecución de un flujo de trabajo."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow con ID '{workflow_id}' no encontrado")
            return False
        
        if workflow.status != WorkflowStatus.PENDING:
            logger.warning(f"Workflow '{workflow_id}' no está en estado PENDING")
            return False
        
        workflow.status = WorkflowStatus.RUNNING
        logger.info(f"Workflow '{workflow.name}' iniciado")
        return True

    def complete_workflow(self, workflow_id: str) -> bool:
        """Marca un flujo de trabajo como completado."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow con ID '{workflow_id}' no encontrado")
            return False
        
        workflow.status = WorkflowStatus.COMPLETED
        logger.info(f"Workflow '{workflow.name}' completado")
        return True

    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """Obtiene el estado de un flujo de trabajo."""
        workflow = self.get_workflow(workflow_id)
        return workflow.status if workflow else None