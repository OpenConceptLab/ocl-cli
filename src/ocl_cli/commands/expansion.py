"""Expansion commands: list, get, create."""

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import output_result, format_expansion_list


@click.group()
def expansion():
    """Manage collection expansions."""
    pass


@expansion.command("list")
@click.argument("owner")
@click.argument("collection")
@click.argument("version")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def expansion_list(ctx, owner, collection, version, owner_type):
    """List expansions for a collection version."""
    client = ctx.obj["client"]
    try:
        result = client.list_expansions(owner, collection, version, owner_type=owner_type)
        output_result(ctx, result, format_expansion_list)
    except APIError as e:
        handle_api_error(e)


@expansion.command()
@click.argument("owner")
@click.argument("collection")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--version", help="Collection version")
@click.option("--expansion-id", help="Specific expansion ID")
@click.pass_context
def get(ctx, owner, collection, owner_type, version, expansion_id):
    """Get a specific or default expansion for a collection."""
    client = ctx.obj["client"]
    try:
        result = client.get_expansion(
            owner, collection, owner_type=owner_type,
            collection_version=version, expansion_id=expansion_id,
        )
        output_result(ctx, result)
    except APIError as e:
        handle_api_error(e)


@expansion.command()
@click.argument("owner")
@click.argument("collection")
@click.argument("version")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def create(ctx, owner, collection, version, owner_type):
    """Trigger an expansion for a collection version."""
    client = ctx.obj["client"]
    try:
        result = client.create_expansion(owner, collection, version, owner_type=owner_type)
        output_result(ctx, result)
    except APIError as e:
        handle_api_error(e)
