from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes import classify_intent, agent, tool_node, respond, route_after_agent


def build_graph() -> StateGraph:
    """Build and compile the StayEase LangGraph agent."""
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("classify", classify_intent)
    graph.add_node("agent",    agent)
    graph.add_node("tools",    tool_node)
    graph.add_node("respond",  respond)

    # Edges
    graph.set_entry_point("classify")
    graph.add_edge("classify", "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "respond": "respond"})
    graph.add_edge("tools",   "agent")   # loop: LLM processes tool result, may call another tool
    graph.add_edge("respond", END)

    return graph.compile()


# Compiled singleton — imported by the API
stayease_graph = build_graph()