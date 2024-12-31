import asyncio
from contextlib import AsyncExitStack
from functools import partial
from typing import Optional

from chatlas import Chat, ChatBedrockAnthropic
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

        def register_mcp_tool(self, mcp_tool):
            def x():
                pass

            tool = Tool(x)
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

    async def chat_async(self, prompt):
        def mcp_tool_func(name: str):
            async def _call(**args):
                result = await self.session.call_tool(name, args)
                print(f"Called: {name}; Result: {result}")
                return result.content[0].text

            return _call

        async def _invoke_mcp_tools_async(self) -> Turn | None:
            turn = self.get_last_turn()
            if turn is None:
                return None

            results: list[ContentToolResult] = []
            for x in turn.contents:
                if isinstance(x, ContentToolRequest):
                    results.append(
                        await self._invoke_tool_async(mcp_tool_func(x.name), x.arguments, x.id)
                    )

            if not results:
                return None

            return Turn("user", results)

        self.llm._invoke_tools_async = partial(_invoke_mcp_tools_async, self.llm)
        await self.llm.chat_async(prompt, echo="text")

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    llm = ChatBedrockAnthropic(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0", aws_region="us-east-1"
    )
    mcp_client = MCPClient(llm)
    await mcp_client.register_mcp_server("http://127.0.01:8082/sse")

    # await mcp_client.chat_async("What is the current Connect host version?")
    await mcp_client.chat_async("Get the current user's id.")
    # await mcp_client.chat_async("Now get me the first 3 content items owned by that user id.")

    # Works! Just commenting for now
    # await mcp_client.chat_async("Update that user's first name to `Testing`")

    mcp_client.llm.export("output.md", overwrite=True, include="all", include_system_prompt=True)

    await mcp_client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
