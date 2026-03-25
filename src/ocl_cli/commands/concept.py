"""Concept commands: search, get, create, update, retire, names, descriptions, extras, versions, match."""

import json as json_lib
import sys

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import (
    output_result, format_concept_list, format_concept_detail,
    format_version_list, format_names_list, format_descriptions_list,
    format_extras, format_match_results,
)


@click.group()
def concept():
    """Manage OCL concepts."""
    pass


# ── Read commands ────────────────────────────────────────────────


@concept.command()
@click.argument("query", required=False)
@click.option("--owner", help="Filter by owner")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]))
@click.option("--repo", help="Filter by source/collection")
@click.option("--repo-type", type=click.Choice(["source", "collection"]), default="source")
@click.option("--version", help="Repository version")
@click.option("--concept-class", help="Filter by concept class")
@click.option("--datatype", help="Filter by datatype")
@click.option("--locale", help="Filter by locale")
@click.option("--include-retired", is_flag=True, help="Include retired concepts")
@click.option("--include-mappings", is_flag=True, help="Include mappings in results")
@click.option("--include-inverse-mappings", is_flag=True)
@click.option("--updated-since", help="Filter by update date (YYYY-MM-DD)")
@click.option("--sort", help="Sort field (prefix with - for descending)")
@click.option("--verbose", is_flag=True, help="Include extra detail")
@click.option("--limit", default=20, help="Results per page")
@click.option("--page", default=1, help="Page number")
@click.pass_context
def search(ctx, query, owner, owner_type, repo, repo_type, version, concept_class,
           datatype, locale, include_retired, include_mappings, include_inverse_mappings,
           updated_since, sort, verbose, limit, page):
    """Search for concepts globally or within a repository."""
    client = ctx.obj["client"]
    try:
        result = client.search_concepts(
            query=query, owner=owner, owner_type=owner_type,
            repo=repo, repo_type=repo_type, version=version,
            concept_class=concept_class, datatype=datatype, locale=locale,
            include_retired=include_retired, include_mappings=include_mappings,
            include_inverse_mappings=include_inverse_mappings,
            updated_since=updated_since, sort=sort, verbose=verbose,
            limit=limit, page=page,
        )
        output_result(ctx, result, lambda d: format_concept_list(d, page, limit, verbose=verbose))
    except APIError as e:
        handle_api_error(e)


@concept.command()
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--version", help="Source version")
@click.option("--concept-version", help="Specific concept version")
@click.option("--include-mappings", is_flag=True)
@click.option("--include-inverse-mappings", is_flag=True)
@click.option("--verbose", is_flag=True)
@click.pass_context
def get(ctx, owner, source, concept_id, owner_type, version, concept_version,
        include_mappings, include_inverse_mappings, verbose):
    """Get a single concept."""
    client = ctx.obj["client"]
    try:
        result = client.get_concept(
            owner, source, concept_id, owner_type=owner_type,
            version=version, concept_version=concept_version,
            include_mappings=include_mappings,
            include_inverse_mappings=include_inverse_mappings,
            verbose=verbose,
        )
        output_result(ctx, result, format_concept_detail)
    except APIError as e:
        handle_api_error(e)


@concept.command("versions")
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--limit", default=20)
@click.option("--page", default=1)
@click.pass_context
def concept_versions(ctx, owner, source, concept_id, owner_type, limit, page):
    """List version history for a concept."""
    client = ctx.obj["client"]
    try:
        result = client.get_concept_versions(owner, source, concept_id,
                                              owner_type=owner_type, limit=limit, page=page)
        output_result(ctx, result, format_version_list)
    except APIError as e:
        handle_api_error(e)


@concept.command("names")
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def concept_names(ctx, owner, source, concept_id, owner_type):
    """List names/translations for a concept."""
    client = ctx.obj["client"]
    try:
        result = client.get_concept_names(owner, source, concept_id, owner_type=owner_type)
        output_result(ctx, result, format_names_list)
    except APIError as e:
        handle_api_error(e)


@concept.command("descriptions")
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def concept_descriptions(ctx, owner, source, concept_id, owner_type):
    """List descriptions for a concept."""
    client = ctx.obj["client"]
    try:
        result = client.get_concept_descriptions(owner, source, concept_id, owner_type=owner_type)
        output_result(ctx, result, format_descriptions_list)
    except APIError as e:
        handle_api_error(e)


@concept.command("extras")
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def concept_extras(ctx, owner, source, concept_id, owner_type):
    """List custom attributes for a concept."""
    client = ctx.obj["client"]
    try:
        result = client.get_concept_extras(owner, source, concept_id, owner_type=owner_type)
        output_result(ctx, result, format_extras)
    except APIError as e:
        handle_api_error(e)


# ── Write commands ───────────────────────────────────────────────


@concept.command()
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--concept-class", required=True, help="Concept class (e.g. Diagnosis, Procedure)")
@click.option("--datatype", help="Data type (e.g. Numeric, Coded)")
@click.option("--name", "name_text", required=True, help="Primary name")
@click.option("--name-locale", default="en", help="Locale for primary name")
@click.option("--name-type", help="Name type (e.g. Fully Specified)")
@click.option("--names-json", help="JSON array of name objects (overrides --name)")
@click.option("--description", "desc_text", help="Primary description")
@click.option("--description-locale", default="en", help="Locale for description")
@click.option("--descriptions-json", help="JSON array of description objects")
@click.option("--external-id", help="External identifier")
@click.option("--extras", help="JSON string of extra attributes")
@click.pass_context
def create(ctx, owner, source, concept_id, owner_type, concept_class, datatype,
           name_text, name_locale, name_type, names_json,
           desc_text, description_locale, descriptions_json,
           external_id, extras):
    """Create a new concept in a source."""
    client = ctx.obj["client"]
    try:
        # Build names list
        if names_json:
            names = json_lib.loads(names_json)
        else:
            name_obj = {"name": name_text, "locale": name_locale, "locale_preferred": True}
            if name_type:
                name_obj["name_type"] = name_type
            names = [name_obj]

        # Build descriptions list
        descriptions = None
        if descriptions_json:
            descriptions = json_lib.loads(descriptions_json)
        elif desc_text:
            descriptions = [{"description": desc_text, "locale": description_locale}]

        extras_dict = json_lib.loads(extras) if extras else None

        result = client.create_concept(
            owner, source, concept_id, concept_class, names,
            owner_type=owner_type, datatype=datatype,
            descriptions=descriptions, external_id=external_id,
            extras=extras_dict,
        )
        output_result(ctx, result, format_concept_detail)
    except APIError as e:
        handle_api_error(e)


@concept.command()
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--concept-class", help="New concept class")
@click.option("--datatype", help="New datatype")
@click.option("--update-comment", help="Comment describing the update")
@click.pass_context
def update(ctx, owner, source, concept_id, owner_type, concept_class, datatype, update_comment):
    """Update an existing concept."""
    client = ctx.obj["client"]
    try:
        fields = {}
        if concept_class:
            fields["concept_class"] = concept_class
        if datatype:
            fields["datatype"] = datatype
        if not fields:
            click.echo("No fields to update. Use --concept-class, --datatype, etc.", err=True)
            sys.exit(1)

        result = client.update_concept(
            owner, source, concept_id, owner_type=owner_type,
            update_comment=update_comment, **fields,
        )
        output_result(ctx, result, format_concept_detail)
    except APIError as e:
        handle_api_error(e)


@concept.command()
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--update-comment", help="Comment for the retirement")
@click.pass_context
def retire(ctx, owner, source, concept_id, owner_type, update_comment):
    """Retire a concept (set retired=true)."""
    client = ctx.obj["client"]
    try:
        result = client.retire_concept(owner, source, concept_id,
                                        owner_type=owner_type, update_comment=update_comment)
        output_result(ctx, result, format_concept_detail)
    except APIError as e:
        handle_api_error(e)


@concept.command("name-add")
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.argument("name_text")
@click.option("--locale", required=True, help="Locale code")
@click.option("--name-type", help="Name type")
@click.option("--locale-preferred", is_flag=True, help="Mark as locale preferred")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def name_add(ctx, owner, source, concept_id, name_text, locale, name_type,
             locale_preferred, owner_type):
    """Add a name/translation to a concept."""
    client = ctx.obj["client"]
    try:
        result = client.add_concept_name(
            owner, source, concept_id, name_text, locale,
            owner_type=owner_type, name_type=name_type,
            locale_preferred=locale_preferred,
        )
        output_result(ctx, result)
    except APIError as e:
        handle_api_error(e)


@concept.command("description-add")
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.argument("text")
@click.option("--locale", required=True, help="Locale code")
@click.option("--description-type", help="Description type")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def description_add(ctx, owner, source, concept_id, text, locale, description_type, owner_type):
    """Add a description to a concept."""
    client = ctx.obj["client"]
    try:
        result = client.add_concept_description(
            owner, source, concept_id, text, locale,
            owner_type=owner_type, description_type=description_type,
        )
        output_result(ctx, result)
    except APIError as e:
        handle_api_error(e)


@concept.command("extra-set")
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.argument("key")
@click.argument("value")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def extra_set(ctx, owner, source, concept_id, key, value, owner_type):
    """Set a custom attribute on a concept."""
    client = ctx.obj["client"]
    try:
        try:
            parsed = json_lib.loads(value)
        except (json_lib.JSONDecodeError, ValueError):
            parsed = value
        result = client.set_concept_extra(owner, source, concept_id, key, parsed,
                                           owner_type=owner_type)
        output_result(ctx, result, format_extras)
    except APIError as e:
        handle_api_error(e)


@concept.command("extra-del")
@click.argument("owner")
@click.argument("source")
@click.argument("concept_id")
@click.argument("key")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.pass_context
def extra_del(ctx, owner, source, concept_id, key, owner_type):
    """Delete a custom attribute from a concept."""
    client = ctx.obj["client"]
    try:
        client.delete_concept_extra(owner, source, concept_id, key, owner_type=owner_type)
        click.echo(f"Deleted extra '{key}'")
    except APIError as e:
        handle_api_error(e)


@concept.command()
@click.argument("terms", nargs=-1, required=True)
@click.option("--target-source", required=True, help="Target source ID")
@click.option("--target-owner", default="CIEL", help="Target source owner")
@click.option("--target-version", help="Target source version")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--concept-class", help="Filter results by concept class (e.g. Diagnosis, Procedure)")
@click.option("--datatype", help="Filter results by datatype (e.g. Numeric, Coded)")
@click.option("--limit", default=5, help="Matches per term")
@click.option("--include-retired", is_flag=True)
@click.option("--include-mappings", is_flag=True, help="Include mapping summary for each result")
@click.option("--no-semantic", is_flag=True, help="Disable semantic matching (use keyword search only)")
@click.option("--verbose", is_flag=True)
@click.pass_context
def match(ctx, terms, target_source, target_owner, target_version, owner_type,
          concept_class, datatype, limit, include_retired, include_mappings,
          no_semantic, verbose):
    """Match terms against concepts using the $match endpoint."""
    client = ctx.obj["client"]
    try:
        # Build target_repo_url
        target_repo_url = f"/{owner_type}/{target_owner}/sources/{target_source}/"
        if target_version:
            target_repo_url = f"/{owner_type}/{target_owner}/sources/{target_source}/{target_version}/"

        result = client.match_concepts(
            terms=list(terms), target_repo_url=target_repo_url,
            concept_class=concept_class, datatype=datatype,
            limit=limit, include_retired=include_retired,
            include_mappings=include_mappings,
            semantic=not no_semantic, verbose=verbose,
        )
        output_result(ctx, result, format_match_results)
    except APIError as e:
        handle_api_error(e)
