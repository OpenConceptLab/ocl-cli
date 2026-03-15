"""Server management commands."""

import click

from ocl_cli.output import output_result, format_table


@click.group()
def server():
    """Manage OCL server configurations."""
    pass


@server.command("list")
@click.pass_context
def server_list(ctx):
    """List configured servers."""
    config = ctx.obj["config"]

    if ctx.obj["json_output"]:
        output_result(ctx, {
            "default_server": config.default_server,
            "servers": config.servers,
        })
        return

    rows = []
    for sid, sdata in config.servers.items():
        rows.append({
            "id": sid,
            "name": sdata.get("name", ""),
            "url": sdata.get("base_url", ""),
            "default": "*" if sid == config.default_server else "",
            "has_token": "yes" if sdata.get("token") else "env" if sdata.get("api_token_env") else "no",
        })

    click.echo(format_table(
        rows,
        columns=["id", "name", "url", "default", "has_token"],
        headers=["ID", "Name", "URL", "Default", "Token"],
    ))


@server.command("add")
@click.argument("server_id")
@click.argument("url")
@click.option("--name", help="Friendly name for the server")
@click.option("--token-env", help="Environment variable name for API token")
@click.pass_context
def server_add(ctx, server_id, url, name, token_env):
    """Add a new server configuration."""
    config = ctx.obj["config"]
    config.add_server(server_id, url, name=name, api_token_env=token_env)
    click.echo(f"Added server '{server_id}' ({url})")


@server.command("remove")
@click.argument("server_id")
@click.pass_context
def server_remove(ctx, server_id):
    """Remove a server configuration."""
    config = ctx.obj["config"]
    try:
        config.remove_server(server_id)
        click.echo(f"Removed server '{server_id}'")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@server.command("use")
@click.argument("server_id")
@click.pass_context
def server_use(ctx, server_id):
    """Set the default server."""
    config = ctx.obj["config"]
    try:
        config.set_default_server(server_id)
        click.echo(f"Default server set to '{server_id}'")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
