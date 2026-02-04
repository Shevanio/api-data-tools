"""Tests for Webhook Receiver."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from tools.webhook_receiver.receiver import (
    PARSERS,
    WebhookReceiver,
    WebhookRequest,
    detect_webhook_type,
    parse_github_webhook,
    parse_slack_webhook,
    parse_stripe_webhook,
)


class TestWebhookRequest:
    """Test WebhookRequest dataclass."""

    def test_webhook_request_creation(self):
        """Test creating a WebhookRequest."""
        dt = datetime.now()
        request = WebhookRequest(
            id="req_001",
            timestamp=dt,
            method="POST",
            path="/webhook",
            headers={"content-type": "application/json"},
            query_params={},
            body={"test": "data"},
            source_ip="127.0.0.1",
        )

        assert request.id == "req_001"
        assert request.timestamp == dt
        assert request.method == "POST"
        assert request.path == "/webhook"
        assert request.source_ip == "127.0.0.1"
        assert request.parser_type is None
        assert request.parsed_data is None

    def test_webhook_request_with_parser(self):
        """Test WebhookRequest with parser data."""
        dt = datetime.now()
        request = WebhookRequest(
            id="req_001",
            timestamp=dt,
            method="POST",
            path="/webhook",
            headers={},
            query_params={},
            body={},
            source_ip="127.0.0.1",
            parser_type="github",
            parsed_data={"event": "push"},
        )

        assert request.parser_type == "github"
        assert request.parsed_data == {"event": "push"}


class TestWebhookReceiver:
    """Test WebhookReceiver functionality."""

    def test_init_default(self):
        """Test initialization with defaults."""
        receiver = WebhookReceiver()
        assert receiver.max_history == 100
        assert len(receiver.history) == 0

    def test_init_custom_max_history(self):
        """Test initialization with custom max_history."""
        receiver = WebhookReceiver(max_history=50)
        assert receiver.max_history == 50

    def test_add_request(self):
        """Test adding a webhook request."""
        receiver = WebhookReceiver()

        request = receiver.add_request(
            method="POST",
            path="/webhook",
            headers={"content-type": "application/json"},
            query_params={"token": "abc123"},
            body={"data": "test"},
            source_ip="192.168.1.1",
        )

        assert len(receiver.history) == 1
        assert request.id == "req_00001"
        assert request.method == "POST"
        assert request.path == "/webhook"
        assert request.source_ip == "192.168.1.1"

    def test_add_multiple_requests(self):
        """Test adding multiple requests."""
        receiver = WebhookReceiver()

        for i in range(5):
            receiver.add_request(
                method="POST",
                path=f"/webhook/{i}",
                headers={},
                query_params={},
                body={},
                source_ip="127.0.0.1",
            )

        assert len(receiver.history) == 5
        assert receiver.history[0].id == "req_00001"
        assert receiver.history[4].id == "req_00005"

    def test_history_trimming(self):
        """Test that history is trimmed when exceeding max_history."""
        receiver = WebhookReceiver(max_history=10)

        # Add 15 requests
        for i in range(15):
            receiver.add_request(
                method="POST",
                path=f"/webhook/{i}",
                headers={},
                query_params={},
                body={},
                source_ip="127.0.0.1",
            )

        # Should only keep last 10
        assert len(receiver.history) == 10
        assert receiver.history[0].path == "/webhook/5"  # First 5 removed
        assert receiver.history[-1].path == "/webhook/14"

    def test_get_history_no_limit(self):
        """Test getting full history."""
        receiver = WebhookReceiver()

        for i in range(5):
            receiver.add_request(
                method="POST",
                path=f"/webhook/{i}",
                headers={},
                query_params={},
                body={},
                source_ip="127.0.0.1",
            )

        history = receiver.get_history()
        assert len(history) == 5
        # Should be reversed (most recent first)
        assert history[0].path == "/webhook/4"
        assert history[-1].path == "/webhook/0"

    def test_get_history_with_limit(self):
        """Test getting limited history."""
        receiver = WebhookReceiver()

        for i in range(10):
            receiver.add_request(
                method="POST",
                path=f"/webhook/{i}",
                headers={},
                query_params={},
                body={},
                source_ip="127.0.0.1",
            )

        history = receiver.get_history(limit=3)
        assert len(history) == 3
        assert history[0].path == "/webhook/9"  # Most recent

    def test_get_request(self):
        """Test getting specific request by ID."""
        receiver = WebhookReceiver()

        receiver.add_request(
            method="POST",
            path="/webhook/1",
            headers={},
            query_params={},
            body={},
            source_ip="127.0.0.1",
        )

        receiver.add_request(
            method="POST",
            path="/webhook/2",
            headers={},
            query_params={},
            body={},
            source_ip="127.0.0.1",
        )

        request = receiver.get_request("req_00001")
        assert request is not None
        assert request.path == "/webhook/1"

    def test_get_request_not_found(self):
        """Test getting non-existent request."""
        receiver = WebhookReceiver()
        request = receiver.get_request("req_99999")
        assert request is None

    def test_clear_history(self):
        """Test clearing history."""
        receiver = WebhookReceiver()

        for i in range(5):
            receiver.add_request(
                method="POST",
                path=f"/webhook/{i}",
                headers={},
                query_params={},
                body={},
                source_ip="127.0.0.1",
            )

        count = receiver.clear_history()
        assert count == 5
        assert len(receiver.history) == 0

    def test_save_to_file(self, tmp_path):
        """Test saving webhook history to file."""
        receiver = WebhookReceiver()

        receiver.add_request(
            method="POST",
            path="/webhook",
            headers={"content-type": "application/json"},
            query_params={},
            body={"test": "data"},
            source_ip="127.0.0.1",
        )

        filepath = tmp_path / "webhooks.json"
        receiver.save_to_file(filepath)

        assert filepath.exists()

        with open(filepath) as f:
            data = json.load(f)

        assert "exported_at" in data
        assert data["total_requests"] == 1
        assert len(data["requests"]) == 1
        assert data["requests"][0]["method"] == "POST"

    def test_load_from_file(self, tmp_path):
        """Test loading webhook history from file."""
        # Create test file
        test_data = {
            "exported_at": datetime.now().isoformat(),
            "total_requests": 2,
            "requests": [
                {
                    "id": "req_001",
                    "timestamp": datetime.now().isoformat(),
                    "method": "POST",
                    "path": "/webhook/1",
                    "headers": {},
                    "query_params": {},
                    "body": {},
                    "source_ip": "127.0.0.1",
                },
                {
                    "id": "req_002",
                    "timestamp": datetime.now().isoformat(),
                    "method": "GET",
                    "path": "/webhook/2",
                    "headers": {},
                    "query_params": {},
                    "body": {},
                    "source_ip": "192.168.1.1",
                },
            ],
        }

        filepath = tmp_path / "webhooks.json"
        with open(filepath, "w") as f:
            json.dump(test_data, f)

        receiver = WebhookReceiver()
        count = receiver.load_from_file(filepath)

        assert count == 2
        assert len(receiver.history) == 2
        assert receiver.history[0].id == "req_001"
        assert receiver.history[1].id == "req_002"


class TestGitHubParser:
    """Test GitHub webhook parser."""

    def test_parse_push_event(self):
        """Test parsing GitHub push event."""
        headers = {"x-github-event": "push"}
        body = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "user/repo"},
            "pusher": {"name": "john"},
            "commits": [{"id": "abc123"}, {"id": "def456"}],
        }

        parsed = parse_github_webhook(headers, body)

        assert parsed is not None
        assert parsed["event"] == "push"
        assert parsed["repository"] == "user/repo"
        assert parsed["ref"] == "refs/heads/main"
        assert parsed["commits"] == 2
        assert parsed["pusher"] == "john"

    def test_parse_pull_request_event(self):
        """Test parsing GitHub pull request event."""
        headers = {"x-github-event": "pull_request"}
        body = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Fix bug",
                "user": {"login": "jane"},
            },
        }

        parsed = parse_github_webhook(headers, body)

        assert parsed is not None
        assert parsed["event"] == "pull_request"
        assert parsed["action"] == "opened"
        assert parsed["pr_number"] == 42
        assert parsed["pr_title"] == "Fix bug"
        assert parsed["pr_author"] == "jane"

    def test_parse_issues_event(self):
        """Test parsing GitHub issues event."""
        headers = {"x-github-event": "issues"}
        body = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Bug report",
            },
        }

        parsed = parse_github_webhook(headers, body)

        assert parsed is not None
        assert parsed["event"] == "issues"
        assert parsed["action"] == "opened"
        assert parsed["issue_number"] == 123
        assert parsed["issue_title"] == "Bug report"

    def test_parse_no_event_header(self):
        """Test parsing without event header."""
        headers = {}
        body = {}

        parsed = parse_github_webhook(headers, body)
        assert parsed is None

    def test_parse_invalid_body(self):
        """Test parsing with invalid body type."""
        headers = {"x-github-event": "push"}
        body = "not a dict"

        parsed = parse_github_webhook(headers, body)
        assert parsed is None


class TestStripeParser:
    """Test Stripe webhook parser."""

    def test_parse_charge_event(self):
        """Test parsing Stripe charge event."""
        headers = {}
        body = {
            "id": "evt_123",
            "type": "charge.succeeded",
            "created": 1234567890,
            "data": {
                "object": {
                    "amount": 5000,
                    "currency": "usd",
                    "status": "succeeded",
                }
            },
        }

        parsed = parse_stripe_webhook(headers, body)

        assert parsed is not None
        assert parsed["event"] == "charge.succeeded"
        assert parsed["id"] == "evt_123"
        assert parsed["amount"] == 5000
        assert parsed["currency"] == "usd"
        assert parsed["status"] == "succeeded"

    def test_parse_customer_event(self):
        """Test parsing Stripe customer event."""
        headers = {}
        body = {
            "id": "evt_456",
            "type": "customer.created",
            "created": 1234567890,
            "data": {
                "object": {
                    "id": "cus_123",
                    "email": "test@example.com",
                }
            },
        }

        parsed = parse_stripe_webhook(headers, body)

        assert parsed is not None
        assert parsed["event"] == "customer.created"
        assert parsed["customer_id"] == "cus_123"
        assert parsed["email"] == "test@example.com"


class TestSlackParser:
    """Test Slack webhook parser."""

    def test_parse_message_event(self):
        """Test parsing Slack message event."""
        headers = {}
        body = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "channel": "C123456",
                "user": "U123456",
                "text": "Hello world",
                "ts": "1234567890.123456",
            },
        }

        parsed = parse_slack_webhook(headers, body)

        assert parsed is not None
        assert parsed["type"] == "event_callback"
        assert parsed["event_type"] == "message"
        assert parsed["channel"] == "C123456"
        assert parsed["user"] == "U123456"
        assert parsed["text"] == "Hello world"


class TestDetectWebhookType:
    """Test webhook type detection."""

    def test_detect_github(self):
        """Test detecting GitHub webhook."""
        headers = {"x-github-event": "push"}
        body = {}

        webhook_type = detect_webhook_type(headers, body)
        assert webhook_type == "github"

    def test_detect_stripe(self):
        """Test detecting Stripe webhook."""
        headers = {"stripe-signature": "t=123,v1=abc"}
        body = {}

        webhook_type = detect_webhook_type(headers, body)
        assert webhook_type == "stripe"

    def test_detect_slack(self):
        """Test detecting Slack webhook."""
        headers = {}
        body = {"type": "url_verification"}

        webhook_type = detect_webhook_type(headers, body)
        assert webhook_type == "slack"

    def test_detect_unknown(self):
        """Test detecting unknown webhook type."""
        headers = {}
        body = {}

        webhook_type = detect_webhook_type(headers, body)
        assert webhook_type is None

    def test_detect_case_insensitive_headers(self):
        """Test that header detection is case-insensitive."""
        headers = {"X-GitHub-Event": "push"}  # Mixed case
        body = {}

        webhook_type = detect_webhook_type(headers, body)
        assert webhook_type == "github"


class TestParsers:
    """Test parsers registry."""

    def test_parsers_registry(self):
        """Test that parsers registry contains expected parsers."""
        assert "github" in PARSERS
        assert "stripe" in PARSERS
        assert "slack" in PARSERS

        assert callable(PARSERS["github"])
        assert callable(PARSERS["stripe"])
        assert callable(PARSERS["slack"])
