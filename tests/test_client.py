from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from click.testing import CliRunner
from tenacity import wait_none

from openconceptlab import OCLAPIClient, __version__

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
        CliRunner().invoke(cli, ["repo", "--help"])
    assert client_cls.call_args.kwargs["client_name"] == CLIENT_NAME
