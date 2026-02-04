"""CLI interface for Webhook Receiver."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.cli import error, info, success
from shared.logger import setup_logger

from .receiver import PARSERS, WebhookReceiver, detect_webhook_type

# Global receiver instance
receiver = WebhookReceiver()

# FastAPI app
app = FastAPI(
    title="Webhook Receiver",
    description="Local webhook debugging server",
    version="0.1.0",
)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def catch_all(request: Request, path: str = ""):
    """Catch-all route to receive webhooks on any path."""
    # Extract request data
    method = request.method
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    source_ip = request.client.host

    # Parse body
    content_type = headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
        except:
            body = await request.body()
            body = body.decode("utf-8") if body else ""
    else:
        body = await request.body()
        body = body.decode("utf-8") if body else ""

    # Add request to history
    webhook_request = receiver.add_request(
        method=method,
        path=f"/{path}",
        headers=headers,
        query_params=query_params,
        body=body,
        source_ip=source_ip,
    )

    # Auto-detect webhook type
    parser_type = detect_webhook_type(headers, body)
    if parser_type and parser_type in PARSERS:
        parsed = PARSERS[parser_type](headers, body)
        webhook_request.parser_type = parser_type
        webhook_request.parsed_data = parsed

    # Display webhook info
    display_webhook(webhook_request, parser_type)

    # Return success response
    return JSONResponse(
        content={"status": "received", "id": webhook_request.id, "timestamp": webhook_request.timestamp.isoformat()},
        status_code=200,
    )


@app.get("/")
async def root():
    """Root endpoint showing receiver status."""
    history = receiver.get_history(limit=10)

    return JSONResponse(
        content={
            "status": "running",
            "total_requests": len(receiver.history),
            "recent_requests": [
                {
                    "id": req.id,
                    "timestamp": req.timestamp.isoformat(),
                    "method": req.method,
                    "path": req.path,
                }
                for req in history
            ],
        }
    )


@app.get("/_history")
async def get_history(limit: int = 50):
    """Get webhook history."""
    history = receiver.get_history(limit=limit)

    return JSONResponse(
        content={
            "total": len(receiver.history),
            "returned": len(history),
            "requests": [
                {
                    "id": req.id,
                    "timestamp": req.timestamp.isoformat(),
                    "method": req.method,
                    "path": req.path,
                    "source_ip": req.source_ip,
                    "parser_type": req.parser_type,
                    "parsed_data": req.parsed_data,
                }
                for req in history
            ],
        }
    )


@app.delete("/_history")
async def clear_history():
    """Clear webhook history."""
    count = receiver.clear_history()
    return JSONResponse(content={"status": "cleared", "count": count})


def display_webhook(webhook: Any, parser_type: Optional[str] = None):
    """Display webhook information in console."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax

    console = Console()

    # Header
    header = f"[bold cyan]{webhook.method}[/bold cyan] {webhook.path}"
    if parser_type:
        header += f" [magenta]({parser_type})[/magenta]"

    console.print(f"\n{header}")
    console.print(f"[dim]ID: {webhook.id} | Time: {webhook.timestamp.strftime('%H:%M:%S')} | From: {webhook.source_ip}[/dim]")

    # Parsed data (if available)
    if webhook.parsed_data:
        console.print("\n[bold yellow]Parsed Data:[/bold yellow]")
        for key, value in webhook.parsed_data.items():
            console.print(f"  {key}: {value}")

    # Headers (important ones)
    important_headers = ["content-type", "user-agent", "x-github-event", "stripe-signature"]
    filtered_headers = {k: v for k, v in webhook.headers.items() if k.lower() in important_headers}

    if filtered_headers:
        console.print("\n[bold yellow]Headers:[/bold yellow]")
        for key, value in filtered_headers.items():
            console.print(f"  {key}: {value}")

    # Body
    if webhook.body:
        console.print("\n[bold yellow]Body:[/bold yellow]")
        if isinstance(webhook.body, dict):
            body_str = json.dumps(webhook.body, indent=2)
            syntax = Syntax(body_str, "json", theme="monokai", line_numbers=False)
            console.print(syntax)
        else:
            console.print(f"  {str(webhook.body)[:500]}")

    console.print("[dim]" + "─" * 80 + "[/dim]")


@click.command()
@click.option(
    "--port",
    "-p",
    type=int,
    default=3000,
    show_default=True,
    help="Port to run server on",
)
@click.option(
    "--host",
    default="0.0.0.0",
    show_default=True,
    help="Host to bind to",
)
@click.option(
    "--save",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Save webhooks to file on exit",
)
@click.option(
    "--load",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Load webhooks from file on start",
)
@click.option(
    "--parser",
    type=click.Choice(list(PARSERS.keys()), case_sensitive=False),
    help="Force specific webhook parser (github, stripe, slack)",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def main(
    port: int,
    host: str,
    save: Optional[Path],
    load: Optional[Path],
    parser: Optional[str],
    verbose: bool,
):
    """
    Webhook Receiver - Local server for webhook debugging.

    This tool starts a local HTTP server that receives and displays
    webhooks in real-time. Perfect for debugging webhook integrations.

    Examples:

        \b
        # Start receiver on default port (3000)
        webhook-recv

        \b
        # Start on custom port
        webhook-recv --port 8080

        \b
        # Save webhooks to file on exit
        webhook-recv --save webhooks.json

        \b
        # Load previous webhooks
        webhook-recv --load webhooks.json

    Endpoints:
        GET  /           - Status and recent requests
        GET  /_history   - Full webhook history
        DELETE /_history - Clear history
        *    /*          - Receive webhooks (any method, any path)
    """
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logger(__name__, level=log_level)

    # Load previous webhooks if requested
    if load:
        try:
            count = receiver.load_from_file(load)
            success(f"Loaded {count} previous webhooks from {load}")
        except Exception as e:
            error(f"Failed to load webhooks: {e}")
            sys.exit(1)

    # Display startup info
    info(f"Starting Webhook Receiver on http://{host}:{port}")
    info("Press CTRL+C to stop")
    info("\nEndpoints:")
    info(f"  GET    http://localhost:{port}/         - Status")
    info(f"  GET    http://localhost:{port}/_history - View history")
    info(f"  DELETE http://localhost:{port}/_history - Clear history")
    info(f"  *      http://localhost:{port}/*         - Receive webhooks")
    info("\n" + "─" * 80)

    try:
        # Run server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="error" if not verbose else "info",
        )
    except KeyboardInterrupt:
        info("\n\nShutting down...")

        # Save webhooks if requested
        if save:
            try:
                receiver.save_to_file(save)
                success(f"Saved {len(receiver.history)} webhooks to {save}")
            except Exception as e:
                error(f"Failed to save webhooks: {e}")

        success("Webhook Receiver stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
