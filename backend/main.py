"""
main.py
FastAPI application — entry point for the Weather AI Agent backend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
from bedrock_agent import run_agent

app = FastAPI(
    title="Weather AI Agent",
    description="AWS Bedrock-powered weather chatbot with real tool calling",
    version="1.0.0",
)

# Allow the frontend (served from file:// or localhost) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory conversation store keyed by session_id
sessions: dict[str, list[dict]] = {}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ToolCallInfo(BaseModel):
    tool: str
    input: dict[str, Any]
    result: Any
    error: str | None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tool_calls: list[ToolCallInfo]


class ClearResponse(BaseModel):
    message: str
    session_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "Weather AI Agent"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the Weather AI Agent.
    The agent will call weather tools as needed and return a response.
    """
    session_id = request.session_id
    history = sessions.get(session_id, [])

    try:
        result = await run_agent(request.message, history)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(exc)}")

    # Update session history (keep last 20 messages to avoid token limits)
    sessions[session_id] = result["updated_history"][-20:]

    tool_calls = [
        ToolCallInfo(
            tool=tc["tool"],
            input=tc["input"],
            result=tc["result"],
            error=tc["error"],
        )
        for tc in result["tool_calls"]
    ]

    return ChatResponse(
        reply=result["text"],
        session_id=session_id,
        tool_calls=tool_calls,
    )


@app.delete("/chat/{session_id}", response_model=ClearResponse)
async def clear_session(session_id: str):
    """Clear conversation history for a session."""
    sessions.pop(session_id, None)
    return ClearResponse(message="Session cleared", session_id=session_id)


@app.get("/sessions")
async def list_sessions():
    """List active sessions and their message counts."""
    return {
        sid: len(msgs)
        for sid, msgs in sessions.items()
    }
