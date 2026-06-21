import unittest
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from ocl_cli.main import cli


class FakeClient:
    def __init__(self):
        self.search_concepts_calls = []
        self.closed = False

    def search_concepts(self, **kwargs):
        self.search_concepts_calls.append(kwargs)
        return {"count": 0, "results": []}

    def close(self):
        self.closed = True


class FakeConfig:
    def get_server(self, server_id):
        return SimpleNamespace(base_url="https://api.example.test")

    def resolve_token(self, server, token_override=None):
        return token_override


class ConceptCommandTest(unittest.TestCase):
    def test_concept_list_delegates_to_search_without_query(self):
        client = FakeClient()
        runner = CliRunner()

        with (
            patch("ocl_cli.main.CLIConfig.load", return_value=FakeConfig()),
            patch("ocl_cli.main.OCLAPIClient", return_value=client),
        ):
            result = runner.invoke(
                cli,
                [
                    "concept",
                    "list",
                    "--owner",
                    "openmrs",
                    "--repo",
                    "BasicLabTests",
                    "--repo-type",
                    "collection",
                    "--limit",
                    "10",
                    "--page",
                    "2",
                    "--verbose",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(
            client.search_concepts_calls,
            [
                {
                    "query": None,
                    "owner": "openmrs",
                    "owner_type": None,
                    "repo": "BasicLabTests",
                    "repo_type": "collection",
                    "repo_version": None,
                    "concept_class": None,
                    "datatype": None,
                    "locale": None,
                    "include_retired": False,
                    "include_mappings": False,
                    "include_inverse_mappings": False,
                    "updated_since": None,
                    "sort": None,
                    "verbose": True,
                    "limit": 10,
                    "page": 2,
                }
            ],
        )
        self.assertEqual(result.output.strip(), "No concepts found.")
        self.assertTrue(client.closed)


if __name__ == "__main__":
    unittest.main()
