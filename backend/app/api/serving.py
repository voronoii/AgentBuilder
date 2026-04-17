from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session, get_sessionmaker
from app.core.errors import AppError, ErrorCode
from app.models.app import PublishedApp
from app.repositories.app import AppRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.run import RunRepository
from app.repositories.workflow import WorkflowRepository
from app.schemas.serving import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    ChoiceMessage,
    ConversationMessageRead,
    ConversationRead,
    DeltaMessage,
    StreamChoice,
    Usage,
)
from app.services.workflow.runtime import WorkflowRuntime

router = APIRouter(prefix="/v1", tags=["serving"])


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


async def _resolve_app(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> tuple[PublishedApp, AsyncSession]:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(
            status_code=401,
            code=ErrorCode.INVALID_API_KEY,
            detail="유효하지 않은 API 키입니다.",
        )
    api_key = authorization.removeprefix("Bearer ").strip()
    app = await AppRepository(session).get_by_api_key(api_key)
    if app is None:
        raise AppError(
            status_code=401,
            code=ErrorCode.INVALID_API_KEY,
            detail="유효하지 않은 API 키입니다.",
        )
    if not app.is_active:
        raise AppError(
            status_code=403,
            code=ErrorCode.APP_INACTIVE,
            detail="비활성화된 앱입니다.",
        )
    return app, session


AppDep = Annotated[tuple[PublishedApp, AsyncSession], Depends(_resolve_app)]


# ---------------------------------------------------------------------------
# SSE streaming helper
# ---------------------------------------------------------------------------


async def _stream_sse(
    run_id: uuid.UUID,
    conversation_id: uuid.UUID,
    completion_id: str,
    session_factory,
) -> AsyncGenerator[str, None]:
    """Read from the workflow queue and emit OpenAI-compatible SSE chunks."""
    queue = None
    # Wait briefly for the queue to be registered
    for _ in range(20):
        queue = WorkflowRuntime.get_queue(run_id)
        if queue is not None:
            break
        await asyncio.sleep(0.05)

    created = int(time.time())
    collected_tokens: list[str] = []

    # First chunk: role announcement
    first_chunk = ChatCompletionChunk(
        id=completion_id,
        created=created,
        choices=[StreamChoice(index=0, delta=DeltaMessage(role="assistant"), finish_reason=None)],
        conversation_id=conversation_id,
    )
    yield f"data: {first_chunk.model_dump_json()}\n\n"

    if queue is not None:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=300)
            except asyncio.TimeoutError:
                break

            if event is None:
                # Sentinel — workflow finished
                break

            event_type = event.get("event_type", "")

            if event_type == "llm_token":
                token = event.get("payload", {}).get("token", "")
                if token:
                    collected_tokens.append(token)
                    chunk = ChatCompletionChunk(
                        id=completion_id,
                        created=created,
                        choices=[
                            StreamChoice(
                                index=0,
                                delta=DeltaMessage(content=token),
                                finish_reason=None,
                            )
                        ],
                        conversation_id=conversation_id,
                    )
                    yield f"data: {chunk.model_dump_json()}\n\n"

            elif event_type in ("workflow_end", "workflow_error"):
                break

    # Final chunk with finish_reason
    final_chunk = ChatCompletionChunk(
        id=completion_id,
        created=created,
        choices=[StreamChoice(index=0, delta=DeltaMessage(), finish_reason="stop")],
        conversation_id=conversation_id,
    )
    yield f"data: {final_chunk.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"

    # Persist assistant message after streaming
    assistant_content = "".join(collected_tokens)
    if assistant_content:
        async with session_factory() as session:
            conv_repo = ConversationRepository(session)
            await conv_repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content,
                run_id=run_id,
            )
            await session.commit()


# ---------------------------------------------------------------------------
# Non-streaming helper
# ---------------------------------------------------------------------------


async def _wait_for_completion(run_id: uuid.UUID) -> str:
    """Wait for workflow completion and return collected text."""
    queue = None
    for _ in range(20):
        queue = WorkflowRuntime.get_queue(run_id)
        if queue is not None:
            break
        await asyncio.sleep(0.05)

    if queue is None:
        return ""

    collected_tokens: list[str] = []

    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=300)
        except asyncio.TimeoutError:
            break

        if event is None:
            break

        event_type = event.get("event_type", "")

        if event_type == "llm_token":
            token = event.get("payload", {}).get("token", "")
            if token:
                collected_tokens.append(token)

        elif event_type in ("workflow_end", "workflow_error"):
            if event_type == "workflow_end" and not collected_tokens:
                # Fallback: use payload output if tokens were not emitted
                output = event.get("payload", {}).get("output", "")
                if output:
                    collected_tokens.append(output)
            break

    return "".join(collected_tokens)


# ---------------------------------------------------------------------------
# POST /v1/chat/completions
# ---------------------------------------------------------------------------


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    payload: ChatCompletionRequest,
    resolved: AppDep,
) -> StreamingResponse | ChatCompletionResponse:
    app, session = resolved
    session_factory = get_sessionmaker()

    conv_repo = ConversationRepository(session)
    run_repo = RunRepository(session)
    wf_repo = WorkflowRepository(session)

    # --- Resolve / create conversation ---
    if payload.conversation_id is not None:
        conv = await conv_repo.get(payload.conversation_id)
        if conv is None:
            raise AppError(
                status_code=404,
                code=ErrorCode.CONVERSATION_NOT_FOUND,
                detail="대화를 찾을 수 없습니다.",
            )
        if conv.app_id != app.id:
            raise AppError(
                status_code=403,
                code=ErrorCode.CONVERSATION_NOT_OWNED,
                detail="이 대화에 접근할 권한이 없습니다.",
            )
        conversation = conv
    else:
        conversation = await conv_repo.create(app_id=app.id)

    # --- Load message history ---
    history_msgs = await conv_repo.get_messages(conversation.id)
    messages_history = [{"role": m.role, "content": m.content} for m in history_msgs]

    # --- Extract user input from request ---
    user_input = payload.messages[-1].content

    # --- Save user message ---
    await conv_repo.add_message(
        conversation_id=conversation.id,
        role="user",
        content=user_input,
    )

    # --- Load workflow ---
    workflow = await wf_repo.get(app.workflow_id)
    if workflow is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.WORKFLOW_NOT_FOUND,
            detail="워크플로우를 찾을 수 없습니다.",
        )

    # --- Create run ---
    run = await run_repo.create(
        workflow_id=workflow.id,
        input_data={"user_input": user_input},
    )
    await session.commit()

    completion_id = f"chatcmpl-{run.id}"

    # --- Start workflow in background ---
    await WorkflowRuntime.start_run(
        run_id=run.id,
        workflow_id=workflow.id,
        nodes=workflow.nodes,
        edges=workflow.edges,
        user_input=user_input,
        session_factory=session_factory,
        messages=messages_history,
    )

    # --- Stream or wait ---
    if payload.stream:
        return StreamingResponse(
            _stream_sse(
                run_id=run.id,
                conversation_id=conversation.id,
                completion_id=completion_id,
                session_factory=session_factory,
            ),
            media_type="text/event-stream",
        )

    # Non-streaming: wait for completion
    assistant_content = await _wait_for_completion(run.id)

    # Save assistant message
    await conv_repo.add_message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_content,
        run_id=run.id,
    )
    await session.commit()

    return ChatCompletionResponse(
        id=completion_id,
        created=int(time.time()),
        choices=[
            Choice(
                index=0,
                message=ChoiceMessage(role="assistant", content=assistant_content),
                finish_reason="stop",
            )
        ],
        conversation_id=conversation.id,
        usage=Usage(),
    )


# ---------------------------------------------------------------------------
# Conversation management endpoints
# ---------------------------------------------------------------------------


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    resolved: AppDep,
) -> list[ConversationRead]:
    app, session = resolved
    convs = await ConversationRepository(session).list_by_app(app.id)
    return [ConversationRead.model_validate(c) for c in convs]


@router.get("/conversations/{conv_id}/messages", response_model=list[ConversationMessageRead])
async def get_conversation_messages(
    conv_id: uuid.UUID,
    resolved: AppDep,
) -> list[ConversationMessageRead]:
    app, session = resolved
    conv_repo = ConversationRepository(session)
    conv = await conv_repo.get(conv_id)
    if conv is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.CONVERSATION_NOT_FOUND,
            detail="대화를 찾을 수 없습니다.",
        )
    if conv.app_id != app.id:
        raise AppError(
            status_code=403,
            code=ErrorCode.CONVERSATION_NOT_OWNED,
            detail="이 대화에 접근할 권한이 없습니다.",
        )
    msgs = await conv_repo.get_messages(conv_id)
    return [ConversationMessageRead.model_validate(m) for m in msgs]


@router.delete(
    "/conversations/{conv_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_conversation(
    conv_id: uuid.UUID,
    resolved: AppDep,
) -> Response:
    app, session = resolved
    conv_repo = ConversationRepository(session)
    conv = await conv_repo.get(conv_id)
    if conv is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.CONVERSATION_NOT_FOUND,
            detail="대화를 찾을 수 없습니다.",
        )
    if conv.app_id != app.id:
        raise AppError(
            status_code=403,
            code=ErrorCode.CONVERSATION_NOT_OWNED,
            detail="이 대화에 접근할 권한이 없습니다.",
        )
    await conv_repo.delete(conv_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
