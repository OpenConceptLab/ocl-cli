"""Owner commands: search, get, members."""

import sys

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import output_result, format_owner_list, format_owner_detail, format_table


@click.group()
def owner():
    """Manage OCL users and organizations."""
    pass


@owner.command()
@click.argument("query", required=False)
@click.option("--owner-type", "owner_type", type=click.Choice(["users", "orgs", "all"]), default="all",
              help="Type of owner to search")
@click.option("--limit", default=20, help="Results per page")
@click.option("--page", default=1, help="Page number")
@click.pass_context
def search(ctx, query, owner_type, limit, page):
    """Search for users and organizations."""
    client = ctx.obj["client"]
    try:
        result = client.search_owners(query=query, owner_type=owner_type, limit=limit, page=page)
        output_result(ctx, result, format_owner_list)
    except APIError as e:
        handle_api_error(e)


@owner.command()
@click.argument("owner_id")
@click.option("--owner-type", "owner_type", type=click.Choice(["users", "orgs"]), default="orgs",
              help="Type of owner")
@click.pass_context
def get(ctx, owner_id, owner_type):
    """Get details for a user or organization."""
    client = ctx.obj["client"]
    try:
        result = client.get_owner(owner_id, owner_type=owner_type)
        output_result(ctx, result, format_owner_detail)
    except APIError as e:
        handle_api_error(e)


@owner.command()
@click.argument("org")
@click.option("--limit", default=100, help="Max members to return")
@click.pass_context
def members(ctx, org, limit):
    """List members of an organization."""
    client = ctx.obj["client"]
    try:
        result = client.get_org_members(org, limit=limit)
        output_result(ctx, result, lambda d: format_table(
            d.get("results", []),
            columns=["username", "name", "url"],
            headers=["Username", "Name", "URL"],
        ))
    except APIError as e:
        handle_api_error(e)
