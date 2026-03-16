"""Authentication commands: login, logout, whoami."""

import sys

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import output_result


@click.command()
@click.pass_context
def login(ctx):
    """Store an API token for the current server."""
    server = ctx.obj["server"]
    config = ctx.obj["config"]

    click.echo(f"Logging in to {server.name} ({server.base_url})")
    token = click.prompt("API Token", hide_input=True)

    if not token or len(token.strip()) == 0:
        click.echo("Error: Token cannot be empty.", err=True)
        sys.exit(1)

    token = token.strip()

    # Validate the token by calling GET /user/
    from ocl_cli.api_client import OCLAPIClient
    test_client = OCLAPIClient(base_url=server.base_url, token=token)
    try:
        user = test_client.get_user()
        config.set_token(server.server_id, token)
        click.echo(f"Logged in as {user.get('username', 'unknown')}.")
    except APIError as e:
        click.echo(f"Error: Invalid token - {e}", err=True)
        sys.exit(1)
    finally:
        test_client.close()


@click.command()
@click.pass_context
def logout(ctx):
    """Remove stored token for the current server."""
    server = ctx.obj["server"]
    config = ctx.obj["config"]
    config.remove_token(server.server_id)
    click.echo(f"Logged out from {server.name}.")


@click.command()
@click.pass_context
def whoami(ctx):
    """Show the current authenticated user."""
    client = ctx.obj["client"]
    try:
        user = client.get_user()
        def _format_user(d):
            name = d.get("name") or f"{d.get('first_name', '')} {d.get('last_name', '')}".strip()
            return (
                f"Username: {d.get('username', '?')}\n"
                f"Name: {name}\n"
                f"Email: {d.get('email', '?')}\n"
                f"Server: {ctx.obj['server'].name} ({ctx.obj['server'].base_url})"
            )
        output_result(ctx, user, _format_user)
    except APIError as e:
        handle_api_error(e)
