"""Configuration management for OCL CLI.

Handles server registry, auth tokens, and CLI settings.
Config stored at ~/.ocl/config.json.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path.home() / ".ocl"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_BASE_URL = "https://api.openconceptlab.org"

DEFAULT_CONFIG = {
    "default_server": "ocl-prod",
    "servers": {
        "ocl-prod": {
            "name": "OCL Online Production Server",
            "base_url": "https://api.openconceptlab.org",
            "api_token_env": "OCL_API_TOKEN_PROD",
            "token": None,
        },
        "ocl-dev": {
            "name": "OCL Online Dev Server",
            "base_url": "https://api.dev.openconceptlab.org",
            "api_token_env": "OCL_API_TOKEN_DEV",
            "token": None,
        },
        "ocl-qa": {
            "name": "OCL Online QA Server",
            "base_url": "https://api.qa.openconceptlab.org",
            "api_token_env": "OCL_API_TOKEN_QA",
            "token": None,
        },
        "ocl-staging": {
            "name": "OCL Online Staging Server",
            "base_url": "https://api.staging.openconceptlab.org",
            "api_token_env": "OCL_API_TOKEN_STAGING",
            "token": None,
        },
    },
}


@dataclass
class ServerInfo:
    """Resolved server configuration."""

    server_id: str
    name: str
    base_url: str
    token: Optional[str] = None
    api_token_env: Optional[str] = None
    is_default: bool = False


@dataclass
class CLIConfig:
    """CLI configuration loaded from ~/.ocl/config.json."""

    default_server: str = "ocl-prod"
    servers: dict = field(default_factory=dict)

    @classmethod
    def load(cls) -> "CLIConfig":
        """Load config from disk, creating default if needed."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                data = json.load(f)
        else:
            data = DEFAULT_CONFIG.copy()

        config = cls()
        config.default_server = data.get("default_server", "ocl-prod")
        config.servers = data.get("servers", DEFAULT_CONFIG["servers"])
        return config

    def save(self) -> None:
        """Save config to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "default_server": self.default_server,
            "servers": self.servers,
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def get_server(self, server_id: Optional[str] = None) -> ServerInfo:
        """Resolve server by ID, env var, or default.

        Resolution order:
        1. Explicit server_id argument (from --server flag)
        2. OCL_SERVER environment variable
        3. default_server from config
        4. Fallback to production
        """
        server_id = server_id or os.getenv("OCL_SERVER") or self.default_server

        server_data = self.servers.get(server_id)
        if not server_data:
            # Fallback: if server_id looks like a URL, use it directly
            if server_id.startswith("http"):
                return ServerInfo(
                    server_id="custom",
                    name="Custom Server",
                    base_url=server_id.rstrip("/"),
                )
            # Otherwise fall back to default
            server_data = self.servers.get(self.default_server, {})
            server_id = self.default_server

        return ServerInfo(
            server_id=server_id,
            name=server_data.get("name", server_id),
            base_url=server_data.get("base_url", DEFAULT_BASE_URL),
            token=server_data.get("token"),
            api_token_env=server_data.get("api_token_env"),
            is_default=(server_id == self.default_server),
        )

    def resolve_token(
        self, server: ServerInfo, token_override: Optional[str] = None
    ) -> Optional[str]:
        """Resolve auth token with priority chain.

        Resolution order:
        1. --token CLI flag (token_override)
        2. OCL_API_TOKEN environment variable
        3. Server-specific env var (e.g. OCL_API_TOKEN_PROD)
        4. Token stored in config file
        """
        if token_override:
            return token_override

        env_token = os.getenv("OCL_API_TOKEN")
        if env_token:
            return env_token

        if server.api_token_env:
            server_env_token = os.getenv(server.api_token_env)
            if server_env_token:
                return server_env_token

        return server.token

    def set_token(self, server_id: str, token: str) -> None:
        """Store a token for a server."""
        if server_id in self.servers:
            self.servers[server_id]["token"] = token
            self.save()
        else:
            raise ValueError(f"Unknown server: {server_id}")

    def remove_token(self, server_id: str) -> None:
        """Remove stored token for a server."""
        if server_id in self.servers:
            self.servers[server_id]["token"] = None
            self.save()

    def add_server(
        self,
        server_id: str,
        url: str,
        name: Optional[str] = None,
        api_token_env: Optional[str] = None,
    ) -> None:
        """Add a new server to the config."""
        self.servers[server_id] = {
            "name": name or server_id,
            "base_url": url.rstrip("/"),
            "api_token_env": api_token_env,
            "token": None,
        }
        self.save()

    def remove_server(self, server_id: str) -> None:
        """Remove a server from the config."""
        if server_id not in self.servers:
            raise ValueError(f"Unknown server: {server_id}")
        if server_id == self.default_server:
            raise ValueError(f"Cannot remove the default server '{server_id}'. Change default first.")
        del self.servers[server_id]
        self.save()

    def set_default_server(self, server_id: str) -> None:
        """Set the default server."""
        if server_id not in self.servers:
            raise ValueError(f"Unknown server: {server_id}")
        self.default_server = server_id
        self.save()
