"""Core API testing logic."""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from shared.logger import get_logger

logger = get_logger(__name__)


class HTTPMethod(str, Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class APIResponse:
    """API response information."""

    url: str
    method: str
    status_code: int
    headers: Dict[str, str]
    body: Any
    elapsed_ms: float
    timestamp: datetime
    error: Optional[str] = None


class APITester:
    """HTTP API testing tool with history and collections."""

    def __init__(self, timeout: float = 30.0):
        """
        Initialize API tester.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.history: List[APIResponse] = []
        logger.debug("Initialized APITester")

    def request(
        self,
        method: HTTPMethod,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        json_data: Optional[Dict] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = True,
    ) -> APIResponse:
        """
        Make HTTP request.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            params: Query parameters
            data: Request body (form data)
            json_data: JSON request body
            auth: (username, password) tuple for basic auth
            follow_redirects: Follow redirects

        Returns:
            APIResponse object
        """
        logger.info(f"{method.value} {url}")

        start_time = datetime.now()

        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=follow_redirects,
            ) as client:
                response = client.request(
                    method=method.value,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data,
                    auth=auth,
                )

                elapsed = (datetime.now() - start_time).total_seconds() * 1000

                # Try to parse response body
                content_type = response.headers.get("content-type", "")

                if "application/json" in content_type:
                    try:
                        body = response.json()
                    except:
                        body = response.text
                else:
                    body = response.text

                api_response = APIResponse(
                    url=str(response.url),
                    method=method.value,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=body,
                    elapsed_ms=elapsed,
                    timestamp=start_time,
                )

                self.history.append(api_response)
                return api_response

        except httpx.RequestError as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Request failed: {e}")

            api_response = APIResponse(
                url=url,
                method=method.value,
                status_code=0,
                headers={},
                body=None,
                elapsed_ms=elapsed,
                timestamp=start_time,
                error=str(e),
            )

            self.history.append(api_response)
            return api_response

    def get(self, url: str, **kwargs) -> APIResponse:
        """Make GET request."""
        return self.request(HTTPMethod.GET, url, **kwargs)

    def post(self, url: str, **kwargs) -> APIResponse:
        """Make POST request."""
        return self.request(HTTPMethod.POST, url, **kwargs)

    def put(self, url: str, **kwargs) -> APIResponse:
        """Make PUT request."""
        return self.request(HTTPMethod.PUT, url, **kwargs)

    def patch(self, url: str, **kwargs) -> APIResponse:
        """Make PATCH request."""
        return self.request(HTTPMethod.PATCH, url, **kwargs)

    def delete(self, url: str, **kwargs) -> APIResponse:
        """Make DELETE request."""
        return self.request(HTTPMethod.DELETE, url, **kwargs)

    def get_history(self, limit: Optional[int] = None) -> List[APIResponse]:
        """
        Get request history.

        Args:
            limit: Maximum number of requests to return

        Returns:
            List of APIResponse (most recent first)
        """
        history = list(reversed(self.history))
        if limit:
            history = history[:limit]
        return history

    def clear_history(self) -> int:
        """Clear request history."""
        count = len(self.history)
        self.history.clear()
        return count

    def save_history(self, filepath: Path) -> None:
        """Save history to JSON file."""
        data = {
            "saved_at": datetime.now().isoformat(),
            "total": len(self.history),
            "requests": [
                {
                    "url": r.url,
                    "method": r.method,
                    "status_code": r.status_code,
                    "elapsed_ms": r.elapsed_ms,
                    "timestamp": r.timestamp.isoformat(),
                    "headers": r.headers,
                    "body": r.body if not isinstance(r.body, (bytes, bytearray)) else str(r.body),
                    "error": r.error,
                }
                for r in self.history
            ],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved history to {filepath}")
