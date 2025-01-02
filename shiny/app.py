# ------------------------------------------------------------------------------------
# A basic Shiny Chat powered by Anthropic's Claude model with Bedrock.
# To run it, you'll need an AWS Bedrock configuration.
# To get started, follow the instructions at https://aws.amazon.com/bedrock/claude/
# as well as https://github.com/anthropics/anthropic-sdk-python#aws-bedrock
# ------------------------------------------------------------------------------------
import os

import anthropic

# import chatlas
import htmltools
import requests

# from anthropic import AnthropicBedrock
from mcp_servers.helpers.swagger import expand_swagger, transform_swagger_to_operation_dict
from openapi_mcp.connect_api import map_operations_to_tools
from shiny import reactive, req
from shiny import ui as core_ui
from shiny.express import input, render, ui

STREAM_CHAT = True


aws_model = os.getenv("AWS_MODEL", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
aws_region = os.getenv("AWS_REGION", "us-east-1")
# chat = chatlas.ChatBedrockAnthropic(
#     model=aws_model,
#     aws_region=aws_region,
# )

# Set some Shiny page options
ui.page_opts(
    title="Hello Anthropic Claude Chat",
    fillable=True,
    fillable_mobile=True,
)

chat_ui = ui.Chat(id="chat")


# @chat_ui.on_user_submit
# async def _():
#     user_input = chat_ui.user_input()
#     if user_input is None:
#         return
#     if STREAM_CHAT:
#         await chat_ui.append_message_stream(chat.stream(user_input))
#     else:
#         await chat_ui.append_message(str(chat.chat(user_input)))


llm = anthropic.AnthropicBedrock(
    # aws_secret_key=os.getenv("AWS_SECRET_KEY"),
    # aws_access_key=os.getenv("AWS_ACCESS_KEY"),
    aws_region=aws_region,
    # aws_account_id=os.getenv("AWS_ACCOUNT_ID"),
)


@chat_ui.on_user_submit
async def _():
    # Get messages currently in the chat
    messages = chat_ui.messages(format="anthropic")
    # Create a response message stream
    # print("anthropic_tools()", anthropic_tools())
    response = llm.messages.create(
        model=aws_model,
        messages=messages,
        stream=STREAM_CHAT,
        max_tokens=1000,
        tools=anthropic_tools(),
    )
    if STREAM_CHAT:
        # Append the response stream into the chat
        await chat_ui.append_message_stream(response)
    else:
        # Append the response as a single message
        await chat_ui.append_message(response)


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
