from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages:         Annotated[list, add_messages]  # Full conversation; auto-merged by LangGraph
    intent:           str                             # search | details | book | escalate
    tool_result:      Any                             # Parsed tool output returned to the API client
    conversation_id:  str                             # Ties state to a DB conversation record
    booking_confirmed: bool                           # Idempotency guard against duplicate bookings