"""CLI interface for API Tester."""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from shared.cli import error, handle_errors, info, success, warning
from shared.logger import setup_logger

from .tester import APITester, HTTPMethod

console = Console()


def display_response(response, show_body: bool = True) -> None:
    """Display API response."""
    if response.error:
        error(f"Request failed: {response.error}")
        return

    # Status line
    status_color = "green" if 200 <= response.status_code < 300 else "red" if response.status_code >= 400 else "yellow"
    console.print(f"\n[{status_color}]HTTP {response.status_code}[/{status_color}] - {response.elapsed_ms:.0f}ms")

    # Headers
    console.print("\n[bold yellow]Headers:[/bold yellow]")
    for key, value in list(response.headers.items())[:10]:  # Show first 10
        console.print(f"  {key}: {value}")

    # Body
    if show_body and response.body:
        console.print("\n[bold yellow]Body:[/bold yellow]")

        if isinstance(response.body, dict) or isinstance(response.body, list):
            body_str = json.dumps(response.body, indent=2)
            syntax = Syntax(body_str, "json", theme="monokai", line_numbers=False)
            console.print(syntax)
        else:
            console.print(str(response.body)[:1000])

    console.print()


@click.command()
@click.argument("url")
@click.option(
    "--method",
    "-X",
    type=click.Choice(["GET", "POST", "PUT", "PATCH", "DELETE"], case_sensitive=False),
    default="GET",
    help="HTTP method",
)
@click.option(
    "--header",
    "-H",
    multiple=True,
    help="Header in format 'Key: Value'",
)
@click.option(
    "--data",
    "-d",
    help="Request body (JSON string)",
)
@click.option(
    "--auth",
    "-a",
    help="Basic auth in format 'username:password'",
)
@click.option(
    "--bearer",
    "-b",
    help="Bearer token",
)
@click.option(
    "--timeout",
    "-t",
    type=float,
    default=30.0,
    help="Request timeout in seconds",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Save response to file",
)
@click.option(
    "--no-body",
    is_flag=True,
    help="Don't show response body",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@handle_errors
def main(
    url: str,
    method: str,
    header: tuple,
    data: Optional[str],
    auth: Optional[str],
    bearer: Optional[str],
    timeout: float,
    output: Optional[Path],
    no_body: bool,
    verbose: bool,
):
    """
    API Tester - HTTP API testing tool.

    Examples:

        \b
        # Simple GET request
        api-test https://api.github.com

        \b
        # POST with JSON
        api-test https://httpbin.org/post -X POST -d '{"name":"test"}'

        \b
        # With headers
        api-test https://api.example.com -H "Authorization: Bearer TOKEN"

        \b
        # Basic auth
        api-test https://api.example.com --auth "user:pass"

        \b
        # Bearer token
        api-test https://api.example.com --bearer "your-token"

        \b
        # Save response
        api-test https://api.github.com/users/octocat -o response.json
    """
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logger(__name__, level=log_level)

    # Initialize tester
    tester = APITester(timeout=timeout)

    # Parse headers
    headers_dict = {}
    for h in header:
        if ":" not in h:
            error(f"Invalid header format: {h}. Use 'Key: Value'")
            sys.exit(1)
        key, value = h.split(":", 1)
        headers_dict[key.strip()] = value.strip()

    # Add bearer token if specified
    if bearer:
        headers_dict["Authorization"] = f"Bearer {bearer}"

    # Parse auth
    auth_tuple = None
    if auth:
        if ":" not in auth:
            error("Invalid auth format. Use 'username:password'")
            sys.exit(1)
        username, password = auth.split(":", 1)
        auth_tuple = (username, password)

    # Parse JSON data
    json_data = None
    if data:
        try:
            json_data = json.loads(data)
        except json.JSONDecodeError as e:
            error(f"Invalid JSON data: {e}")
            sys.exit(1)

    # Make request
    info(f"{method} {url}")

    http_method = HTTPMethod(method.upper())
    response = tester.request(
        method=http_method,
        url=url,
        headers=headers_dict if headers_dict else None,
        json_data=json_data,
        auth=auth_tuple,
    )

    # Display response
    if not response.error:
        display_response(response, show_body=not no_body)

        if 200 <= response.status_code < 300:
            success(f"Request successful ({response.elapsed_ms:.0f}ms)")
        else:
            warning(f"Request completed with status {response.status_code}")

        # Save to file if requested
        if output:
            if isinstance(response.body, (dict, list)):
                with open(output, "w") as f:
                    json.dump(response.body, f, indent=2)
            else:
                with open(output, "w") as f:
                    f.write(str(response.body))
            success(f"Response saved to {output}")

        sys.exit(0)
    else:
        error(f"Request failed: {response.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
