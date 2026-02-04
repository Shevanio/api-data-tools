"""Core webhook receiving and storage logic."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WebhookRequest:
    """Represents a received webhook request."""

    id: str
    timestamp: datetime
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    body: Any
    source_ip: str
    parser_type: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None


class WebhookReceiver:
    """
    Manages webhook storage and retrieval.

    Attributes:
        history: List of received webhook requests
        max_history: Maximum number of requests to keep in memory
    """

    def __init__(self, max_history: int = 100):
        """
        Initialize webhook receiver.

        Args:
            max_history: Maximum number of requests to keep in memory
        """
        self.history: List[WebhookRequest] = []
        self.max_history = max_history
        self._request_counter = 0

    def add_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        query_params: Dict[str, str],
        body: Any,
        source_ip: str,
    ) -> WebhookRequest:
        """
        Add a new webhook request to history.

        Args:
            method: HTTP method
            path: Request path
            headers: Request headers
            query_params: Query parameters
            body: Request body
            source_ip: Source IP address

        Returns:
            Created WebhookRequest
        """
        self._request_counter += 1

        request = WebhookRequest(
            id=f"req_{self._request_counter:05d}",
            timestamp=datetime.now(),
            method=method,
            path=path,
            headers=headers,
            query_params=query_params,
            body=body,
            source_ip=source_ip,
        )

        self.history.append(request)

        # Trim history if needed
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

        logger.info(f"Received {method} {path} from {source_ip}")
        return request

    def get_history(self, limit: Optional[int] = None) -> List[WebhookRequest]:
        """
        Get webhook request history.

        Args:
            limit: Maximum number of requests to return

        Returns:
            List of WebhookRequest objects (most recent first)
        """
        history = list(reversed(self.history))
        if limit:
            history = history[:limit]
        return history

    def get_request(self, request_id: str) -> Optional[WebhookRequest]:
        """
        Get a specific request by ID.

        Args:
            request_id: Request ID

        Returns:
            WebhookRequest or None if not found
        """
        for request in self.history:
            if request.id == request_id:
                return request
        return None

    def clear_history(self) -> int:
        """
        Clear all webhook history.

        Returns:
            Number of requests cleared
        """
        count = len(self.history)
        self.history.clear()
        self._request_counter = 0
        logger.info(f"Cleared {count} webhook requests")
        return count

    def save_to_file(self, filepath: Path) -> None:
        """
        Save webhook history to JSON file.

        Args:
            filepath: Path to save file
        """
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_requests": len(self.history),
            "requests": [
                {
                    **asdict(req),
                    "timestamp": req.timestamp.isoformat(),
                }
                for req in self.history
            ],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(self.history)} requests to {filepath}")

    def load_from_file(self, filepath: Path) -> int:
        """
        Load webhook history from JSON file.

        Args:
            filepath: Path to load file

        Returns:
            Number of requests loaded
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        loaded_count = 0
        for req_data in data.get("requests", []):
            req_data["timestamp"] = datetime.fromisoformat(req_data["timestamp"])
            request = WebhookRequest(**req_data)
            self.history.append(request)
            loaded_count += 1

        logger.info(f"Loaded {loaded_count} requests from {filepath}")
        return loaded_count


# Parser utilities for common webhook providers


def parse_github_webhook(headers: Dict[str, str], body: Any) -> Optional[Dict[str, Any]]:
    """
    Parse GitHub webhook payload.

    Args:
        headers: Request headers
        body: Request body

    Returns:
        Parsed data or None
    """
    event_type = headers.get("x-github-event")
    if not event_type:
        return None

    if not isinstance(body, dict):
        return None

    parsed = {"event": event_type}

    if event_type == "push":
        parsed["repository"] = body.get("repository", {}).get("full_name")
        parsed["ref"] = body.get("ref")
        parsed["commits"] = len(body.get("commits", []))
        parsed["pusher"] = body.get("pusher", {}).get("name")

    elif event_type == "pull_request":
        pr = body.get("pull_request", {})
        parsed["action"] = body.get("action")
        parsed["pr_number"] = pr.get("number")
        parsed["pr_title"] = pr.get("title")
        parsed["pr_author"] = pr.get("user", {}).get("login")

    elif event_type == "issues":
        issue = body.get("issue", {})
        parsed["action"] = body.get("action")
        parsed["issue_number"] = issue.get("number")
        parsed["issue_title"] = issue.get("title")

    return parsed


def parse_stripe_webhook(headers: Dict[str, str], body: Any) -> Optional[Dict[str, Any]]:
    """
    Parse Stripe webhook payload.

    Args:
        headers: Request headers
        body: Request body

    Returns:
        Parsed data or None
    """
    if not isinstance(body, dict):
        return None

    event_type = body.get("type")
    if not event_type:
        return None

    parsed = {
        "event": event_type,
        "id": body.get("id"),
        "created": body.get("created"),
    }

    data = body.get("data", {}).get("object", {})

    if "charge" in event_type:
        parsed["amount"] = data.get("amount")
        parsed["currency"] = data.get("currency")
        parsed["status"] = data.get("status")

    elif "customer" in event_type:
        parsed["customer_id"] = data.get("id")
        parsed["email"] = data.get("email")

    return parsed


def parse_slack_webhook(headers: Dict[str, str], body: Any) -> Optional[Dict[str, Any]]:
    """
    Parse Slack webhook payload.

    Args:
        headers: Request headers
        body: Request body

    Returns:
        Parsed data or None
    """
    if not isinstance(body, dict):
        return None

    event = body.get("event", {})

    parsed = {
        "type": body.get("type"),
        "event_type": event.get("type"),
        "channel": event.get("channel"),
        "user": event.get("user"),
        "text": event.get("text"),
        "ts": event.get("ts"),
    }

    return parsed


PARSERS = {
    "github": parse_github_webhook,
    "stripe": parse_stripe_webhook,
    "slack": parse_slack_webhook,
}


def detect_webhook_type(headers: Dict[str, str], body: Any) -> Optional[str]:
    """
    Auto-detect webhook provider from headers.

    Args:
        headers: Request headers
        body: Request body

    Returns:
        Provider name or None
    """
    headers_lower = {k.lower(): v for k, v in headers.items()}

    if "x-github-event" in headers_lower:
        return "github"
    elif "stripe-signature" in headers_lower:
        return "stripe"
    elif isinstance(body, dict) and body.get("type") == "url_verification":
        return "slack"

    return None
