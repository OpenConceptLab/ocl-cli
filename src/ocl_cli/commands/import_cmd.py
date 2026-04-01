"""Import commands: submit, monitor, and list bulk imports."""

import os
import sys
import time

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import (
    format_import_list,
    format_import_status,
    format_import_submit,
    output_result,
)

SUPPORTED_EXTENSIONS = {".json", ".jsonl", ".csv", ".zip"}


def _poll_task(client, task_id):
    """Poll a task until it reaches a terminal state. Returns final task data."""
    while True:
        try:
            task_data = client.get_task(task_id)
        except APIError:
            time.sleep(5)
            continue
        state = task_data.get("state")
        if state == "SUCCESS":
            click.echo("Import completed successfully.", err=True)
            return task_data
        elif state in ("FAILURE", "REVOKED"):
            click.echo(f"Import failed: {state}", err=True)
            return task_data
        else:
            click.echo(f"  State: {state}, waiting...", err=True)
            time.sleep(5)


@click.group("import")
def import_cmd():
    """Bulk import resources into OCL."""
    pass


@import_cmd.command("file")
@click.argument("file_path", type=click.Path(exists=True, readable=True))
@click.option("--queue", help="Named queue for sequential processing")
@click.option("--no-update", is_flag=True, help="Don't update existing resources")
@click.option(
    "--parallel",
    type=click.IntRange(1, 10),
    default=None,
    help="Parallel thread count (1-10)",
)
@click.option("--wait", is_flag=True, help="Poll until import completes")
@click.pass_context
def import_file(ctx, file_path, queue, no_update, parallel, wait):
    """Submit a file for bulk import.

    Supports JSON Lines (.json, .jsonl), CSV (.csv), and OCL export (.zip) files.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        click.echo(
            f"Error: Unsupported file type '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            err=True,
        )
        sys.exit(1)

    client = ctx.obj["client"]
    try:
        result = client.import_file(
            file_path=file_path,
            queue=queue,
            update_if_exists=not no_update,
            parallel=parallel,
        )
        output_result(ctx, result, format_import_submit)

        if wait:
            task_id = result.get("task") or result.get("id")
            if task_id:
                click.echo("Waiting for import to complete...", err=True)
                final = _poll_task(client, task_id)
                output_result(ctx, final, format_import_status)
    except APIError as e:
        handle_api_error(e)


@import_cmd.command("status")
@click.argument("task_id")
@click.option("--wait", is_flag=True, help="Poll until import completes")
@click.pass_context
def import_status(ctx, task_id, wait):
    """Get the status of a bulk import task."""
    client = ctx.obj["client"]
    try:
        result = client.import_status(task_id)
        output_result(ctx, result, format_import_status)

        if wait:
            # Check if already in terminal state
            task_data = result[0] if isinstance(result, list) and result else result
            state = task_data.get("state", "") if isinstance(task_data, dict) else ""
            if state not in ("SUCCESS", "FAILURE", "REVOKED"):
                click.echo("Waiting for import to complete...", err=True)
                final = _poll_task(client, task_id)
                output_result(ctx, final, format_import_status)
    except APIError as e:
        handle_api_error(e)


@import_cmd.command("list")
@click.option("--queue", help="Filter by queue name")
@click.pass_context
def import_list(ctx, queue):
    """List active and recent bulk imports."""
    client = ctx.obj["client"]
    try:
        result = client.import_list(queue=queue)
        output_result(ctx, result, format_import_list)
    except APIError as e:
        handle_api_error(e)
