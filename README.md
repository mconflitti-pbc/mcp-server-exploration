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
- [x] Expand swagger file reference objects
- [x] Create bridge between swagger file and tool call
- [x] Register tool calls with chatlas
- [ ] Make function to process generic swagger file
- [ ] Make shiny chat app
  - [ ] Accepts a plumber API URL
  - [ ] Swagger docs in the main page
  - [ ] Leverage new function
- [ ] Make into package?
  - [ ] Export function that accepts a swagger file and returns tool calls
