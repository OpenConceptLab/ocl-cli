"""Owner commands: search, get, members, create-org, delete-org."""

import json as json_lib
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


@owner.command("create-org")
@click.argument("org_id")
@click.argument("name")
@click.option("--company", help="Company name")
@click.option("--website", help="Website URL")
@click.option("--location", help="Location")
@click.option("--public-access", "public_access",
              type=click.Choice(["View", "Edit", "None"]), default="View",
              help="Public access level")
@click.option("--extras", help="Custom attributes as JSON string")
@click.pass_context
def create_org(ctx, org_id, name, company, website, location, public_access, extras):
    """Create a new organization."""
    client = ctx.obj["client"]
    extras_dict = None
    if extras:
        try:
            extras_dict = json_lib.loads(extras)
        except json_lib.JSONDecodeError:
            click.echo("Error: --extras must be valid JSON", err=True)
            sys.exit(1)
    try:
        result = client.create_org(
            org_id, name,
            company=company, website=website, location=location,
            public_access=public_access, extras=extras_dict,
        )
        output_result(ctx, result, format_owner_detail)
    except APIError as e:
        handle_api_error(e)


@owner.command("delete-org")
@click.argument("org_id")
@click.option("--yes", "confirmed", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_org(ctx, org_id, confirmed):
    """Delete an organization. This is irreversible."""
    if not confirmed:
        click.confirm(f"Delete organization '{org_id}'? This cannot be undone", abort=True)
    client = ctx.obj["client"]
    try:
        client.delete_org(org_id)
        click.echo(f"Organization '{org_id}' deleted.")
    except APIError as e:
        handle_api_error(e)
