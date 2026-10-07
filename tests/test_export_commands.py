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

    def test_name_cannot_leave_the_target_directory(self):
        response = export_response(headers={"content-disposition": 'attachment; filename="../../evil.zip"'})

        files, _ = self.download(response, "-o", "downloads")

        self.assertEqual(files, ["./downloads/evil.zip"])

    def test_unnamed_export_asks_for_output(self):
        response = export_response(url="https://api.example.test/orgs/PIH/sources/PIH/1.8.24/export/")

        files, result = self.download(response, exit_code=1)

        self.assertEqual(files, [])
        self.assertIn("Pass -o FILE", result.stderr)
