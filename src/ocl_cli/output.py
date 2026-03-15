"""Output formatting for OCL CLI.

Handles JSON and human-readable table output.
"""

import json
import sys
from typing import Any, Callable, Optional

import click


def output_result(
    ctx: click.Context,
    data: Any,
    human_formatter: Optional[Callable] = None,
) -> None:
    """Output data as JSON or human-readable format based on --json flag."""
    if ctx.obj.get("json_output"):
        click.echo(json.dumps(data, indent=2, default=str))
    elif human_formatter:
        click.echo(human_formatter(data))
    else:
        # Fallback to JSON for anything without a custom formatter
        click.echo(json.dumps(data, indent=2, default=str))


def output_error(message: str, detail: str = "", status_code: int = 0) -> None:
    """Output error to stderr."""
    click.echo(f"Error: {message}", err=True)
    if detail:
        click.echo(f"  {detail}", err=True)


def format_table(rows: list[dict], columns: list[str], headers: Optional[list[str]] = None) -> str:
    """Format data as a simple aligned table."""
    if not rows:
        return "No results found."

    headers = headers or columns

    # Calculate column widths
    widths = [len(h) for h in headers]
    str_rows = []
    for row in rows:
        str_row = [str(row.get(col, "")) for col in columns]
        for i, val in enumerate(str_row):
            widths[i] = max(widths[i], len(val))
        str_rows.append(str_row)

    # Cap column widths at 60 chars
    widths = [min(w, 60) for w in widths]

    # Build output
    lines = []
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("  ".join("─" * w for w in widths))

    for str_row in str_rows:
        line = "  ".join(val[:widths[i]].ljust(widths[i]) for i, val in enumerate(str_row))
        lines.append(line)

    return "\n".join(lines)


def format_pagination(data: dict, page: int = 1, limit: int = 20) -> str:
    """Format pagination footer."""
    total = data.get("count", 0)
    if total == 0:
        return ""

    total_pages = max(1, (total + limit - 1) // limit)
    showing_start = (page - 1) * limit + 1
    showing_end = min(page * limit, total)

    parts = [f"Showing {showing_start}-{showing_end} of {total} results"]
    if total_pages > 1:
        parts.append(f"(page {page} of {total_pages})")
        if page < total_pages:
            parts.append(f"Use --page {page + 1} for next page.")

    return " ".join(parts)


# ── Resource-specific formatters ─────────────────────────────────


def format_owner_list(data: dict) -> str:
    """Format owner search results."""
    lines = []

    for section, label in [("users", "Users"), ("organizations", "Organizations")]:
        section_data = data.get(section)
        if not section_data:
            continue
        results = section_data.get("results", [])
        if not results:
            lines.append(f"\n{label}: No results found.")
            continue

        lines.append(f"\n{label}:")
        table = format_table(
            results,
            columns=["username", "name", "url"],
            headers=["Username", "Name", "URL"],
        )
        lines.append(table)

        count = section_data.get("count", len(results))
        if count > len(results):
            lines.append(f"  ... and {count - len(results)} more")

    return "\n".join(lines) if lines else "No results found."


def format_owner_detail(data: dict) -> str:
    """Format a single owner's details."""
    lines = []
    for key in ["username", "name", "company", "location", "url", "type", "public_access",
                 "members", "created_on", "updated_on"]:
        val = data.get(key)
        if val is not None:
            lines.append(f"  {key}: {val}")
    extras = data.get("extras")
    if extras:
        lines.append(f"  extras: {json.dumps(extras, default=str)}")
    return "\n".join(lines) if lines else json.dumps(data, indent=2, default=str)


def format_repo_list(data: dict) -> str:
    """Format repository search results."""
    results = data.get("results", [])
    if not results:
        return "No repositories found."

    table = format_table(
        results,
        columns=["short_code", "name", "owner", "repo_type", "url"],
        headers=["ID", "Name", "Owner", "Type", "URL"],
    )
    pagination = format_pagination(data)
    return f"{table}\n{pagination}" if pagination else table


def format_repo_detail(data: dict) -> str:
    """Format a single repo's details."""
    lines = []
    for key in ["short_code", "name", "full_name", "description", "type", "owner", "owner_type",
                 "url", "canonical_url", "default_locale", "supported_locales",
                 "source_type", "collection_type", "custom_validation_schema",
                 "public_access", "versions_url", "concepts_url", "active_concepts",
                 "active_mappings", "created_on", "updated_on"]:
        val = data.get(key)
        if val is not None:
            lines.append(f"  {key}: {val}")
    extras = data.get("extras")
    if extras:
        lines.append(f"  extras: {json.dumps(extras, default=str)}")
    return "\n".join(lines) if lines else json.dumps(data, indent=2, default=str)


def format_version_list(data: dict) -> str:
    """Format repository version list."""
    results = data.get("results", [])
    if not results:
        return "No versions found."
    return format_table(
        results,
        columns=["id", "released", "description", "created_on"],
        headers=["Version", "Released", "Description", "Created"],
    )


def format_concept_list(data: dict, page: int = 1, limit: int = 20, verbose: bool = False) -> str:
    """Format concept search results."""
    results = data.get("results", [])
    if not results:
        return "No concepts found."

    if verbose:
        # Build rows with names summary and updated date
        display_rows = []
        for r in results:
            names = r.get("names", [])
            names_summary = ", ".join(
                f"{n.get('locale', '?')}:{n.get('name', '')}"
                for n in names[:4]
            )
            if len(names) > 4:
                names_summary += f" (+{len(names) - 4})"
            display_rows.append({
                "id": r.get("id", ""),
                "display_name": r.get("display_name", ""),
                "concept_class": r.get("concept_class", ""),
                "datatype": r.get("datatype", ""),
                "source": r.get("source", ""),
                "retired": str(r.get("retired", "")),
                "names": names_summary,
                "updated_on": str(r.get("updated_on", ""))[:10],
            })
        table = format_table(
            display_rows,
            columns=["id", "display_name", "concept_class", "datatype", "source", "retired", "names", "updated_on"],
            headers=["ID", "Name", "Class", "Datatype", "Source", "Retired", "Names", "Updated"],
        )
    else:
        table = format_table(
            results,
            columns=["id", "display_name", "concept_class", "datatype", "source", "retired"],
            headers=["ID", "Name", "Class", "Datatype", "Source", "Retired"],
        )

    pagination = format_pagination(data, page, limit)
    return f"{table}\n{pagination}" if pagination else table


def format_concept_detail(data: dict) -> str:
    """Format a single concept's details."""
    lines = []
    for key in ["id", "display_name", "concept_class", "datatype", "retired",
                 "url", "owner", "owner_type", "source", "version",
                 "external_id", "created_on", "updated_on", "version_created_on"]:
        val = data.get(key)
        if val is not None:
            lines.append(f"  {key}: {val}")

    names = data.get("names", [])
    if names:
        lines.append("  names:")
        for n in names:
            pref = " *" if n.get("locale_preferred") else ""
            lines.append(f"    [{n.get('locale', '?')}] {n.get('name', '')}{pref} ({n.get('name_type', '')})")

    descriptions = data.get("descriptions", [])
    if descriptions:
        lines.append("  descriptions:")
        for d in descriptions:
            lines.append(f"    [{d.get('locale', '?')}] {d.get('description', '')}")

    extras = data.get("extras")
    if extras:
        lines.append(f"  extras: {json.dumps(extras, default=str)}")

    return "\n".join(lines) if lines else json.dumps(data, indent=2, default=str)


def format_mapping_list(data: dict, page: int = 1, limit: int = 20, verbose: bool = False) -> str:
    """Format mapping search results."""
    results = data.get("results", [])
    if not results:
        return "No mappings found."

    # Build display rows with from/to info
    display_rows = []
    for m in results:
        row = {
            "id": m.get("id", ""),
            "map_type": m.get("map_type", ""),
            "from": m.get("from_concept_code", "") or m.get("from_concept_url", ""),
            "to": m.get("to_concept_code", "") or m.get("to_concept_url", ""),
            "source": m.get("source", ""),
            "retired": str(m.get("retired", False)),
        }
        if verbose:
            row["from_name"] = m.get("from_concept_name", "")
            row["to_name"] = m.get("to_concept_name", "")
            row["updated_on"] = str(m.get("updated_on", ""))[:10]
        display_rows.append(row)

    if verbose:
        table = format_table(
            display_rows,
            columns=["id", "map_type", "from", "from_name", "to", "to_name", "source", "retired", "updated_on"],
            headers=["ID", "Map Type", "From", "From Name", "To", "To Name", "Source", "Retired", "Updated"],
        )
    else:
        table = format_table(
            display_rows,
            columns=["id", "map_type", "from", "to", "source", "retired"],
            headers=["ID", "Map Type", "From", "To", "Source", "Retired"],
        )

    pagination = format_pagination(data, page, limit)
    return f"{table}\n{pagination}" if pagination else table


def format_mapping_detail(data: dict) -> str:
    """Format a single mapping's details."""
    lines = []
    for key in ["id", "map_type", "retired", "url", "source", "owner", "owner_type",
                 "from_concept_url", "from_concept_code", "from_concept_name", "from_source_url",
                 "to_concept_url", "to_concept_code", "to_concept_name", "to_source_url",
                 "external_id", "created_on", "updated_on"]:
        val = data.get(key)
        if val is not None:
            lines.append(f"  {key}: {val}")
    extras = data.get("extras")
    if extras:
        lines.append(f"  extras: {json.dumps(extras, default=str)}")
    return "\n".join(lines) if lines else json.dumps(data, indent=2, default=str)


def format_match_results(data: dict) -> str:
    """Format $match results."""
    results = data.get("results", [])
    if not results:
        return "No match results."

    lines = []
    for item in results:
        row = item.get("row", {})
        lines.append(f"\nQuery: {row.get('name', row)}")
        matches = item.get("results", [])
        if not matches:
            lines.append("  No matches found.")
            continue
        for m in matches:
            score = m.get("search_meta", {}).get("search_score", "?")
            match_type = m.get("search_meta", {}).get("match_type", "")
            lines.append(
                f"  [{score:.2f}] {m.get('id', '')} - {m.get('display_name', '')}"
                f"  ({match_type}) {m.get('url', '')}"
            )
    return "\n".join(lines)


def format_cascade_results(data: dict) -> str:
    """Format $cascade results."""
    entries = data.get("entry", [])
    if not entries:
        return "No cascade results."

    concepts = [e for e in entries if "concept_class" in e or e.get("type") == "Concept"]
    mappings = [e for e in entries if "map_type" in e or e.get("type") == "Mapping"]
    other = [e for e in entries if e not in concepts and e not in mappings]

    lines = [f"Cascade results: {len(concepts)} concepts, {len(mappings)} mappings"]

    if concepts:
        lines.append("\nConcepts:")
        for c in concepts[:50]:
            lines.append(f"  {c.get('id', '')} - {c.get('display_name', c.get('name', ''))}")
        if len(concepts) > 50:
            lines.append(f"  ... and {len(concepts) - 50} more")

    if mappings:
        lines.append("\nMappings:")
        for m in mappings[:30]:
            lines.append(f"  {m.get('id', '')} [{m.get('map_type', '')}] → {m.get('to_concept_code', m.get('to_concept_url', ''))}")
        if len(mappings) > 30:
            lines.append(f"  ... and {len(mappings) - 30} more")

    return "\n".join(lines)


def format_ref_list(data: dict, page: int = 1, limit: int = 20) -> str:
    """Format collection reference list."""
    results = data.get("results", [])
    if not results:
        return "No references found."

    # References can be strings or dicts
    if results and isinstance(results[0], str):
        return "\n".join(results)

    table = format_table(
        results,
        columns=["expression", "reference_type", "concept_class"],
        headers=["Expression", "Type", "Class"],
    )
    pagination = format_pagination(data, page, limit)
    return f"{table}\n{pagination}" if pagination else table


def format_names_list(data: dict) -> str:
    """Format concept names."""
    results = data.get("results", [])
    if not results:
        return "No names found."

    return format_table(
        results,
        columns=["uuid", "name", "locale", "name_type", "locale_preferred"],
        headers=["UUID", "Name", "Locale", "Type", "Preferred"],
    )


def format_descriptions_list(data: dict) -> str:
    """Format concept descriptions."""
    results = data.get("results", [])
    if not results:
        return "No descriptions found."

    return format_table(
        results,
        columns=["uuid", "description", "locale", "description_type"],
        headers=["UUID", "Description", "Locale", "Type"],
    )


def format_extras(data: dict) -> str:
    """Format extras (custom attributes)."""
    if not data:
        return "No custom attributes."
    lines = []
    for key, val in data.items():
        lines.append(f"  {key}: {val}")
    return "\n".join(lines)


def format_expansion_list(data: dict) -> str:
    """Format expansion list."""
    results = data.get("results", [])
    if not results:
        return "No expansions found."

    return format_table(
        results,
        columns=["mnemonic", "id", "created_on"],
        headers=["Mnemonic", "ID", "Created"],
    )
