from contextlib import AsyncExitStack
from typing import Any, Optional

import chatlas
from chatlas import Chat
from mcp import ClientSession
from mcp.client.sse import sse_client

from openapi_mcp.chatlas import RawChatlasTool


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
        assert isinstance(self.session, ClientSession)

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

        self_session = self.session

        def register_mcp_tool(chat: chatlas.Chat, mcp_tool):
            async def _call(**args: Any) -> Any:
                # print(f"Client - Calling: {mcp_tool.name}")
                result = await self_session.call_tool(mcp_tool.name, args)
                # print(f"Client - Called: {mcp_tool.name}; Result: {result}")
                if result.content[0].type == "text":
                    return result.content[0].text
                else:
                    raise RuntimeError(f"Unexpected content type: {result.content[0].type}")

            tool = RawChatlasTool(
                name=mcp_tool.name,
                fn=_call,
                description=mcp_tool.description,
                input_schema=mcp_tool.inputSchema,
            )
            RawChatlasTool.register_tool(chat, tool)

        for tool in tools:
            register_mcp_tool(self.llm, tool)

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()
