import unittest
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from ocl_cli.api_client import OCLAPIClient
from ocl_cli.main import cli


class FakeClient:
    def __init__(self):
        self.calls = []

    def create_repo_version(self, *args, **kwargs):
        self.calls.append(("create_repo_version", args, kwargs))
        return {"id": args[2], "version": args[2]}

    def update_repo_version(self, *args, **kwargs):
        self.calls.append(("update_repo_version", args, kwargs))
        return {"id": args[2], "version": args[2]}

    def close(self):
        pass


class FakeConfig:
    def get_server(self, server_id):
        return SimpleNamespace(base_url="https://api.example.test")

    def resolve_token(self, server, token_override=None):
        return token_override


class RepoVersionCommandTest(unittest.TestCase):
    def invoke(self, *args):
        client = FakeClient()
        with (
            patch("ocl_cli.main.CLIConfig.load", return_value=FakeConfig()),
            patch("ocl_cli.main.OCLAPIClient", return_value=client),
        ):
            result = CliRunner().invoke(cli, ["--json", "repo", *args])
        self.assertEqual(result.exit_code, 0, result.output)
        return client, result

    def test_version_create_sends_match_algorithms(self):
        client, _ = self.invoke(
            "version-create", "Regenstrief", "LOINC", "2.82", "--match-algorithms", "es, llm"
        )

        [(_, args, kwargs)] = client.calls
        self.assertEqual(args, ("Regenstrief", "LOINC", "2.82"))
        self.assertEqual(kwargs["match_algorithms"], ["es", "llm"])

    def test_version_create_without_match_algorithms_lets_the_server_decide(self):
        client, result = self.invoke("version-create", "CIEL", "CIEL", "v2026-10-01")

        [(_, _, kwargs)] = client.calls
        self.assertIsNone(kwargs["match_algorithms"])
        self.assertEqual(result.stderr, "")

    def test_version_update_match_algorithms_warns(self):
        client, result = self.invoke(
            "version-update", "CIEL", "CIEL", "v2026-10-01", "--match-algorithms", "es,llm"
        )

        [(_, _, kwargs)] = client.calls
        self.assertEqual(kwargs["match_algorithms"], ["es", "llm"])
        self.assertIn("Warning", result.stderr)
        self.assertIn("version-create --match-algorithms", result.stderr)

    def test_version_update_without_match_algorithms_does_not_warn(self):
        _, result = self.invoke("version-update", "CIEL", "CIEL", "v2026-10-01", "--released")

        self.assertEqual(result.stderr, "")


class CreateRepoVersionClientTest(unittest.TestCase):
    def create(self, **kwargs):
        client = OCLAPIClient(base_url="https://api.example.test", token="t")
        with patch.object(OCLAPIClient, "post", return_value={}) as post:
            client.create_repo_version("CIEL", "CIEL", "v1", **kwargs)
        return post.call_args.kwargs["json"]

    def test_body_includes_match_algorithms_when_given(self):
        self.assertEqual(
            self.create(match_algorithms=["es", "llm"]),
            {"id": "v1", "released": True, "match_algorithms": ["es", "llm"]},
        )

    def test_body_leaves_match_algorithms_out_by_default(self):
        self.assertEqual(self.create(), {"id": "v1", "released": True})
