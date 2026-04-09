from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., Any]


class MCPToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        fn: Callable[..., Any],
    ) -> None:
        self._tools[name] = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            fn=fn,
        )

    def discover_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def invoke(self, name: str, payload: dict[str, Any]) -> Any:
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in MCP registry")

        tool = self._tools[name]
        required = tool.input_schema.get("required", [])
        missing = [k for k in required if k not in payload]
        if missing:
            raise ValueError(f"Missing required fields for {name}: {missing}")

        return tool.fn(**payload)
