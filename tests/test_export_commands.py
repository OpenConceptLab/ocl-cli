import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from click.testing import CliRunner

from ocl_cli.main import cli

API_NAME = "orgs_PIH_sources_PIH_1.8.24_2026-09-30_123456.zip"
SIGNED_URL = "https://exports.example.test/orgs/PIH/PIH_PIH_v1.8.24.2026-09-30_123456.zip?X-Amz-Signature=abc"


def export_response(url=SIGNED_URL, headers=None):
    return httpx.Response(200, headers=headers, content=b"zip-bytes", request=httpx.Request("GET", url))


def make_runner():
    # Click 8.1 mixes stderr into stdout unless told not to; 8.2 dropped mix_stderr.
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


class FakeConfig:
    def get_server(self, server_id):
        return SimpleNamespace(base_url="https://api.example.test")

    def resolve_token(self, server, token_override=None):
        return token_override


class FakeExportClient:
    def __init__(self, response):
        self.response = response

    def export_download(self, *args, **kwargs):
        return self.response

    def close(self):
        pass


class ExportDownloadCommandTest(unittest.TestCase):
    def download(self, response, *args, exit_code=0):
        runner = make_runner()
        with (
            runner.isolated_filesystem(),
            patch("ocl_cli.main.CLIConfig.load", return_value=FakeConfig()),
            patch("ocl_cli.main.OCLAPIClient", return_value=FakeExportClient(response)),
        ):
            os.mkdir("downloads")
            result = runner.invoke(
                cli, ["repo", "export", "download", "PIH", "PIH", "1.8.24", "--type", "source", *args]
            )
            self.assertEqual(result.exit_code, exit_code, result.output)
            files = sorted(
                os.path.join(root, name) for root, _, names in os.walk(".") for name in names
            )
        return files, result

    def test_saves_under_the_content_disposition_name_by_default(self):
        response = export_response(headers={"content-disposition": f'attachment; filename="{API_NAME}"'})

        files, _ = self.download(response)

        self.assertEqual(files, [f"./{API_NAME}"])

    def test_reads_the_name_from_the_signed_url_without_a_header(self):
        url = f"{SIGNED_URL}&response-content-disposition=attachment%3B%20filename%3D%22{API_NAME}%22"

        files, _ = self.download(export_response(url=url))

        self.assertEqual(files, [f"./{API_NAME}"])

    def test_falls_back_to_the_storage_name(self):
        files, _ = self.download(export_response())

        self.assertEqual(files, ["./PIH_PIH_v1.8.24.2026-09-30_123456.zip"])

    def test_output_directory_keeps_the_api_name(self):
        response = export_response(headers={"content-disposition": f'attachment; filename="{API_NAME}"'})

        files, _ = self.download(response, "-o", "downloads")

        self.assertEqual(files, [f"./downloads/{API_NAME}"])

    def test_output_file_overrides_the_api_name(self):
        response = export_response(headers={"content-disposition": f'attachment; filename="{API_NAME}"'})

        files, _ = self.download(response, "-o", "mine.zip")

        self.assertEqual(files, ["./mine.zip"])

    def test_a_path_in_the_name_is_rejected(self):
        response = export_response(headers={"content-disposition": 'attachment; filename="../../evil.zip"'})

        files, _ = self.download(response, "-o", "downloads")

        self.assertEqual(files, ["./downloads/PIH_PIH_v1.8.24.2026-09-30_123456.zip"])

    def test_filename_star_wins_over_filename(self):
        disposition = f"attachment; filename=\"fallback.zip\"; filename*=UTF-8''{API_NAME}"

        files, _ = self.download(export_response(headers={"content-disposition": disposition}))

        self.assertEqual(files, [f"./{API_NAME}"])

    def test_unusable_header_name_falls_back_to_the_signed_url(self):
        url = f"{SIGNED_URL}&response-content-disposition=attachment%3B%20filename%3D%22{API_NAME}%22"
        for disposition in ("attachment; filename*=UTF-8''evil%00.zip", 'attachment; filename="NUL.zip"',
                            'attachment; filename="victim.txt:stream.zip"', "attachment; filename*=UTF-8''%FF.zip"):
            with self.subTest(disposition=disposition):
                files, _ = self.download(export_response(url=url, headers={"content-disposition": disposition}))

                self.assertEqual(files, [f"./{API_NAME}"])

    def test_quoted_parameters_can_contain_semicolons(self):
        disposition = 'attachment; note="x; filename=wrong.zip; y"; filename="right.zip"'

        files, _ = self.download(export_response(headers={"content-disposition": disposition}))

        self.assertEqual(files, ["./right.zip"])

    def test_storage_name_may_start_with_an_underscore(self):
        url = "https://exports.example.test/orgs/_PIH/_PIH_PIH_v1.8.24.zip?X-Amz-Signature=abc"

        files, _ = self.download(export_response(url=url))

        self.assertEqual(files, ["./_PIH_PIH_v1.8.24.zip"])

    def test_an_existing_file_is_not_overwritten(self):
        response = export_response(headers={"content-disposition": f'attachment; filename="{API_NAME}"'})
        runner = make_runner()
        with (
            runner.isolated_filesystem(),
            patch("ocl_cli.main.CLIConfig.load", return_value=FakeConfig()),
            patch("ocl_cli.main.OCLAPIClient", return_value=FakeExportClient(response)),
        ):
            with open("important.txt", "w") as f:
                f.write("keep")
            os.symlink("important.txt", API_NAME)
            result = runner.invoke(cli, ["repo", "export", "download", "PIH", "PIH", "1.8.24", "--type", "source"])

            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("already exists", result.stderr)
            with open("important.txt") as f:
                self.assertEqual(f.read(), "keep")

    def test_a_name_too_long_for_the_filesystem_asks_for_output(self):
        long_name = "orgs_PIH_sources_" + "x" * 300 + ".zip"
        response = export_response(headers={"content-disposition": f'attachment; filename="{long_name}"'})

        files, result = self.download(response, exit_code=1)

        self.assertEqual(files, [])
        self.assertIn("too long", result.stderr)

    def test_a_missing_output_directory_is_an_error(self):
        files, result = self.download(export_response(), "-o", "missing/", exit_code=1)

        self.assertEqual(files, [])
        self.assertIn("doesn't exist", result.stderr)

    def test_unnamed_export_asks_for_output(self):
        response = export_response(url="https://api.example.test/orgs/PIH/sources/PIH/1.8.24/export/")

        files, result = self.download(response, exit_code=1)

        self.assertEqual(files, [])
        self.assertIn("Pass -o FILE", result.stderr)


def test_export_download_follows_the_redirect_to_the_named_file(httpx_mock):
    from ocl_cli.api_client import OCLAPIClient
    from ocl_cli.commands.export import export_filename

    httpx_mock.add_response(
        method="GET", url="https://api.example.test/orgs/PIH/sources/PIH/1.8.24/export/",
        status_code=302, headers={"location": SIGNED_URL},
    )
    httpx_mock.add_response(
        method="GET", url=SIGNED_URL, content=b"zip-bytes",
        headers={"content-disposition": f'attachment; filename="{API_NAME}"'},
    )

    response = OCLAPIClient(base_url="https://api.example.test", token="t").export_download("PIH", "PIH", "1.8.24")

    assert response.content == b"zip-bytes"
    assert export_filename(response) == API_NAME
