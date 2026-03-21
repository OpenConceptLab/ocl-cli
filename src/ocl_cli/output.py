"""Output formatting for OCL CLI.

Handles JSON and human-readable table output.
"""

import json
import sys
from typing import Any, Callable, Optional

import click


def _source_from_url(url: str) -> str:
    """Extract a short source identifier from a source URL like /orgs/WHO/sources/ICD-10-WHO/."""
    if not url:
        return ""
    parts = [p for p in url.strip("/").split("/") if p]
    # Expected: orgs/OWNER/sources/SOURCE or users/OWNER/sources/SOURCE
    if len(parts) >= 4 and parts[2] == "sources":
        return f"{parts[1]}/{parts[3]}"
    return url


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

    mappings = data.get("mappings", [])
    if mappings:
        lines.append("  mappings:")
        for m in mappings:
            to_source = _source_from_url(m.get("to_source_url", ""))
            to_code = m.get("to_concept_code", m.get("to_concept_url", ""))
            to_name = m.get("to_concept_name") or m.get("to_concept_name_resolved", "")
            name_label = f" {to_name}" if to_name else ""
            source_label = f" ({to_source})" if to_source else ""
            lines.append(f"    [{m.get('map_type', '')}] → {to_code}{name_label}{source_label}")

    inverse_mappings = data.get("inverse_mappings", [])
    if inverse_mappings:
        lines.append("  inverse_mappings:")
        for m in inverse_mappings:
            from_source = _source_from_url(m.get("from_source_url", ""))
            from_code = m.get("from_concept_code", m.get("from_concept_url", ""))
            from_name = m.get("from_concept_name") or m.get("from_concept_name_resolved", "")
            name_label = f" {from_name}" if from_name else ""
            source_label = f" ({from_source})" if from_source else ""
            lines.append(f"    [{m.get('map_type', '')}] ← {from_code}{name_label}{source_label}")

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
            row["from_name"] = m.get("from_concept_name") or m.get("from_concept_name_resolved", "")
            row["to_source"] = _source_from_url(m.get("to_source_url", ""))
            row["to_name"] = m.get("to_concept_name") or m.get("to_concept_name_resolved", "")
            row["updated_on"] = str(m.get("updated_on", ""))[:10]
        display_rows.append(row)

    if verbose:
        table = format_table(
            display_rows,
            columns=["id", "map_type", "from", "from_name", "to", "to_source", "to_name", "source", "retired", "updated_on"],
            headers=["ID", "Map Type", "From", "From Name", "To", "To Source", "To Name", "Source", "Retired", "Updated"],
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
        # Fall back to *_resolved fields for concept names
        if val is None and key in ("from_concept_name", "to_concept_name"):
            val = data.get(f"{key}_resolved")
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


def _format_concept_label(c: dict, verbose: bool = False) -> str:
    """Format a concept label, optionally with class and datatype."""
    label = f"{c.get('id', '')} - {c.get('display_name', c.get('name', ''))}"
    if verbose:
        parts = []
        concept_class = c.get("concept_class")
        if concept_class:
            parts.append(concept_class)
        datatype = c.get("datatype")
        if datatype and datatype not in ("None", "N/A", "", None):
            parts.append(datatype)
        if parts:
            label += f" [{', '.join(parts)}]"
    return label


def _format_cascade_summary(concepts: list, mappings: list, verbose: bool = False) -> str:
    """Format the cascade summary line with optional class breakdown."""
    if verbose and concepts:
        from collections import Counter
        class_counts = Counter(c.get("concept_class", "Unknown") for c in concepts)
        if len(class_counts) > 1:
            breakdown = ", ".join(f"{count} {cls}" for cls, count in class_counts.most_common())
            return f"Cascade results: {len(concepts)} concepts ({breakdown}), {len(mappings)} mappings"
    return f"Cascade results: {len(concepts)} concepts, {len(mappings)} mappings"


def format_cascade_results(data: dict, root_id: str = "", verbose: bool = False) -> str:
    """Format $cascade results (flat view)."""
    entries = data.get("entry", [])
    if not entries:
        return "No cascade results."

    concepts = [e for e in entries if "concept_class" in e or e.get("type") == "Concept"]
    mappings = [e for e in entries if "map_type" in e or e.get("type") == "Mapping"]

    lines = [_format_cascade_summary(concepts, mappings, verbose)]

    if concepts:
        lines.append("\nConcepts:")
        for c in concepts[:50]:
            label = _format_concept_label(c, verbose)
            if root_id and str(c.get("id", "")) == str(root_id):
                label += " (root)"
            lines.append(f"  {label}")
        if len(concepts) > 50:
            lines.append(f"  ... and {len(concepts) - 50} more")

    if mappings:
        lines.append("\nMappings:")
        for m in mappings[:30]:
            to_source = _source_from_url(m.get("to_source_url", ""))
            to_code = m.get("to_concept_code", m.get("to_concept_url", ""))
            source_label = f" ({to_source})" if to_source else ""
            lines.append(f"  {m.get('id', '')} [{m.get('map_type', '')}] → {to_code}{source_label}")
        if len(mappings) > 30:
            lines.append(f"  ... and {len(mappings) - 30} more")

    return "\n".join(lines)


def _render_tree(node: dict, prefix: str, is_last: bool, lines: list,
                 verbose: bool, node_count: list, max_nodes: int,
                 concept_details: dict | None = None) -> None:
    """Recursively render a hierarchy node as a tree."""
    if node_count[0] >= max_nodes:
        return

    node_count[0] += 1
    connector = "└── " if is_last else "├── "
    # Render mappings differently from concepts
    if node.get("type") == "Mapping" or "map_type" in node:
        to_source = _source_from_url(node.get("to_source_url", ""))
        to_code = node.get("to_concept_code", node.get("to_concept_url", ""))
        source_label = f" ({to_source})" if to_source else ""
        label = f"[{node.get('map_type', '')}] → {to_code}{source_label}"
        lines.append(f"{prefix}{connector}{label}")
        return
    # Enrich node with concept details if available
    enriched = node
    if verbose and concept_details:
        detail = concept_details.get(str(node.get("id", "")))
        if detail:
            enriched = {**node, **{k: detail[k] for k in ("concept_class", "datatype") if k in detail}}
    label = _format_concept_label(enriched, verbose)
    lines.append(f"{prefix}{connector}{label}")

    children = node.get("entries", [])
    if not children:
        return

    child_prefix = prefix + ("    " if is_last else "│   ")

    remaining_budget = max_nodes - node_count[0]
    if len(children) > remaining_budget > 0:
        # Show what we can, then summarize
        for i, child in enumerate(children[:remaining_budget]):
            _render_tree(child, child_prefix, i == remaining_budget - 1 and remaining_budget == len(children),
                         lines, verbose, node_count, max_nodes, concept_details)
        if remaining_budget < len(children):
            lines.append(f"{child_prefix}... and {len(children) - remaining_budget} more")
        return

    for i, child in enumerate(children):
        _render_tree(child, child_prefix, i == len(children) - 1,
                     lines, verbose, node_count, max_nodes, concept_details)


def _count_nodes(node: dict) -> int:
    """Count total nodes in a hierarchy tree."""
    count = 1
    for child in node.get("entries", []):
        count += _count_nodes(child)
    return count


def _count_by_type(node: dict) -> tuple[int, int]:
    """Count concepts and mappings in a hierarchy tree."""
    is_mapping = node.get("type") == "Mapping" or "map_type" in node
    concepts = 0 if is_mapping else 1
    mappings = 1 if is_mapping else 0
    for child in node.get("entries", []):
        c, m = _count_by_type(child)
        concepts += c
        mappings += m
    return concepts, mappings


def format_cascade_hierarchy(data: dict, verbose: bool = False,
                             concept_details: dict | None = None) -> str:
    """Format $cascade results as a tree (hierarchy view)."""
    entry = data.get("entry", {})
    if not entry:
        return "No cascade results."

    # Hierarchy view returns a single root node with nested entries
    if isinstance(entry, list):
        # Flat response passed to hierarchy formatter — fall back
        return format_cascade_results(data, verbose=verbose)

    total = _count_nodes(entry)
    total_concepts, total_mappings = _count_by_type(entry)
    max_nodes = 100
    lines = []

    # Root node — enrich with concept details if available
    root = entry
    if verbose and concept_details:
        detail = concept_details.get(str(entry.get("id", "")))
        if detail:
            root = {**entry, **{k: detail[k] for k in ("concept_class", "datatype") if k in detail}}
    root_label = _format_concept_label(root, verbose)
    lines.append(root_label)

    children = entry.get("entries", [])
    node_count = [0]  # mutable counter for recursion

    for i, child in enumerate(children):
        _render_tree(child, "", i == len(children) - 1,
                     lines, verbose, node_count, max_nodes, concept_details)

    if total > max_nodes:
        lines.append(f"\nShowing {max_nodes} of {total} total nodes")

    # Append summary
    parts = []
    if total_concepts:
        parts.append(f"{total_concepts} concepts")
    if total_mappings:
        parts.append(f"{total_mappings} mappings")
    lines.insert(0, f"Cascade: {', '.join(parts) if parts else f'{total} nodes'}\n")

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
