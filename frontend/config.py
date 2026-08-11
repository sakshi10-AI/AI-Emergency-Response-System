"""
Frontend Configuration Settings

Stores frontend API URLs, session keys, and display constants.
"""
import os

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
WS_API_URL = os.getenv("WS_API_URL", "ws://localhost:8000/api/v1/ws")
DEFAULT_MAP_CENTER = [21.1458, 79.0882]  # Nagpur, Maharashtra, India
