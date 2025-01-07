from contextlib import AsyncExitStack
from functools import partial
from typing import Any, Optional

from chatlas import Chat
from chatlas._content import ContentToolRequest, ContentToolResult
from chatlas._tools import Tool
from chatlas._turn import Turn
from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPClient:
    def __init__(self, llm: Chat):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm: Chat = llm

    async def register_mcp_server(self, server_url: str):
        """
        Connect to an MCP server.

        Arguments
        ---------
        server_url
            URL for mcp server
        """
        sse_transport = await self.exit_stack.enter_async_context(sse_client(server_url))
        self.sse, self.write = sse_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.sse, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

        self_session = self.session

        def register_mcp_tool(self, mcp_tool):
            async def _call(**args: Any) -> Any:
                # print(f"Client - Calling: {mcp_tool.name}")
                result = await self_session.call_tool(mcp_tool.name, args)
                # print(f"Client - Called: {mcp_tool.name}; Result: {result}")
                return result.content[0].text

            tool = Tool(_call)
            tool.name = mcp_tool.name
            tool.schema = {
                "type": "function",
                "function": {
                    "name": mcp_tool.name,
                    "description": mcp_tool.description,
                    "parameters": mcp_tool.inputSchema,
                },
            }
            self._tools[tool.name] = tool

        self.llm.register_tool = partial(register_mcp_tool, self.llm)

        for tool in tools:
            self.llm.register_tool(tool)

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()
