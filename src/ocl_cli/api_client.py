"""Synchronous OCL API client.

Adapted from ocl-mcp's async client. Uses httpx.Client (sync) with retry logic.
Business logic lives here so it can be reused by future MCP server wrappers.
"""

import sys
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class APIError(Exception):
    """Structured API error with status code and detail."""

    def __init__(self, message: str, status_code: int = 0, detail: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail

    def to_dict(self) -> dict:
        d = {"error": str(self), "status_code": self.status_code}
        if self.detail:
            d["detail"] = self.detail
        return d


def _repo_type_stem(repo_type: str) -> str:
    """Convert 'source'/'collection' to plural URL segment."""
    if repo_type == "source":
        return "sources"
    elif repo_type == "collection":
        return "collections"
    else:
        raise ValueError(f"repo_type must be 'source' or 'collection', got '{repo_type}'")


def _validate_owner_type(owner_type: str) -> None:
    if owner_type not in ("users", "orgs"):
        raise ValueError(f"owner_type must be 'users' or 'orgs', got '{owner_type}'")


def _build_repo_endpoint(
    owner_type: str,
    owner: str,
    repo_type: str,
    repo: str,
    version: Optional[str] = None,
    suffix: str = "",
) -> str:
    """Build a repository-scoped endpoint URL."""
    _validate_owner_type(owner_type)
    stem = _repo_type_stem(repo_type)
    base = f"/{owner_type}/{owner}/{stem}/{repo}"
    if version:
        base = f"{base}/{version}"
    return f"{base}/{suffix}" if suffix else f"{base}/"


class OCLAPIClient:
    """Synchronous client for the OCL API."""

    DEFAULT_BASE_URL = "https://api.openconceptlab.org"

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.token = token
        self.debug = False

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Token {self.token}"

        self.client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _log_request(self, method: str, endpoint: str, params: dict | None = None,
                     body: Any = None):
        if self.debug:
            url = f"{self.base_url}{endpoint}"
            if params:
                from urllib.parse import urlencode
                url = f"{url}?{urlencode(params, doseq=True)}"
            print(f"  {method} {url}", file=sys.stderr)
            if body is not None:
                import json as _json
                print(f"  Body: {_json.dumps(body, default=str)}", file=sys.stderr)

    def _handle_error(self, response: httpx.Response) -> None:
        """Convert HTTP errors to APIError."""
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            raise APIError(
                f"Rate limit exceeded. Retry after {retry_after}s",
                status_code=429,
            )
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise APIError(
                f"HTTP {response.status_code}",
                status_code=response.status_code,
                detail=str(detail),
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    def get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        self._log_request("GET", endpoint, params)
        response = self.client.get(endpoint, params=params)
        self._handle_error(response)
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    def post(self, endpoint: str, json: Optional[dict] = None, params: Optional[dict] = None) -> Any:
        self._log_request("POST", endpoint, params, body=json)
        response = self.client.post(endpoint, json=json, params=params)
        self._handle_error(response)
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    def put(self, endpoint: str, json: Optional[dict] = None) -> Any:
        self._log_request("PUT", endpoint, body=json)
        response = self.client.put(endpoint, json=json)
        self._handle_error(response)
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    def patch(self, endpoint: str, json: Optional[dict] = None, params: Optional[dict] = None) -> Any:
        self._log_request("PATCH", endpoint, params, body=json)
        response = self.client.patch(endpoint, json=json, params=params)
        self._handle_error(response)
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    def delete(self, endpoint: str) -> Any:
        self._log_request("DELETE", endpoint)
        response = self.client.delete(endpoint)
        self._handle_error(response)
        if response.status_code == 204:
            return {}
        return response.json()

    # ── Helpers ──────────────────────────────────────────────────────

    def _normalize(self, response: Any) -> dict:
        """Normalize list responses to {count, results} format."""
        if isinstance(response, list):
            return {"count": len(response), "results": response}
        return response

    def _require_auth(self) -> None:
        if not self.token:
            raise APIError("Authentication required. Run 'ocl login' first.", status_code=401)

    # ── High-level API methods ───────────────────────────────────────

    def get_user(self) -> dict:
        """Get current authenticated user info."""
        self._require_auth()
        return self.get("/user/")

    def search_owners(
        self,
        query: Optional[str] = None,
        owner_type: str = "all",
        limit: int = 20,
        page: int = 1,
    ) -> dict:
        """Search for users and organizations."""
        if owner_type not in ("users", "orgs", "all"):
            raise ValueError("owner_type must be 'users', 'orgs', or 'all'")

        results = {}
        params: dict[str, Any] = {"limit": limit, "page": page}
        if query:
            params["q"] = query

        if owner_type in ("users", "all"):
            results["users"] = self._normalize(self.get("/users/", params=params))
        if owner_type in ("orgs", "all"):
            results["organizations"] = self._normalize(self.get("/orgs/", params=params))

        return results

    def get_owner(self, owner: str, owner_type: str = "orgs") -> dict:
        """Get a specific user or org."""
        _validate_owner_type(owner_type)
        return self.get(f"/{owner_type}/{owner}/")

    def get_org_members(self, org: str, limit: int = 100) -> dict:
        """List members of an organization."""
        return self._normalize(self.get(f"/orgs/{org}/members/", params={"limit": limit}))

    def search_repos(
        self,
        query: Optional[str] = None,
        owner: Optional[str] = None,
        owner_type: str = "all",
        repo_type: str = "all",
        verbose: bool = False,
        limit: int = 20,
        page: int = 1,
    ) -> dict:
        """Search for repositories (sources and collections)."""
        params: dict[str, Any] = {"limit": limit, "page": page}
        if verbose:
            params["verbose"] = True
        if query:
            params["q"] = query
        if owner:
            params["owner"] = owner
        if owner_type != "all":
            params["ownerType"] = "Organization" if owner_type == "orgs" else "User"
        if repo_type != "all":
            params["repoType"] = "Source" if repo_type == "source" else "Collection"

        return self._normalize(self.get("/repos/", params=params))

    def get_repo(
        self,
        owner: str,
        repo: str,
        owner_type: str = "orgs",
        repo_type: str = "source",
        version: Optional[str] = None,
    ) -> dict:
        """Get a specific repository, optionally at a version."""
        endpoint = _build_repo_endpoint(owner_type, owner, repo_type, repo, version)
        return self.get(endpoint)

    def get_repo_versions(
        self,
        owner: str,
        repo: str,
        owner_type: str = "orgs",
        repo_type: str = "source",
        released: Optional[bool] = None,
        processing: Optional[bool] = None,
        limit: int = 20,
        page: int = 1,
    ) -> dict:
        """List versions for a repository."""
        endpoint = _build_repo_endpoint(owner_type, owner, repo_type, repo, suffix="versions/")
        params: dict[str, Any] = {"limit": limit, "page": page}
        if released is not None:
            params["released"] = str(released).lower()
        if processing is not None:
            params["processing"] = str(processing).lower()
        return self._normalize(self.get(endpoint, params=params))

    def search_concepts(
        self,
        query: Optional[str] = None,
        owner: Optional[str] = None,
        owner_type: Optional[str] = None,
        repo_type: Optional[str] = None,
        repo: Optional[str] = None,
        version: Optional[str] = None,
        concept_class: Optional[str] = None,
        datatype: Optional[str] = None,
        locale: Optional[str] = None,
        include_retired: bool = False,
        include_mappings: bool = False,
        include_inverse_mappings: bool = False,
        updated_since: Optional[str] = None,
        sort: Optional[str] = None,
        verbose: bool = False,
        limit: int = 20,
        page: int = 1,
    ) -> dict:
        """Search for concepts globally or within a repository."""
        params: dict[str, Any] = {"limit": limit, "page": page}
        if verbose:
            params["verbose"] = True
        if query:
            params["q"] = query
        if concept_class:
            params["conceptClass"] = concept_class
        if datatype:
            params["datatype"] = datatype
        if locale:
            params["locale"] = locale
        if include_retired:
            params["includeRetired"] = "true"
        if include_mappings:
            params["includeMappings"] = "true"
        if include_inverse_mappings:
            params["includeInverseMappings"] = "true"
        if updated_since:
            params["updatedSince"] = updated_since
        if sort:
            params["sortAsc"] = sort if not sort.startswith("-") else None
            if sort.startswith("-"):
                params["sortDesc"] = sort[1:]
        if owner:
            params["owner"] = owner
        if owner_type and owner_type not in ("all",):
            params["ownerType"] = "Organization" if owner_type == "orgs" else "User"

        # Determine endpoint scope
        if all([owner_type, owner, repo_type, repo]):
            endpoint = _build_repo_endpoint(
                owner_type, owner, repo_type, repo, version, suffix="concepts/"
            )
        elif owner and repo:
            # Assume orgs/source if not specified
            ot = owner_type or "orgs"
            rt = repo_type or "source"
            endpoint = _build_repo_endpoint(ot, owner, rt, repo, version, suffix="concepts/")
        else:
            endpoint = "/concepts/"

        return self._normalize(self.get(endpoint, params=params))

    def get_concept(
        self,
        owner: str,
        source: str,
        concept_id: str,
        owner_type: str = "orgs",
        version: Optional[str] = None,
        concept_version: Optional[str] = None,
        include_mappings: bool = False,
        include_inverse_mappings: bool = False,
        verbose: bool = False,
    ) -> dict:
        """Get a single concept."""
        _validate_owner_type(owner_type)
        stem = _repo_type_stem("source")
        base = f"/{owner_type}/{owner}/{stem}/{source}"
        if version:
            base = f"{base}/{version}"
        endpoint = f"{base}/concepts/{concept_id}/"
        if concept_version:
            endpoint = f"{base}/concepts/{concept_id}/{concept_version}/"

        params: dict[str, Any] = {}
        if include_mappings:
            params["includeMappings"] = "true"
        if include_inverse_mappings:
            params["includeInverseMappings"] = "true"
        if verbose:
            params["verbose"] = "true"

        return self.get(endpoint, params=params or None)

    def get_concept_versions(
        self,
        owner: str,
        source: str,
        concept_id: str,
        owner_type: str = "orgs",
        limit: int = 20,
        page: int = 1,
    ) -> dict:
        """List version history for a concept."""
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/concepts/{concept_id}/versions/"
        return self._normalize(self.get(endpoint, params={"limit": limit, "page": page}))

    def get_concept_names(
        self,
        owner: str,
        source: str,
        concept_id: str,
        owner_type: str = "orgs",
    ) -> dict:
        """List names for a concept."""
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/concepts/{concept_id}/names/"
        return self._normalize(self.get(endpoint))

    def get_concept_descriptions(
        self,
        owner: str,
        source: str,
        concept_id: str,
        owner_type: str = "orgs",
    ) -> dict:
        """List descriptions for a concept."""
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/concepts/{concept_id}/descriptions/"
        return self._normalize(self.get(endpoint))

    def get_concept_extras(
        self,
        owner: str,
        source: str,
        concept_id: str,
        owner_type: str = "orgs",
    ) -> dict:
        """Get extras (custom attributes) for a concept."""
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/concepts/{concept_id}/extras/"
        return self.get(endpoint)

    def search_mappings(
        self,
        query: Optional[str] = None,
        owner: Optional[str] = None,
        owner_type: Optional[str] = None,
        repo_type: Optional[str] = None,
        repo: Optional[str] = None,
        version: Optional[str] = None,
        map_type: Optional[str] = None,
        from_source: Optional[str] = None,
        from_concept: Optional[str] = None,
        to_source: Optional[str] = None,
        to_concept: Optional[str] = None,
        concept: Optional[str] = None,
        include_retired: bool = False,
        updated_since: Optional[str] = None,
        sort: Optional[str] = None,
        verbose: bool = False,
        limit: int = 20,
        page: int = 1,
    ) -> dict:
        """Search for mappings globally or within a repository."""
        params: dict[str, Any] = {"limit": limit, "page": page}
        if verbose:
            params["verbose"] = True
        if query:
            params["q"] = query
        if map_type:
            params["mapType"] = map_type
        if from_source:
            params["fromConceptSource"] = from_source
        if from_concept:
            params["fromConcept"] = from_concept
        if to_source:
            params["toConceptSource"] = to_source
        if to_concept:
            params["toConcept"] = to_concept
        if concept:
            params["concept"] = concept
        if include_retired:
            params["includeRetired"] = "true"
        if updated_since:
            params["updatedSince"] = updated_since
        if sort:
            params["sortAsc"] = sort if not sort.startswith("-") else None
            if sort.startswith("-"):
                params["sortDesc"] = sort[1:]
        if owner:
            params["owner"] = owner
        if owner_type and owner_type not in ("all",):
            params["ownerType"] = "Organization" if owner_type == "orgs" else "User"

        if all([owner_type, owner, repo_type, repo]):
            endpoint = _build_repo_endpoint(
                owner_type, owner, repo_type, repo, version, suffix="mappings/"
            )
        elif owner and repo:
            ot = owner_type or "orgs"
            rt = repo_type or "source"
            endpoint = _build_repo_endpoint(ot, owner, rt, repo, version, suffix="mappings/")
        else:
            endpoint = "/mappings/"

        return self._normalize(self.get(endpoint, params=params))

    def get_mapping(
        self,
        owner: str,
        source: str,
        mapping_id: str,
        owner_type: str = "orgs",
        version: Optional[str] = None,
    ) -> dict:
        """Get a single mapping."""
        _validate_owner_type(owner_type)
        base = f"/{owner_type}/{owner}/sources/{source}"
        if version:
            base = f"{base}/{version}"
        return self.get(f"{base}/mappings/{mapping_id}/")

    def get_mapping_versions(
        self,
        owner: str,
        source: str,
        mapping_id: str,
        owner_type: str = "orgs",
        limit: int = 20,
        page: int = 1,
    ) -> dict:
        """List version history for a mapping."""
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/mappings/{mapping_id}/versions/"
        return self._normalize(self.get(endpoint, params={"limit": limit, "page": page}))

    def cascade(
        self,
        owner: str,
        repo: str,
        concept_id: str,
        owner_type: str = "orgs",
        repo_type: str = "source",
        version: Optional[str] = None,
        map_types: Optional[list[str]] = None,
        exclude_map_types: Optional[list[str]] = None,
        return_map_types: Optional[list[str]] = None,
        method: str = "sourcetoconcepts",
        cascade_hierarchy: bool = True,
        cascade_mappings: bool = True,
        cascade_levels: str = "*",
        reverse: bool = False,
        view: str = "hierarchy",
        verbose: bool = False,
        omit_if_exists_in: Optional[str] = None,
        equivalency_map_type: Optional[str] = None,
    ) -> dict:
        """Execute $cascade operation on a concept."""
        endpoint = _build_repo_endpoint(
            owner_type, owner, repo_type, repo, version,
            suffix=f"concepts/{concept_id}/$cascade/"
        )

        params: dict[str, Any] = {}
        if verbose:
            params["verbose"] = True
        if map_types:
            params["mapTypes"] = ",".join(map_types)
        if exclude_map_types:
            params["excludeMapTypes"] = ",".join(exclude_map_types)
        if return_map_types:
            params["returnMapTypes"] = ",".join(return_map_types)
        if method != "sourcetoconcepts":
            params["method"] = method
        if not cascade_hierarchy:
            params["cascadeHierarchy"] = "false"
        if not cascade_mappings:
            params["cascadeMappings"] = "false"
        if cascade_levels != "*":
            params["cascadeLevels"] = cascade_levels
        if reverse:
            params["reverse"] = "true"
        if view != "hierarchy":
            params["view"] = view
        else:
            params["view"] = "hierarchy"
        if omit_if_exists_in:
            params["omitIfExistsIn"] = omit_if_exists_in
        if equivalency_map_type:
            params["equivalencyMapType"] = equivalency_map_type

        result = self.get(endpoint, params=params or None)
        if isinstance(result, list):
            return {"resourceType": "Bundle", "type": "searchset", "entry": result}
        return result

    def match_concepts(
        self,
        terms: list[str],
        target_repo_url: str,
        limit: int = 5,
        include_retired: bool = False,
        semantic: bool = True,
        verbose: bool = False,
    ) -> dict:
        """Match concepts using the $match endpoint."""
        body = {
            "rows": [{"name": term} for term in terms],
            "target_repo_url": target_repo_url,
        }
        params: dict[str, Any] = {
            "includeSearchMeta": True,
            "semantic": semantic,
            "bestMatch": True,
        }
        if limit:
            params["limit"] = limit
        if include_retired:
            params["includeRetired"] = True
        if verbose:
            params["verbose"] = True

        result = self.post("/concepts/$match/", params=params, json=body)
        return self._normalize(result)

    def list_expansions(
        self,
        owner: str,
        collection: str,
        collection_version: str,
        owner_type: str = "orgs",
    ) -> dict:
        """List expansions for a collection version."""
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/collections/{collection}/{collection_version}/expansions/"
        return self._normalize(self.get(endpoint, params={"verbose": True}))

    def get_expansion(
        self,
        owner: str,
        collection: str,
        owner_type: str = "orgs",
        collection_version: Optional[str] = None,
        expansion_id: Optional[str] = None,
    ) -> dict:
        """Get a specific or default expansion for a collection."""
        _validate_owner_type(owner_type)

        if expansion_id:
            if collection_version:
                endpoint = f"/{owner_type}/{owner}/collections/{collection}/{collection_version}/expansions/{expansion_id}/"
            else:
                endpoint = f"/{owner_type}/{owner}/collections/{collection}/expansions/{expansion_id}/"
            return self.get(endpoint, params={"verbose": True})

        # Look up default expansion from collection version
        if collection_version:
            col_endpoint = f"/{owner_type}/{owner}/collections/{collection}/{collection_version}/"
        else:
            col_endpoint = f"/{owner_type}/{owner}/collections/{collection}/"

        col_data = self.get(col_endpoint)
        expansion_url = col_data.get("expansion_url")
        if expansion_url:
            return self.get(expansion_url, params={"verbose": True})
        return {
            "message": "No default expansion configured for this collection version",
            "expansion_url": None,
        }

    def list_collection_refs(
        self,
        owner: str,
        collection: str,
        owner_type: str = "orgs",
        version: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
    ) -> dict:
        """List references in a collection."""
        _validate_owner_type(owner_type)
        base = f"/{owner_type}/{owner}/collections/{collection}"
        if version:
            base = f"{base}/{version}"
        endpoint = f"{base}/references/"
        return self._normalize(self.get(endpoint, params={"limit": limit, "page": page}))

    def resolve_reference(self, *expressions: str, namespace: Optional[str] = None) -> dict:
        """Resolve references using $resolveReference."""
        params: dict[str, Any] = {}
        if namespace:
            params["namespace"] = namespace
        body = {"references": list(expressions)}
        return self.post("/$resolveReference/", json=body, params=params or None)

    # ── Write operations ─────────────────────────────────────────────

    def create_repo(
        self,
        owner: str,
        repo_id: str,
        name: str,
        owner_type: str = "orgs",
        repo_type: str = "source",
        description: Optional[str] = None,
        default_locale: Optional[str] = None,
        supported_locales: Optional[list[str]] = None,
        public_access: Optional[str] = None,
        source_type: Optional[str] = None,
        collection_type: Optional[str] = None,
        custom_validation_schema: Optional[str] = None,
        canonical_url: Optional[str] = None,
        extras: Optional[dict] = None,
    ) -> dict:
        """Create a new repository (source or collection)."""
        self._require_auth()
        _validate_owner_type(owner_type)
        stem = _repo_type_stem(repo_type)
        endpoint = f"/{owner_type}/{owner}/{stem}/"

        body: dict[str, Any] = {"id": repo_id, "short_code": repo_id, "name": name}
        if description:
            body["description"] = description
        if default_locale:
            body["default_locale"] = default_locale
        if supported_locales:
            body["supported_locales"] = supported_locales
        elif repo_type == "source":
            body["supported_locales"] = ["en"]
        if public_access:
            body["public_access"] = public_access
        if source_type and repo_type == "source":
            body["source_type"] = source_type
        if collection_type and repo_type == "collection":
            body["collection_type"] = collection_type
        if custom_validation_schema:
            body["custom_validation_schema"] = custom_validation_schema
        if canonical_url:
            body["canonical_url"] = canonical_url
        if extras:
            body["extras"] = extras

        return self.post(endpoint, json=body)

    def update_repo(
        self,
        owner: str,
        repo: str,
        owner_type: str = "orgs",
        repo_type: str = "source",
        **fields: Any,
    ) -> dict:
        """Update a repository."""
        self._require_auth()
        endpoint = _build_repo_endpoint(owner_type, owner, repo_type, repo)
        body = {k: v for k, v in fields.items() if v is not None}
        return self.patch(endpoint, json=body)

    def create_repo_version(
        self,
        owner: str,
        repo: str,
        version_id: str,
        owner_type: str = "orgs",
        repo_type: str = "source",
        description: Optional[str] = None,
        released: bool = True,
    ) -> dict:
        """Create a new repository version (snapshot)."""
        self._require_auth()
        endpoint = _build_repo_endpoint(owner_type, owner, repo_type, repo, suffix="versions/")
        body: dict[str, Any] = {"id": version_id, "released": released}
        if description:
            body["description"] = description
        return self.post(endpoint, json=body)

    def update_repo_version(
        self,
        owner: str,
        repo: str,
        version_id: str,
        owner_type: str = "orgs",
        repo_type: str = "source",
        **fields: Any,
    ) -> dict:
        """Update a repository version."""
        self._require_auth()
        _validate_owner_type(owner_type)
        stem = _repo_type_stem(repo_type)
        endpoint = f"/{owner_type}/{owner}/{stem}/{repo}/{version_id}/"
        body = {k: v for k, v in fields.items() if v is not None}
        return self.patch(endpoint, json=body)

    def create_concept(
        self,
        owner: str,
        source: str,
        concept_id: str,
        concept_class: str,
        names: list[dict],
        owner_type: str = "orgs",
        datatype: Optional[str] = None,
        descriptions: Optional[list[dict]] = None,
        external_id: Optional[str] = None,
        extras: Optional[dict] = None,
    ) -> dict:
        """Create a new concept in a source."""
        self._require_auth()
        _validate_owner_type(owner_type)

        if not names:
            raise ValueError("At least one name is required")

        endpoint = f"/{owner_type}/{owner}/sources/{source}/concepts/"
        body: dict[str, Any] = {
            "id": concept_id,
            "concept_class": concept_class,
            "names": names,
        }
        if datatype:
            body["datatype"] = datatype
        if descriptions:
            body["descriptions"] = descriptions
        if external_id:
            body["external_id"] = external_id
        if extras:
            body["extras"] = extras

        return self.post(endpoint, json=body)

    def update_concept(
        self,
        owner: str,
        source: str,
        concept_id: str,
        owner_type: str = "orgs",
        update_comment: Optional[str] = None,
        **fields: Any,
    ) -> dict:
        """Update an existing concept."""
        self._require_auth()
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/concepts/{concept_id}/"
        body = {k: v for k, v in fields.items() if v is not None}
        if update_comment:
            body["update_comment"] = update_comment
        return self.patch(endpoint, json=body)

    def retire_concept(
        self,
        owner: str,
        source: str,
        concept_id: str,
        owner_type: str = "orgs",
        update_comment: Optional[str] = None,
    ) -> dict:
        """Retire a concept (set retired=true)."""
        return self.update_concept(
            owner, source, concept_id,
            owner_type=owner_type,
            update_comment=update_comment,
            retired=True,
        )

    def add_concept_name(
        self,
        owner: str,
        source: str,
        concept_id: str,
        name: str,
        locale: str,
        owner_type: str = "orgs",
        name_type: Optional[str] = None,
        locale_preferred: bool = False,
    ) -> dict:
        """Add a name/translation to a concept."""
        self._require_auth()
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/concepts/{concept_id}/names/"
        body: dict[str, Any] = {"name": name, "locale": locale}
        if name_type:
            body["name_type"] = name_type
        if locale_preferred:
            body["locale_preferred"] = True
        return self.post(endpoint, json=body)

    def add_concept_description(
        self,
        owner: str,
        source: str,
        concept_id: str,
        description: str,
        locale: str,
        owner_type: str = "orgs",
        description_type: Optional[str] = None,
    ) -> dict:
        """Add a description to a concept."""
        self._require_auth()
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/concepts/{concept_id}/descriptions/"
        body: dict[str, Any] = {"description": description, "locale": locale}
        if description_type:
            body["description_type"] = description_type
        return self.post(endpoint, json=body)

    def set_concept_extra(
        self,
        owner: str,
        source: str,
        concept_id: str,
        key: str,
        value: Any,
        owner_type: str = "orgs",
    ) -> dict:
        """Set a custom attribute on a concept."""
        self._require_auth()
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/concepts/{concept_id}/extras/"
        return self.put(endpoint, json={key: value})

    def delete_concept_extra(
        self,
        owner: str,
        source: str,
        concept_id: str,
        key: str,
        owner_type: str = "orgs",
    ) -> dict:
        """Delete a custom attribute from a concept."""
        self._require_auth()
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/concepts/{concept_id}/extras/{key}/"
        return self.delete(endpoint)

    def create_mapping(
        self,
        owner: str,
        source: str,
        map_type: str,
        owner_type: str = "orgs",
        from_concept_url: Optional[str] = None,
        from_source_url: Optional[str] = None,
        from_concept_code: Optional[str] = None,
        from_concept_name: Optional[str] = None,
        to_concept_url: Optional[str] = None,
        to_source_url: Optional[str] = None,
        to_concept_code: Optional[str] = None,
        to_concept_name: Optional[str] = None,
        external_id: Optional[str] = None,
        extras: Optional[dict] = None,
    ) -> dict:
        """Create a new mapping between concepts."""
        self._require_auth()
        _validate_owner_type(owner_type)

        if not from_concept_url and not (from_source_url and from_concept_code):
            raise ValueError("from_concept requires either from_concept_url or (from_source_url + from_concept_code)")
        if not to_concept_url and not (to_source_url and to_concept_code):
            raise ValueError("to_concept requires either to_concept_url or (to_source_url + to_concept_code)")

        endpoint = f"/{owner_type}/{owner}/sources/{source}/mappings/"
        body: dict[str, Any] = {"map_type": map_type}

        if from_concept_url:
            body["from_concept_url"] = from_concept_url
        else:
            body["from_source_url"] = from_source_url
            body["from_concept_code"] = from_concept_code
        if from_concept_name:
            body["from_concept_name"] = from_concept_name

        if to_concept_url:
            body["to_concept_url"] = to_concept_url
        else:
            body["to_source_url"] = to_source_url
            body["to_concept_code"] = to_concept_code
        if to_concept_name:
            body["to_concept_name"] = to_concept_name

        if external_id:
            body["external_id"] = external_id
        if extras:
            body["extras"] = extras

        return self.post(endpoint, json=body)

    def update_mapping(
        self,
        owner: str,
        source: str,
        mapping_id: str,
        owner_type: str = "orgs",
        update_comment: Optional[str] = None,
        **fields: Any,
    ) -> dict:
        """Update an existing mapping."""
        self._require_auth()
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{source}/mappings/{mapping_id}/"
        body = {k: v for k, v in fields.items() if v is not None}
        if update_comment:
            body["update_comment"] = update_comment
        return self.patch(endpoint, json=body)

    def retire_mapping(
        self,
        owner: str,
        source: str,
        mapping_id: str,
        owner_type: str = "orgs",
        update_comment: Optional[str] = None,
    ) -> dict:
        """Retire a mapping."""
        return self.update_mapping(
            owner, source, mapping_id,
            owner_type=owner_type,
            update_comment=update_comment,
            retired=True,
        )

    def add_collection_ref(
        self,
        owner: str,
        collection: str,
        expressions: list[str],
        owner_type: str = "orgs",
        cascade: Optional[str] = None,
    ) -> dict:
        """Add references to a collection."""
        self._require_auth()
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/collections/{collection}/references/"
        body: dict[str, Any] = {"data": {"expressions": expressions}}
        params: dict[str, Any] = {}
        if cascade:
            params["cascade"] = cascade
        return self.put(endpoint, json=body)

    def remove_collection_ref(
        self,
        owner: str,
        collection: str,
        expressions: list[str],
        owner_type: str = "orgs",
    ) -> dict:
        """Remove references from a collection."""
        self._require_auth()
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/collections/{collection}/references/"
        # DELETE with body
        response = self.client.request(
            "DELETE", endpoint, json={"references": expressions}
        )
        self._handle_error(response)
        if response.status_code == 204:
            return {}
        return response.json()

    def create_expansion(
        self,
        owner: str,
        collection: str,
        version: str,
        owner_type: str = "orgs",
        **params: Any,
    ) -> dict:
        """Create/trigger an expansion for a collection version."""
        self._require_auth()
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/collections/{collection}/{version}/expansions/"
        body = {k: v for k, v in params.items() if v is not None}
        return self.post(endpoint, json=body or None)

    def clone(
        self,
        owner: str,
        dest_source: str,
        expressions: list[str],
        owner_type: str = "orgs",
        map_types: Optional[list[str]] = None,
        exclude_map_types: Optional[list[str]] = None,
        method: Optional[str] = None,
        cascade_levels: Optional[str] = None,
        cascade_hierarchy: bool = True,
        cascade_mappings: bool = True,
    ) -> dict:
        """Clone concepts using $clone operation."""
        self._require_auth()
        _validate_owner_type(owner_type)
        endpoint = f"/{owner_type}/{owner}/sources/{dest_source}/$clone/"

        body: dict[str, Any] = {"expressions": expressions}
        params: dict[str, Any] = {}
        if map_types:
            params["mapTypes"] = ",".join(map_types)
        if exclude_map_types:
            params["excludeMapTypes"] = ",".join(exclude_map_types)
        if method:
            params["method"] = method
        if cascade_levels:
            params["cascadeLevels"] = cascade_levels
        if not cascade_hierarchy:
            params["cascadeHierarchy"] = "false"
        if not cascade_mappings:
            params["cascadeMappings"] = "false"

        return self.post(endpoint, json=body, params=params or None)

    def set_repo_extra(
        self,
        owner: str,
        repo: str,
        key: str,
        value: Any,
        owner_type: str = "orgs",
        repo_type: str = "source",
    ) -> dict:
        """Set a custom attribute on a repository."""
        self._require_auth()
        endpoint = _build_repo_endpoint(owner_type, owner, repo_type, repo, suffix="extras/")
        return self.put(endpoint, json={key: value})

    def delete_repo_extra(
        self,
        owner: str,
        repo: str,
        key: str,
        owner_type: str = "orgs",
        repo_type: str = "source",
    ) -> dict:
        """Delete a custom attribute from a repository."""
        self._require_auth()
        _validate_owner_type(owner_type)
        stem = _repo_type_stem(repo_type)
        return self.delete(f"/{owner_type}/{owner}/{stem}/{repo}/extras/{key}/")

    def get_repo_extras(
        self,
        owner: str,
        repo: str,
        owner_type: str = "orgs",
        repo_type: str = "source",
    ) -> dict:
        """Get custom attributes for a repository."""
        endpoint = _build_repo_endpoint(owner_type, owner, repo_type, repo, suffix="extras/")
        return self.get(endpoint)

    def add_org_member(self, org: str, username: str) -> dict:
        """Add a member to an organization."""
        self._require_auth()
        return self.put(f"/orgs/{org}/members/{username}/")

    def remove_org_member(self, org: str, username: str) -> dict:
        """Remove a member from an organization."""
        self._require_auth()
        return self.delete(f"/orgs/{org}/members/{username}/")

    # ── Task operations ─────────────────────────────────────────────

    def list_tasks(
        self,
        state: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
    ) -> dict:
        """List async tasks for the authenticated user."""
        self._require_auth()
        params: dict[str, Any] = {"limit": limit, "page": page}
        if state:
            params["state"] = state
        return self._normalize(self.get("/user/tasks/", params=params))

    def get_task(self, task_id: str) -> dict:
        """Get details of a specific task."""
        self._require_auth()
        return self.get(f"/tasks/{task_id}/")

    # ── Organization CRUD ───────────────────────────────────────────

    def create_org(
        self,
        org_id: str,
        name: str,
        company: Optional[str] = None,
        website: Optional[str] = None,
        location: Optional[str] = None,
        public_access: str = "View",
        extras: Optional[dict] = None,
    ) -> dict:
        """Create a new organization."""
        self._require_auth()
        body: dict[str, Any] = {
            "id": org_id,
            "name": name,
            "public_access": public_access,
        }
        if company:
            body["company"] = company
        if website:
            body["website"] = website
        if location:
            body["location"] = location
        if extras:
            body["extras"] = extras
        return self.post("/orgs/", json=body)

    def delete_org(self, org: str) -> dict:
        """Delete an organization."""
        self._require_auth()
        return self.delete(f"/orgs/{org}/")

    # ── Repository delete ───────────────────────────────────────────

    def delete_repo(
        self,
        owner: str,
        repo: str,
        owner_type: str = "orgs",
        repo_type: str = "source",
    ) -> dict:
        """Delete a repository (source or collection)."""
        self._require_auth()
        endpoint = _build_repo_endpoint(owner_type, owner, repo_type, repo)
        return self.delete(endpoint)

    # ── Bulk import ─────────────────────────────────────────────────

    def bulk_import(self, lines: list[dict], update_if_exists: bool = True) -> dict:
        """Submit a bulk import (JSON Lines format to /manage/bulkimport/)."""
        self._require_auth()
        if not lines:
            return {"message": "no references"}
        import json as _json
        body = "\n".join(_json.dumps(item, ensure_ascii=False) for item in lines) + "\n"
        params = {}
        if update_if_exists:
            params["update_if_exists"] = "true"
        self._log_request("POST", "/manage/bulkimport/", params)
        response = self.client.post(
            "/manage/bulkimport/",
            content=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            params=params,
            timeout=120.0,
        )
        self._handle_error(response)
        try:
            return response.json()
        except Exception:
            return {"message": response.text}

    def get_bulk_import_status(self) -> list:
        """Get status of bulk import tasks."""
        self._require_auth()
        return self.get("/manage/bulkimport/")

    # ── Cascade concept fetching (for pruning) ──────────────────────

    def fetch_cascade_children(self, concept_url: str) -> set[str]:
        """Fetch child concept URLs via cascade for a given concept expression."""
        url = concept_url.rstrip("/") + "/cascade/"
        params = {
            "method": "sourcetoconcepts",
            "cascadeHierarchy": "true",
            "cascadeMappings": "true",
            "cascadeLevels": "*",
            "reverse": "false",
            "includeRetired": "false",
        }
        try:
            data = self.get(url, params=params)
        except (APIError, Exception):
            return set()
        entries = data.get("entry") or []
        if isinstance(entries, dict):
            entries = [entries]
        children: set[str] = set()
        parent = concept_url.rstrip("/") + "/"
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("type") != "Concept":
                continue
            child_url = entry.get("url", "").rstrip("/") + "/"
            if child_url and child_url != parent:
                children.add(child_url)
        return children
