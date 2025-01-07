# ------------------------------------------------------------------------------------
# A basic Shiny Chat powered by Anthropic's Claude model with Bedrock.
# To run it, you'll need an AWS Bedrock configuration.
# To get started, follow the instructions at https://aws.amazon.com/bedrock/claude/
# as well as https://github.com/anthropics/anthropic-sdk-python#aws-bedrock
# ------------------------------------------------------------------------------------
import os
from typing import Any

import chatlas
import htmltools
import mcp.types as mcp_types
import requests
from typing_extensions import TYPE_CHECKING

# import anthropic
# from anthropic import AnthropicBedrock
from mcp_servers.helpers.swagger import (
    OperationDef,
    expand_swagger,
    transform_swagger_to_operation_dict,
)
from openapi_mcp.connect_api import (
    handle_operation,
    make_request,
    map_arguments_to_api_params,
    map_operations_to_tools,
)
from shiny import reactive, req
from shiny import ui as core_ui
from shiny.express import input, render, ui

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionToolParam
STREAM_CHAT = True


aws_model = os.getenv("AWS_MODEL", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
aws_region = os.getenv("AWS_REGION", "us-east-1")
chat = chatlas.ChatBedrockAnthropic(model=aws_model, aws_region=aws_region)

# Set some Shiny page options
ui.page_opts(
    title="Hello Anthropic Claude Chat",
    fillable=True,
    fillable_mobile=True,
)

chat_ui = ui.Chat(id="chat")


@chat_ui.on_user_submit
async def _():
    user_input = chat_ui.user_input()

    print("Tools:", chat._tools)
    print("STREAM_CHAT:", STREAM_CHAT)

    if user_input is None:
        return
    if STREAM_CHAT:
        await chat_ui.append_message_stream(await chat.stream_async(user_input, echo="all"))
    else:
        await chat_ui.append_message(str(chat.chat(user_input)))


# llm = anthropic.AnthropicBedrock(
#     # aws_secret_key=os.getenv("AWS_SECRET_KEY"),
#     # aws_access_key=os.getenv("AWS_ACCESS_KEY"),
#     aws_region=aws_region,
#     # aws_account_id=os.getenv("AWS_ACCOUNT_ID"),
# )

# def make_func(operation) -> Callable:

#     class SimpleObject:
#         ...
#     class ComplicatedObject:
#         inner: SimpleObject
#         ...


#     def ret_fn(...) -> ComplicatedObject:
#         handle_operation(SUPPORTED_OPERATIONS, name, arguments)

#     ret_fn.__doc__ = operation["description"]
#     return {fn: ret_fn, classes: [SimpleObject, ComplicatedObject]}


# @chat_ui.on_user_submit
# async def _():
#     # Get messages currently in the chat
#     messages = chat_ui.messages(format="anthropic")
#     # Create a response message stream
#     # print("anthropic_tools()", anthropic_tools())
#     response = llm.messages.create(
#         model=aws_model,
#         messages=messages,
#         stream=STREAM_CHAT,
#         max_tokens=1000,
#         tools=anthropic_tools(),
#     )

#     llm.messages.

#     if STREAM_CHAT:
#         # Append the response stream into the chat
#         await chat_ui.append_message_stream(response)
#     else:
#         # Append the response as a single message
#         await chat_ui.append_message(response)


# class ToolParam(TypedDict, total=False):
#     input_schema: Required[InputSchema]
#     """[JSON schema](https://json-schema.org/) for this tool's input.

#     This defines the shape of the `input` that your tool accepts and that the model
#     will produce.
#     """

#     name: Required[str]
#     """Name of the tool.

#     This is how the tool will be called by the model and in tool_use blocks.
#     """

#     cache_control: Optional[CacheControlEphemeralParam]

#     description: str
#     """Description of what this tool does.

#     Tool descriptions should be as detailed as possible. The more information that
#     the model has about what the tool is and how to use it, the better it will
#     perform. You can use natural language descriptions to reinforce important
#     aspects of the tool input JSON schema.
#     """


@reactive.calc
def anthropic_tools():
    return [
        {
            "input_schema": tool.inputSchema,
            "name": tool.name,
            "description": tool.description,
        }
        for tool in openapi_tools()
    ]


class RawChatlasTool(chatlas.Tool):
    @staticmethod
    def reset_tools(chat: chatlas.Chat):
        chat._tools = {}
        return

    @staticmethod
    def register_tool(chat: chatlas.Chat, tool: "RawChatlasTool"):
        chat._tools[tool.name] = tool
        return

    def __init__(self, *, base_url: str, operation: OperationDef):
        operation_name = operation["name"]

        operation_description = operation["definition"]["description"]
        tool = map_operations_to_tools({operation_name: operation})[0]
        operation_input_schema = tool.inputSchema

        async def call_api(**kwargs: Any):
            print("\n\nCalling tool", self.name, "with args:", kwargs)
            # handle_operation({self.name: }, self.name, kwargs)

            # print(f"Calling {name} with args: {arguments}")
            # operation = operations[name]
            api_params = map_arguments_to_api_params(
                kwargs,
                operation["definition"].get("parameters", []),
            )

            print("Calling operation: ", operation, api_params)
            result = await make_request(base_url, operation, api_params)
            # print("Received Result")
            print("Received Result: `{result}`")
            return [mcp_types.TextContent(text=result, type="text")]
            return "hello barret!"

        super().__init__(call_api, model=None)

        # Now override the name, description, and input_schema
        self.name = operation_name
        self.description = operation_description
        self.schema: ChatCompletionToolParam = {
            "type": "function",
            "function": {
                "name": operation_name,
                "description": operation_description,
                "parameters": operation_input_schema,
            },
        }
        # RawChatlasTool class variables
        self._operation = operation
        self._tool = tool


@reactive.effect
def _():
    api_operations = openapi_operations()
    if not api_operations:
        req(api_operations)
        return
    print("Registering operations!", [operation["name"] for operation in api_operations.values()])
    print(api_operations)

    # _ = [
    #     {
    #         "input_schema": {"type": "object", "properties": {}, "required": []},
    #         "name": "read_root__get",
    #         "description": "Root endpoint returning a simple message.",
    #     },
    #     {
    #         "input_schema": {
    #             "type": "object",
    #             "properties": {
    #                 "item_id": {"type": "integer", "description": "(No description provided)"},
    #                 "query_param": {"type": "string", "description": "(No description provided)"},
    #             },
    #             "required": ["item_id"],
    #         },
    #         "name": "read_item_items__item_id__get",
    #         "description": "Endpoint to retrieve item details.",
    #     },
    # ]

    # input_schema = {
    #     "type": "function",
    #     "function": {
    #         "name": tool["name"],
    #         "description": tool["description"],
    #         "parameters": tool["input_schema"],
    #     },
    # }

    api_url = openapi_url.get()

    RawChatlasTool.reset_tools(chat)
    for operation in api_operations.values():
        print("operation", operation)
        RawChatlasTool.register_tool(
            chat,
            RawChatlasTool(
                # fn=fn,
                base_url=api_url,
                operation=operation,
            ),
        )

    print("Tools registered!", chat._tools)


# @reactive.effect
# def _():
#     operations = openapi_operations()
#     ui.notification_show("Making tools", id="making_tools")

#     funcs = []
#     for operation in operations.values():

#         def make_func(operation):
#             async def _call(**args):
#                 result = await chat.stream(operation["name"], **args)
#                 print(f"Called: {operation['name']}; Result: {result}")
#                 return result.content[0].text

#             return _call

#         funcs.append(make_func(operation))

#     # tools = openapi_tools()
#     # ui.notification_show("Registering tools", id="registering_tools")
#     # for tool in tools:
#     #     chat._tools[tool.name] = tool
#     #     # chat.register_tool(tool)


with ui.sidebar(open="open", id="sidebar", title="LLM", width="50%"):

    @render.ui
    def _openapi_tools():
        tools = [
            core_ui.TagList(
                core_ui.tags.dt(tool.name),
                # ": ",
                core_ui.tags.dl(tool.description),
            )
            for tool in openapi_tools()
        ]
        ret = core_ui.TagList(
            core_ui.tags.h3("Available Tools: ", len(tools)),
            core_ui.tags.dl(*tools),
        )
        return ret

    # Display chat
    chat_ui.ui(
        placeholder="Type here...",
    )


@render.ui
def _openapi_frame():
    api_url = openapi_url.get()
    if not api_url:
        return ui.h1("OpenAPI Documentation")
    api_docs_url = f"{api_url}docs"
    frame = ui.tags.iframe(
        src=api_docs_url,
        style=htmltools.css(width="100%", height="100%"),
    )
    return ui.fill.as_fill_item(frame)


swagger_url = reactive.value()

modal = ui.modal(
    ui.input_text(
        "api_url",
        "Enter the URL of the Swagger file:",
        placeholder="http://127.0.0.1:8000/",
    ),
    id="api_url_modal",
    title="API URL",
    easy_close=False,
    footer=ui.input_action_button("api_url_submit", "Save"),
)


@reactive.effect
def _():
    ui.modal_show(modal)


ui.HTML("""
<script>
    function click_submit() {
        document.getElementById("api_url_submit").click();
    };
    setTimeout(click_submit, 1 * 1000);
</script>
        """)


# defined to be end with `/`
openapi_url = reactive.value()


@reactive.calc
def openapi_json():
    api_url_val = openapi_url.get()
    if api_url_val is None:
        req(False)
        return
    url = f"{api_url_val}openapi.json"
    ui.notification_show(f"Fetching OpenAPI schema from {url}", id="fetching_openapi")
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to fetch OpenAPI schema from", url)
        print(response)
        req(False)
        return
    result = response.json()
    # ui.notification_remove("fetching_openapi")
    return result


@reactive.calc
def openapi_operations():
    ui.notification_show("Transforming OpenAPI schema to operations", id="transforming_openapi")
    document = expand_swagger(openapi_json())
    operations = transform_swagger_to_operation_dict(document)
    return operations


@reactive.calc
def openapi_tools():
    return map_operations_to_tools(openapi_operations())


@reactive.calc
def chat_tools():
    api_tools = openapi_tools()
    if not api_tools:
        req(api_tools)
        return

    ret_tools: RawChatlasTool = []


# @reactive.effect
# def _():
#     # print("openapi", openapi())
#     print("openapi_operations", openapi_operations())
#     # print("openapi_tools", openapi_tools())


@reactive.effect
@reactive.event(input.api_url_submit)
def _():
    input_api_url = input.api_url()
    if input_api_url is None:
        return
    if not isinstance(input_api_url, str):
        print("Be sure to enter a string. Received:", input_api_url)
        return
    if input_api_url == "":
        input_api_url = "http://127.0.0.1:8000/"

    if input_api_url.endswith((".json", ".yaml")):
        raise ValueError("Please enter the URL of the Swagger file, not the file itself.")
    if not input_api_url.endswith("/"):
        raise ValueError("Please enter a URL ending with a slash.")

    openapi_url.set(input_api_url)
    ui.modal_remove()
