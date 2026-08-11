"""
FastAPI Notifications & EOC Alert Router

Provides endpoints for sending dispatcher alerts, broadcasting public emergency SMS alerts,
and retrieving system notifications.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/notifications", tags=["EOC Notifications & Alerts"])

# In-memory notifications store
_NOTIFICATIONS_DB: List[Dict[str, Any]] = [
    {"id": "NOTIF-001", "type": "DISPATCH", "message": "AMB-101 dispatched to INC-8821", "priority": "HIGH", "timestamp": "10:12:15", "read": False},
    {"id": "NOTIF-002", "type": "HOSPITAL_ALERT", "message": "SF General ICU capacity at 85%", "priority": "MEDIUM", "timestamp": "10:10:30", "read": False},
    {"id": "NOTIF-003", "type": "PUBLIC_SMS", "message": "Traffic alert: Hwy 101 northbound closed", "priority": "LOW", "timestamp": "10:08:00", "read": True},
]


class DispatcherAlertRequest(BaseModel):
    message: str = Field(..., min_length=1)
    priority: str = Field(default="HIGH")
    incident_id: Optional[str] = None


class PublicSmsRequest(BaseModel):
    sector: str = Field(..., min_length=1)
    alert_text: str = Field(..., min_length=1)
    severity: str = Field(default="WARNING")


@router.get("/", response_model=List[Dict[str, Any]])
async def get_recent_notifications(limit: int = Query(20, ge=1, le=100)):
    """Retrieves recent notifications list."""
    return _NOTIFICATIONS_DB[:limit]


@router.post("/dispatcher-alert", response_model=Dict[str, Any])
async def send_dispatcher_alert(req: DispatcherAlertRequest):
    """Sends a priority alert message to all active EOC dispatchers."""
    notif_id = f"NOTIF-{len(_NOTIFICATIONS_DB)+1:03d}"
    entry = {
        "id": notif_id,
        "type": "DISPATCHER_ALERT",
        "message": req.message,
        "priority": req.priority,
        "incident_id": req.incident_id,
        "timestamp": "JUST_NOW",
        "read": False
    }
    _NOTIFICATIONS_DB.insert(0, entry)
    return {"status": "DELIVERED", "notification": entry}


@router.post("/public-sms", response_model=Dict[str, Any])
async def broadcast_public_sms(req: PublicSmsRequest):
    """Broadcasts a public emergency SMS alert to a geographic sector."""
    notif_id = f"NOTIF-{len(_NOTIFICATIONS_DB)+1:03d}"
    entry = {
        "id": notif_id,
        "type": "PUBLIC_SMS",
        "message": f"[{req.sector}] {req.alert_text}",
        "priority": req.severity,
        "timestamp": "JUST_NOW",
        "read": False
    }
    _NOTIFICATIONS_DB.insert(0, entry)
    return {"status": "BROADCAST_SENT", "sector": req.sector, "subscribers_notified": 14200}


@router.put("/{notification_id}/read", response_model=Dict[str, Any])
async def mark_notification_read(notification_id: str):
    """Marks a notification as acknowledged/read."""
    for n in _NOTIFICATIONS_DB:
        if n["id"] == notification_id:
            n["read"] = True
            return {"status": "success", "notification_id": notification_id}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification '{notification_id}' not found.")
