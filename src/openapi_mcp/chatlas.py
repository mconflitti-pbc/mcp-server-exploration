from typing import Any, Callable

import chatlas
import mcp.types as mcp_types
from typing_extensions import TYPE_CHECKING

from openapi_mcp.connect_api import (
    make_request,
    map_arguments_to_api_params,
    map_operations_to_tools,
)
from openapi_mcp.swagger import (
    OperationDef,
)

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionToolParam


class RawChatlasTool(chatlas.Tool):
    # TODO-chatlas: Add this method to the chatlas.Chat class
    @staticmethod
    def reset_tools(chat: chatlas.Chat):
        chat._tools = {}
        return

    # TODO-chatlas: Add this method to the chatlas.Chat class
    @staticmethod
    def register_tool(chat: chatlas.Chat, tool: "RawChatlasTool"):
        chat._tools[tool.name] = tool
        return

    def __init__(
        self, *, name: str, fn: Callable, description: str, input_schema: Any, model=None
    ):
        super().__init__(fn, model=model)

        self._chatlas_tool = chatlas.Tool(fn)

        # Now override the name, description, and input_schema
        self.name = name
        self.description = description
        self.schema: ChatCompletionToolParam = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": input_schema,
            },
        }


class SwaggerTool(RawChatlasTool):
    def __init__(self, *, base_url: str, operation: OperationDef):
        operation_name = operation["name"]

        operation_description = operation["definition"]["description"]
        tool = map_operations_to_tools({operation_name: operation})[0]
        operation_input_schema = tool.inputSchema

        async def call_api(**kwargs: Any):
            # print("\n\nCalling tool", self.name, "with args:", kwargs)
            api_params = map_arguments_to_api_params(
                kwargs,
                operation["definition"].get("parameters", []),
            )
            result = await make_request(base_url, operation, api_params)
            return [mcp_types.TextContent(text=result, type="text")]

        super().__init__(
            name=operation_name,
            fn=call_api,
            description=operation_description,
            input_schema=operation_input_schema,
        )

        # RawChatlasTool class variables
        self._operation = operation
