"""Index commands: trigger Elasticsearch reindexing for sources, expansions, and global indexes."""

import sys

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import output_result, format_index_task


@click.group()
def index():
    """Trigger Elasticsearch reindexing operations."""
    pass


# ── Source subgroup ──────────────────────────────────────────────────

@index.group()
def source():
    """Reindex concepts or mappings for a source."""
    pass


@source.command("concepts")
@click.argument("owner")
@click.argument("source_name", metavar="SOURCE")
@click.option("--version", help="Source version to reindex (omit for HEAD)")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--single-batch", is_flag=True, help="Process as a single batch instead of parallel chunks")
@click.option("--no-parallel", is_flag=True, help="Disable parallel processing")
@click.pass_context
def source_concepts(ctx, owner, source_name, version, owner_type, single_batch, no_parallel):
    """Reindex all concepts for a source."""
    client = ctx.obj["client"]
    try:
        result = client.index_source_concepts(
            owner, source_name, owner_type=owner_type, version=version,
            single_batch=single_batch, parallel=not no_parallel,
        )
        output_result(ctx, result, format_index_task)
    except APIError as e:
        handle_api_error(e)


@source.command("mappings")
@click.argument("owner")
@click.argument("source_name", metavar="SOURCE")
@click.option("--version", help="Source version to reindex (omit for HEAD)")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--single-batch", is_flag=True, help="Process as a single batch instead of parallel chunks")
@click.pass_context
def source_mappings(ctx, owner, source_name, version, owner_type, single_batch):
    """Reindex all mappings for a source."""
    client = ctx.obj["client"]
    try:
        result = client.index_source_mappings(
            owner, source_name, owner_type=owner_type, version=version,
            single_batch=single_batch,
        )
        output_result(ctx, result, format_index_task)
    except APIError as e:
        handle_api_error(e)


# ── Expansion subgroup ───────────────────────────────────────────────

@index.group()
def expansion():
    """Reindex concepts or mappings for a collection expansion (admin only)."""
    pass


@expansion.command("concepts")
@click.argument("owner")
@click.argument("collection")
@click.argument("version")
@click.argument("expansion")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def expansion_concepts(ctx, owner, collection, version, expansion, owner_type):
    """Reindex concepts for a collection expansion."""
    client = ctx.obj["client"]
    try:
        result = client.index_expansion_concepts(
            owner, collection, version, expansion, owner_type=owner_type,
        )
        output_result(ctx, result, format_index_task)
    except APIError as e:
        handle_api_error(e)


@expansion.command("mappings")
@click.argument("owner")
@click.argument("collection")
@click.argument("version")
@click.argument("expansion")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def expansion_mappings(ctx, owner, collection, version, expansion, owner_type):
    """Reindex mappings for a collection expansion."""
    client = ctx.obj["client"]
    try:
        result = client.index_expansion_mappings(
            owner, collection, version, expansion, owner_type=owner_type,
        )
        output_result(ctx, result, format_index_task)
    except APIError as e:
        handle_api_error(e)


# ── Admin commands ───────────────────────────────────────────────────

@index.command()
@click.option("--apps", help="Comma-separated app names to rebuild (omit for all)")
@click.pass_context
def rebuild(ctx, apps):
    """Rebuild all Elasticsearch indexes from scratch (admin only)."""
    client = ctx.obj["client"]
    try:
        result = client.index_rebuild(apps=apps)
        output_result(ctx, result, format_index_task)
    except APIError as e:
        handle_api_error(e)


@index.command()
@click.option("--apps", help="Comma-separated app names to populate (omit for all)")
@click.pass_context
def populate(ctx, apps):
    """Populate Elasticsearch indexes without rebuilding (admin only)."""
    client = ctx.obj["client"]
    try:
        result = client.index_populate(apps=apps)
        output_result(ctx, result, format_index_task)
    except APIError as e:
        handle_api_error(e)


@index.command()
@click.argument("resource")
@click.option("--ids", help="Comma-separated resource IDs to reindex")
@click.option("--uri", help="URI pattern to match resources for reindexing")
@click.option("--filter", "filter_str", help="JSON filter string to select resources")
@click.option("--update-indexed", is_flag=True, help="Update the indexed flag on matched resources")
@click.pass_context
def resource(ctx, resource, ids, uri, filter_str, update_indexed):
    """Batch reindex a specific resource type (admin only).

    RESOURCE is the resource type, e.g. concepts, mappings, sources, collections.
    Exactly one of --ids, --uri, or --filter is required.
    """
    if not ids and not uri and not filter_str:
        click.echo("Error: one of --ids, --uri, or --filter is required.", err=True)
        sys.exit(1)
    client = ctx.obj["client"]
    try:
        result = client.index_resource(
            resource, ids=ids, uri=uri, filter_str=filter_str, update_indexed=update_indexed,
        )
        output_result(ctx, result, format_index_task)
    except APIError as e:
        handle_api_error(e)
