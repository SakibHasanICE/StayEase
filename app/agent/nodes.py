import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from langgraph.prebuilt import ToolNode

from app.agent.state import AgentState
from app.agent.tools import TOOLS
from app.config.settings import settings

# ── LLM ─────────────────────────────────────────────────────────────────────

_llm = ChatGroq(model=settings.model_name, api_key=settings.groq_api_key, temperature=0)
llm_with_tools = _llm.bind_tools(TOOLS)

SYSTEM_PROMPT = SystemMessage(content="""
You are the StayEase booking assistant for Bangladesh. You handle exactly three tasks:
1. Search available properties — need location, check-in date, check-out date, guest count
2. Get listing details    — need a listing ID
3. Create a booking       — need listing ID, guest full name, phone, check-in, check-out, guest count

For anything else, tell the guest you will escalate to a human agent.
Always reply in the same language the guest uses. All prices are in BDT (৳).
""")

# ── Nodes ────────────────────────────────────────────────────────────────────

def classify_intent(state: AgentState) -> AgentState:
    """
    Keyword-match the latest user message to set intent.
    Updates: intent | Next: agent
    """
    text = state["messages"][-1].content.lower()

    if any(w in text for w in ["search", "find", "available", "room", "place", "need", "looking"]):
        intent = "search"
    elif any(w in text for w in ["detail", "about", "tell me", "more info", "describe", "info"]):
        intent = "details"
    elif any(w in text for w in ["book", "reserve", "confirm", "want to stay", "i'll take"]):
        intent = "book"
    else:
        intent = "escalate"

    return {**state, "intent": intent}


def agent(state: AgentState) -> AgentState:
    """
    Send full conversation to the Groq LLM with tools bound.
    LLM either calls a tool or returns a direct reply.
    Updates: messages | Next: tools or respond
    """
    response: AIMessage = llm_with_tools.invoke([SYSTEM_PROMPT, *state["messages"]])
    return {**state, "messages": [response]}


# Prebuilt node — automatically runs whichever tool the LLM called
tool_node = ToolNode(TOOLS)


def respond(state: AgentState) -> AgentState:
    """
    Finalize state. Extract tool_result and flag confirmed bookings.
    Updates: tool_result, booking_confirmed | Next: END
    """
    tool_result      = state.get("tool_result")
    booking_confirmed = state.get("booking_confirmed", False)

    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            try:
                tool_result = json.loads(msg.content)
                if isinstance(tool_result, dict) and "booking_id" in tool_result:
                    booking_confirmed = True
            except (json.JSONDecodeError, TypeError):
                tool_result = msg.content
            break

    return {**state, "tool_result": tool_result, "booking_confirmed": booking_confirmed}


# ── Router ───────────────────────────────────────────────────────────────────

def route_after_agent(state: AgentState) -> str:
    """Go to 'tools' if LLM issued a tool call, otherwise 'respond'."""
    last = state["messages"][-1]
    return "tools" if isinstance(last, AIMessage) and last.tool_calls else "respond"