"""
Hospital API Service Client

Encapsulates all hospital capacity operations: querying trauma centers, filtering by
specialty/trauma level, ICU bed reservation, capacity updates, and incoming unit tracking.
"""

from typing import Optional, Dict, Any, List
from frontend.api_clients.base_client import base_api_client, BaseAPIClient, APIConnectionError, ResourceNotFoundError
from frontend.api_clients.mock_data import MOCK_HOSPITALS
from utils.logger import app_logger


class HospitalClient:
    """API Service client for hospital capacity and routing operations."""

    def __init__(self, client: Optional[BaseAPIClient] = None):
        self.client = client or base_api_client

    def get_hospitals(
        self,
        specialty: Optional[str] = None,
        trauma_level: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetches the regional hospital network with optional filters."""
        params = {}
        if specialty:
            params["specialty"] = specialty
        if trauma_level:
            params["trauma_level"] = trauma_level
        if status:
            params["status"] = status

        try:
            result = self.client.execute_request("GET", "/api/v1/hospitals/", params=params, cache_ttl=20)
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and ("hospitals" in result or "data" in result):
                return result.get("hospitals", result.get("data", []))
            return MOCK_HOSPITALS
        except (APIConnectionError, Exception) as e:
            app_logger.warning(f"[HospitalClient] Backend offline ({e}). Returning mock hospital data.")
            hospitals = list(MOCK_HOSPITALS)
            if specialty:
                hospitals = [h for h in hospitals if specialty in h.get("specialties", [])]
            if trauma_level:
                hospitals = [h for h in hospitals if h.get("trauma_level") == trauma_level]
            if status:
                hospitals = [h for h in hospitals if h.get("status") == status]
            return hospitals

    def get_hospital_by_id(self, hospital_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single hospital record by ID."""
        try:
            return self.client.execute_request("GET", f"/api/v1/hospitals/{hospital_id}", cache_ttl=15)
        except (APIConnectionError, ResourceNotFoundError, Exception):
            return next((h for h in MOCK_HOSPITALS if h["hospital_id"] == hospital_id), None)

    def reserve_icu_bed(self, hospital_id: str) -> Dict[str, Any]:
        """Reserves one ICU bed at the specified hospital."""
        try:
            res = self.client.execute_request(
                "POST", f"/api/v1/hospitals/{hospital_id}/reserve-bed",
                json_data={}, use_cache=False
            )
            if res:
                return res
        except (APIConnectionError, Exception):
            pass

        # Update local mock data fallback
        for h in MOCK_HOSPITALS:
            if h["hospital_id"] == hospital_id and h["available_icu_beds"] > 0:
                h["available_icu_beds"] -= 1
                return {"status": "RESERVED_FALLBACK", "hospital_id": hospital_id, "available_icu_beds": h["available_icu_beds"]}
        return {"status": "ERROR", "message": "No ICU beds available or hospital not found."}

    def update_capacity(
        self,
        hospital_id: str,
        available_icu_beds: Optional[int] = None,
        er_occupancy_percent: Optional[int] = None
    ) -> Dict[str, Any]:
        """Updates live capacity metrics for a hospital."""
        payload: Dict[str, Any] = {}
        if available_icu_beds is not None:
            payload["available_icu_beds"] = available_icu_beds
        if er_occupancy_percent is not None:
            payload["er_occupancy_percent"] = er_occupancy_percent

        try:
            res = self.client.execute_request(
                "PUT", f"/api/v1/hospitals/{hospital_id}/capacity",
                json_data=payload, use_cache=False
            )
            if res:
                return res
        except (APIConnectionError, Exception):
            pass

        for h in MOCK_HOSPITALS:
            if h["hospital_id"] == hospital_id:
                h.update(payload)
                return {"status": "UPDATED_FALLBACK", **payload}
        return {"error": "Hospital not found in fallback store."}

    def get_incoming_ambulances(self, hospital_id: str) -> List[Dict[str, Any]]:
        """Fetches incoming ambulance pre-arrival notifications for a hospital."""
        try:
            result = self.client.execute_request(
                "GET", f"/api/v1/hospitals/{hospital_id}/incoming-ambulances", cache_ttl=10
            )
            if isinstance(result, list):
                return result
            return result.get("ambulances", [])
        except Exception:
            return [
                {"unit": "AMB-101 (Medic 101)", "eta_minutes": 4.2, "condition": "Severe Burn & Trauma", "vitals": "BP 110/70, HR 115"},
                {"unit": "AMB-102 (Medic 102)", "eta_minutes": 6.0, "condition": "Chemical Inhalation", "vitals": "SpO2 91%, HR 98"},
            ]


# Global Singleton Client
hospital_client = HospitalClient()
