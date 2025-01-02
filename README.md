# MCP

A simple example of a client and server using the Connect API.

## Usage

Run an MCP server:

```bash
CONNECT_API_KEY="<your key>" SWAGGER_FILE="swagger.yaml" make server
```

Then run the MCP client:

```bash
make client
```

Modify the chat in the main function of `app.py` to ask different questions.


## Tasks

- [x] Read swagger file
- [x] Expand swagger file reference objects: `doc = expand_swagger(doc)
- [x] Create bridge between swagger file and tool call: `
- [x] Register tool calls with chatlas
- [x] Make function to process generic swagger file: `operations = transform_swagger_to_operation_dict(doc)`
- [ ] Move all of `mcp_servers` into `openapi_mcp` as methods
- [ ] Make shiny chat app
  - [x] Accepts a plumber API URL
  - [x] Swagger docs in the main page
  - [ ] Leverage new function
- [ ] Make into package?
  - [ ] Export function that accepts a swagger file and returns tool calls
