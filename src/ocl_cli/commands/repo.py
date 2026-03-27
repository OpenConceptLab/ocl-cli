"""Repository commands: list, get, create, update, versions, extras, export."""

import json as json_lib
import sys

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import (
    output_result, format_repo_list, format_repo_detail,
    format_version_list, format_extras,
)


@click.group()
def repo():
    """Manage OCL repositories (sources and collections)."""
    pass


@repo.command("list")
@click.argument("query", required=False)
@click.option("--owner", help="Filter by owner")
@click.option("--owner-type", type=click.Choice(["users", "orgs", "all"]), default="all")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection", "all"]), default="all",
              help="Repository type")
@click.option("--custom-validation-schema", help="Filter by validation schema (e.g. OpenMRS)")
@click.option("--updated-since", help="Filter by update date (YYYY-MM-DD)")
@click.option("--all-versions", is_flag=True, help="Include all repo versions, not just HEAD")
@click.option("--verbose", is_flag=True, help="Include full details in results")
@click.option("--limit", default=20, help="Results per page")
@click.option("--page", default=1, help="Page number")
@click.pass_context
def repo_list(ctx, query, owner, owner_type, repo_type, custom_validation_schema,
              updated_since, all_versions, verbose, limit, page):
    """Search for repositories (sources and collections)."""
    client = ctx.obj["client"]
    try:
        result = client.search_repos(
            query=query, owner=owner, owner_type=owner_type,
            repo_type=repo_type, custom_validation_schema=custom_validation_schema,
            updated_since=updated_since, all_versions=all_versions,
            verbose=verbose, limit=limit, page=page,
        )
        output_result(ctx, result, lambda d: format_repo_list(d, page=page, limit=limit, verbose=verbose))
    except APIError as e:
        handle_api_error(e)


@repo.command()
@click.argument("owner")
@click.argument("repo_name")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection"]), default="source",
              help="Repository type")
@click.option("--repo-version", help="Repository version (omit for HEAD, use 'latest' for latest released)")
@click.pass_context
def get(ctx, owner, repo_name, owner_type, repo_type, repo_version):
    """Get details for a specific repository."""
    client = ctx.obj["client"]
    try:
        result = client.get_repo(
            owner, repo_name, owner_type=owner_type,
            repo_type=repo_type, repo_version=repo_version,
        )
        output_result(ctx, result, format_repo_detail)
    except APIError as e:
        handle_api_error(e)


@repo.command()
@click.argument("owner")
@click.argument("repo_name")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection"]), default="source")
@click.option("--released", type=bool, default=None, help="Filter by released status")
@click.option("--updated-since", help="Filter by update date (YYYY-MM-DD)")
@click.option("--limit", default=20, help="Results per page")
@click.option("--page", default=1, help="Page number")
@click.pass_context
def versions(ctx, owner, repo_name, owner_type, repo_type, released, updated_since, limit, page):
    """List versions for a repository."""
    client = ctx.obj["client"]
    try:
        result = client.get_repo_versions(
            owner, repo_name, owner_type=owner_type, repo_type=repo_type,
            released=released, updated_since=updated_since, limit=limit, page=page,
        )
        output_result(ctx, result, lambda d: format_version_list(d, page=page, limit=limit))
    except APIError as e:
        handle_api_error(e)


@repo.command()
@click.argument("owner")
@click.argument("repo_id")
@click.argument("name")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection"]), required=True,
              help="Repository type")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--description", help="Repository description")
@click.option("--default-locale", help="Default locale code")
@click.option("--supported-locales", help="Comma-separated locale codes")
@click.option("--public-access", type=click.Choice(["View", "Edit", "None"]))
@click.option("--source-type", help="Source type (sources only)")
@click.option("--collection-type", help="Collection type (collections only)")
@click.option("--canonical-url", help="Canonical URL")
@click.option("--custom-validation-schema", help="Validation schema")
@click.option("--extras", help="JSON string of extra attributes")
@click.pass_context
def create(ctx, owner, repo_id, name, repo_type, owner_type, description,
           default_locale, supported_locales, public_access, source_type,
           collection_type, canonical_url, custom_validation_schema, extras):
    """Create a new repository."""
    client = ctx.obj["client"]
    try:
        locales = supported_locales.split(",") if supported_locales else None
        extras_dict = json_lib.loads(extras) if extras else None

        result = client.create_repo(
            owner, repo_id, name, owner_type=owner_type, repo_type=repo_type,
            description=description, default_locale=default_locale,
            supported_locales=locales, public_access=public_access,
            source_type=source_type, collection_type=collection_type,
            canonical_url=canonical_url,
            custom_validation_schema=custom_validation_schema,
            extras=extras_dict,
        )
        output_result(ctx, result, format_repo_detail)
    except APIError as e:
        handle_api_error(e)


@repo.command()
@click.argument("owner")
@click.argument("repo_name")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection"]), default="source")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--name", "new_name", help="New name")
@click.option("--description", help="New description")
@click.option("--default-locale", help="New default locale")
@click.option("--public-access", type=click.Choice(["View", "Edit", "None"]))
@click.pass_context
def update(ctx, owner, repo_name, repo_type, owner_type, new_name, description,
           default_locale, public_access):
    """Update a repository."""
    client = ctx.obj["client"]
    try:
        fields = {}
        if new_name:
            fields["name"] = new_name
        if description:
            fields["description"] = description
        if default_locale:
            fields["default_locale"] = default_locale
        if public_access:
            fields["public_access"] = public_access

        if not fields:
            click.echo("No fields to update. Use --name, --description, etc.", err=True)
            sys.exit(1)

        result = client.update_repo(owner, repo_name, owner_type=owner_type,
                                     repo_type=repo_type, **fields)
        output_result(ctx, result, format_repo_detail)
    except APIError as e:
        handle_api_error(e)


@repo.command("version-create")
@click.argument("owner")
@click.argument("repo_name")
@click.argument("version_id")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection"]), default="source")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--description", help="Version description")
@click.option("--released/--no-released", default=True, help="Mark as released (default: true)")
@click.pass_context
def version_create(ctx, owner, repo_name, version_id, repo_type, owner_type, description, released):
    """Create a new repository version (snapshot)."""
    client = ctx.obj["client"]
    try:
        result = client.create_repo_version(
            owner, repo_name, version_id, owner_type=owner_type,
            repo_type=repo_type, description=description, released=released,
        )
        output_result(ctx, result, format_repo_detail)
    except APIError as e:
        handle_api_error(e)


@repo.command("version-update")
@click.argument("owner")
@click.argument("repo_name")
@click.argument("version_id")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection"]), default="source")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--description", help="Version description")
@click.option("--released/--no-released", default=None, help="Released status")
@click.option("--match-algorithms", default=None, help="Comma-separated match algorithms (e.g. es,llm)")
@click.pass_context
def version_update(ctx, owner, repo_name, version_id, repo_type, owner_type, description, released, match_algorithms):
    """Update a repository version."""
    client = ctx.obj["client"]
    try:
        fields = {}
        if description is not None:
            fields["description"] = description
        if released is not None:
            fields["released"] = released
        if match_algorithms is not None:
            fields["match_algorithms"] = [a.strip() for a in match_algorithms.split(",")]
        result = client.update_repo_version(
            owner, repo_name, version_id, owner_type=owner_type,
            repo_type=repo_type, **fields,
        )
        output_result(ctx, result, format_repo_detail)
    except APIError as e:
        handle_api_error(e)


@repo.command()
@click.argument("owner")
@click.argument("repo_name")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection"]), default="source")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def extras(ctx, owner, repo_name, repo_type, owner_type):
    """List custom attributes for a repository."""
    client = ctx.obj["client"]
    try:
        result = client.get_repo_extras(owner, repo_name, owner_type=owner_type, repo_type=repo_type)
        output_result(ctx, result, format_extras)
    except APIError as e:
        handle_api_error(e)


@repo.command("extra-set")
@click.argument("owner")
@click.argument("repo_name")
@click.argument("key")
@click.argument("value")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection"]), default="source")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def extra_set(ctx, owner, repo_name, key, value, repo_type, owner_type):
    """Set a custom attribute on a repository."""
    client = ctx.obj["client"]
    try:
        # Try to parse value as JSON
        try:
            parsed = json_lib.loads(value)
        except (json_lib.JSONDecodeError, ValueError):
            parsed = value

        result = client.set_repo_extra(owner, repo_name, key, parsed,
                                        owner_type=owner_type, repo_type=repo_type)
        output_result(ctx, result, format_extras)
    except APIError as e:
        handle_api_error(e)


@repo.command("extra-del")
@click.argument("owner")
@click.argument("repo_name")
@click.argument("key")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection"]), default="source")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def extra_del(ctx, owner, repo_name, key, repo_type, owner_type):
    """Delete a custom attribute from a repository."""
    client = ctx.obj["client"]
    try:
        client.delete_repo_extra(owner, repo_name, key, owner_type=owner_type, repo_type=repo_type)
        click.echo(f"Deleted extra '{key}'")
    except APIError as e:
        handle_api_error(e)


@repo.command("delete")
@click.argument("owner")
@click.argument("repo_name")
@click.option("--type", "repo_type", type=click.Choice(["source", "collection"]), required=True,
              help="Repository type")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--yes", "confirmed", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def repo_delete(ctx, owner, repo_name, repo_type, owner_type, confirmed):
    """Delete a repository. This is irreversible."""
    if not confirmed:
        click.confirm(
            f"Delete {repo_type} '{owner}/{repo_name}'? This cannot be undone",
            abort=True,
        )
    client = ctx.obj["client"]
    try:
        client.delete_repo(owner, repo_name, owner_type=owner_type, repo_type=repo_type)
        click.echo(f"{repo_type.title()} '{owner}/{repo_name}' deleted.")
    except APIError as e:
        handle_api_error(e)


# Register export subgroup
from ocl_cli.commands.export import export  # noqa: E402

repo.add_command(export)
