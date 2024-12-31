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
