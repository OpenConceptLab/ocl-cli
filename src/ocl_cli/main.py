"""OCL CLI entry point.

Root Click group with global options and command registration.
"""

import sys

import click

from ocl_cli import __version__
from ocl_cli.api_client import APIError, OCLAPIClient
from ocl_cli.config import CLIConfig
from ocl_cli.output import output_error


@click.group()
@click.option("--json", "-j", "json_output", is_flag=True, help="Output as JSON")
@click.option("--server", "-s", "server_id", help="OCL server to use")
@click.option("--token", help="API token override")
@click.option("--debug", "-d", is_flag=True, help="Debug output (show HTTP requests on stderr)")
@click.option("--show-request", is_flag=True, help="Show server URL and API requests on stderr")
@click.version_option(version=__version__, prog_name="ocl")
@click.pass_context
def cli(ctx, json_output, server_id, token, debug, show_request):
    """OCL CLI - Command-line interface for the Open Concept Lab API."""
    ctx.ensure_object(dict)

    config = CLIConfig.load()
    server = config.get_server(server_id)
    resolved_token = config.resolve_token(server, token_override=token)

    client = OCLAPIClient(base_url=server.base_url, token=resolved_token)
    client.debug = debug
    client.show_request = show_request

    ctx.obj["json_output"] = json_output
    ctx.obj["config"] = config
    ctx.obj["server"] = server
    ctx.obj["client"] = client

    # Ensure client is closed on exit
    ctx.call_on_close(client.close)


def handle_api_error(e: APIError) -> None:
    """Handle API errors with appropriate exit codes."""
    output_error(str(e), detail=e.detail, status_code=e.status_code)
    if e.status_code == 401 or e.status_code == 403:
        sys.exit(3)
    elif 400 <= e.status_code < 500:
        sys.exit(1)
    else:
        sys.exit(2)


# ── Register command groups ──────────────────────────────────────

from ocl_cli.commands.auth import login, logout, whoami  # noqa: E402
from ocl_cli.commands.server import server  # noqa: E402

cli.add_command(login)
cli.add_command(logout)
cli.add_command(whoami)
cli.add_command(server)

# Phase 2: Read commands
from ocl_cli.commands.org import org  # noqa: E402
from ocl_cli.commands.user import user  # noqa: E402
from ocl_cli.commands.repo import repo  # noqa: E402
from ocl_cli.commands.concept import concept  # noqa: E402
from ocl_cli.commands.mapping import mapping  # noqa: E402
from ocl_cli.commands.cascade import cascade_cmd  # noqa: E402
from ocl_cli.commands.ref import ref  # noqa: E402
from ocl_cli.commands.expansion import expansion  # noqa: E402

cli.add_command(org)
cli.add_command(user)
cli.add_command(repo)
cli.add_command(concept)
cli.add_command(mapping)
cli.add_command(cascade_cmd)
cli.add_command(ref)
cli.add_command(expansion)

# Phase 3: Task commands
from ocl_cli.commands.task import task  # noqa: E402

cli.add_command(task)

# Operational tools
from ocl_cli.commands.tool import tool  # noqa: E402

cli.add_command(tool)

# Utility commands
from ocl_cli.commands.reference import reference  # noqa: E402

cli.add_command(reference)
