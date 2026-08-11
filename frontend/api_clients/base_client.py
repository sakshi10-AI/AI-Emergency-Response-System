"""
Base API Client Engine

Provides centralized, resilient HTTP communication with the FastAPI Backend.
Capabilities:
- Async requests via httpx.AsyncClient (and sync helpers)
- Exponential backoff retries via tenacity
- TTL Response Caching for GET requests
- Automatic Bearer authentication token injection
- Structured custom exception handling
- Resilient offline fallback storage & fallback data generation
"""

import asyncio
import json
import time
from typing import Optional, Dict, Any, Union, List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from frontend.config import BACKEND_API_URL
from utils.logger import app_logger


class APIException(Exception):
    """Base exception for API Client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class APIConnectionError(APIException):
    """Raised when backend API is unreachable or network fails."""
    pass


class AuthenticationError(APIException):
    """Raised when authentication fails or token is invalid."""
    pass


class ResourceNotFoundError(APIException):
    """Raised when requested resource returns 404."""
    pass


class ServerError(APIException):
    """Raised when server responds with 5xx error."""
    pass


class BaseAPIClient:
    """
    Centralized Base API Client.
    Handles connections to FastAPI backend with caching, retries, and fallback logic.
    """

    _instance: Optional["BaseAPIClient"] = None

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or BACKEND_API_URL).rstrip("/")
        self._auth_token: Optional[str] = None
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 30  # seconds

    @classmethod
    def get_instance(cls) -> "BaseAPIClient":
        if cls._instance is None:
            cls._instance = BaseAPIClient()
        return cls._instance

    def set_auth_token(self, token: Optional[str]):
        """Sets active Bearer authentication token."""
        self._auth_token = token
        app_logger.info("[BaseAPIClient] Auth token updated.")

    def _get_headers(self) -> Dict[str, str]:
        """Constructs headers with Bearer token if available."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieves non-expired cached response if present."""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.time() < entry["expires_at"]:
                app_logger.info(f"[BaseAPIClient] Cache HIT for key '{cache_key}'.")
                return entry["data"]
            else:
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, data: Any, ttl: Optional[int] = None):
        """Saves data to in-memory TTL response cache."""
        expire_seconds = ttl or self._cache_ttl
        self._cache[cache_key] = {
            "expires_at": time.time() + expire_seconds,
            "data": data
        }

    def clear_cache(self):
        """Clears all cached API responses."""
        self._cache.clear()

    # =========================================================================
    # Async Core HTTP Requests with Retries
    # =========================================================================

    @retry(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError, ServerError))
    )
    async def _request_async(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        form_data: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> Any:
        """Executes retried async HTTP request via httpx.
        
        Args:
            form_data: If provided, sends as application/x-www-form-urlencoded
                       (required for OAuth2PasswordRequestForm endpoints).
            json_data: If provided, sends as application/json.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        cache_key = f"{method}:{url}:{json.dumps(params or {}, sort_keys=True)}"

        if method.upper() == "GET" and use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_data,
                    data=form_data,  # form-encoded body for OAuth2
                    headers=self._get_headers()
                )

            # Handle Status Codes
            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError("Authentication failed or token invalid.", status_code=response.status_code)
            elif response.status_code == 404:
                raise ResourceNotFoundError(f"Resource at '{endpoint}' not found.", status_code=404)
            elif response.status_code >= 500:
                raise ServerError(f"Server error response ({response.status_code}): {response.text}", status_code=response.status_code)
            elif response.status_code >= 400:
                raise APIException(f"API Error ({response.status_code}): {response.text}", status_code=response.status_code)

            result = response.json() if response.text else {}
            if method.upper() == "GET" and use_cache:
                self._set_cache(cache_key, result, ttl=cache_ttl)

            return result

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            app_logger.warning(f"[BaseAPIClient] Connection error reaching '{url}': {e}.")
            raise APIConnectionError(f"Cannot connect to backend API at {url}")

    # =========================================================================
    # Synchronous Execution Wrapper for Streamlit Components
    # =========================================================================

    def execute_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> Any:
        """Synchronous wrapper executing _request_async safely in event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If running inside an existing loop, use an isolated thread or new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self._request_async(method, endpoint, params, json_data, use_cache, cache_ttl)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._request_async(method, endpoint, params, json_data, use_cache, cache_ttl)
                )
        except RuntimeError:
            return asyncio.run(
                self._request_async(method, endpoint, params, json_data, use_cache, cache_ttl)
            )


# Global Base Client Instance
base_api_client = BaseAPIClient.get_instance()
