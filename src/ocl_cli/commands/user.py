"""User commands: list, get, orgs, repos."""

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import (
    output_result, format_user_list, format_user_detail,
    format_org_list, format_repo_list,
)


@click.group()
def user():
    """Manage OCL users."""
    pass


@user.command("list")
@click.argument("query", required=False)
@click.option("--verbose", is_flag=True, help="Include full details in results")
@click.option("--limit", default=25, help="Results per page")
@click.option("--page", default=1, help="Page number")
@click.pass_context
def user_list(ctx, query, verbose, limit, page):
    """Search for users."""
    client = ctx.obj["client"]
    try:
        result = client.list_users(query=query, verbose=verbose, limit=limit, page=page)
        output_result(ctx, result, lambda d: format_user_list(d, page=page, limit=limit, verbose=verbose))
    except APIError as e:
        handle_api_error(e)


@user.command()
@click.argument("username")
@click.pass_context
def get(ctx, username):
    """Get details for a user."""
    client = ctx.obj["client"]
    try:
        result = client.get_user_detail(username)
        output_result(ctx, result, format_user_detail)
    except APIError as e:
        handle_api_error(e)


@user.command()
@click.argument("username")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection", "all"]), default="all",
              help="Repository type")
@click.option("--verbose", is_flag=True, help="Include full details in results")
@click.option("--limit", default=20, help="Results per page")
@click.option("--page", default=1, help="Page number")
@click.pass_context
def repos(ctx, username, repo_type, verbose, limit, page):
    """List repositories owned by a user."""
    client = ctx.obj["client"]
    try:
        result = client.list_user_repos(username, repo_type=repo_type, limit=limit, page=page)
        output_result(ctx, result, lambda d: format_repo_list(d, page=page, limit=limit, verbose=verbose))
    except APIError as e:
        handle_api_error(e)


@user.command()
@click.argument("username")
@click.option("--limit", default=100, help="Max organizations to return")
@click.pass_context
def orgs(ctx, username, limit):
    """List organizations a user belongs to."""
    client = ctx.obj["client"]
    try:
        result = client.list_user_orgs(username, limit=limit)
        output_result(ctx, result, format_org_list)
    except APIError as e:
        handle_api_error(e)
