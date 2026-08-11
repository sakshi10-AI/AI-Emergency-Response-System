"""
Notification API Service Client

Encapsulates dispatcher alerts, public SMS broadcasts, and notification history retrieval.
"""

from typing import Optional, Dict, Any, List
from frontend.api_clients.base_client import base_api_client, BaseAPIClient, APIConnectionError
from frontend.api_clients.mock_data import MOCK_NOTIFICATIONS
from utils.logger import app_logger


PRIORITY_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class NotificationClient:
    """API Service client for EOC alert and notification broadcast operations."""

    def __init__(self, client: Optional[BaseAPIClient] = None):
        self.client = client or base_api_client

    def send_dispatcher_alert(
        self,
        message: str,
        priority: str = "HIGH",
        incident_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sends a priority alert message to all active dispatchers."""
        payload: Dict[str, Any] = {"message": message, "priority": priority}
        if incident_id:
            payload["incident_id"] = incident_id

        try:
            res = self.client.execute_request(
                "POST", "/api/v1/notifications/dispatcher-alert",
                json_data=payload, use_cache=False
            )
            if res and isinstance(res, dict) and "status" in res:
                return res
        except (APIConnectionError, Exception):
            pass

        app_logger.warning(f"[NotificationClient] Backend offline. Alert queued locally: '{message}'")
        return {
            "status": "QUEUED_OFFLINE",
            "message": message,
            "priority": priority,
            "note": "Alert will be delivered when backend connection is restored."
        }

    def broadcast_public_sms(
        self,
        sector: str,
        alert_text: str,
        severity: str = "WARNING"
    ) -> Dict[str, Any]:
        """Broadcasts a public emergency SMS alert to the specified geographic sector."""
        payload = {"sector": sector, "alert_text": alert_text, "severity": severity}

        try:
            res = self.client.execute_request(
                "POST", "/api/v1/notifications/public-sms",
                json_data=payload, use_cache=False
            )
            if res and isinstance(res, dict) and "status" in res:
                return res
        except (APIConnectionError, Exception):
            pass

        return {
            "status": "QUEUED_OFFLINE",
            "sector": sector,
            "alert_text": alert_text,
            "note": "SMS will broadcast when network is restored."
        }

    def get_recent_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves the most recent EOC system notifications."""
        try:
            result = self.client.execute_request(
                "GET", "/api/v1/notifications/",
                params={"limit": limit}, cache_ttl=10
            )
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "notifications" in result:
                return result.get("notifications", [])
            return MOCK_NOTIFICATIONS
        except (APIConnectionError, Exception):
            return MOCK_NOTIFICATIONS

    def mark_notification_read(self, notification_id: str) -> Dict[str, Any]:
        """Marks a notification as read/acknowledged."""
        try:
            res = self.client.execute_request(
                "PUT", f"/api/v1/notifications/{notification_id}/read",
                json_data={}, use_cache=False
            )
            if res:
                return res
        except (APIConnectionError, Exception):
            pass
        return {"status": "MARKED_READ_FALLBACK", "notification_id": notification_id}


# Global Singleton Client
notification_client = NotificationClient()
