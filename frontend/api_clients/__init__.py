"""
API Clients Package

Exports all singleton API Service Client instances and exception classes
for use throughout Streamlit views.
"""

from frontend.api_clients.base_client import (
    BaseAPIClient,
    base_api_client,
    APIException,
    APIConnectionError,
    AuthenticationError,
    ResourceNotFoundError,
    ServerError
)
from frontend.api_clients.auth_client import AuthenticationClient, auth_client
from frontend.api_clients.incident_client import IncidentClient, incident_client
from frontend.api_clients.hospital_client import HospitalClient, hospital_client
from frontend.api_clients.ambulance_client import AmbulanceClient, ambulance_client
from frontend.api_clients.report_client import ReportClient, report_client
from frontend.api_clients.notification_client import NotificationClient, notification_client

__all__ = [
    # Base
    "BaseAPIClient", "base_api_client",
    "APIException", "APIConnectionError", "AuthenticationError",
    "ResourceNotFoundError", "ServerError",
    # Domain Clients
    "AuthenticationClient", "auth_client",
    "IncidentClient", "incident_client",
    "HospitalClient", "hospital_client",
    "AmbulanceClient", "ambulance_client",
    "ReportClient", "report_client",
    "NotificationClient", "notification_client",
]
