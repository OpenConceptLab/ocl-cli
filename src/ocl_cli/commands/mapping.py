"""Mapping commands: search, get, create, update, retire, versions."""

import sys

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import (
    output_result, format_mapping_list, format_mapping_detail,
    format_version_list,
)


@click.group()
def mapping():
    """Manage OCL mappings."""
    pass


# ── Read commands ────────────────────────────────────────────────


@mapping.command()
@click.argument("query", required=False)
@click.option("--owner", help="Mapping owner (org or user that owns the source containing the mapping)")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]))
@click.option("--repo", help="Mapping repository (source or collection containing the mapping)")
@click.option("--repo-type", type=click.Choice(["source", "collection"]), default="source")
@click.option("--version", help="Repository version")
@click.option("--map-type", help="Filter by map type (e.g. SAME-AS, NARROWER-THAN)")
@click.option("--from-source", help="Filter by from-concept source name")
@click.option("--from-concept", help="Filter by from-concept code")
@click.option("--from-concept-owner", help="Filter by from-concept owner")
@click.option("--to-source", help="Filter by to-concept source name")
@click.option("--to-concept", help="Filter by to-concept code")
@click.option("--to-concept-owner", help="Filter by to-concept owner")
@click.option("--include-retired", is_flag=True)
@click.option("--updated-since", help="Filter by update date")
@click.option("--sort", help="Sort field")
@click.option("--verbose", is_flag=True)
@click.option("--limit", default=20)
@click.option("--page", default=1)
@click.pass_context
def search(ctx, query, owner, owner_type, repo, repo_type, version, map_type,
           from_source, from_concept, from_concept_owner, to_source, to_concept,
           to_concept_owner, include_retired, updated_since, sort, verbose, limit, page):
    """Search for mappings globally or within a repository.

    Note: --owner/--repo scope the mapping's own source, not the from/to
    concept sources. Use --from-source/--to-source to filter by concept source.
    """
    client = ctx.obj["client"]
    try:
        result = client.search_mappings(
            query=query, owner=owner, owner_type=owner_type,
            repo=repo, repo_type=repo_type, version=version,
            map_type=map_type, from_source=from_source, from_concept=from_concept,
            from_concept_owner=from_concept_owner,
            to_source=to_source, to_concept=to_concept,
            to_concept_owner=to_concept_owner,
            include_retired=include_retired, updated_since=updated_since,
            sort=sort, verbose=verbose, limit=limit, page=page,
        )
        output_result(ctx, result, lambda d: format_mapping_list(d, page, limit, verbose=verbose))
    except APIError as e:
        handle_api_error(e)


@mapping.command()
@click.argument("owner")
@click.argument("source")
@click.argument("mapping_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--version", help="Source version")
@click.pass_context
def get(ctx, owner, source, mapping_id, owner_type, version):
    """Get a single mapping."""
    client = ctx.obj["client"]
    try:
        result = client.get_mapping(owner, source, mapping_id,
                                     owner_type=owner_type, version=version)
        output_result(ctx, result, format_mapping_detail)
    except APIError as e:
        handle_api_error(e)


@mapping.command("versions")
@click.argument("owner")
@click.argument("source")
@click.argument("mapping_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--limit", default=20)
@click.option("--page", default=1)
@click.pass_context
def mapping_versions(ctx, owner, source, mapping_id, owner_type, limit, page):
    """List version history for a mapping."""
    client = ctx.obj["client"]
    try:
        result = client.get_mapping_versions(owner, source, mapping_id,
                                              owner_type=owner_type, limit=limit, page=page)
        output_result(ctx, result, format_version_list)
    except APIError as e:
        handle_api_error(e)


# ── Write commands ───────────────────────────────────────────────


@mapping.command()
@click.argument("owner")
@click.argument("source")
@click.option("--map-type", required=True, help="Mapping type (e.g. SAME-AS, NARROWER-THAN)")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--from-concept-url", help="OCL URL for from concept")
@click.option("--from-source-url", help="Source URL for from concept")
@click.option("--from-concept-code", help="Code for from concept (with --from-source-url)")
@click.option("--from-concept-name", help="Display name for from concept")
@click.option("--to-concept-url", help="OCL URL for to concept")
@click.option("--to-source-url", help="Source URL for to concept")
@click.option("--to-concept-code", help="Code for to concept (with --to-source-url)")
@click.option("--to-concept-name", help="Display name for to concept")
@click.option("--external-id", help="External identifier")
@click.option("--extras", help="JSON string of extra attributes")
@click.pass_context
def create(ctx, owner, source, map_type, owner_type,
           from_concept_url, from_source_url, from_concept_code, from_concept_name,
           to_concept_url, to_source_url, to_concept_code, to_concept_name,
           external_id, extras):
    """Create a new mapping between concepts."""
    client = ctx.obj["client"]
    try:
        import json as json_lib
        extras_dict = json_lib.loads(extras) if extras else None

        result = client.create_mapping(
            owner, source, map_type, owner_type=owner_type,
            from_concept_url=from_concept_url, from_source_url=from_source_url,
            from_concept_code=from_concept_code, from_concept_name=from_concept_name,
            to_concept_url=to_concept_url, to_source_url=to_source_url,
            to_concept_code=to_concept_code, to_concept_name=to_concept_name,
            external_id=external_id, extras=extras_dict,
        )
        output_result(ctx, result, format_mapping_detail)
    except (APIError, ValueError) as e:
        if isinstance(e, APIError):
            handle_api_error(e)
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@mapping.command()
@click.argument("owner")
@click.argument("source")
@click.argument("mapping_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--map-type", help="New map type")
@click.option("--update-comment", help="Comment for the update")
@click.pass_context
def update(ctx, owner, source, mapping_id, owner_type, map_type, update_comment):
    """Update an existing mapping."""
    client = ctx.obj["client"]
    try:
        fields = {}
        if map_type:
            fields["map_type"] = map_type
        if not fields:
            click.echo("No fields to update.", err=True)
            sys.exit(1)

        result = client.update_mapping(owner, source, mapping_id,
                                        owner_type=owner_type,
                                        update_comment=update_comment, **fields)
        output_result(ctx, result, format_mapping_detail)
    except APIError as e:
        handle_api_error(e)


@mapping.command()
@click.argument("owner")
@click.argument("source")
@click.argument("mapping_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--update-comment", help="Comment for the retirement")
@click.pass_context
def retire(ctx, owner, source, mapping_id, owner_type, update_comment):
    """Retire a mapping."""
    client = ctx.obj["client"]
    try:
        result = client.retire_mapping(owner, source, mapping_id,
                                        owner_type=owner_type, update_comment=update_comment)
        output_result(ctx, result, format_mapping_detail)
    except APIError as e:
        handle_api_error(e)
