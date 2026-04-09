from __future__ import annotations

from functools import partial

from langgraph.graph import END, StateGraph

from app.agents import (
    WorkflowState,
    character_designer_node,
    hitl_node,
    image_synthesis_node,
    memory_commit_node,
    mode_selector_node,
    script_validator_node,
    scriptwriter_node,
)
from app.mcp_registry import MCPToolRegistry


def _route_after_mode(state: WorkflowState) -> str:
    mode = state.get("mode")
    if mode == "manual":
        return "validator"
    return "scriptwriter"


def _route_after_hitl(state: WorkflowState) -> str:
    if state.get("needs_approval"):
        return END
    return "character"


def _route_if_error(state: WorkflowState) -> str:
    if state.get("status") == "error":
        return END
    return "hitl"


def build_workflow(registry: MCPToolRegistry):
    g = StateGraph(WorkflowState)

    g.add_node("mode_selector", mode_selector_node)
    g.add_node("validator", partial(script_validator_node, registry=registry))
    g.add_node("scriptwriter", partial(scriptwriter_node, registry=registry))
    g.add_node("hitl", hitl_node)
    g.add_node("character", partial(character_designer_node, registry=registry))
    g.add_node("image", partial(image_synthesis_node, registry=registry))
    g.add_node("memory", partial(memory_commit_node, registry=registry))

    g.set_entry_point("mode_selector")

    g.add_conditional_edges("mode_selector", _route_after_mode)
    g.add_conditional_edges("validator", _route_if_error)
    g.add_conditional_edges("scriptwriter", _route_if_error)
    g.add_conditional_edges("hitl", _route_after_hitl)

    g.add_edge("character", "image")
    g.add_edge("image", "memory")
    g.add_edge("memory", END)

    return g.compile()
