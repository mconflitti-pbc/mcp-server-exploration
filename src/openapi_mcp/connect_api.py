import os
import urllib.parse

import httpx
import mcp.types as types
import yaml
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route

from mcp_servers.helpers.swagger import (
    OperationDef,
    expand_swagger,
    transform_swagger_to_operation_dict,
)

SupportedOperations = dict[str, OperationDef]

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


def map_swagger_params_to_input_schema(params):
    schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    for param in params:
        if param["in"] == "body":
            schema["properties"][param["name"]] = {
                "description": param["description"],
                **param["schema"],
            }
        else:
            if "schema" in param and "type" in param["schema"]:
                # OpenAPI v3
                param_type = param["schema"]["type"]
            elif "type" in param:
                # OpenAPI v2
                param_type = param["type"]
            else:
                param_type = "string"

            if "description" in param:
                param_description = param["description"]
            else:
                param_description = "(No description provided)"
            schema["properties"][param["name"]] = {
                "type": param_type,
                "description": param_description,
            }
        if "required" in param and param["required"]:
            schema["required"].append(param["name"])
    return schema


def map_operations_to_tools(operations: SupportedOperations):
    return [
        types.Tool(
            name=operation["name"],
            description=operation["definition"][
                "description"
            ],  # + f" Possible responses: {operation['definition']['responses']}",
            inputSchema=map_swagger_params_to_input_schema(
                operation["definition"].get("parameters", [])
            ),
        )
        for operation in operations.values()
    ]


def map_arguments_to_api_params(arguments, swagger_params):
    """
    Maps arguments to API parameters.

    Example arguments:
    ```
    {
        "name": "guid",
        "in": "path",
        "type": "string",
        "required": true,
        "description": "The unique identifier of the desired content item."
    },
    {
        "name": "location",
        "in": "body",
        ...
    },
    {
        "name": "date",
        "in": "query",
        ...
    },
    ```
    """
    api_params = {
        "path": [],
        "query": [],
        "body": [],
    }

    if arguments is None:
        return api_params

    swagger_params = {param["name"]: param for param in swagger_params}

    for arg_name, arg_value in arguments.items():
        if arg_name in swagger_params and len(arg_value) > 0:
            param = swagger_params[arg_name]
            api_params[param["in"]].append(
                {
                    "name": arg_name,
                    "value": arg_value,
                }
            )

    return api_params


def map_path_params(route, path_params):
    """
    Maps path parameters to the route.

    Args:
        route: The route with placeholders for path parameters.
        path_params: A list of path parameters with 'name' and 'value' fields.

    Returns
    -------
    :
        The route with path parameters replaced.
    """
    for param in path_params:
        route = route.replace(f"{{{param['name']}}}", str(param["value"]))
    return route


def map_query_params(query_params):
    """
    Maps query parameters to a dictionary.

    Args:
        query_params: A list of query parameters with 'name' and 'value' fields.

    Returns
    -------
    :
        A dictionary of query parameters.
    """
    return {param["name"]: param["value"] for param in query_params}


def map_body_params(body_params):
    """
    Maps body parameters to a dictionary.

    Args:
        body_params: A list of body parameters with 'name' and 'value' fields.

    Returns
    -------
    :
        A dictionary of body parameters.
    """
    body = {}
    for param in body_params:
        body = body | param["value"]
    return body


async def make_request(operation, api_params):
    """
    Makes an HTTP request using httpx with the given operation and parameters.

    Args:
        operation: A dictionary containing the HTTP method and route.
        api_params: A dictionary containing path, query, and body parameters.

    Returns
    -------
    :
        The response text.
    """
    # Map path, query, and body parameters
    route = map_path_params(operation["route"], api_params["path"])
    query_params = map_query_params(api_params["query"])
    body_params = map_body_params(api_params["body"])

    # Construct the full URL
    base_url = urllib.parse.urljoin(CONNECT_SERVER, "__api__")

    # print(base_url, route)
    # print(query_params)
    # print(body_params)

    # Make the request
    async with httpx.AsyncClient(verify=False, base_url=base_url) as client:
        response = await client.request(
            method=operation["method"],
            url=route,
            headers={"Authorization": f"Key {CONNECT_API_KEY}"},
            params=query_params,
            json=body_params,
        )
        return response.text


async def handle_operation(operations: SupportedOperations, name: str, arguments: dict | None):
    """
    Handle tool execution requests.

    Arguments
    ---------
    operations
        A dictionary of supported operations.
    name
        The name of the operation to execute.
    arguments
        The arguments to pass to the operation.

    Returns
    -------
    :
        A list containing a single text content object.
    """
    if name not in operations:
        return [
            types.TextContent(
                text=f"Operation '{name}' is not supported.",
                contentType="text/plain",
            )
        ]

    print(f"Calling {name} with args: {arguments}")
    operation = operations[name]
    api_params = map_arguments_to_api_params(
        arguments,
        operation["definition"].get("parameters", []),
    )

    result = await make_request(operation, api_params)
    print("Received Result")
    # print("Received Result: {result}")
    return [types.TextContent(text=result, contentType="text/plain")]


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
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.

    Returns
    -------
        A list containing a single text content object.
    """
    return await handle_operation(SUPPORTED_OPERATIONS, name, arguments)


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
