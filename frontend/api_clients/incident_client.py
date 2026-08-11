"""
Incident API Service Client

Encapsulates all incident lifecycle operations: creation, retrieval, status updates,
workflow dispatch triggers, and timeline fetching.
"""

from typing import Optional, Dict, Any, List
from frontend.api_clients.base_client import base_api_client, BaseAPIClient, APIConnectionError, ResourceNotFoundError
from frontend.api_clients.mock_data import MOCK_INCIDENTS as _MOCK_INCIDENTS
from utils.logger import app_logger


class IncidentClient:
    """API Service client for emergency incident operations."""

    def __init__(self, client: Optional[BaseAPIClient] = None):
        self.client = client or base_api_client

    def get_incidents(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetches list of incidents with optional filters."""
        params = {"limit": limit}
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority

        try:
            result = self.client.execute_request("GET", "/api/v1/incidents/", params=params, cache_ttl=15)
            if isinstance(result, list):
                return result
            return result.get("incidents", result.get("data", []))
        except APIConnectionError:
            app_logger.warning("[IncidentClient] Backend offline. Returning local mock incidents.")
            return _MOCK_INCIDENTS
        except Exception as e:
            app_logger.error(f"[IncidentClient] get_incidents error: {e}")
            return _MOCK_INCIDENTS

    def get_incident_by_id(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single incident by its ID."""
        try:
            return self.client.execute_request("GET", f"/api/v1/incidents/{incident_id}", cache_ttl=10)
        except ResourceNotFoundError:
            app_logger.warning(f"[IncidentClient] Incident '{incident_id}' not found in backend.")
            return next((i for i in _MOCK_INCIDENTS if i["incident_id"] == incident_id), None)
        except APIConnectionError:
            return next((i for i in _MOCK_INCIDENTS if i["incident_id"] == incident_id), None)
        except Exception as e:
            app_logger.error(f"[IncidentClient] get_incident_by_id error: {e}")
            return None

    def create_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new emergency incident record."""
        try:
            return self.client.execute_request(
                "POST", "/api/v1/incidents/",
                json_data=incident_data, use_cache=False
            )
        except APIConnectionError:
            app_logger.warning("[IncidentClient] Backend offline. Incident stored locally.")
            incident_data["incident_id"] = f"INC-LOCAL-{len(_MOCK_INCIDENTS)+1}"
            incident_data["status"] = "PENDING_SYNC"
            _MOCK_INCIDENTS.append(incident_data)
            return incident_data
        except Exception as e:
            app_logger.error(f"[IncidentClient] create_incident error: {e}")
            return {"error": str(e)}

    def update_incident_status(self, incident_id: str, status: str, notes: str = "") -> Dict[str, Any]:
        """Updates the operational status of an incident."""
        try:
            return self.client.execute_request(
                "PUT", f"/api/v1/incidents/{incident_id}/status",
                json_data={"status": status, "notes": notes}, use_cache=False
            )
        except APIConnectionError:
            for inc in _MOCK_INCIDENTS:
                if inc["incident_id"] == incident_id:
                    inc["status"] = status
                    return inc
            return {"status": "FALLBACK_UPDATED"}
        except Exception as e:
            app_logger.error(f"[IncidentClient] update_incident_status error: {e}")
            return {"error": str(e)}

    def trigger_workflow_dispatch(self, incident_id: str) -> Dict[str, Any]:
        """Triggers the LangGraph multi-agent dispatch workflow for an incident."""
        try:
            return self.client.execute_request(
                "POST", f"/api/v1/incidents/{incident_id}/dispatch",
                json_data={}, use_cache=False
            )
        except APIConnectionError:
            return {
                "status": "FALLBACK_DISPATCH",
                "message": f"Dispatch workflow queued locally for {incident_id}.",
                "thread_id": f"thread-{incident_id}"
            }
        except Exception as e:
            app_logger.error(f"[IncidentClient] trigger_workflow_dispatch error: {e}")
            return {"error": str(e)}

    def get_incident_timeline(self, incident_id: str) -> List[Dict[str, Any]]:
        """Fetches chronological audit timeline events for an incident."""
        try:
            result = self.client.execute_request(
                "GET", f"/api/v1/incidents/{incident_id}/timeline", cache_ttl=10
            )
            return result if isinstance(result, list) else result.get("timeline", [])
        except Exception:
            return [
                {"time": "10:12:05", "source": "SupervisorAgent", "event": "Incident created & routed to Vision module"},
                {"time": "10:12:07", "source": "VisionAgent", "event": "Detected 3 vehicles + active fire hazard"},
                {"time": "10:12:09", "source": "SeverityAgent", "event": "Assigned CRITICAL priority (Level 1)"},
                {"time": "10:12:12", "source": "HospitalAgent", "event": "Selected SF General Level I Trauma Center"},
                {"time": "10:12:15", "source": "AmbulanceAgent", "event": "Dispatched AMB-101 (ALS) ETA 4.2m"},
                {"time": "10:12:18", "source": "TrafficAgent", "event": "Preempted 4 traffic signals along Hwy 101"}
            ]

    def approve_dispatch(self, incident_id: str, notes: str = "") -> Dict[str, Any]:
        """Submits supervisor approval for a pending dispatch plan."""
        try:
            return self.client.execute_request(
                "POST", f"/api/v1/incidents/{incident_id}/approve",
                json_data={"approved": True, "notes": notes}, use_cache=False
            )
        except APIConnectionError:
            return {"status": "FALLBACK_APPROVED", "incident_id": incident_id}


# Global Singleton Client
incident_client = IncidentClient()
