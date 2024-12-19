from mcp.server.sse import SseServerTransport
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from starlette.applications import Starlette
from starlette.routing import Route

server = Server("example-server")
sse = SseServerTransport("/messages")

def add(args: dict):
    a: int = args['a']
    b: int = args['b']
    return a + b

TOOLS = dict(
    add=add,
)

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="add",
            description="Add two integers together",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {
                        "type": "integer",
                        "description": "An integer",
                    },
                    "b": {
                        "type": "integer",
                        "description": "Another integer",
                    },
                },
                "required": ["a", "b"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can fetch weather data and notify clients of changes.
    """
    if not arguments:
        raise ValueError("Missing arguments")
    
    if name not in TOOLS:
        raise ValueError("Tool name not found")
    
    print(f"Calling {name} with args: {arguments}")
    result = TOOLS[name](arguments)
    print(f"Result: {result}")
    return [
        types.TextContent(
            type="text",
            text=str(result)
        )
    ]

# Needed to allow starlette to process handlers
def setup_handler(f):
    async def h(req):
        return f
    return h

async def handle_sse(scope, receive, send):
    async with sse.connect_sse(scope, receive, send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())

async def handle_messages(scope, receive, send):
    await sse.handle_post_message(scope, receive, send)

# TODO: add basic auth

app = Starlette(
    routes=[
        Route("/sse", endpoint=setup_handler(handle_sse)),
        Route("/messages", endpoint=setup_handler(handle_messages), methods=["POST"]),
    ]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8081)