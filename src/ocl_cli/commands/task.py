"""Task commands: list and get async tasks."""

import sys

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import output_result, format_task_list, format_task_detail


@click.group()
def task():
    """Manage OCL async tasks."""
    pass


@task.command("list")
@click.option("--state", type=click.Choice(
    ["STARTED", "SUCCESS", "FAILURE", "PENDING", "RECEIVED", "REVOKED", "RETRY"],
    case_sensitive=False,
), help="Filter by task state")
@click.option("--limit", default=20, help="Results per page")
@click.option("--page", default=1, help="Page number")
@click.option("--verbose", is_flag=True, help="Show additional timing details")
@click.pass_context
def task_list(ctx, state, limit, page, verbose):
    """List async tasks for the authenticated user."""
    client = ctx.obj["client"]
    try:
        result = client.list_tasks(state=state, limit=limit, page=page)
        output_result(ctx, result, lambda d: format_task_list(d, page=page, limit=limit, verbose=verbose))
    except APIError as e:
        handle_api_error(e)


@task.command("get")
@click.argument("task_id")
@click.pass_context
def task_get(ctx, task_id):
    """Get details of a specific task."""
    client = ctx.obj["client"]
    try:
        result = client.get_task(task_id)
        output_result(ctx, result, format_task_detail)
    except APIError as e:
        handle_api_error(e)
