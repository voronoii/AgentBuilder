from __future__ import annotations

import logging
import secrets
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import AppError, ErrorCode
from app.models.mcp import MCPAuthType, MCPServer, MCPTransport
from app.repositories.mcp import MCPRepository
from app.schemas.mcp import (
    MCPOAuthStartResponse,
    MCPOAuthStatus,
    MCPServerCreate,
    MCPServerRead,
    MCPServerUpdate,
)
from app.services.mcp import oauth as oauth_svc
from app.services.mcp.discovery import discover_tools
from app.services.mcp.oauth_state import StateEntry, get_state_store

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


# ---------- helpers ----------


async def _get_or_404(server_id: uuid.UUID, session: AsyncSession) -> MCPServer:
    server = await MCPRepository(session).get_by_id(server_id)
    if server is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.MCP_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )
    return server


async def _try_discover(server_id: uuid.UUID, timeout: float) -> None:
    """Attempt discovery in a fresh DB session (non-fatal for registration).

    Uses its own session to avoid reusing the request-scoped session
    which may already be closed by the time this background task runs.
    """
    from app.core.db import get_sessionmaker  # noqa: PLC0415

    try:
        async with get_sessionmaker()() as session:
            server = await MCPRepository(session).get_by_id(server_id)
            if server is None:
                _log.warning("Auto-discovery: server %s not found", server_id)
                return
            # OAuth-authed servers can only be discovered after the user completes
            # the authorization flow. Skip auto-discovery here; the callback
            # handler triggers discovery once tokens are stored.
            if server.auth_type == MCPAuthType.OAUTH and not server.oauth_access_token:
                _log.info(
                    "Auto-discovery skipped for OAuth server %s; awaiting connect", server_id
                )
                return
            await discover_tools(server, session, timeout=timeout)
            await session.commit()
    except AppError as exc:
        _log.warning("Auto-discovery failed for server %s: %s", server_id, exc.detail)
    except Exception as exc:  # noqa: BLE001
        _log.warning("Auto-discovery failed for server %s: %s", server_id, exc)


# ---------- CRUD ----------


@router.post("", response_model=MCPServerRead, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    payload: MCPServerCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    background_tasks: BackgroundTasks,
) -> MCPServer:
    repo = MCPRepository(session)
    try:
        server = await repo.create(payload)
        await session.commit()
    except IntegrityError as exc:
        raise AppError(
            status_code=409,
            code=ErrorCode.MCP_DUPLICATE_NAME,
            detail=f"MCP server with name '{payload.name}' already exists",
        ) from exc
    # Trigger discovery in background so registration always succeeds
    settings = get_settings()
    background_tasks.add_task(_try_discover, server.id, float(settings.mcp_discovery_timeout))
    return server


@router.get("", response_model=list[MCPServerRead])
async def list_mcp_servers(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[MCPServer]:
    return await MCPRepository(session).list_all()


@router.get("/{server_id}", response_model=MCPServerRead)
async def get_mcp_server(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MCPServer:
    return await _get_or_404(server_id, session)


@router.put("/{server_id}", response_model=MCPServerRead)
async def update_mcp_server(
    server_id: uuid.UUID,
    payload: MCPServerUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MCPServer:
    repo = MCPRepository(session)
    await _get_or_404(server_id, session)
    try:
        server = await repo.update(server_id, payload)
        await session.commit()
    except IntegrityError as exc:
        raise AppError(
            status_code=409,
            code=ErrorCode.MCP_DUPLICATE_NAME,
            detail=f"MCP server with name '{payload.name}' already exists",
        ) from exc
    assert server is not None  # guaranteed by _get_or_404
    await session.refresh(server)
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_mcp_server(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await MCPRepository(session).delete(server_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Discovery ----------


@router.post("/{server_id}/discover", response_model=MCPServerRead)
async def rediscover_tools(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MCPServer:
    """Manually trigger tool discovery for a registered MCP server."""
    server = await _get_or_404(server_id, session)
    settings = get_settings()
    await discover_tools(server, session, timeout=float(settings.mcp_discovery_timeout))
    await session.commit()
    # Reload to refresh server-side defaults (updated_at via onupdate=func.now())
    # which would otherwise be in expired state and trigger a lazy load during
    # response serialization.
    await session.refresh(server)
    return server


# ---------- OAuth ----------


def _server_url_or_422(server: MCPServer) -> str:
    if server.transport != MCPTransport.STREAMABLE_HTTP:
        raise AppError(
            status_code=422,
            code=ErrorCode.MCP_OAUTH_NOT_CONFIGURED,
            detail="OAuth is only supported for streamable_http transport",
        )
    url = (server.config or {}).get("url", "")
    if not url:
        raise AppError(
            status_code=422,
            code=ErrorCode.MCP_OAUTH_NOT_CONFIGURED,
            detail="server config is missing 'url'",
        )
    return url


@router.post("/{server_id}/oauth/start", response_model=MCPOAuthStartResponse)
async def oauth_start(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MCPOAuthStartResponse:
    """Discover OAuth metadata, register a client (DCR), and return an authorize URL.

    Frontend should open the returned URL in a popup or new tab. The user completes
    the authorization, the provider redirects to our callback, and the popup is
    closed by the callback handler.
    """
    server = await _get_or_404(server_id, session)
    if server.auth_type != MCPAuthType.OAUTH:
        raise AppError(
            status_code=422,
            code=ErrorCode.MCP_OAUTH_NOT_CONFIGURED,
            detail="server is not configured for OAuth",
        )

    server_url = _server_url_or_422(server)
    settings = get_settings()
    redirect_uri = settings.mcp_oauth_redirect_uri

    metadata = await oauth_svc.discover_metadata(server_url)
    if not metadata.registration_endpoint:
        raise AppError(
            status_code=502,
            code=ErrorCode.MCP_OAUTH_REGISTRATION_FAILED,
            detail="authorization server does not advertise a registration endpoint (RFC 7591)",
        )

    # Reuse a previously registered client_id if we already have one for this server.
    if not server.oauth_client_id:
        client_id, client_secret = await oauth_svc.register_client(
            metadata.registration_endpoint,
            redirect_uri=redirect_uri,
            client_name=f"agentbuilder:{server.name}",
            scopes=metadata.scopes_supported,
        )
        server.oauth_client_id = client_id
        server.oauth_client_secret = client_secret

    # Cache discovered endpoints for refresh.
    server.oauth_authorize_url = metadata.authorization_endpoint
    server.oauth_token_url = metadata.token_endpoint
    server.oauth_scopes = " ".join(metadata.scopes_supported) if metadata.scopes_supported else None
    # RFC 8707: bind tokens to this specific resource (audience). Fall back to the
    # configured server URL if PRM didn't advertise a resource id.
    server.oauth_resource = metadata.resource or server_url
    await session.flush()
    await session.commit()

    # PKCE + state
    code_verifier, code_challenge = oauth_svc.generate_pkce_pair()
    state = secrets.token_urlsafe(24)
    await get_state_store().put(
        state,
        StateEntry(
            server_id=server.id,
            code_verifier=code_verifier,
            expires_at=time.time() + settings.mcp_oauth_state_ttl_seconds,
        ),
    )

    authorize_url = oauth_svc.build_authorize_url(
        metadata,
        client_id=server.oauth_client_id,  # type: ignore[arg-type]
        state=state,
        code_challenge=code_challenge,
        redirect_uri=redirect_uri,
        scopes=metadata.scopes_supported,
        resource=server.oauth_resource,
    )
    return MCPOAuthStartResponse(authorize_url=authorize_url)


@router.get("/oauth/callback")
async def oauth_callback(
    session: Annotated[AsyncSession, Depends(get_session)],
    background_tasks: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> Response:
    """OAuth provider redirects here after authorization. Exchanges code for tokens."""
    if error:
        return _callback_html(
            ok=False,
            message=f"OAuth error: {error} — {error_description or ''}",
        )
    if not code or not state:
        return _callback_html(ok=False, message="missing code or state")

    entry = await get_state_store().pop(state)
    if entry is None:
        raise AppError(
            status_code=400,
            code=ErrorCode.MCP_OAUTH_INVALID_STATE,
            detail="state is invalid or expired",
        )

    server = await MCPRepository(session).get_by_id(entry.server_id)
    if server is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.MCP_NOT_FOUND,
            detail=f"server {entry.server_id} not found",
        )
    if not server.oauth_token_url or not server.oauth_client_id:
        raise AppError(
            status_code=400,
            code=ErrorCode.MCP_OAUTH_NOT_CONFIGURED,
            detail="server is missing OAuth client configuration",
        )

    settings = get_settings()
    tokens = await oauth_svc.exchange_code(
        server.oauth_token_url,
        code=code,
        code_verifier=entry.code_verifier,
        client_id=server.oauth_client_id,
        client_secret=server.oauth_client_secret,
        redirect_uri=settings.mcp_oauth_redirect_uri,
        resource=server.oauth_resource,
    )
    oauth_svc.apply_tokens(server, tokens)
    await session.flush()
    await session.commit()

    # Now that we have a token, run tool discovery in the background.
    background_tasks.add_task(_try_discover, server.id, float(settings.mcp_discovery_timeout))

    # Redirect the user back to the frontend.
    if settings.mcp_oauth_post_callback_url:
        return RedirectResponse(
            url=f"{settings.mcp_oauth_post_callback_url}?mcp_oauth=connected&id={server.id}",
            status_code=303,
        )
    return _callback_html(ok=True, message="연결이 완료되었습니다. 이 창을 닫아주세요.")


@router.post("/{server_id}/oauth/disconnect", response_model=MCPServerRead)
async def oauth_disconnect(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MCPServer:
    server = await _get_or_404(server_id, session)
    server.oauth_access_token = None
    server.oauth_refresh_token = None
    server.oauth_token_expires_at = None
    await session.flush()
    await session.commit()
    return server


@router.get("/{server_id}/oauth/status", response_model=MCPOAuthStatus)
async def oauth_status(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MCPOAuthStatus:
    server = await _get_or_404(server_id, session)
    return MCPOAuthStatus(
        connected=bool(server.oauth_access_token),
        expires_at=server.oauth_token_expires_at,
    )


def _callback_html(*, ok: bool, message: str) -> HTMLResponse:
    body = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>MCP OAuth</title></head>
<body style="font-family: system-ui, -apple-system, sans-serif; padding: 24px;">
  <h2>{"연결 완료" if ok else "연결 실패"}</h2>
  <p>{message}</p>
  <script>
    try {{ window.opener && window.opener.postMessage({{ type: "mcp-oauth", ok: {str(ok).lower()} }}, "*"); }} catch (e) {{}}
    setTimeout(() => window.close(), 1500);
  </script>
</body></html>"""
    return HTMLResponse(content=body, status_code=200 if ok else 400)
