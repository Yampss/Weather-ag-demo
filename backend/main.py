import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Any
from bedrock_agent import run_agent

app = FastAPI(
    title="Weather AI Agent",
    description="AWS Bedrock + LangChain weather chatbot with tool calling",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, list[dict]] = {}

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


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


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Weather AI Agent"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id
    history = sessions.get(session_id, [])

    try:
        result = await run_agent(request.message, history)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(exc)}")

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
    sessions.pop(session_id, None)
    return ClearResponse(message="Session cleared", session_id=session_id)


@app.get("/sessions")
async def list_sessions():
    return {sid: len(msgs) for sid, msgs in sessions.items()}


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
