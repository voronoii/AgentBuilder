"""MCP OAuth 2.1 client (auto-discovery only).

Implements:
- RFC 9728 (OAuth Protected Resource Metadata) — primary, recommended by MCP spec
- RFC 8414 (OAuth Authorization Server Metadata) — fallback
- RFC 7591 (Dynamic Client Registration)
- PKCE S256

No manual configuration is supported in this MVP — if a server doesn't expose
discovery + DCR, OAuth setup fails with a clear error.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.models.mcp import MCPAuthType, MCPServer

_log = logging.getLogger(__name__)

_DISCOVERY_TIMEOUT = 10.0
_TOKEN_TIMEOUT = 15.0
# Refresh access_token if it expires within this window.
_REFRESH_LEEWAY_SECONDS = 60


@dataclass(frozen=True)
class OAuthMetadata:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None
    scopes_supported: list[str]
    resource: str | None  # RFC 8707 audience identifier from PRM


@dataclass(frozen=True)
class TokenResponse:
    access_token: str
    refresh_token: str | None
    expires_in: int | None  # seconds


# ---------- Discovery ----------


def _origin_and_path(url: str) -> tuple[str, str]:
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        raise AppError(
            status_code=422,
            code=ErrorCode.MCP_OAUTH_DISCOVERY_FAILED,
            detail=f"invalid server url: {url}",
        )
    return f"{p.scheme}://{p.netloc}", (p.path or "")


async def discover_metadata(server_url: str) -> OAuthMetadata:
    """Fetch OAuth metadata. Tries RFC 9728 (path-suffixed then origin) then RFC 8414."""
    origin, path = _origin_and_path(server_url)

    # RFC 9728 §3.1: when the resource has a path, the metadata URL appends the path
    # under .well-known/oauth-protected-resource. Try the path-suffixed form FIRST
    # because servers that host multiple resources on one origin (e.g. /social/mcp,
    # /news/mcp) only expose path-specific PRM.
    candidates_prm: list[str] = []
    if path and path != "/":
        candidates_prm.append(f"{origin}/.well-known/oauth-protected-resource{path}")
    candidates_prm.append(f"{origin}/.well-known/oauth-protected-resource")

    candidates_as_origin = [
        f"{origin}/.well-known/oauth-authorization-server",
        f"{origin}/.well-known/openid-configuration",
    ]

    resource_id: str | None = None
    scopes_from_prm: list[str] = []

    async with httpx.AsyncClient(timeout=_DISCOVERY_TIMEOUT, follow_redirects=True) as client:
        as_url: str | None = None
        for url in candidates_prm:
            data = await _try_get_json(client, url)
            if data is None:
                continue
            resource_id = data.get("resource") or resource_id
            scopes_from_prm = list(data.get("scopes_supported") or [])
            servers = data.get("authorization_servers") or []
            if servers:
                as_url = servers[0]
                break

        as_metadata: dict[str, Any] | None = None
        if as_url:
            as_metadata = await _fetch_as_metadata(client, as_url)
        if as_metadata is None:
            for url in candidates_as_origin:
                data = await _try_get_json(client, url)
                if data is not None:
                    as_metadata = data
                    break

    if as_metadata is None:
        raise AppError(
            status_code=502,
            code=ErrorCode.MCP_OAUTH_DISCOVERY_FAILED,
            detail=(
                f"could not discover OAuth metadata for {origin}{path}: "
                "neither RFC 9728 protected-resource nor RFC 8414 authorization-server "
                "metadata was reachable"
            ),
        )

    issuer = as_metadata.get("issuer", origin)
    auth_ep = as_metadata.get("authorization_endpoint")
    token_ep = as_metadata.get("token_endpoint")
    if not auth_ep or not token_ep:
        raise AppError(
            status_code=502,
            code=ErrorCode.MCP_OAUTH_DISCOVERY_FAILED,
            detail="authorization server metadata missing required endpoints",
        )

    # Prefer scopes from PRM (resource-scoped); fall back to AS-advertised scopes.
    scopes = scopes_from_prm or list(as_metadata.get("scopes_supported") or [])

    return OAuthMetadata(
        issuer=issuer,
        authorization_endpoint=auth_ep,
        token_endpoint=token_ep,
        registration_endpoint=as_metadata.get("registration_endpoint"),
        scopes_supported=scopes,
        resource=resource_id,
    )


async def _fetch_as_metadata(client: httpx.AsyncClient, as_url: str) -> dict[str, Any] | None:
    # If as_url is itself a metadata document URL, fetch directly; otherwise probe well-knowns.
    direct = await _try_get_json(client, as_url)
    if direct is not None and "token_endpoint" in direct:
        return direct
    origin, _ = _origin_and_path(as_url)
    for url in (
        f"{origin}/.well-known/oauth-authorization-server",
        f"{origin}/.well-known/openid-configuration",
    ):
        data = await _try_get_json(client, url)
        if data is not None:
            return data
    return None


async def _try_get_json(client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
    try:
        resp = await client.get(url, headers={"Accept": "application/json"})
    except httpx.HTTPError as exc:
        _log.debug("OAuth discovery GET failed for %s: %s", url, exc)
        return None
    if resp.status_code != 200:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


# ---------- Dynamic Client Registration (RFC 7591) ----------


async def register_client(
    registration_endpoint: str,
    *,
    redirect_uri: str,
    client_name: str,
    scopes: list[str],
) -> tuple[str, str | None]:
    """Register a public client via RFC 7591. Returns (client_id, client_secret|None)."""
    payload: dict[str, Any] = {
        "client_name": client_name,
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",  # public client + PKCE
    }
    if scopes:
        payload["scope"] = " ".join(scopes)

    async with httpx.AsyncClient(timeout=_TOKEN_TIMEOUT) as client:
        try:
            resp = await client.post(registration_endpoint, json=payload)
        except httpx.HTTPError as exc:
            raise AppError(
                status_code=502,
                code=ErrorCode.MCP_OAUTH_REGISTRATION_FAILED,
                detail=f"DCR request failed: {exc}",
            ) from exc

    if resp.status_code not in (200, 201):
        raise AppError(
            status_code=502,
            code=ErrorCode.MCP_OAUTH_REGISTRATION_FAILED,
            detail=f"DCR returned {resp.status_code}: {resp.text[:300]}",
        )

    data = resp.json()
    client_id = data.get("client_id")
    if not client_id:
        raise AppError(
            status_code=502,
            code=ErrorCode.MCP_OAUTH_REGISTRATION_FAILED,
            detail="DCR response missing client_id",
        )
    return client_id, data.get("client_secret")


# ---------- PKCE / authorize URL ----------


def generate_pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge_S256)."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_authorize_url(
    metadata: OAuthMetadata,
    *,
    client_id: str,
    state: str,
    code_challenge: str,
    redirect_uri: str,
    scopes: list[str],
    resource: str | None = None,
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if scopes:
        params["scope"] = " ".join(scopes)
    if resource:
        # RFC 8707 — bind issued tokens to the protected resource (audience).
        params["resource"] = resource
    sep = "&" if "?" in metadata.authorization_endpoint else "?"
    return f"{metadata.authorization_endpoint}{sep}{urlencode(params)}"


# ---------- Token endpoint ----------


async def exchange_code(
    token_url: str,
    *,
    code: str,
    code_verifier: str,
    client_id: str,
    client_secret: str | None,
    redirect_uri: str,
    resource: str | None = None,
) -> TokenResponse:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    if client_secret:
        data["client_secret"] = client_secret
    if resource:
        data["resource"] = resource
    return await _post_token(token_url, data)


async def refresh_access_token(
    token_url: str,
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str | None,
    resource: str | None = None,
) -> TokenResponse:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    if client_secret:
        data["client_secret"] = client_secret
    if resource:
        data["resource"] = resource
    return await _post_token(token_url, data)


async def _post_token(token_url: str, data: dict[str, str]) -> TokenResponse:
    async with httpx.AsyncClient(timeout=_TOKEN_TIMEOUT) as client:
        try:
            resp = await client.post(
                token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise AppError(
                status_code=502,
                code=ErrorCode.MCP_OAUTH_TOKEN_FAILED,
                detail=f"token endpoint request failed: {exc}",
            ) from exc

    if resp.status_code != 200:
        raise AppError(
            status_code=502,
            code=ErrorCode.MCP_OAUTH_TOKEN_FAILED,
            detail=f"token endpoint returned {resp.status_code}: {resp.text[:300]}",
        )

    body = resp.json()
    access_token = body.get("access_token")
    if not access_token:
        raise AppError(
            status_code=502,
            code=ErrorCode.MCP_OAUTH_TOKEN_FAILED,
            detail="token response missing access_token",
        )
    return TokenResponse(
        access_token=access_token,
        refresh_token=body.get("refresh_token"),
        expires_in=body.get("expires_in"),
    )


# ---------- Server-side helpers (DB-aware) ----------


async def ensure_valid_token(server: MCPServer, session: AsyncSession) -> str:
    """Return a non-expired access_token for an OAuth-authed server.

    Refreshes via refresh_token if expiring soon. Caller must commit the session
    afterwards if a refresh occurred (token fields are mutated on the ORM object).
    """
    if server.auth_type != MCPAuthType.OAUTH or not server.oauth_access_token:
        raise AppError(
            status_code=400,
            code=ErrorCode.MCP_OAUTH_NOT_CONFIGURED,
            detail=f"server '{server.name}' is not connected via OAuth",
        )

    if not _expiring_soon(server.oauth_token_expires_at):
        return server.oauth_access_token

    if not server.oauth_refresh_token or not server.oauth_token_url or not server.oauth_client_id:
        # No way to refresh — surface as not configured so the user reconnects.
        raise AppError(
            status_code=401,
            code=ErrorCode.MCP_OAUTH_NOT_CONFIGURED,
            detail=f"OAuth token for '{server.name}' expired and cannot be refreshed; reconnect",
        )

    tokens = await refresh_access_token(
        server.oauth_token_url,
        refresh_token=server.oauth_refresh_token,
        client_id=server.oauth_client_id,
        client_secret=server.oauth_client_secret,
        resource=server.oauth_resource,
    )
    apply_tokens(server, tokens)
    await session.flush()
    return server.oauth_access_token  # type: ignore[return-value]


def apply_tokens(server: MCPServer, tokens: TokenResponse) -> None:
    server.oauth_access_token = tokens.access_token
    if tokens.refresh_token:
        server.oauth_refresh_token = tokens.refresh_token
    if tokens.expires_in is not None:
        server.oauth_token_expires_at = datetime.now(tz=UTC) + timedelta(
            seconds=int(tokens.expires_in)
        )
    else:
        server.oauth_token_expires_at = None


def _expiring_soon(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    return datetime.now(tz=UTC) >= (expires_at - timedelta(seconds=_REFRESH_LEEWAY_SECONDS))
