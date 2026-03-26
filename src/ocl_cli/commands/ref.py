"""Collection reference commands: list, add, remove."""

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import output_result, format_reference_list


@click.group()
def ref():
    """Manage collection references."""
    pass


@ref.command("list")
@click.argument("owner")
@click.argument("collection")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--collection-version", help="Collection version")
@click.option("--limit", default=20)
@click.option("--page", default=1)
@click.pass_context
def ref_list(ctx, owner, collection, owner_type, collection_version, limit, page):
    """List references in a collection."""
    client = ctx.obj["client"]
    try:
        result = client.list_collection_refs(
            owner, collection, owner_type=owner_type,
            collection_version=collection_version, limit=limit, page=page,
        )
        output_result(ctx, result, format_reference_list)
    except APIError as e:
        handle_api_error(e)


@ref.command()
@click.argument("owner")
@click.argument("collection")
@click.argument("expressions", nargs=-1, required=True)
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--cascade", "cascade_opt",
              type=click.Choice(["none", "sourcemappings", "sourcetoconcepts"]),
              help="Cascade behavior when adding references")
@click.pass_context
def add(ctx, owner, collection, expressions, owner_type, cascade_opt):
    """Add references to a collection.

    EXPRESSIONS are concept/mapping URLs to add as references.
    """
    client = ctx.obj["client"]
    try:
        result = client.add_collection_ref(
            owner, collection, list(expressions),
            owner_type=owner_type, cascade=cascade_opt,
        )
        output_result(ctx, result)
    except APIError as e:
        handle_api_error(e)


@ref.command()
@click.argument("owner")
@click.argument("collection")
@click.argument("expressions", nargs=-1, required=True)
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def remove(ctx, owner, collection, expressions, owner_type):
    """Remove references from a collection."""
    client = ctx.obj["client"]
    try:
        result = client.remove_collection_ref(
            owner, collection, list(expressions), owner_type=owner_type,
        )
        output_result(ctx, result)
        click.echo(f"Removed {len(expressions)} reference(s)")
    except APIError as e:
        handle_api_error(e)
