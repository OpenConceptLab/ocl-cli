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
    results = data.get("results", [])
    if not results:
        return "No owners found."

    rows = []
    for owner in results:
        rows.append({
            "id": owner.get("id", ""),
            "name": owner.get("name", ""),
            "type": owner.get("type", ""),
            "public_repos": owner.get("public_sources", 0) + owner.get("public_collections", 0),
            "location": owner.get("location", ""),
        })

    table = format_table(
        rows,
        ["id", "name", "type", "public_repos", "location"],
        ["ID", "Name", "Type", "Public Repos", "Location"],
    )

    pagination = format_pagination(data)
    return f"{table}\n\n{pagination}" if pagination else table


def format_owner_detail(data: dict) -> str:
    """Format single owner details."""
    lines = []
    lines.append(f"ID: {data.get('id', '')}")
    lines.append(f"Name: {data.get('name', '')}")
    lines.append(f"Type: {data.get('type', '')}")
    lines.append(f"Company: {data.get('company', '')}")
    lines.append(f"Location: {data.get('location', '')}")
    lines.append(f"Website: {data.get('website', '')}")
    lines.append(f"Public Sources: {data.get('public_sources', 0)}")
    lines.append(f"Public Collections: {data.get('public_collections', 0)}")
    lines.append(f"Created: {data.get('created_on', '')}")
    lines.append(f"Updated: {data.get('updated_on', '')}")

    if data.get("extras"):
        lines.append("\nExtras:")
        for key, value in data["extras"].items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def format_repo_list(data: dict, verbose: bool = False) -> str:
    """Format repository search results."""
    results = data.get("results", [])
    if not results:
        return "No repositories found."

    rows = []
    for repo in results:
        row = {
            "id": repo.get("id", ""),
            "name": repo.get("name", ""),
            "type": repo.get("source_type") or repo.get("collection_type", ""),
            "owner": repo.get("owner", ""),
            "version": repo.get("version", ""),
            "concepts": repo.get("active_concepts", 0),
        }

        if verbose:
            row.update({
                "description": repo.get("description", "")[:50] + ("..." if len(repo.get("description", "")) > 50 else ""),
                "updated": repo.get("updated_on", "")[:10] if repo.get("updated_on") else "",
            })

        rows.append(row)

    columns = ["id", "name", "type", "owner", "version", "concepts"]
    headers = ["ID", "Name", "Type", "Owner", "Version", "Concepts"]

    if verbose:
        columns.extend(["description", "updated"])
        headers.extend(["Description", "Updated"])

    table = format_table(rows, columns, headers)
    pagination = format_pagination(data)
    return f"{table}\n\n{pagination}" if pagination else table


def format_repo_detail(data: dict) -> str:
    """Format single repository details."""
    lines = []
    lines.append(f"ID: {data.get('id', '')}")
    lines.append(f"Name: {data.get('name', '')}")
    lines.append(f"Type: {data.get('source_type') or data.get('collection_type', '')}")
    lines.append(f"Owner: {data.get('owner', '')}")
    lines.append(f"Version: {data.get('version', '')}")
    lines.append(f"Description: {data.get('description', '')}")
    lines.append(f"Default Locale: {data.get('default_locale', '')}")
    lines.append(f"Supported Locales: {', '.join(data.get('supported_locales', []))}")
    lines.append(f"Public Access: {data.get('public_access', '')}")
    lines.append(f"Active Concepts: {data.get('active_concepts', 0)}")
    lines.append(f"Active Mappings: {data.get('active_mappings', 0)}")
    lines.append(f"Created: {data.get('created_on', '')}")
    lines.append(f"Updated: {data.get('updated_on', '')}")
    lines.append(f"URL: {data.get('url', '')}")

    if data.get("extras"):
        lines.append("\nExtras:")
        for key, value in data["extras"].items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def format_concept_list(data: dict, page: int = 1, limit: int = 20, verbose: bool = False) -> str:
    """Format concept search results."""
    results = data.get("results", [])
    if not results:
        return "No concepts found."

    rows = []
    for concept in results:
        row = {
            "id": concept.get("id", ""),
            "display_name": concept.get("display_name", ""),
            "concept_class": concept.get("concept_class", ""),
            "datatype": concept.get("datatype", ""),
            "source": _source_from_url(concept.get("source_url", "")),
        }

        if verbose:
            row.update({
                "description": concept.get("description", "")[:40] + ("..." if len(concept.get("description", "")) > 40 else ""),
                "updated": concept.get("updated_on", "")[:10] if concept.get("updated_on") else "",
            })

        rows.append(row)

    columns = ["id", "display_name", "concept_class", "datatype", "source"]
    headers = ["ID", "Display Name", "Class", "Datatype", "Source"]

    if verbose:
        columns.extend(["description", "updated"])
        headers.extend(["Description", "Updated"])

    table = format_table(rows, columns, headers)
    pagination = format_pagination(data, page, limit)
    return f"{table}\n\n{pagination}" if pagination else table


def format_concept_detail(data: dict) -> str:
    """Format single concept details."""
    lines = []
    lines.append(f"ID: {data.get('id', '')}")
    lines.append(f"Display Name: {data.get('display_name', '')}")
    lines.append(f"Concept Class: {data.get('concept_class', '')}")
    lines.append(f"Datatype: {data.get('datatype', '')}")
    lines.append(f"Source: {_source_from_url(data.get('source_url', ''))}")
    lines.append(f"Owner: {data.get('owner', '')}")
    lines.append(f"Version: {data.get('version', '')}")
    lines.append(f"Description: {data.get('description', '')}")
    lines.append(f"Retired: {data.get('retired', False)}")
    lines.append(f"Created: {data.get('created_on', '')}")
    lines.append(f"Updated: {data.get('updated_on', '')}")
    lines.append(f"URL: {data.get('url', '')}")

    # Names
    if data.get("names"):
        lines.append("\nNames:")
        for name in data["names"]:
            locale = name.get("locale", "")
            name_type = name.get("name_type", "")
            name_val = name.get("name", "")
            lines.append(f"  {name_val} ({locale}, {name_type})")

    # Descriptions
    if data.get("descriptions"):
        lines.append("\nDescriptions:")
        for desc in data["descriptions"]:
            locale = desc.get("locale", "")
            desc_type = desc.get("description_type", "")
            desc_val = desc.get("description", "")
            lines.append(f"  {desc_val} ({locale}, {desc_type})")

    # Mappings (if included)
    if data.get("mappings"):
        lines.append("\nMappings:")
        lines.append(format_mappings_table(data["mappings"]))

    # Extras
    if data.get("extras"):
        lines.append("\nExtras:")
        for key, value in data["extras"].items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def format_mappings_table(mappings: list) -> str:
    """Format mappings as a cross-reference table."""
    if not mappings:
        return "  No mappings found."

    rows = []
    for mapping in mappings:
        # Extract target source from to_source_url
        target_source = _source_from_url(mapping.get("to_source_url", ""))

        rows.append({
            "target_source": target_source,
            "target_code": mapping.get("to_concept_code", ""),
            "target_name": mapping.get("to_concept_name", ""),
            "map_type": mapping.get("map_type", ""),
        })

    # Format as indented table
    table = format_table(
        rows,
        ["target_source", "target_code", "target_name", "map_type"],
        ["Target Source", "Target Code", "Target Name", "Map Type"],
    )

    # Indent each line
    return "\n".join(f"  {line}" for line in table.split("\n"))


def format_mapping_list(data: dict, page: int = 1, limit: int = 20, verbose: bool = False) -> str:
    """Format mapping search results."""
    results = data.get("results", [])
    if not results:
        return "No mappings found."

    rows = []
    for mapping in results:
        raw_from = mapping.get("from_concept_name") or mapping.get("from_concept_name_resolved") or ""
        from_name = raw_from[:30] + ("..." if len(raw_from) > 30 else "")
        raw_to = mapping.get("to_concept_name") or mapping.get("to_concept_name_resolved") or ""
        to_name = raw_to[:30] + ("..." if len(raw_to) > 30 else "")

        row = {
            "id": mapping.get("id", ""),
            "from_source": _source_from_url(mapping.get("from_source_url", "")),
            "from_code": mapping.get("from_concept_code", ""),
            "from_name": from_name,
            "map_type": mapping.get("map_type", ""),
            "to_source": _source_from_url(mapping.get("to_source_url", "")),
            "to_code": mapping.get("to_concept_code", ""),
            "to_name": to_name,
        }
        rows.append(row)

    columns = ["id", "from_source", "from_code", "map_type", "to_source", "to_code"]
    headers = ["ID", "From Source", "From Code", "Map Type", "To Source", "To Code"]

    if verbose:
        columns = ["id", "from_source", "from_code", "from_name", "map_type", "to_source", "to_code", "to_name"]
        headers = ["ID", "From Source", "From Code", "From Name", "Map Type", "To Source", "To Code", "To Name"]

    table = format_table(rows, columns, headers)
    pagination = format_pagination(data, page, limit)
    return f"{table}\n\n{pagination}" if pagination else table


def format_mapping_detail(data: dict) -> str:
    """Format single mapping details."""
    lines = []
    lines.append(f"ID: {data.get('id', '')}")
    lines.append(f"Map Type: {data.get('map_type', '')}")
    lines.append(f"From Concept: {data.get('from_concept_code', '')} - {data.get('from_concept_name', '')}")
    lines.append(f"To Concept: {data.get('to_concept_code', '')} - {data.get('to_concept_name', '')}")
    lines.append(f"Source: {_source_from_url(data.get('source_url', ''))}")
    lines.append(f"To Source: {_source_from_url(data.get('to_source_url', ''))}")
    lines.append(f"Owner: {data.get('owner', '')}")
    lines.append(f"Version: {data.get('version', '')}")
    lines.append(f"Retired: {data.get('retired', False)}")
    lines.append(f"Created: {data.get('created_on', '')}")
    lines.append(f"Updated: {data.get('updated_on', '')}")
    lines.append(f"URL: {data.get('url', '')}")

    if data.get("extras"):
        lines.append("\nExtras:")
        for key, value in data["extras"].items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def format_version_list(data: dict) -> str:
    """Format version list."""
    results = data.get("results", [])
    if not results:
        return "No versions found."

    rows = []
    for version in results:
        algos = version.get("match_algorithms", [])
        rows.append({
            "id": version.get("id", ""),
            "description": version.get("description", ""),
            "released": "Yes" if version.get("released") else "No",
            "match": ", ".join(algos) if algos else "",
            "created": version.get("created_at", "")[:10] if version.get("created_at") else "",
        })

    return format_table(
        rows,
        ["id", "description", "released", "match", "created"],
        ["Version", "Description", "Released", "Match Algos", "Created"],
    )


def format_names_list(data: dict) -> str:
    """Format concept names list."""
    results = data.get("results", [])
    if not results:
        return "No names found."

    rows = []
    for name in results:
        rows.append({
            "name": name.get("name", ""),
            "locale": name.get("locale", ""),
            "type": name.get("name_type", ""),
            "preferred": "Yes" if name.get("locale_preferred") else "No",
        })

    return format_table(
        rows,
        ["name", "locale", "type", "preferred"],
        ["Name", "Locale", "Type", "Preferred"],
    )


def format_descriptions_list(data: dict) -> str:
    """Format concept descriptions list."""
    results = data.get("results", [])
    if not results:
        return "No descriptions found."

    rows = []
    for desc in results:
        description_text = desc.get("description", "")
        if len(description_text) > 60:
            description_text = description_text[:57] + "..."

        rows.append({
            "description": description_text,
            "locale": desc.get("locale", ""),
            "type": desc.get("description_type", ""),
            "preferred": "Yes" if desc.get("locale_preferred") else "No",
        })

    return format_table(
        rows,
        ["description", "locale", "type", "preferred"],
        ["Description", "Locale", "Type", "Preferred"],
    )


def format_extras(data: dict) -> str:
    """Format extras dictionary."""
    if not data:
        return "No extras found."

    lines = []
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2)
        lines.append(f"{key}: {value}")

    return "\n".join(lines)


def format_match_results(data: dict) -> str:
    """Format $match results grouped by input term."""
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
            score_str = f"{score:.2f}" if isinstance(score, (int, float)) else str(score)
            lines.append(
                f"  [{score_str}] {m.get('id', '')} - {m.get('display_name', '')}"
                f"  {m.get('url', '')}"
            )
    return "\n".join(lines)


def format_cascade_results(data: dict, tree_view: bool = True, verbose: bool = False) -> str:
    """Format cascade results with tree visualization."""
    # Hierarchy view returns entry (dict with nested entries), flat view returns results (list)
    entry = data.get("entry")
    if entry and isinstance(entry, dict):
        results = [entry]
    else:
        results = data.get("results", [])
    if not results:
        return "No cascade results found."

    if tree_view:
        return _format_cascade_tree(results, verbose)
    else:
        return _format_cascade_table(results, verbose)


def _format_cascade_tree(results: list, verbose: bool = False, level: int = 0, is_last: list = None) -> str:
    """Format cascade results as a tree."""
    if is_last is None:
        is_last = []

    lines = []
    for i, item in enumerate(results):
        is_last_item = i == len(results) - 1
        current_is_last = is_last + [is_last_item]

        # Build prefix
        prefix = ""
        for j, last in enumerate(current_is_last[:-1]):
            if last:
                prefix += "    "
            else:
                prefix += "│   "

        if level > 0:
            if is_last_item:
                prefix += "└── "
            else:
                prefix += "├── "

        # Format item
        concept_id = item.get("id", "")
        display_name = item.get("display_name", "")
        concept_class = item.get("concept_class", "")

        line = f"{prefix}{concept_id}"
        if display_name:
            line += f" - {display_name}"
        if verbose and concept_class:
            line += f" ({concept_class})"

        lines.append(line)

        # Recursively format children (API uses "entries" for hierarchy view)
        children = item.get("entries", [])
        if children:
            child_lines = _format_cascade_tree(children, verbose, level + 1, current_is_last)
            lines.append(child_lines)

    return "\n".join(lines)


def _format_cascade_table(results: list, verbose: bool = False) -> str:
    """Format cascade results as a flat table."""
    rows = []

    def flatten_results(items, level=0):
        for item in items:
            row = {
                "level": "  " * level,
                "id": item.get("id", ""),
                "display_name": item.get("display_name", ""),
                "concept_class": item.get("concept_class", ""),
                "source": _source_from_url(item.get("source_url", "")),
            }

            if verbose:
                row["datatype"] = item.get("datatype", "")

            rows.append(row)

            # Process children (API uses "entries" for hierarchy view)
            children = item.get("entries", [])
            if children:
                flatten_results(children, level + 1)

    flatten_results(results)

    columns = ["level", "id", "display_name", "concept_class", "source"]
    headers = ["Level", "ID", "Display Name", "Class", "Source"]

    if verbose:
        columns.append("datatype")
        headers.append("Datatype")

    return format_table(rows, columns, headers)


def format_reference_list(data: dict) -> str:
    """Format collection reference list."""
    results = data.get("results", [])
    if not results:
        return "No references found."

    rows = []
    for ref in results:
        rows.append({
            "expression": ref.get("expression", ""),
            "type": ref.get("reference_type", ""),
            "concepts": ref.get("concepts", 0),
            "mappings": ref.get("mappings", 0),
        })

    return format_table(
        rows,
        ["expression", "type", "concepts", "mappings"],
        ["Expression", "Type", "Concepts", "Mappings"],
    )


def format_expansion_list(data: dict) -> str:
    """Format expansion list."""
    results = data.get("results", [])
    if not results:
        return "No expansions found."

    rows = []
    for expansion in results:
        rows.append({
            "id": expansion.get("id", ""),
            "collection_version": expansion.get("collection_version", ""),
            "concepts": expansion.get("concepts", 0),
            "mappings": expansion.get("mappings", 0),
            "created": expansion.get("created_on", "")[:10] if expansion.get("created_on") else "",
        })

    return format_table(
        rows,
        ["id", "collection_version", "concepts", "mappings", "created"],
        ["ID", "Collection Version", "Concepts", "Mappings", "Created"],
    )


def format_expansion_detail(data: dict) -> str:
    """Format single expansion details."""
    lines = []
    lines.append(f"ID: {data.get('id', '')}")
    lines.append(f"Collection Version: {data.get('collection_version', '')}")
    lines.append(f"Concepts: {data.get('concepts', 0)}")
    lines.append(f"Mappings: {data.get('mappings', 0)}")
    lines.append(f"Created: {data.get('created_on', '')}")
    lines.append(f"URL: {data.get('url', '')}")

    return "\n".join(lines)


def format_user_detail(data: dict) -> str:
    """Format user profile (whoami)."""
    lines = []
    lines.append(f"Username: {data.get('username', '')}")

    # Prefer 'name' field over first_name/last_name concatenation
    name = data.get("name", "").strip()
    if not name:
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        name = f"{first_name} {last_name}".strip()

    if name:
        lines.append(f"Name: {name}")

    lines.append(f"Email: {data.get('email', '')}")
    lines.append(f"Company: {data.get('company', '')}")
    lines.append(f"Location: {data.get('location', '')}")
    lines.append(f"Date Joined: {data.get('date_joined', '')}")
    lines.append(f"Last Login: {data.get('last_login', '')}")
    lines.append(f"Organizations: {data.get('organizations', 0)}")
    lines.append(f"Public Sources: {data.get('public_sources', 0)}")
    lines.append(f"Public Collections: {data.get('public_collections', 0)}")

    return "\n".join(lines)


def format_server_list(servers: dict, default_server: str) -> str:
    """Format server list."""
    if not servers:
        return "No servers configured."

    rows = []
    for server_id, config in servers.items():
        marker = "* " if server_id == default_server else "  "
        rows.append({
            "marker": marker,
            "id": server_id,
            "name": config.get("name", ""),
            "url": config.get("base_url", ""),
        })

    return format_table(
        rows,
        ["marker", "id", "name", "url"],
        ["", "ID", "Name", "URL"],
    )


def format_task_list(data: dict, verbose: bool = False) -> str:
    """Format task list results."""
    results = data.get("results", [])
    if not results:
        return "No tasks found."

    if verbose:
        display_rows = []
        for t in results:
            row = {
                "id": str(t.get("id", "")),
                "state": t.get("state", ""),
                "name": t.get("name", t.get("task", "")),
                "queue": t.get("queue", ""),
                "started_at": str(t.get("started_at", ""))[:19],
                "finished_at": str(t.get("finished_at", ""))[:19],
                "runtime": _format_runtime(t.get("started_at"), t.get("finished_at")),
                "message": str(t.get("result", t.get("summary", "")))[:60],
            }
            display_rows.append(row)
        return format_table(
            display_rows,
            columns=["id", "state", "name", "queue", "started_at", "finished_at", "runtime", "message"],
            headers=["ID", "State", "Name", "Queue", "Started", "Finished", "Runtime", "Message"],
        )
    else:
        display_rows = []
        for t in results:
            display_rows.append({
                "id": str(t.get("id", "")),
                "state": t.get("state", ""),
                "name": t.get("name", t.get("task", "")),
                "updated_on": str(t.get("finished_at") or t.get("started_at") or "")[:19],
            })
        return format_table(
            display_rows,
            columns=["id", "state", "name", "updated_on"],
            headers=["ID", "State", "Name", "Updated"],
        )


def _format_runtime(started: Any, finished: Any) -> str:
    """Calculate runtime between two timestamp strings."""
    if not started or not finished:
        return ""
    try:
        from datetime import datetime
        fmt = "%Y-%m-%dT%H:%M:%S"
        s = str(started)[:19]
        f = str(finished)[:19]
        delta = datetime.fromisoformat(s) - datetime.fromisoformat(f)
        seconds = abs(delta.total_seconds())
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        else:
            return f"{seconds / 3600:.1f}h"
    except Exception:
        return ""


def format_task_detail(data: dict) -> str:
    """Format a single task's details."""
    lines = []
    for key in ["id", "state", "name", "task", "queue",
                 "started_at", "finished_at", "created_on",
                 "result", "summary", "traceback"]:
        val = data.get(key)
        if val is not None and val != "":
            lines.append(f"  {key}: {val}")
    return "\n".join(lines) if lines else json.dumps(data, indent=2, default=str)
