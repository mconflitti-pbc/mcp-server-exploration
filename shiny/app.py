# ------------------------------------------------------------------------------------
# A basic Shiny Chat powered by Anthropic's Claude model with Bedrock.
# To run it, you'll need an AWS Bedrock configuration.
# To get started, follow the instructions at https://aws.amazon.com/bedrock/claude/
# as well as https://github.com/anthropics/anthropic-sdk-python#aws-bedrock
# ------------------------------------------------------------------------------------
import asyncio
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
    expand_all_references,
    transform_swagger_to_operation_dict,
)
from openapi_mcp.connect_api import (
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

    if user_input is None:
        return
    if STREAM_CHAT:
        await chat_ui.append_message_stream(await chat.stream_async(user_input, echo="all"))
    else:
        await chat_ui.append_message(str(chat.chat(user_input)))


# @reactive.calc
# def anthropic_tools():
#     return [
#         {
#             "input_schema": tool.inputSchema,
#             "name": tool.name,
#             "description": tool.description,
#         }
#         for tool in openapi_tools()
#     ]


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

    api_url = openapi_url.get()

    RawChatlasTool.reset_tools(chat)
    for operation in api_operations.values():
        RawChatlasTool.register_tool(
            chat,
            RawChatlasTool(
                base_url=api_url,
                operation=operation,
            ),
        )


with ui.sidebar(open="open", id="sidebar", width="50%"):
    with ui.accordion(id="acc", open="chat_panel"):
        with ui.accordion_panel("Available Tools", value="available_tools_panel"):

            @render.ui
            def _openapi_tools():
                tools = [
                    core_ui.TagList(
                        core_ui.tags.dt(tool.name),
                        # ": ",
                        core_ui.tags.dl(core_ui.tags.pre(tool.description)),
                    )
                    for tool in openapi_tools()
                ]
                return core_ui.tags.dl(*tools)

            @reactive.effect
            def _():
                ui.update_accordion_panel(
                    "acc",
                    "available_tools_panel",
                    title=f"Available Tools ({len(openapi_tools())})",
                )

        with ui.accordion_panel("Chat", value="chat_panel"):
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
    return result


@reactive.calc
def openapi_operations():
    ui.notification_show("Transforming OpenAPI schema to operations", id="transforming_openapi")
    document = expand_all_references(openapi_json())
    operations = transform_swagger_to_operation_dict(document)
    return operations


@reactive.calc
def openapi_tools():
    return map_operations_to_tools(openapi_operations())


@reactive.effect
@reactive.event(input.api_url_submit)
async def _():
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


# Helpful debugging setup for interactive / non-deployed mode
# if not os.environ.get("CONNECT_CONTENT_GUID", ""):
if False:
    ui.HTML("""
<script>
    function click_submit() {
        document.getElementById("api_url_submit").click();
    };
    setTimeout(click_submit, 1 * 1000);
</script>
        """)

    # When the url is set, wait a bit before setting the chat input and submit it
    @reactive.effect
    @reactive.event(openapi_url)
    def _():
        trigger_set_chat()

    # Wait a bit
    @reactive.extended_task
    async def trigger_set_chat(delay: int = 1) -> int:
        await asyncio.sleep(delay)
        return delay

    # Set the chat input and submit it
    @reactive.effect
    async def _():
        # Only when the waited "result" is finished
        trigger_set_chat.result()

        chat_ui.update_user_input(
            # value="Hello"
            # value="who is the tallest person in Luke Skywalker's extended (max distance of 2 people) family tree (including force relationships)?"
            value="who is the tallest person in Luke Skywalker's immidiate family?"
        )

        add_chat_entry = ui.HTML("""
        <script>
            setTimeout(async () => {
                const enterEvent = new KeyboardEvent('keydown', {
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13,
                });

                // Dispatch the 'Enter' event on the input element
                console.log("Dispatching Enter event");
                document.querySelector("textarea#chat_user_input").dispatchEvent(enterEvent);
            }, 500);
        </script>
                """)
        ui.insert_ui(add_chat_entry, "body")
