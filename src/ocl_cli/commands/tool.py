"""Tool commands: operational utilities for collection management.

Ported from OpenConceptLab/oclcli (Filipe Lopes), adapted to use
the centralized api_client pattern.
"""

import datetime
import json
import re
import sys
import time

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error

# Regex to detect versioned concept/mapping expressions (e.g. /concepts/100/1/)
VERSIONED_EXPR = re.compile(r"/(concepts|mappings)/\d+/\d+/?$")


def _canonicalize(expr: str | None) -> str | None:
    """Normalize an expression to end with exactly one trailing slash."""
    if not expr:
        return expr
    return expr.strip().rstrip("/") + "/"


def _is_concept_expression(expr: str | None) -> bool:
    return bool(expr and "/concepts/" in expr)


def _cascade_rank(cascade_obj: dict | None) -> int:
    """Rank cascade methods: sourcetoconcepts > sourcemappings > none."""
    if not cascade_obj:
        return 0
    method = cascade_obj.get("method")
    if method == "sourcetoconcepts":
        return 2
    if method == "sourcemappings":
        return 1
    return 0


def _translate_cascade(value) -> dict | None:
    """Convert a cascade value from export JSON to a cascade config dict."""
    if not value:
        return None
    v = str(value).strip().lower()
    if v in ("sourcemappings", "source mappings"):
        return {"method": "sourcemappings"}
    if v in ("sourcetoconcepts", "source to concepts"):
        return {"method": "sourcetoconcepts"}
    click.echo(f"[warn] Unsupported cascade value {value!r}. Ignoring...", err=True)
    return None


def _build_resource_indexes(export: dict) -> dict:
    """Build a version-to-base URL index from export concepts and mappings."""
    version_to_base: dict[str, str] = {}
    for resource_list in (export.get("concepts", []), export.get("mappings", [])):
        for item in resource_list:
            base = item.get("url")
            version_url = item.get("version_url")
            if base and version_url:
                version_to_base[_canonicalize(version_url)] = _canonicalize(base)
    return {"version_to_base": version_to_base}


def _resolve_expression(ref: dict, idx: dict) -> str | None:
    """Resolve a reference expression, stripping version numbers."""
    expression = ref.get("expression")
    if not expression:
        return expression
    expr = _canonicalize(expression)
    if not VERSIONED_EXPR.search(expr or ""):
        return _canonicalize(expr)
    # Try direct lookup in version-to-base index
    resolved = idx["version_to_base"].get(expr or "")
    if resolved:
        return _canonicalize(resolved)
    # Fallback: strip version from URL pattern
    m = re.search(r"^(.*?)/(concepts|mappings)/(\d+)(?:/\d+)?/?$", expr or "")
    if m:
        prefix, ref_type, concept_id = m.groups()
        base_id = ref.get("code") or concept_id
        fallback = f"{prefix}/{ref_type}/{base_id}/"
        click.echo(f"[warn] Stripping version: {expr} -> {fallback}", err=True)
        return _canonicalize(fallback)
    click.echo(f"[warn] Could not strip version, using original: {expression}", err=True)
    return _canonicalize(expr)


def _build_collection_payload(export: dict, override_name: str | None = None) -> dict:
    """Build a collection create payload from export data."""
    coll = export.get("collection", {})
    name = override_name or coll.get("name", "")
    cid = override_name or coll.get("id", "")
    return {
        "id": cid,
        "name": name,
        "full_name": name if override_name else (coll.get("full_name") or name),
        "mnemonic": cid,
        "description": coll.get("description", ""),
        "collection_type": coll.get("collection_type", "Subset"),
        "default_locale": coll.get("default_locale", "en"),
        "supported_locales": coll.get("supported_locales", ["en"]),
        "public_access": coll.get("public_access", "View"),
        "custom_validation_schema": coll.get("custom_validation_schema", "None"),
    }


def _collection_url(org: str | None, collection_id: str) -> str:
    """Build the collection URL path."""
    if org:
        return f"/orgs/{org}/collections/{collection_id}/"
    return f"/user/collections/{collection_id}/"


def _build_references(export, org, collection_id, client, callback=None):
    """Build deduplicated, versionless reference lines from export data.

    Returns (references, stats).
    """
    reference_entries = export.get("references", [])
    total = len(reference_entries)
    resource_idx = _build_resource_indexes(export)
    collection_url = _collection_url(org, collection_id)

    seen: dict[str, tuple[int, dict]] = {}
    stats = {
        "duplicates": 0,
        "skipped_non_concepts": 0,
        "skipped_mappings": 0,
        "pruned_children": 0,
    }

    for i, ref in enumerate(reference_entries, start=1):
        if not ref.get("include", True):
            continue
        expression = _canonicalize(_resolve_expression(ref, resource_idx))
        if not expression:
            continue
        if not _is_concept_expression(expression):
            stats["skipped_non_concepts"] += 1
            if "/mappings/" in expression:
                stats["skipped_mappings"] += 1
            continue

        cascade_obj = _translate_cascade(ref.get("cascade"))
        if not cascade_obj:
            cascade_obj = {"method": "sourcetoconcepts"}
        rank = _cascade_rank(cascade_obj)

        item = {
            "type": "Reference",
            "collection_url": collection_url,
            "data": {"expressions": [expression]},
            "__cascade": cascade_obj,
        }

        existing = seen.get(expression)
        if existing:
            stats["duplicates"] += 1
            if rank > existing[0]:
                seen[expression] = (rank, item)
            continue
        seen[expression] = (rank, item)

        if callback and i % 100 == 0:
            callback(i, total)

    # Prune child concepts covered by parent cascade sets
    if client:
        expressions = list(seen.keys())
        total_cascade = len(expressions)
        if total_cascade:
            click.echo(f"[info] Checking {total_cascade} concept(s) for hierarchy pruning...")
        removed = set()
        parent_for = {}
        for idx, expr in enumerate(expressions, start=1):
            if idx % 10 == 0 or idx == total_cascade:
                click.echo(f"  Cascade lookup {idx}/{total_cascade}...", err=True)
            children = client.fetch_cascade_children(expr)
            for child in children:
                if child in seen:
                    removed.add(child)
                    parent_for.setdefault(child, expr)
        for child in removed:
            seen.pop(child, None)
        stats["pruned_children"] = len(removed)
        if removed:
            click.echo(f"[info] Pruned {len(removed)} child concept(s) covered by parent sets.")

    return [entry[1] for entry in seen.values()], stats


@click.group()
def tool():
    """Operational tools for collection management."""
    pass


@tool.command("recreate-collection")
@click.option("--input", "-i", "input_path", required=True,
              type=click.Path(exists=True, readable=True),
              help="Path to collection export JSON file")
@click.option("--org", "-o", help="Target organization (omit for user-scoped)")
@click.option("--name", "-n", help="Override collection id/name")
@click.option("--output", "output_path", type=click.Path(),
              help="Output file for generated references JSON")
@click.option("--dry-run/--no-dry-run", default=True, show_default=True,
              help="Generate JSON only (use --no-dry-run to apply changes)")
@click.pass_context
def recreate_collection(ctx, input_path, org, name, output_path, dry_run):
    """Recreate a collection with versionless references.

    Loads a collection export JSON, strips versioned reference URLs,
    deduplicates, prunes child concepts covered by parent cascade sets,
    and outputs a bulk-import-ready JSON file.

    With --no-dry-run, deletes and recreates the collection, then runs
    a bulk import of the versionless references.

    Ported from OpenConceptLab/oclcli by Filipe Lopes.
    """
    client = ctx.obj["client"]

    # Load export
    try:
        with open(input_path, encoding="utf-8") as f:
            export_data = json.load(f)
    except Exception as exc:
        click.echo(f"Error: Failed to load export file: {exc}", err=True)
        sys.exit(1)

    collection_id = name or export_data.get("collection", {}).get("id")
    if not collection_id:
        click.echo("Error: Collection id not found in export and --name not provided.", err=True)
        sys.exit(1)

    # Default output filename
    if not output_path:
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M")
        scope = org or "user"
        output_path = f"{scope}_{collection_id}_{ts}.json"

    # Build references
    references, stats = _build_references(export_data, org, collection_id, client)

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(references, f, indent=2, ensure_ascii=False)
        f.write("\n")
    click.echo(f"Prepared {len(references)} references (saved to {output_path})")

    # Show stats
    notes = []
    if stats["duplicates"]:
        notes.append(f"{stats['duplicates']} duplicate(s)")
    if stats["skipped_non_concepts"]:
        notes.append(f"{stats['skipped_non_concepts']} non-concept reference(s) skipped")
    if stats["skipped_mappings"]:
        notes.append(f"{stats['skipped_mappings']} mapping reference(s) skipped")
    if stats["pruned_children"]:
        notes.append(f"{stats['pruned_children']} child concept(s) pruned")
    if notes:
        click.echo("Notes: " + "; ".join(notes))

    if dry_run:
        click.echo("Dry run: collection was not recreated. Use --no-dry-run to apply changes.")
        return

    # Delete and recreate collection
    click.echo("Recreating collection and importing references...")
    collection_path = _collection_url(org, collection_id)
    try:
        # Check if collection exists
        try:
            client.get(collection_path)
            click.echo(f"Deleting collection {collection_id}...")
            client.delete(collection_path)
        except APIError as e:
            if e.status_code == 404:
                click.echo(f"Collection {collection_id} does not exist, skipping delete.")
            else:
                raise

        # Create collection
        click.echo(f"Creating collection {collection_id}...")
        payload = _build_collection_payload(export_data, name)
        collections_path = f"/orgs/{org}/collections/" if org else "/user/collections/"
        client.post(collections_path, json=payload)

        # Bulk import
        result = client.bulk_import(references)
        click.echo("Bulk import started.")
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))

        # Wait for completion if task ID returned
        task_id = result.get("id")
        if task_id:
            click.echo("Waiting for bulk import to complete...")
            while True:
                try:
                    task_data = client.get_task(task_id)
                except APIError:
                    time.sleep(5)
                    continue
                state = task_data.get("state")
                if state == "SUCCESS":
                    click.echo("Bulk import completed successfully.")
                    break
                elif state in ("FAILURE", "REVOKED"):
                    click.echo(f"Bulk import failed: {state}", err=True)
                    sys.exit(2)
                else:
                    click.echo(f"  Task state: {state}, waiting...")
                    time.sleep(5)

    except APIError as e:
        handle_api_error(e)
