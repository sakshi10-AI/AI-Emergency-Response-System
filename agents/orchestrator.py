"""
Emergency Coordinator Agent (Central Multi-Agent Orchestrator)

Central supervisor orchestrating multi-agent workflows:
Intake Classification -> Specialized Domain Analysis (Medical/Police/Fire/Traffic) ->
Resource Allocation -> Communication & Alerts -> Report Generation.
"""
import time
from typing import List, Dict, Any
from uuid import UUID
from agents.base_agent import BaseAgent
from agents.schemas import (
    OrchestratorPipelineInput, OrchestratorPipelineOutput,
    ClassificationInput, MedicalInput, PoliceInput, FireInput, TrafficInput,
    ResourceAllocationInput, CommunicationInput, ReportGenerationInput, NotificationInput
)
from agents.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from agents.specialized_agents import (
    IncidentClassificationAgent, MedicalAssistanceAgent, PoliceAssistanceAgent,
    FireAssistanceAgent, TrafficAnalysisAgent, ResourceAllocationAgent,
    CommunicationAgent, ReportGenerationAgent, NotificationAgent
)
from utils.logger import app_logger

class EmergencyCoordinatorAgent(BaseAgent):
    """Central orchestrator managing multi-agent emergency response execution pipeline."""

    def __init__(self):
        super().__init__(
            name="EmergencyCoordinatorAgent",
            system_instruction=ORCHESTRATOR_SYSTEM_PROMPT,
            input_schema=OrchestratorPipelineInput,
            output_schema=OrchestratorPipelineOutput
        )

        # Initialize sub-agents
        self.classification_agent = IncidentClassificationAgent()
        self.medical_agent = MedicalAssistanceAgent()
        self.police_agent = PoliceAssistanceAgent()
        self.fire_agent = FireAssistanceAgent()
        self.traffic_agent = TrafficAnalysisAgent()
        self.resource_agent = ResourceAllocationAgent()
        self.communication_agent = CommunicationAgent()
        self.notification_agent = NotificationAgent()
        self.report_agent = ReportGenerationAgent()

    async def execute_pipeline(
        self, 
        pipeline_input: OrchestratorPipelineInput,
        available_units: List[Dict[str, Any]]
    ) -> OrchestratorPipelineOutput:
        """Executes the multi-agent DAG pipeline."""
        start_time = time.time()
        app_logger.info(f"[Orchestrator] Starting multi-agent pipeline for Incident '{pipeline_input.incident_id}'...")

        # ---------------- Stage 1: Classification ----------------
        class_input = ClassificationInput(
            description=pipeline_input.description,
            latitude=pipeline_input.latitude,
            longitude=pipeline_input.longitude,
            address_text=pipeline_input.address_text
        )
        classification_res = await self.classification_agent.execute(class_input)

        # ---------------- Stage 2: Specialized Domain Analysis ----------------
        medical_res = None
        if classification_res.requires_medical:
            medical_res = await self.medical_agent.execute(MedicalInput(
                description=pipeline_input.description,
                severity=classification_res.severity
            ))

        police_res = None
        if classification_res.requires_police:
            police_res = await self.police_agent.execute(PoliceInput(
                description=pipeline_input.description,
                severity=classification_res.severity
            ))

        fire_res = None
        if classification_res.requires_fire or classification_res.requires_hazmat:
            fire_res = await self.fire_agent.execute(FireInput(
                description=pipeline_input.description,
                severity=classification_res.severity
            ))

        traffic_res = await self.traffic_agent.execute(TrafficInput(
            latitude=pipeline_input.latitude,
            longitude=pipeline_input.longitude,
            incident_type=classification_res.category
        ))

        # ---------------- Stage 3: Resource Allocation ----------------
        resource_input = ResourceAllocationInput(
            incident_id=pipeline_input.incident_id,
            category=classification_res.category,
            severity=classification_res.severity,
            requires_medical=classification_res.requires_medical,
            requires_police=classification_res.requires_police,
            requires_fire=classification_res.requires_fire,
            requires_hazmat=classification_res.requires_hazmat,
            available_units=available_units
        )
        resource_res = await self.resource_agent.execute(resource_input)

        # ---------------- Stage 4: Communication & Notifications ----------------
        assigned_callsigns = [u.call_sign for u in resource_res.recommended_units]
        first_aid_steps = medical_res.first_aid_instructions if medical_res else []

        comm_res = await self.communication_agent.execute(CommunicationInput(
            incident_summary=classification_res.summary,
            severity=classification_res.severity,
            assigned_units=assigned_callsigns,
            medical_instructions=first_aid_steps
        ))

        notification_res = await self.notification_agent.execute(NotificationInput(
            title=f"{classification_res.category.upper()} Emergency",
            description=pipeline_input.description,
            severity=classification_res.severity,
            latitude=pipeline_input.latitude,
            longitude=pipeline_input.longitude,
            target_radius_km=3.0
        ))

        # ---------------- Stage 5: Post-Incident Report Generation ----------------
        report_res = await self.report_agent.execute(ReportGenerationInput(
            incident_id=pipeline_input.incident_id,
            tracking_code=f"EMG-{str(pipeline_input.incident_id)[:8]}",
            description=pipeline_input.description,
            classification=classification_res.model_dump(),
            assignments=[u.model_dump() for u in resource_res.recommended_units]
        ))

        elapsed = time.time() - start_time
        app_logger.info(f"[Orchestrator] Multi-agent pipeline completed in {elapsed:.2f} seconds.")

        return OrchestratorPipelineOutput(
            incident_id=pipeline_input.incident_id,
            tracking_code=f"EMG-{str(pipeline_input.incident_id)[:8]}",
            classification=classification_res,
            medical_assessment=medical_res,
            police_assessment=police_res,
            fire_assessment=fire_res,
            traffic_analysis=traffic_res,
            resource_allocation=resource_res,
            communications=comm_res,
            notification=notification_res,
            incident_report=report_res,
            execution_duration_seconds=max(0.001, round(elapsed, 3))
        )

    def fallback_execution(self, input_data: OrchestratorPipelineInput) -> OrchestratorPipelineOutput:
        """Not called directly; sub-agents handle individual fallbacks."""
        raise NotImplementedError("Orchestrator uses execute_pipeline.")

coordinator_agent = EmergencyCoordinatorAgent()
