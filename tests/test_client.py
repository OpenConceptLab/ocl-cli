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


# ── Identifiers in paths, and the origin check (ocl_online#553) ──────────


@pytest.fixture
def no_retry_wait(monkeypatch):
    for name in ("get", "post", "put", "patch", "delete", "_get_list"):
        monkeypatch.setattr(getattr(OCLAPIClient, name).retry, "wait", wait_none())


def test_an_identifier_is_encoded_as_one_path_segment(httpx_mock):
    httpx_mock.add_response(json={})
    OCLAPIClient(base_url=BASE).get_concept("CIEL", "CIEL", "A B+50%é&:[]")
    assert httpx_mock.get_requests()[0].url.raw_path == (
        b"/orgs/CIEL/sources/CIEL/concepts/A%20B%2B50%25%C3%A9%26%3A%5B%5D/"
    )


def test_a_percent_escape_in_an_identifier_is_sent_literally(httpx_mock):
    httpx_mock.add_response(json={})
    OCLAPIClient(base_url=BASE).get_concept("CIEL", "CIEL", "a%2Fb")
    assert httpx_mock.get_requests()[0].url.raw_path == b"/orgs/CIEL/sources/CIEL/concepts/a%252Fb/"


def test_identifiers_are_encoded_under_a_base_url_prefix(httpx_mock):
    httpx_mock.add_response(json={})
    OCLAPIClient(base_url="https://api.example.test/ocl-api").get_concept("X", "S", "a b")
    assert httpx_mock.get_requests()[0].url.raw_path == b"/ocl-api/orgs/X/sources/S/concepts/a%20b/"


# Every method that puts a caller's value in a path, with that value set to v.
PATH_BUILDERS = {
    "get_org": lambda c, v: c.get_org(v),
    "list_org_repos": lambda c, v: c.list_org_repos(v),
    "get_user_detail": lambda c, v: c.get_user_detail(v),
    "list_user_repos": lambda c, v: c.list_user_repos(v),
    "list_user_orgs": lambda c, v: c.list_user_orgs(v),
    "get_org_members": lambda c, v: c.get_org_members(v),
    "search_repos owner": lambda c, v: c.search_repos(owner=v),
    "search_repos scoped owner": lambda c, v: c.search_repos(owner=v, owner_type="users"),
    "get_repo": lambda c, v: c.get_repo("X", v),
    "get_repo version": lambda c, v: c.get_repo("X", "R", repo_version=v),
    "get_repo_versions": lambda c, v: c.get_repo_versions(v, "R"),
    "search_concepts": lambda c, v: c.search_concepts(owner="X", repo=v),
    "get_concept": lambda c, v: c.get_concept("X", "S", v),
    "get_concept repo version": lambda c, v: c.get_concept("X", "S", "C", repo_version=v),
    "get_concept concept version": lambda c, v: c.get_concept("X", "S", "C", concept_version=v),
    "get_concept_versions": lambda c, v: c.get_concept_versions("X", "S", v),
    "get_concept_names": lambda c, v: c.get_concept_names("X", "S", v),
    "get_concept_descriptions": lambda c, v: c.get_concept_descriptions("X", "S", v),
    "get_concept_extras": lambda c, v: c.get_concept_extras("X", v, "C"),
    "search_mappings": lambda c, v: c.search_mappings(owner="X", repo=v),
    "get_mapping": lambda c, v: c.get_mapping("X", "S", v),
    "get_mapping repo version": lambda c, v: c.get_mapping("X", "S", "M", repo_version=v),
    "get_mapping_versions": lambda c, v: c.get_mapping_versions("X", "S", v),
    "cascade": lambda c, v: c.cascade("X", "S", v),
    "list_expansions": lambda c, v: c.list_expansions("X", "C", v),
    "get_expansion": lambda c, v: c.get_expansion("X", "C", expansion_id=v),
    "get_expansion in a version": lambda c, v: c.get_expansion("X", "C", collection_version="v1", expansion_id=v),
    "get_expansion default": lambda c, v: c.get_expansion("X", "C", collection_version=v),
    "list_expansion_concepts": lambda c, v: c.list_expansion_concepts("X", "C", "v1", expansion_id=v),
    "list_expansion_concepts version": lambda c, v: c.list_expansion_concepts("X", "C", v, expansion_id="e1"),
    "list_collection_refs": lambda c, v: c.list_collection_refs("X", v),
    "list_collection_refs version": lambda c, v: c.list_collection_refs("X", "C", collection_version=v),
    "create_repo": lambda c, v: c.create_repo(v, "R", "Name"),
    "update_repo": lambda c, v: c.update_repo("X", v, name="n"),
    "create_repo_version": lambda c, v: c.create_repo_version("X", v, "v1"),
    "update_repo_version": lambda c, v: c.update_repo_version("X", "R", v, description="d"),
    "create_concept": lambda c, v: c.create_concept("X", v, "C", "Misc", [{"name": "n", "locale": "en"}]),
    "update_concept": lambda c, v: c.update_concept("X", "S", v, retired=False),
    "retire_concept": lambda c, v: c.retire_concept("X", "S", v),
    "delete_concept": lambda c, v: c.delete_concept("X", "S", v),
    "add_concept_name": lambda c, v: c.add_concept_name("X", "S", v, "n", "en"),
    "add_concept_description": lambda c, v: c.add_concept_description("X", "S", v, "d", "en"),
    "set_concept_extra": lambda c, v: c.set_concept_extra("X", "S", "C", v, 1),
    "delete_concept_extra": lambda c, v: c.delete_concept_extra("X", "S", "C", v),
    "create_mapping": lambda c, v: c.create_mapping("X", v, "SAME-AS", from_concept_url="/a/", to_concept_url="/b/"),
    "update_mapping": lambda c, v: c.update_mapping("X", "S", v, retired=False),
    "retire_mapping": lambda c, v: c.retire_mapping("X", "S", v),
    "delete_mapping": lambda c, v: c.delete_mapping("X", "S", v),
    "add_collection_ref": lambda c, v: c.add_collection_ref("X", v, ["/a/"]),
    "remove_collection_ref": lambda c, v: c.remove_collection_ref("X", v, ["/a/"]),
    "create_expansion": lambda c, v: c.create_expansion("X", "C", v),
    "clone": lambda c, v: c.clone("X", v, ["/a/"]),
    "set_repo_extra": lambda c, v: c.set_repo_extra("X", "R", v, 1),
    "delete_repo_extra": lambda c, v: c.delete_repo_extra("X", "R", v),
    "get_repo_extras": lambda c, v: c.get_repo_extras("X", v),
    "add_org_member": lambda c, v: c.add_org_member("X", v),
    "remove_org_member": lambda c, v: c.remove_org_member("X", v),
    "get_task": lambda c, v: c.get_task(v),
    "delete_org": lambda c, v: c.delete_org(v),
    "delete_repo": lambda c, v: c.delete_repo("X", v),
    "import_file": lambda c, v: c.import_file("unused.json", queue=v),
    "import_list": lambda c, v: c.import_list(queue=v),
    "export_status": lambda c, v: c.export_status("X", "R", v),
    "export_create": lambda c, v: c.export_create("X", "R", v),
    "export_delete": lambda c, v: c.export_delete("X", "R", v),
    "export_download": lambda c, v: c.export_download("X", "R", v),
}


@pytest.mark.parametrize("value", ["..", ".", "a/b"])
@pytest.mark.parametrize("call", PATH_BUILDERS.values(), ids=PATH_BUILDERS.keys())
def test_an_identifier_that_would_change_the_endpoint_is_refused(httpx_mock, no_retry_wait, call, value):
    with pytest.raises(APIError) as err:
        call(OCLAPIClient(base_url=BASE, token="t"), value)
    assert err.value.status_code == 0
    assert httpx_mock.get_requests() == []


def test_an_empty_identifier_is_refused(httpx_mock, no_retry_wait):
    client = OCLAPIClient(base_url=BASE, token="t")
    for call in (lambda: client.get_org(""), lambda: client.update_repo_version("X", "R", "", description="d")):
        with pytest.raises(APIError):
            call()
    assert httpx_mock.get_requests() == []


def test_search_repos_refuses_an_unknown_owner_type(httpx_mock):
    with pytest.raises(ValueError):
        OCLAPIClient(base_url=BASE).search_repos(owner="X", owner_type="../admin")
    assert httpx_mock.get_requests() == []


@pytest.mark.parametrize("path", ["%2e%2e/other/", "a%2F..%2F..%2Fother/", "..%5C..%5Cother/"])
def test_an_encoded_dot_segment_cannot_leave_base_url_prefix(httpx_mock, path):
    with pytest.raises(APIError):
        OCLAPIClient(base_url="https://api.example.test/ocl-api").get(f"https://api.example.test/ocl-api/{path}")
    assert httpx_mock.get_requests() == []


def test_an_encoded_backslash_inside_the_prefix_is_allowed(httpx_mock):
    url = "https://api.example.test/ocl-api/orgs/X/sources/S/concepts/A%5CB/"
    httpx_mock.add_response(url=url, json={"ok": True})
    assert OCLAPIClient(base_url="https://api.example.test/ocl-api").get(url) == {"ok": True}


def test_a_malformed_international_host_is_refused(httpx_mock):
    with pytest.raises(APIError):
        OCLAPIClient(base_url=BASE, token="t").get("https://xn--a.example/x/")
    assert httpx_mock.get_requests() == []


def test_an_international_host_matches_its_punycode_form(httpx_mock):
    httpx_mock.add_response(url="https://xn--bcher-kva.example/x/", json={"ok": True})
    assert OCLAPIClient(base_url="https://bücher.example").get("https://xn--bcher-kva.example/x/") == {"ok": True}


def test_a_url_with_credentials_is_refused(httpx_mock, no_retry_wait):
    with pytest.raises(APIError) as err:
        OCLAPIClient(base_url=BASE, token="t").get("https://user:pw@api.example.test/x/")
    assert "pw" not in str(err.value)
    assert httpx_mock.get_requests() == []


def test_ocl_concept_get_encodes_special_characters(httpx_mock):
    from ocl_cli.main import cli

    httpx_mock.add_response(json={"id": "A B+50%"})
    with patch("ocl_cli.main.CLIConfig.load", return_value=_FakeConfig()):
        result = CliRunner().invoke(cli, ["--json", "concept", "get", "CIEL", "CIEL", "A B+50%"])
    assert result.exit_code == 0, result.output
    assert httpx_mock.get_requests()[0].url.raw_path == b"/orgs/CIEL/sources/CIEL/concepts/A%20B%2B50%25/"


def test_recreate_collection_refuses_an_export_whose_id_would_change_the_endpoint(httpx_mock, no_retry_wait, tmp_path):
    from ocl_cli.main import cli

    export = tmp_path / "export.json"
    export.write_text(json.dumps({"collection": {"id": ".."}, "references": []}))
    with patch("ocl_cli.main.CLIConfig.load", return_value=_FakeConfig()):
        result = CliRunner().invoke(cli, [
            "tool", "recreate-collection", "--input", str(export), "--org", "PIH",
            "--output", str(tmp_path / "refs.json"), "--no-dry-run",
        ])
    assert httpx_mock.get_requests() == []
    assert result.exit_code == 1
    assert "Invalid identifier" in result.output


def test_get_still_takes_a_whole_path(httpx_mock):
    httpx_mock.add_response(json={})
    OCLAPIClient(base_url=BASE).get("/orgs/CIEL/sources/CIEL/concepts/a b&c/")
    assert httpx_mock.get_requests()[0].url.raw_path == b"/orgs/CIEL/sources/CIEL/concepts/a%20b&c/"


def test_a_path_outside_the_prefix_that_normalizes_inside_is_refused(httpx_mock):
    with pytest.raises(APIError):
        OCLAPIClient(base_url="https://api.example.test/ocl-api").get("https://api.example.test/other/..%5Cocl-api/x/")
    assert httpx_mock.get_requests() == []


@pytest.mark.parametrize("method", ["export_status", "export_create", "export_delete", "export_download"])
def test_an_export_needs_a_version(httpx_mock, method):
    with pytest.raises(APIError):
        getattr(OCLAPIClient(base_url=BASE, token="t"), method)("X", "R", "")
    assert httpx_mock.get_requests() == []


@pytest.mark.parametrize("follow_redirects", [False, True])
def test_a_redirect_to_a_malformed_host_raises_api_error(httpx_mock, follow_redirects):
    httpx_mock.add_response(url=f"{BASE}/x/", status_code=302, headers={"Location": "https://xn--a.example/y/"})
    with pytest.raises(APIError):
        OCLAPIClient(base_url=BASE, token="t").request("GET", "/x/", follow_redirects=follow_redirects)


@pytest.mark.parametrize("expression", [
    "/orgs/X/sources/S/concepts/../", "/orgs/X/sources/S/concepts/./", "/orgs/X/sources/S/concepts/%2e%2e/",
    "/orgs/X/sources/S/concepts/1?x=/", "/orgs/X/sources/S/concepts/1#/",
])
def test_cascade_children_of_an_expression_that_would_change_the_endpoint_are_not_fetched(
    httpx_mock, no_retry_wait, expression
):
    assert OCLAPIClient(base_url=BASE, token="t").fetch_cascade_children(expression) == set()
    assert httpx_mock.get_requests() == []


def test_cascade_children_are_fetched_for_a_concept_expression(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(rf"{re.escape(BASE)}/orgs/X/sources/S/concepts/1/cascade/\?.*"),
        json={"entry": [{"type": "Concept", "url": "/orgs/X/sources/S/concepts/2/"}]},
    )
    children = OCLAPIClient(base_url=BASE, token="t").fetch_cascade_children("/orgs/X/sources/S/concepts/1/")
    assert children == {"/orgs/X/sources/S/concepts/2/"}


@pytest.mark.parametrize("path", ["/%6Fcl-api/x/", "/ocl-api%2Fx/", "/ocl-api/..;/x/", "/ocl-api/%252e%252e/x/"])
def test_a_path_outside_the_prefix_under_any_reading_is_refused(httpx_mock, path):
    with pytest.raises(APIError):
        OCLAPIClient(base_url="https://api.example.test/ocl-api").get(f"https://api.example.test{path}")
    assert httpx_mock.get_requests() == []


def test_a_redirect_outside_the_raw_prefix_is_refused(httpx_mock):
    httpx_mock.add_response(url="https://api.example.test/ocl-api/x/", status_code=302, headers={"Location": "/%6Fcl-api/y/"})
    with pytest.raises(APIError):
        OCLAPIClient(base_url="https://api.example.test/ocl-api", token="t").request("GET", "/x/", follow_redirects=True)
    assert len(httpx_mock.get_requests()) == 1


def test_an_encoded_prefix_and_a_semicolon_in_an_identifier_still_work(httpx_mock):
    httpx_mock.add_response(json={})
    OCLAPIClient(base_url="https://api.example.test/my api").get_concept("X", "S", "a;b")
    assert httpx_mock.get_requests()[0].url.raw_path == b"/my%20api/orgs/X/sources/S/concepts/a%3Bb/"
