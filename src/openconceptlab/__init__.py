"""Open Concept Lab API client, shared by the `ocl` command and other OCL tools."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("openconceptlab")
except PackageNotFoundError:  # a source tree that isn't installed
    __version__ = "0.0.0"

from openconceptlab.client import APIError, OCLAPIClient  # noqa: E402

__all__ = ["APIError", "OCLAPIClient", "__version__"]
