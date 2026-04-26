from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   
    intent: str                                
    tool_result: Any                           
    conversation_id: str                       
    booking_confirmed: bool                    