"""API entry point for the read-only Gemini business assistant."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.agents.business_agent import (
    MAX_MESSAGE_LENGTH,
    AgentConfigurationError,
    AgentLoopLimitError,
    AgentToolError,
    AgentUpstreamError,
    AgentValidationError,
    run_business_agent,
)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class AssistantQuery(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be empty")
        return value


@router.post("/query")
def assistant_query(request: AssistantQuery):
    try:
        return run_business_agent(request.message)
    except AgentConfigurationError as exc:
        raise HTTPException(status_code=503, detail="AI assistant is not configured") from exc
    except AgentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (AgentUpstreamError, AgentLoopLimitError, AgentToolError) as exc:
        raise HTTPException(status_code=502, detail="AI assistant could not complete the request") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unexpected assistant service error") from exc

