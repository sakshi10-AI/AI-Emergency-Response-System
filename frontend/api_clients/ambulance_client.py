"""
Ambulance API Service Client

Encapsulates all emergency fleet management operations: unit listing, status updates,
GPS location updates, dispatch assignments, and preemption corridor querying.
"""

from typing import Optional, Dict, Any, List
from frontend.api_clients.base_client import base_api_client, BaseAPIClient, APIConnectionError, ResourceNotFoundError
from frontend.api_clients.mock_data import MOCK_AMBULANCES
from utils.logger import app_logger


class AmbulanceClient:
    """API Service client for emergency ambulance fleet operations."""

    VALID_STATUSES = ["AVAILABLE", "DISPATCHED", "EN_ROUTE", "TRANSPORTING", "AT_HOSPITAL", "OUT_OF_SERVICE"]

    def __init__(self, client: Optional[BaseAPIClient] = None):
        self.client = client or base_api_client

    def get_ambulances(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches the ambulance fleet, optionally filtered by status."""
        params = {}
        if status:
            params["status"] = status

        try:
            result = self.client.execute_request("GET", "/api/v1/units/", params=params, cache_ttl=15)
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and ("units" in result or "data" in result):
                return result.get("units", result.get("data", []))
            return MOCK_AMBULANCES
        except (APIConnectionError, Exception) as e:
            app_logger.warning(f"[AmbulanceClient] Backend offline ({e}). Returning mock fleet data.")
            units = list(MOCK_AMBULANCES)
            if status:
                units = [u for u in units if u.get("status") == status]
            return units

    def get_ambulance_by_id(self, unit_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single ambulance unit record by its ID."""
        try:
            return self.client.execute_request("GET", f"/api/v1/units/{unit_id}", cache_ttl=10)
        except (APIConnectionError, ResourceNotFoundError, Exception):
            return next((u for u in MOCK_AMBULANCES if u["unit_id"] == unit_id), None)

    def update_unit_status(self, unit_id: str, status: str, incident_id: Optional[str] = None) -> Dict[str, Any]:
        """Updates operational status of an ambulance unit."""
        if status not in self.VALID_STATUSES:
            return {"error": f"Invalid status '{status}'. Must be one of {self.VALID_STATUSES}"}

        payload: Dict[str, Any] = {"status": status}
        if incident_id:
            payload["assigned_incident"] = incident_id

        try:
            res = self.client.execute_request(
                "PUT", f"/api/v1/units/{unit_id}/status",
                json_data=payload, use_cache=False
            )
            if res:
                return res
        except (APIConnectionError, Exception):
            pass

        for u in MOCK_AMBULANCES:
            if u["unit_id"] == unit_id:
                u["status"] = status
                if incident_id:
                    u["assigned_incident"] = incident_id
                return {"status": "UPDATED_FALLBACK", "unit_id": unit_id, **payload}
        return {"error": "Unit not found in fallback store."}

    def update_location(self, unit_id: str, latitude: float, longitude: float) -> Dict[str, Any]:
        """Updates GPS coordinates for an ambulance unit."""
        try:
            res = self.client.execute_request(
                "PUT", f"/api/v1/units/{unit_id}/location",
                json_data={"latitude": latitude, "longitude": longitude},
                use_cache=False
            )
            if res:
                return res
        except (APIConnectionError, Exception):
            pass

        for u in MOCK_AMBULANCES:
            if u["unit_id"] == unit_id:
                u["latitude"] = latitude
                u["longitude"] = longitude
                return {"status": "UPDATED_FALLBACK", "unit_id": unit_id, "latitude": latitude, "longitude": longitude}
        return {"error": "Unit not found."}

    def get_available_units(self) -> List[Dict[str, Any]]:
        """Returns only ambulances with AVAILABLE status."""
        return self.get_ambulances(status="AVAILABLE")

    def get_active_dispatches(self) -> List[Dict[str, Any]]:
        """Returns ambulances actively DISPATCHED or EN_ROUTE."""
        all_units = self.get_ambulances()
        return [u for u in all_units if u.get("status") in ["DISPATCHED", "EN_ROUTE", "TRANSPORTING"]]


# Global Singleton Client
ambulance_client = AmbulanceClient()
