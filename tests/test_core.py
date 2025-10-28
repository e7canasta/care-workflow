"""
Tests para el módulo core de Care Workflow.
"""

import pytest
from care_workflow.core import WorkflowManager, WorkflowStep, WorkflowStatus


class TestWorkflowManager:
    """Tests para la clase WorkflowManager."""
    
    def test_create_workflow_manager(self):
        """Test de creación del gestor de workflows."""
        manager = WorkflowManager()
        assert len(manager.workflows) == 0
    
    def test_create_workflow(self):
        """Test de creación de workflow."""
        manager = WorkflowManager()
        steps = [
            WorkflowStep(
                id="step_1",
                name="Test Step",
                description="Paso de prueba"
            )
        ]
        
        workflow = manager.create_workflow(
            workflow_id="test_001",
            name="Test Workflow",
            description="Workflow de prueba",
            steps=steps
        )
        
        assert workflow.id == "test_001"
        assert workflow.name == "Test Workflow"
        assert len(workflow.steps) == 1
        assert workflow.status == WorkflowStatus.PENDING
    
    def test_get_workflow(self):
        """Test de obtención de workflow."""
        manager = WorkflowManager()
        steps = [
            WorkflowStep(
                id="step_1",
                name="Test Step",
                description="Paso de prueba"
            )
        ]
        
        manager.create_workflow(
            workflow_id="test_001",
            name="Test Workflow",
            description="Workflow de prueba",
            steps=steps
        )
        
        workflow = manager.get_workflow("test_001")
        assert workflow is not None
        assert workflow.id == "test_001"
        
        # Test workflow que no existe
        non_existent = manager.get_workflow("non_existent")
        assert non_existent is None
    
    def test_start_workflow(self):
        """Test de inicio de workflow."""
        manager = WorkflowManager()
        steps = [
            WorkflowStep(
                id="step_1",
                name="Test Step",
                description="Paso de prueba"
            )
        ]
        
        manager.create_workflow(
            workflow_id="test_001",
            name="Test Workflow",
            description="Workflow de prueba",
            steps=steps
        )
        
        # Iniciar workflow existente
        result = manager.start_workflow("test_001")
        assert result is True
        
        workflow = manager.get_workflow("test_001")
        assert workflow.status == WorkflowStatus.RUNNING
        
        # Intentar iniciar workflow que no existe
        result = manager.start_workflow("non_existent")
        assert result is False
    
    def test_complete_workflow(self):
        """Test de completar workflow."""
        manager = WorkflowManager()
        steps = [
            WorkflowStep(
                id="step_1",
                name="Test Step",
                description="Paso de prueba"
            )
        ]
        
        manager.create_workflow(
            workflow_id="test_001",
            name="Test Workflow",
            description="Workflow de prueba",
            steps=steps
        )
        
        # Completar workflow
        result = manager.complete_workflow("test_001")
        assert result is True
        
        workflow = manager.get_workflow("test_001")
        assert workflow.status == WorkflowStatus.COMPLETED


class TestWorkflowStep:
    """Tests para la clase WorkflowStep."""
    
    def test_create_workflow_step(self):
        """Test de creación de paso de workflow."""
        step = WorkflowStep(
            id="step_1",
            name="Test Step",
            description="Paso de prueba"
        )
        
        assert step.id == "step_1"
        assert step.name == "Test Step"
        assert step.description == "Paso de prueba"
        assert step.status == WorkflowStatus.PENDING
        assert step.metadata == {}
    
    def test_workflow_step_with_metadata(self):
        """Test de paso con metadata."""
        metadata = {"priority": "high", "duration": 30}
        step = WorkflowStep(
            id="step_1",
            name="Test Step",
            description="Paso de prueba",
            metadata=metadata
        )
        
        assert step.metadata == metadata