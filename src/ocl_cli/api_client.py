"""Compatibility shim: the client lives in the open core, `openconceptlab.client`."""

from openconceptlab.client import APIError, OCLAPIClient

__all__ = ["APIError", "OCLAPIClient"]
