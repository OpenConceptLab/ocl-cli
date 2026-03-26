"""Export commands: status, create, delete, download."""

import sys

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import format_export_status, output_result


def export_args(f):
    """Common arguments and options for all export subcommands."""
    f = click.argument("version")(f)
    f = click.argument("repo")(f)
    f = click.argument("owner")(f)
    f = click.option(
        "--type", "repo_type",
        type=click.Choice(["source", "collection"]),
        required=True,
        help="Repository type.",
    )(f)
    f = click.option(
        "--owner-type",
        type=click.Choice(["users", "orgs"]),
        default="orgs",
        help="Owner type (default: orgs).",
    )(f)
    return f


@click.group()
def export():
    """Manage repository version exports."""
    pass


@export.command()
@export_args
@click.pass_context
def status(ctx, owner, repo, version, repo_type, owner_type):
    """Check export status for a repository version."""
    client = ctx.obj["client"]
    try:
        result = client.export_status(
            owner, repo, version, owner_type=owner_type, repo_type=repo_type,
        )
        output_result(ctx, result, format_export_status)
    except APIError as e:
        handle_api_error(e)


@export.command()
@export_args
@click.pass_context
def create(ctx, owner, repo, version, repo_type, owner_type):
    """Trigger export creation for a repository version."""
    client = ctx.obj["client"]
    try:
        result = client.export_create(
            owner, repo, version, owner_type=owner_type, repo_type=repo_type,
        )
        output_result(ctx, result, format_export_status)
    except APIError as e:
        handle_api_error(e)


@export.command()
@export_args
@click.pass_context
def delete(ctx, owner, repo, version, repo_type, owner_type):
    """Delete a cached export for a repository version."""
    client = ctx.obj["client"]
    try:
        client.export_delete(
            owner, repo, version, owner_type=owner_type, repo_type=repo_type,
        )
        click.echo("Export deleted.")
    except APIError as e:
        handle_api_error(e)


@export.command()
@export_args
@click.option(
    "-o", "--output", "output_path",
    type=click.Path(),
    help="Output file path (required).",
    required=True,
)
@click.pass_context
def download(ctx, owner, repo, version, repo_type, owner_type, output_path):
    """Download an export file to a local path."""
    client = ctx.obj["client"]
    try:
        click.echo(f"Downloading export...", err=True)
        response = client.export_download(
            owner, repo, version, owner_type=owner_type, repo_type=repo_type,
        )

        with open(output_path, "wb") as f:
            f.write(response.content)

        size = len(response.content)
        click.echo(f"Saved to {output_path} ({size:,} bytes)", err=True)
    except APIError as e:
        handle_api_error(e)
