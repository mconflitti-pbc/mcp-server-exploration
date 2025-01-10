import os
from typing import TYPE_CHECKING, Sequence

import mcp.types as types
import yaml
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route

from .map import handle_operation, map_operations_to_tools
from .swagger import (
    expand_swagger,
    transform_swagger_to_operation_dict,
)

if TYPE_CHECKING:
    from .map import SupportedOperations  # noqa: TC004


CONNECT_SERVER = os.environ.get("CONNECT_SERVER", "http://localhost:3939")
CONNECT_API_KEY = os.environ.get("CONNECT_API_KEY", "")
SWAGGER_FILE = os.environ.get("SWAGGER_FILE") or "swagger.yaml"

if not os.path.exists(SWAGGER_FILE):
    raise FileNotFoundError(
        f"Swagger file not found at `{SWAGGER_FILE}`. "
        "Please specify the path to the file using the SWAGGER_FILE= environment variable."
    )

server = Server("connect-api-server")
sse = SseServerTransport("/messages")


with open(SWAGGER_FILE, "r", encoding="utf-8") as file:
    document = yaml.safe_load(file)

document = expand_swagger(document)
operations = transform_swagger_to_operation_dict(document)


SUPPORTED_OPERATIONS: SupportedOperations = {
    # "listHosts": operations["listHosts"],
    "getCurrentUser": operations["getCurrentUser"],
    "updateUser": operations["updateUser"],
    "getContents": operations["getContents"],
}


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.

    Each tool specifies its arguments using JSON Schema validation.

    Returns
    -------
    :
        A list of tool objects.
    """
    return map_operations_to_tools(SUPPORTED_OPERATIONS)


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.

    Returns
    -------
        A list containing a single text content object.
    """
    return await handle_operation(
        SUPPORTED_OPERATIONS,
        name,
        arguments,
        CONNECT_SERVER=CONNECT_SERVER,
        CONNECT_API_KEY=CONNECT_API_KEY,
    )


# Needed to allow starlette to process handlers
def setup_handler(f):
    async def h(_req):
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

    uvicorn.run(app, host="127.0.0.1", port=8082)
