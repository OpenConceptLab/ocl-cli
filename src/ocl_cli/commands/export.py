"""Export commands: status, create, delete, download."""

import errno
import os
import re
from urllib.parse import parse_qs, unquote, urlsplit

import click

from ocl_cli.api_client import APIError
from ocl_cli.main import handle_api_error
from ocl_cli.output import format_export_status, output_result


def export_args(f):
    """Common arguments and options for all export subcommands."""
    f = click.argument("version")(f)
    f = click.argument("repo")(f)
    f = click.argument("owner")(f)
    f = click.option(
        "--type", "repo_type",
        type=click.Choice(["source", "collection"]),
        required=True,
        help="Repository type.",
    )(f)
    f = click.option(
        "--owner-type",
        type=click.Choice(["users", "orgs"]),
        default="orgs",
        help="Owner type (default: orgs).",
    )(f)
    return f


@click.group()
def export():
    """Manage repository version exports."""
    pass


@export.command()
@export_args
@click.pass_context
def status(ctx, owner, repo, version, repo_type, owner_type):
    """Check export status for a repository version."""
    client = ctx.obj["client"]
    try:
        result = client.export_status(
            owner, repo, version, owner_type=owner_type, repo_type=repo_type,
        )
        output_result(ctx, result, format_export_status)
    except APIError as e:
        handle_api_error(e)


@export.command()
@export_args
@click.pass_context
def create(ctx, owner, repo, version, repo_type, owner_type):
    """Trigger export creation for a repository version."""
    client = ctx.obj["client"]
    try:
        result = client.export_create(
            owner, repo, version, owner_type=owner_type, repo_type=repo_type,
        )
        output_result(ctx, result, format_export_status)
    except APIError as e:
        handle_api_error(e)


@export.command()
@export_args
@click.pass_context
def delete(ctx, owner, repo, version, repo_type, owner_type):
    """Delete a cached export for a repository version."""
    client = ctx.obj["client"]
    try:
        client.export_delete(
            owner, repo, version, owner_type=owner_type, repo_type=repo_type,
        )
        click.echo("Export deleted.")
    except APIError as e:
        handle_api_error(e)


# OCL names (and so export and storage names) use only these characters; a leading '.' is never a name.
SAFE_FILENAME = re.compile(r"[A-Za-z0-9_@-][A-Za-z0-9._@-]*")
WINDOWS_DEVICE_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                        *(f"LPT{i}" for i in range(1, 10))}
DISPOSITION_PARAM = re.compile(r'\s*;\s*([^\s=;]+)\s*=\s*("(?:[^"\\]|\\.)*"|[^;]*)')


def _disposition_params(value):
    """Parameters of a Content-Disposition value, lower-cased names, quoted values unescaped."""
    params = {}
    pos = value.find(";")
    while 0 <= pos < len(value):
        match = DISPOSITION_PARAM.match(value, pos)
        if not match:
            break
        raw = match.group(2).strip()
        if raw.startswith('"') and raw.endswith('"') and len(raw) > 1:
            raw = re.sub(r"\\(.)", r"\1", raw[1:-1])
        params.setdefault(match.group(1).lower(), raw)
        pos = match.end()
    return params


def _filename_from_content_disposition(value):
    """The filename in a Content-Disposition value, preferring filename* (RFC 6266), or None."""
    params = _disposition_params(value or "")
    extended = params.get("filename*", "")
    if extended.count("'") >= 2:
        charset, _, encoded = extended.split("'", 2)
        try:
            return unquote(encoded, encoding=charset or "utf-8", errors="strict")
        except (LookupError, UnicodeDecodeError):
            pass
    return params.get("filename")


def _usable_filename(name):
    if not name or not SAFE_FILENAME.fullmatch(name):
        return False
    return name.split(".")[0].upper() not in WINDOWS_DEVICE_NAMES


def export_filename(response):
    """The name the API gives the export, or None.

    Tried in order: the Content-Disposition header, the signed URL's
    response-content-disposition, then the URL's last path segment. A name
    must be a plain file name made of the characters the API uses.
    """
    url = urlsplit(str(response.url))
    candidates = (
        lambda: _filename_from_content_disposition(response.headers.get("content-disposition")),
        lambda: _filename_from_content_disposition(
            parse_qs(url.query).get("response-content-disposition", [None])[0]),
        lambda: unquote(url.path.rsplit("/", 1)[-1]),
    )
    for candidate in candidates:
        try:
            name = candidate()
        except ValueError:
            continue
        if _usable_filename(name):
            return name
    return None


@export.command()
@export_args
@click.option(
    "-o", "--output", "output_path",
    type=click.Path(),
    help="Output file, or an existing directory (default: the API's name for the export, in the current directory).",
)
@click.pass_context
def download(ctx, owner, repo, version, repo_type, owner_type, output_path):
    """Download an export file, named as the API names it unless -o gives a file."""
    client = ctx.obj["client"]
    try:
        click.echo("Downloading export...", err=True)
        response = client.export_download(
            owner, repo, version, owner_type=owner_type, repo_type=repo_type,
        )

        # An explicit -o FILE is overwritten, as before. A name the API chose never replaces an existing file.
        mode = "wb"
        if not output_path or os.path.isdir(output_path):
            filename = export_filename(response)
            if not filename:
                raise click.ClickException("The API didn't name the export. Pass -o FILE to choose a name.")
            output_path = os.path.join(output_path or "", filename)
            mode = "xb"
        elif output_path.endswith(("/", os.sep)):
            raise click.ClickException(f"Directory {output_path} doesn't exist.")

        try:
            with open(output_path, mode) as f:
                f.write(response.content)
        except FileExistsError:
            raise click.ClickException(f"{output_path} already exists. Remove it, or pass -o FILE to overwrite.") from None
        except OSError as e:
            if mode != "xb" or e.errno != errno.ENAMETOOLONG:
                raise
            raise click.ClickException(
                "The export's name is too long for this filesystem. Pass -o FILE to choose a name."
            ) from None

        size = len(response.content)
        click.echo(f"Saved to {output_path} ({size:,} bytes)", err=True)
    except APIError as e:
        handle_api_error(e)
