import json
import re
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from click.testing import CliRunner
from tenacity import wait_none

from openconceptlab import APIError, OCLAPIClient, __version__

BASE = "https://api.example.test"


def test_default_identity_and_token_scheme(httpx_mock):
    httpx_mock.add_response(json={})
    OCLAPIClient(base_url=BASE, token="abc").get("/x/")
    req = httpx_mock.get_request()
    assert req.headers["Authorization"] == "Token abc"
    assert req.headers["X-OCL-CLIENT"] == f"openconceptlab/{__version__}"
    assert req.headers["User-Agent"].startswith(f"openconceptlab/{__version__} (httpx/")


def test_bearer_client_name_extra_headers_and_timeout(httpx_mock):
    httpx_mock.add_response(json={})
    client = OCLAPIClient(
        base_url=BASE,
        token="kc-token",
        auth_scheme="Bearer",
        client_name="ocl-example/1.2.3",
        headers={"X-OCL-Request-Source": "api"},
        timeout=12.5,
    )
    client.get("/x/")
    req = httpx_mock.get_request()
    assert req.headers["Authorization"] == "Bearer kc-token"
    assert req.headers["X-OCL-CLIENT"] == "ocl-example/1.2.3"
    assert req.headers["X-OCL-Request-Source"] == "api"
    assert client.client.timeout.read == 12.5


def test_extra_headers_override_defaults_case_insensitively(httpx_mock):
    httpx_mock.add_response(json={})
    OCLAPIClient(
        base_url=BASE, token="abc", headers={"authorization": "Bearer other", "x-ocl-client": "mine/1"}
    ).get("/x/")
    req = httpx_mock.get_request()
    assert req.headers.get_list("Authorization") == ["Bearer other"]
    assert req.headers.get_list("X-OCL-CLIENT") == ["mine/1"]


def test_api_error_carries_the_parsed_body(httpx_mock):
    httpx_mock.add_response(status_code=404, json={"detail": "Not found."})
    with pytest.raises(APIError) as err:
        OCLAPIClient(base_url=BASE).get("/x/")
    assert err.value.body == {"detail": "Not found."}
    assert err.value.detail == "{'detail': 'Not found.'}"  # unchanged: the CLI prints it


def test_api_error_body_is_the_text_when_not_json(httpx_mock):
    httpx_mock.add_response(status_code=502, text="Bad gateway")
    with pytest.raises(APIError) as err:
        OCLAPIClient(base_url=BASE).get("/x/")
    assert err.value.body == "Bad gateway"
    assert err.value.status_code == 502


def test_no_authorization_header_without_a_token(httpx_mock):
    httpx_mock.add_response(json={})
    OCLAPIClient(base_url=BASE).get("/x/")
    assert "Authorization" not in httpx_mock.get_request().headers


def test_post_is_not_retried_after_a_read_timeout(httpx_mock, monkeypatch):
    monkeypatch.setattr(OCLAPIClient.post.retry, "wait", wait_none())
    httpx_mock.add_exception(httpx.ReadTimeout("slow"))
    with pytest.raises(httpx.ReadTimeout):
        OCLAPIClient(base_url=BASE, token="t").post("/concepts/$match/", json={"rows": []})
    assert len(httpx_mock.get_requests()) == 1


def test_post_is_retried_when_the_connection_failed(httpx_mock, monkeypatch):
    monkeypatch.setattr(OCLAPIClient.post.retry, "wait", wait_none())
    httpx_mock.add_exception(httpx.ConnectError("refused"))
    httpx_mock.add_response(method="POST", json={"ok": True})
    assert OCLAPIClient(base_url=BASE, token="t").post("/x/", json={}) == {"ok": True}
    assert len(httpx_mock.get_requests()) == 2


def test_get_raises_the_network_error_once_retries_run_out(httpx_mock, monkeypatch):
    monkeypatch.setattr(OCLAPIClient.get.retry, "wait", wait_none())
    for _ in range(3):
        httpx_mock.add_exception(httpx.ReadTimeout("slow"))
    with pytest.raises(httpx.ReadTimeout):
        OCLAPIClient(base_url=BASE, token="t").get("/x/")
    assert len(httpx_mock.get_requests()) == 3


class _FakeConfig:
    def get_server(self, server_id):
        return SimpleNamespace(base_url=BASE)

    def resolve_token(self, server, token_override=None):
        return "t"


def test_cli_names_itself_to_the_api():
    from ocl_cli import CLIENT_NAME
    from ocl_cli.main import cli

    with (
        patch("ocl_cli.main.CLIConfig.load", return_value=_FakeConfig()),
        patch("ocl_cli.main.OCLAPIClient") as client_cls,
    ):
        result = CliRunner().invoke(cli, ["repo", "--help"])
    assert result.exit_code == 0, result.output
    assert client_cls.call_args.kwargs["client_name"] == CLIENT_NAME


MATCH_URL = re.compile(r"https://api\.example\.test/concepts/\$match/.*")


def test_match_sends_full_rows_and_the_reranker(httpx_mock):
    httpx_mock.add_response(method="POST", url=MATCH_URL, json=[{"row": {"name": "fever"}, "results": []}])
    out = OCLAPIClient(base_url=BASE, token="t").match_concepts(
        [],
        "/orgs/CIEL/sources/CIEL/",
        rows=[{"name": "fever", "concept_class": "Diagnosis"}],
        reranker=True,
        limit=3,
    )
    req = httpx_mock.get_request()
    assert json.loads(req.content) == {
        "rows": [{"name": "fever", "concept_class": "Diagnosis"}],
        "target_repo_url": "/orgs/CIEL/sources/CIEL/",
    }
    assert req.url.params["reranker"] == "true"
    assert req.url.params["semantic"] == "true"
    assert req.url.params["limit"] == "3"
    assert out == {"count": 1, "results": [{"row": {"name": "fever"}, "results": []}]}


def test_match_terms_still_become_name_rows_without_the_reranker(httpx_mock):
    httpx_mock.add_response(method="POST", url=MATCH_URL, json=[])
    OCLAPIClient(base_url=BASE, token="t").match_concepts(["fever", "cough"], "/orgs/CIEL/sources/CIEL/")
    req = httpx_mock.get_request()
    assert json.loads(req.content)["rows"] == [{"name": "fever"}, {"name": "cough"}]
    assert "reranker" not in req.url.params


def test_expansion_concepts_by_id(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r".*/orgs/PIH/collections/HIV/v1/expansions/e1/concepts/.*"),
        json=[{"id": "1"}],
        headers={"num_found": "40"},
    )
    out = OCLAPIClient(base_url=BASE).list_expansion_concepts("PIH", "HIV", "v1", expansion_id="e1", query="cd4", limit=5)
    req = httpx_mock.get_request()
    assert req.url.params["q"] == "cd4" and req.url.params["limit"] == "5"
    assert out == {"count": 40, "results": [{"id": "1"}]}


def test_expansion_concepts_from_the_default_expansion(httpx_mock):
    httpx_mock.add_response(
        url=f"{BASE}/orgs/PIH/collections/HIV/v1/",
        json={"expansion_url": "/orgs/PIH/collections/HIV/v1/expansions/autoexpand-v1/"},
    )
    httpx_mock.add_response(
        url=re.compile(r".*/expansions/autoexpand-v1/concepts/.*"), json=[], headers={"num_found": "0"}
    )
    out = OCLAPIClient(base_url=BASE).list_expansion_concepts("PIH", "HIV", "v1")
    assert out == {"count": 0, "results": []}


def test_expansion_concepts_without_a_default_expansion(httpx_mock):
    httpx_mock.add_response(url=f"{BASE}/orgs/PIH/collections/HIV/v1/", json={"expansion_url": None})
    with pytest.raises(APIError) as err:
        OCLAPIClient(base_url=BASE).list_expansion_concepts("PIH", "HIV", "v1")
    assert err.value.status_code == 404


CHANGELOG_URL = re.compile(r"https://api\.example\.test/sources/\$changelog/.*")
V1, V2 = "/orgs/CIEL/sources/CIEL/v2024/", "/orgs/CIEL/sources/CIEL/v2025/"


def test_changelog_returns_the_result(httpx_mock):
    httpx_mock.add_response(method="POST", url=CHANGELOG_URL, json={"meta": {}, "concepts": {"new": {}}})
    out = OCLAPIClient(base_url=BASE, token="t").changelog("source", V1, V2)
    req = httpx_mock.get_request()
    assert json.loads(req.content) == {"version1": V1, "version2": V2}
    assert req.url.params["verbosity"] == "4"
    assert out == {"meta": {}, "concepts": {"new": {}}}


def test_changelog_still_computing(httpx_mock):
    httpx_mock.add_response(method="POST", url=CHANGELOG_URL, status_code=202, json={"id": "task-1", "state": "PENDING"})
    out = OCLAPIClient(base_url=BASE, token="t").changelog("source", V1, V2)
    assert out == {"status": "pending", "task": {"id": "task-1", "state": "PENDING"}}


def test_changelog_already_queued(httpx_mock):
    httpx_mock.add_response(method="POST", url=CHANGELOG_URL, status_code=409, json={"detail": "Already Queued"})
    out = OCLAPIClient(base_url=BASE, token="t").changelog("source", V1, V2)
    assert out == {"status": "pending", "detail": "Already queued"}


def test_changelog_errors_raise(httpx_mock):
    httpx_mock.add_response(method="POST", url=CHANGELOG_URL, status_code=404, json={"detail": "Not found."})
    with pytest.raises(APIError) as err:
        OCLAPIClient(base_url=BASE, token="t").changelog("source", V1, V2)
    assert err.value.status_code == 404


def test_expansion_url_on_another_host_is_refused(httpx_mock):
    httpx_mock.add_response(
        url=f"{BASE}/orgs/PIH/collections/HIV/v1/",
        json={"expansion_url": "https://elsewhere.example/orgs/PIH/collections/HIV/v1/expansions/e1/"},
    )
    with pytest.raises(APIError):
        OCLAPIClient(base_url=BASE, token="t").list_expansion_concepts("PIH", "HIV", "v1")
    assert len(httpx_mock.get_requests()) == 1


def test_relative_path_cannot_leave_base_url_prefix(httpx_mock):
    with pytest.raises(APIError):
        OCLAPIClient(base_url="https://api.example.test/ocl-api").get("../other/")
    assert httpx_mock.get_requests() == []


def test_same_origin_absolute_url_is_allowed(httpx_mock):
    httpx_mock.add_response(url=f"{BASE}/x/", json={"ok": True})
    assert OCLAPIClient(base_url=BASE).get(f"{BASE}/x/") == {"ok": True}
