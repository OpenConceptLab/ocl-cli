"""Reference command — dumps the full CLI command tree.

Designed for AI agent consumption: one command to discover the entire CLI surface.
"""

import json

import click


def _collect_params(cmd):
    """Collect arguments and options from a Click command."""
    arguments = []
    options = []

    for param in cmd.params:
        if isinstance(param, click.Argument):
            arguments.append({
                "name": param.name,
                "required": param.required,
                "nargs": param.nargs,
                "type": param.type.name,
            })
        elif isinstance(param, click.Option):
            opt = {
                "flags": param.opts + param.secondary_opts,
                "help": param.help or "",
                "required": param.required,
                "type": param.type.name,
                "is_flag": param.is_flag,
            }
            if (param.default is not None
                    and not param.is_flag
                    and "Sentinel" not in repr(param.default)):
                opt["default"] = param.default
            options.append(opt)

    return arguments, options


def _walk_tree(cmd, prefix="ocl"):
    """Recursively walk the Click command tree and yield command info dicts."""
    if isinstance(cmd, click.Group):
        for name in sorted(cmd.list_commands(click.Context(cmd, info_name=prefix))):
            subcmd = cmd.get_command(click.Context(cmd, info_name=prefix), name)
            if subcmd is None:
                continue
            full_name = f"{prefix} {name}"
            arguments, options = _collect_params(subcmd)
            yield {
                "command": full_name,
                "help": subcmd.get_short_help_str(limit=300),
                "arguments": arguments,
                "options": options,
                "is_group": isinstance(subcmd, click.Group),
            }
            if isinstance(subcmd, click.Group):
                yield from _walk_tree(subcmd, prefix=full_name)


def _format_text(commands):
    """Format command tree as human-readable text."""
    lines = []
    lines.append("OCL CLI Reference")
    lines.append("=" * 60)
    lines.append("")

    for cmd in commands:
        lines.append(cmd["command"])
        lines.append(f"  {cmd['help']}")

        if cmd["arguments"]:
            args_str = " ".join(
                f"{a['name'].upper()}"
                + ("..." if a["nargs"] == -1 else "")
                + ("" if a["required"] else "?")
                for a in cmd["arguments"]
            )
            lines.append(f"  Args: {args_str}")

        if cmd["options"]:
            for opt in cmd["options"]:
                flags = ", ".join(opt["flags"])
                parts = [f"    {flags}"]
                if opt["is_flag"]:
                    parts.append("(flag)")
                elif opt.get("default") is not None:
                    parts.append(f"[default: {opt['default']}]")
                if opt["required"]:
                    parts.append("(required)")
                if opt["help"]:
                    parts.append(f"— {opt['help']}")
                lines.append(" ".join(parts))

        lines.append("")

    return "\n".join(lines)


@click.command("reference")
@click.option("--json", "-j", "json_output", is_flag=True,
              help="Output as machine-readable JSON")
@click.pass_context
def reference(ctx, json_output):
    """Print the complete CLI command reference.

    Outputs every command, subcommand, argument, and option in a single
    invocation. Designed for AI agent consumption — run this once to
    understand the full CLI surface.
    """
    from ocl_cli.main import cli as root_cli

    commands = list(_walk_tree(root_cli))

    # Add global options from root
    _, global_options = _collect_params(root_cli)
    header = {
        "command": "ocl",
        "help": "OCL CLI - Command-line interface for the Open Concept Lab API.",
        "arguments": [],
        "options": global_options,
        "is_group": True,
    }

    all_commands = [header] + commands

    if json_output:
        click.echo(json.dumps(all_commands, indent=2))
    else:
        click.echo(_format_text(all_commands))
