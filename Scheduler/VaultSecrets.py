import json
import os
import threading
import time
import urllib.request
from typing import Dict, Optional


_LOCK = threading.Lock()
_CACHE: Dict[str, str] = {}
_LAST_SYNC = 0
_CACHE_TTL_SECONDS = 60


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def fetch_vault_secrets() -> Dict[str, str]:
    vault_addr = _require_env("VAULT_ADDR").rstrip("/")
    vault_token = _require_env("VAULT_TOKEN")
    vault_secret_path = _require_env("VAULT_SECRET_PATH").lstrip("/")

    url = f"{vault_addr}/v1/{vault_secret_path}"

    request = urllib.request.Request(
        url,
        headers={"X-Vault-Token": vault_token},
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))

    data = payload["data"]["data"]

    return {
        str(key): "" if value is None else str(value)
        for key, value in data.items()
    }


def refresh_vault_secrets() -> Dict[str, str]:
    global _CACHE, _LAST_SYNC

    secrets = fetch_vault_secrets()

    with _LOCK:
        _CACHE = secrets
        _LAST_SYNC = time.time()

    return secrets


def get_vault_secrets(force_refresh: bool = False) -> Dict[str, str]:
    global _CACHE, _LAST_SYNC

    with _LOCK:
        cache_age = time.time() - _LAST_SYNC
        has_valid_cache = bool(_CACHE) and cache_age < _CACHE_TTL_SECONDS

    if force_refresh or not has_valid_cache:
        return refresh_vault_secrets()

    with _LOCK:
        return dict(_CACHE)


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    secrets = get_vault_secrets()
    return secrets.get(name, default)