"""Cascade command."""

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import output_result, format_cascade_results


@click.command("cascade")
@click.argument("owner")
@click.argument("repo")
@click.argument("concept_id")
@click.option("--owner-type", type=click.Choice(["users", "orgs"]), default="orgs")
@click.option("--repo-type", type=click.Choice(["source", "collection"]), default="source")
@click.option("--repo-version", help="Repository version")
@click.option("--map-types", help="Comma-separated map types to traverse during cascade (controls which relationships are followed)")
@click.option("--exclude-map-types", help="Comma-separated map types to exclude")
@click.option("--return-map-types", help="Comma-separated map types to include in output (does not affect traversal)")
@click.option("--method", type=click.Choice(["sourcetoconcepts", "sourcemappings"]),
              default="sourcetoconcepts")
@click.option("--cascade-hierarchy/--no-cascade-hierarchy", default=True)
@click.option("--cascade-mappings/--no-cascade-mappings", default=True)
@click.option("--levels", default="*", help="Max recursion depth (* for unlimited)")
@click.option("--reverse", is_flag=True, help="Cascade in reverse direction")
@click.option("--view", type=click.Choice(["hierarchy", "flat"]), default="hierarchy")
@click.option("--verbose", is_flag=True, help="Include concept class and datatype in results")
@click.option("--omit-if-exists-in", help="Repository URL to check existence")
@click.option("--equivalency-map-type", help="Map type indicating equivalency")
@click.pass_context
def cascade_cmd(ctx, owner, repo, concept_id, owner_type, repo_type, repo_version,
                map_types, exclude_map_types, return_map_types, method,
                cascade_hierarchy, cascade_mappings, levels, reverse, view,
                verbose, omit_if_exists_in, equivalency_map_type):
    """Execute $cascade operation on a concept.

    Navigates concept hierarchies and mappings starting from a given concept.
    """
    client = ctx.obj["client"]
    try:
        cascade_kwargs = dict(
            owner_type=owner_type, repo_type=repo_type, repo_version=repo_version,
            map_types=map_types.split(",") if map_types else None,
            exclude_map_types=exclude_map_types.split(",") if exclude_map_types else None,
            return_map_types=return_map_types.split(",") if return_map_types else None,
            method=method,
            cascade_hierarchy=cascade_hierarchy,
            cascade_mappings=cascade_mappings,
            cascade_levels=levels,
            reverse=reverse,
            omit_if_exists_in=omit_if_exists_in,
            equivalency_map_type=equivalency_map_type,
        )
        result = client.cascade(
            owner, repo, concept_id, view=view, verbose=verbose, **cascade_kwargs,
        )
        tree_view = view == "hierarchy"
        output_result(ctx, result, lambda d: format_cascade_results(d, tree_view=tree_view, verbose=verbose))
    except APIError as e:
        handle_api_error(e)
