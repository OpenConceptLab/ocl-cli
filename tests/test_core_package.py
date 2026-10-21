import builtins
import importlib
import sys
from importlib.metadata import version

import openconceptlab
from openconceptlab import APIError, OCLAPIClient


def test_core_exports_client_error_and_version():
    assert openconceptlab.__version__ == version("openconceptlab")
    assert OCLAPIClient.__module__ == "openconceptlab.client"
    assert issubclass(APIError, Exception)


def test_cli_shim_and_version_point_at_the_core():
    from ocl_cli import CLIENT_NAME, __version__
    from ocl_cli.api_client import APIError as ShimError
    from ocl_cli.api_client import OCLAPIClient as ShimClient

    assert ShimClient is OCLAPIClient and ShimError is APIError
    assert __version__ == openconceptlab.__version__
    assert CLIENT_NAME == f"ocl-cli/{openconceptlab.__version__}"


def test_core_imports_without_click(monkeypatch):
    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name == "click" or name.startswith("click."):
            raise ImportError("the core must not need click")
        return real_import(name, *args, **kwargs)

    for mod in [m for m in sys.modules if m == "openconceptlab" or m.startswith("openconceptlab.")]:
        monkeypatch.delitem(sys.modules, mod)
    monkeypatch.setattr(builtins, "__import__", guarded)
    importlib.import_module("openconceptlab")
