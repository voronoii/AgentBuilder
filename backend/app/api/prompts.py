from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AppError, ErrorCode
from app.repositories.settings import SettingsRepository
from app.services.providers.chat.registry import make_chat_model

router = APIRouter(prefix="/prompts", tags=["prompts"])


# Fallback chain when neither request override nor DB settings are present.
_DEFAULT_PROVIDER = "openrouter"
_DEFAULT_MODEL = "openai/gpt-5.2"

_SETTING_PROVIDER_KEY = "INSTRUCTION_GENERATOR_PROVIDER"
_SETTING_MODEL_KEY = "INSTRUCTION_GENERATOR_MODEL"


# Allowed enum values. The frontend keeps these in sync.
_TONE_VALUES = {"friendly", "professional", "concise", "detailed"}
_TOOL_POLICY_VALUES = {"when_needed", "aggressive", "never"}
_UNKNOWN_HANDLING_VALUES = {"say_dont_know", "ask", "best_effort"}


class AgentInstructionGenerateRequest(BaseModel):
    goal: str = Field(min_length=5, max_length=4000)
    provider: str | None = Field(
        default=None,
        description="선택. 지정하지 않으면 INSTRUCTION_GENERATOR_PROVIDER 또는 내장 디폴트 사용.",
    )
    model: str | None = Field(
        default=None,
        description="선택. 지정하지 않으면 INSTRUCTION_GENERATOR_MODEL 또는 내장 디폴트 사용.",
    )
    tone: str = "friendly"
    tool_policy: str = "when_needed"
    unknown_handling: str = "say_dont_know"
    output_language: str = "ko"
    knowledge_bases: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class AgentInstructionGenerateResponse(BaseModel):
    instruction: str
    used_provider: str
    used_model: str


def _format_list(values: list[str]) -> str:
    cleaned = [value.strip() for value in values if value.strip()]
    if not cleaned:
        return "(none)"
    return "\n".join(f"- {value}" for value in cleaned)


def _normalize_enum(value: str, allowed: set[str], default: str) -> str:
    """Coerce unknown enum values to the default to keep meta-prompt deterministic."""
    return value if value in allowed else default


def _build_system_message(
    *,
    has_knowledge_bases: bool,
    has_tools: bool,
    output_language: str,
) -> str:
    """Compose the system message. Meta-prompt is in English for LLM stability,
    but the generated output is forced into Korean (or the requested language).
    """
    knowledge_section_clause = (
        '- ## 지식 및 도구 사용 — REQUIRED. List concrete rules for using the connected '
        "knowledge bases and/or MCP tools."
        if (has_knowledge_bases or has_tools)
        else "- ## 지식 및 도구 사용 — OMIT this section entirely. Do not output the header. "
        "The agent has no knowledge bases or tools connected."
    )

    return f"""You are an expert prompt engineer for AI agent workflow builders.
Your task is to convert a non-technical user's natural-language goal into a
production-ready system instruction for a single ReAct-style Agent node.

================================================================
OUTPUT REQUIREMENTS
================================================================
1. Output language: write the instruction in the language requested by
   `output_language` (default: Korean / `ko`). Do NOT use any other language
   in the body.
2. Output ONLY the final system instruction. No preface, no explanation, no
   meta-comments. Do not say things like "Here is the system prompt".
3. Use the EXACT section headers below, in this order. Do not rename, translate
   differently, or reorder them.

================================================================
OUTPUT STRUCTURE (Korean headers, in this exact order)
================================================================
- ## 역할        — REQUIRED. Define who the agent is and its scope of expertise.
- ## 목표        — REQUIRED. State what the agent must accomplish for the user.
{knowledge_section_clause}
- ## 운영 규칙   — REQUIRED. Concrete behavioral rules (numbered list preferred).
- ## 응답 스타일 — REQUIRED. Tone, formatting, length guidance.
- ## 제약 사항   — REQUIRED. Hard limits and safety defaults (see SAFETY DEFAULTS below).

================================================================
OPTION MAPPINGS (apply exactly — do NOT reinterpret)
================================================================
tone:
  friendly      → 사용자에게 따뜻하고 공감적이며 친근한 어조로 답변하도록 지시한다.
  professional  → 격식 있고 정확한 비즈니스 톤을 유지하도록 지시한다.
  concise       → 불필요한 수식 없이 핵심만 짧게 전달하도록 지시한다.
  detailed      → 배경과 맥락을 충분히 설명하며 상세하게 답변하도록 지시한다.

tool_policy:
  when_needed   → 도구는 답변에 필요할 때만 선택적으로 호출하도록 지시한다.
  aggressive    → 근거가 필요한 모든 답변에서 도구를 우선 사용하도록 지시한다.
  never         → 도구를 호출하지 말고 모델 지식만으로 답변하도록 지시한다.

unknown_handling:
  say_dont_know → 확실하지 않은 정보는 추측하지 말고 "확인되지 않습니다" 또는
                  "잘 모르겠습니다"라고 명시적으로 알리도록 지시한다.
  ask           → 정보가 부족하거나 모호하면 사용자에게 추가 질문을 하여
                  명확히 한 후 답변하도록 지시한다.
  best_effort   → 확인된 부분만 답하고, 어디까지가 확신이며 어디부터가
                  불확실한 영역인지 응답에 명시하도록 지시한다.

================================================================
CONTEXT-DRIVEN BEHAVIOR
================================================================
- If knowledge bases are listed: include guidance on when to search them,
  how to ground answers in retrieved content, and how to behave when the
  search returns nothing relevant. Refer to them generically as
  "연결된 지식베이스" — do NOT invent specific KB names beyond those provided.
- If MCP tools are listed: include guidance on when to call them, how to
  validate results, and how to combine results with the agent's own reasoning.
  Refer to them generically as "사용 가능한 도구" — do NOT invent specific tool
  names beyond those provided.
- Do NOT invent API names, endpoint URLs, database names, or schemas that
  were not provided in the input.

================================================================
SAFETY DEFAULTS (always include inside "## 제약 사항")
================================================================
- 역할 범위를 벗어난 요청이나 명시되지 않은 도메인 외 질문에는 정중히 거절하거나
  본 역할로 다시 안내한다.
- 개인정보, 인증 정보, 보안 키 등 민감 정보를 노출하거나 출력에 포함하지 않는다.
- 허위 정보를 사실처럼 단정하지 않는다.

================================================================
QUALITY BAR
================================================================
- Every sentence must give the agent a concrete behavior, decision rule, or
  constraint. No empty filler.
- Typical instruction length: 200-600 words.
- The instruction must be directly pasteable into an Agent node's system
  prompt without further editing.

Begin generating the final system instruction now. Output the instruction
ONLY (no preface), in {output_language}.
"""


def _build_human_message(request: AgentInstructionGenerateRequest) -> str:
    tone = _normalize_enum(request.tone, _TONE_VALUES, "friendly")
    tool_policy = _normalize_enum(
        request.tool_policy, _TOOL_POLICY_VALUES, "when_needed"
    )
    unknown_handling = _normalize_enum(
        request.unknown_handling, _UNKNOWN_HANDLING_VALUES, "say_dont_know"
    )

    return f"""User goal (natural language):
{request.goal}

Generation context:
- output_language: {request.output_language}
- tone: {tone}
- tool_policy: {tool_policy}
- unknown_handling: {unknown_handling}

Connected knowledge bases ({len(request.knowledge_bases)}):
{_format_list(request.knowledge_bases)}

Connected MCP tools ({len(request.tools)}):
{_format_list(request.tools)}

Generate the final system instruction now.
"""


def _build_messages(
    request: AgentInstructionGenerateRequest,
) -> list[SystemMessage | HumanMessage]:
    system = _build_system_message(
        has_knowledge_bases=any(s.strip() for s in request.knowledge_bases),
        has_tools=any(s.strip() for s in request.tools),
        output_language=request.output_language,
    )
    human = _build_human_message(request)
    return [SystemMessage(content=system), HumanMessage(content=human)]


async def _resolve_generator_model(
    request: AgentInstructionGenerateRequest,
    session: AsyncSession,
) -> tuple[str, str]:
    """Resolve the provider/model to use for instruction generation.

    Resolution order:
    1. Request override (both provider AND model must be present).
    2. DB settings (INSTRUCTION_GENERATOR_PROVIDER + INSTRUCTION_GENERATOR_MODEL).
    3. Hard-coded default (openrouter + openai/gpt-5.2).
    """
    if request.provider and request.model:
        return request.provider, request.model

    repo = SettingsRepository(session)
    provider = await repo.get_value(_SETTING_PROVIDER_KEY)
    model = await repo.get_value(_SETTING_MODEL_KEY)
    if provider and model:
        return provider, model
    return _DEFAULT_PROVIDER, _DEFAULT_MODEL


@router.post("/agent-instruction/generate", response_model=AgentInstructionGenerateResponse)
async def generate_agent_instruction(
    request: AgentInstructionGenerateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AgentInstructionGenerateResponse:
    """Generate an Agent node instruction from a user's natural-language goal."""
    used_provider, used_model = await _resolve_generator_model(request, session)

    chat_model = await make_chat_model(
        used_provider,
        used_model,
        session,
        temperature=0.2,
        streaming=False,
    )
    result = await chat_model.ainvoke(_build_messages(request))
    content = result.content
    if isinstance(content, list):
        instruction = "\n".join(
            str(part.get("text", part)) if isinstance(part, dict) else str(part)
            for part in content
        ).strip()
    else:
        instruction = str(content).strip()

    if not instruction:
        raise AppError(
            status_code=502,
            code=ErrorCode.INTERNAL_UNEXPECTED,
            detail="지시문 생성 결과가 비어 있습니다. 다른 모델로 다시 시도해주세요.",
        )

    return AgentInstructionGenerateResponse(
        instruction=instruction,
        used_provider=used_provider,
        used_model=used_model,
    )
