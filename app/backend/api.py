from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.graph import stayease_graph
from app.agent.state import AgentState
from app.config.database import engine, Base
from app.config.deps import get_db
from app.config.models import Conversation


# ── Lifespan: create tables on startup ──────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="StayEase API", version="2.0.0", lifespan=lifespan)


# ── Schemas ──────────────────────────────────────────────────────────────────

class MessageRequest(BaseModel):
    message: str


class MessageResponse(BaseModel):
    conversation_id: str
    reply:           str
    intent:          str
    tool_result:     Any = None


class HistoryResponse(BaseModel):
    conversation_id: str
    messages:        list[dict]


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _load_history(conversation_id: str, db: AsyncSession) -> list:
    """Load prior turns from DB and convert to LangChain message objects."""
    stmt = (
        select(Conversation)
        .where(Conversation.conversation_id == conversation_id)
        .order_by(Conversation.created_at)
    )
    rows = (await db.execute(stmt)).scalars().all()

    messages = []
    for row in rows:
        if row.role == "user":
            messages.append(HumanMessage(content=row.content))
        else:
            messages.append(AIMessage(content=row.content))
    return messages


async def _save_turn(
    conversation_id: str,
    user_msg: str,
    assistant_msg: str,
    intent: str,
    db: AsyncSession,
) -> None:
    """Persist both the user and assistant turns to the conversations table."""
    now = datetime.now(timezone.utc)
    db.add(Conversation(conversation_id=conversation_id, role="user",      content=user_msg,      intent=intent, created_at=now))
    db.add(Conversation(conversation_id=conversation_id, role="assistant", content=assistant_msg, intent=intent, created_at=now))
    await db.commit()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post(
    "/api/chat/{conversation_id}/message",
    response_model=MessageResponse,
    summary="Send a guest message",
)
async def send_message(
    conversation_id: str,
    body: MessageRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Accepts a guest message, runs the LangGraph agent, persists both turns
    to PostgreSQL, and returns the assistant reply with structured tool output.
    """
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Restore history from DB
    history = await _load_history(conversation_id, db)
    history.append(HumanMessage(content=body.message))

    initial_state: AgentState = {
        "messages":         history,
        "intent":           "",
        "tool_result":      None,
        "conversation_id":  conversation_id,
        "booking_confirmed": False,
    }

    result: AgentState = stayease_graph.invoke(initial_state)

    # Extract final reply text
    last_msg  = result["messages"][-1]
    reply_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # Persist to DB
    await _save_turn(conversation_id, body.message, reply_text, result.get("intent", ""), db)

    return MessageResponse(
        conversation_id=conversation_id,
        reply=reply_text,
        intent=result.get("intent", ""),
        tool_result=result.get("tool_result"),
    )


@app.get(
    "/api/chat/{conversation_id}/history",
    response_model=HistoryResponse,
    summary="Get conversation history",
)
async def get_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    """Return all persisted messages for a conversation from PostgreSQL."""
    stmt = (
        select(Conversation)
        .where(Conversation.conversation_id == conversation_id)
        .order_by(Conversation.created_at)
    )
    rows = (await db.execute(stmt)).scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return HistoryResponse(
        conversation_id=conversation_id,
        messages=[
            {
                "role":      row.role,
                "content":   row.content,
                "intent":    row.intent,
                "timestamp": row.created_at.isoformat(),
            }
            for row in rows
        ],
    )


@app.get("/health", summary="Health check")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    """Ping both the app and the database."""
    try:
        await db.execute(select(1))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"
    return {"status": "ok", "database": db_status}