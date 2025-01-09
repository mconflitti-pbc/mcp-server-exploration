import asyncio

from chatlas import ChatBedrockAnthropic

from openapi_mcp.client import MCPClient


async def main():
    llm = ChatBedrockAnthropic(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        aws_region="us-east-1",
    )
    mcp_client = MCPClient(llm)
    await mcp_client.register_mcp_server("http://127.0.01:8082/sse")

    if True:
        mcp_client.llm.app(bg_thread=True)

        await asyncio.sleep(1000)
    else:
        # await mcp_client.chat_async("What is the current Connect host version?")
        await mcp_client.chat_async("Get the current user's id.")
        # await mcp_client.chat_async("Now get me the first 3 content items owned by that user id.")

        # Works! Just commenting for now
        # await mcp_client.chat_async("Update that user's first name to `Testing`")

        mcp_client.llm.export(
            "output.md", overwrite=True, include="all", include_system_prompt=True
        )

        await mcp_client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
