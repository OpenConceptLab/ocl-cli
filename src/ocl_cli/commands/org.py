"""Organization commands: list, get, members, repos, create, delete, add-member, remove-member."""

import json as json_lib
import sys

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import (
    output_result, format_org_list, format_org_detail,
    format_member_list, format_repo_list,
)


@click.group()
def org():
    """Manage OCL organizations."""
    pass


@org.command("list")
@click.argument("query", required=False)
@click.option("--verbose", is_flag=True, help="Include full details in results")
@click.option("--limit", default=25, help="Results per page")
@click.option("--page", default=1, help="Page number")
@click.pass_context
def org_list(ctx, query, verbose, limit, page):
    """Search for organizations."""
    client = ctx.obj["client"]
    try:
        result = client.list_orgs(query=query, verbose=verbose, limit=limit, page=page)
        output_result(ctx, result, format_org_list)
    except APIError as e:
        handle_api_error(e)


@org.command()
@click.argument("org_id")
@click.pass_context
def get(ctx, org_id):
    """Get details for an organization."""
    client = ctx.obj["client"]
    try:
        result = client.get_org(org_id)
        output_result(ctx, result, format_org_detail)
    except APIError as e:
        handle_api_error(e)


@org.command()
@click.argument("org_id")
@click.option("--limit", default=100, help="Max members to return")
@click.pass_context
def members(ctx, org_id, limit):
    """List members of an organization."""
    client = ctx.obj["client"]
    try:
        result = client.get_org_members(org_id, limit=limit)
        output_result(ctx, result, format_member_list)
    except APIError as e:
        handle_api_error(e)


@org.command()
@click.argument("org_id")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection", "all"]), default="all",
              help="Repository type")
@click.option("--limit", default=20, help="Results per page")
@click.option("--page", default=1, help="Page number")
@click.pass_context
def repos(ctx, org_id, repo_type, limit, page):
    """List repositories owned by an organization."""
    client = ctx.obj["client"]
    try:
        result = client.list_org_repos(org_id, repo_type=repo_type, limit=limit, page=page)
        output_result(ctx, result, format_repo_list)
    except APIError as e:
        handle_api_error(e)


@org.command()
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
def create(ctx, org_id, name, company, website, location, public_access, extras):
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
        output_result(ctx, result, format_org_detail)
    except APIError as e:
        handle_api_error(e)


@org.command()
@click.argument("org_id")
@click.option("--yes", "confirmed", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(ctx, org_id, confirmed):
    """Delete an organization. This is irreversible."""
    if not confirmed:
        click.confirm(f"Delete organization '{org_id}'? This cannot be undone", abort=True)
    client = ctx.obj["client"]
    try:
        client.delete_org(org_id)
        click.echo(f"Organization '{org_id}' deleted.")
    except APIError as e:
        handle_api_error(e)


@org.command("add-member")
@click.argument("org_id")
@click.argument("username")
@click.pass_context
def add_member(ctx, org_id, username):
    """Add a member to an organization."""
    client = ctx.obj["client"]
    try:
        client.add_org_member(org_id, username)
        click.echo(f"Added '{username}' to organization '{org_id}'.")
    except APIError as e:
        handle_api_error(e)


@org.command("remove-member")
@click.argument("org_id")
@click.argument("username")
@click.option("--yes", "confirmed", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def remove_member(ctx, org_id, username, confirmed):
    """Remove a member from an organization."""
    if not confirmed:
        click.confirm(f"Remove '{username}' from organization '{org_id}'?", abort=True)
    client = ctx.obj["client"]
    try:
        client.remove_org_member(org_id, username)
        click.echo(f"Removed '{username}' from organization '{org_id}'.")
    except APIError as e:
        handle_api_error(e)
