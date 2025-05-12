# SQLServer MCP Server

## Features

- Get table schema
- Validate performance
- Run safe diagnostic (with rollback)

## Prerequisites

### Environment variables

You can set:

- transport method.
- endpoint
- custom host name, port number of this service.
- SQLServer user/password, database name, enable/disable trust certificate and encryption.
- allow PoC mode (call function without LLM) to check mechanism of this service, just set `IS_ENV` to **poc**. Otherwise communicate via normal transport method (`stdio`, `sse`, `streamable-http`).

Please refer to `.env.example`.

### Your target SQLServer

Don't forget to start it.

## Usage

### Start server

#### Locally

```sh
uv venv
source .venv/bin/activate
uv sync
```

then run

```sh
uv run main.py
```

#### Container compose

Assume your root repo is `mcp-server-sqlserver`:

```yml
services:
  mcp-server-sqlserver:
    container_name: mcp-server-sqlserver
    build:
      context: ./mcp-server-sqlserver
      dockerfile: Dockerfile
    ports:
      - "4200:4200"
    env_file:
      - ./mcp-server-sqlserver/.env
    volumes:
      - ./mcp-server-sqlserver:/app
    networks:
      - same_network_as_sqlserver_if_exists
    tty: true
    restart: always
```

### Add MCP server to your agent

```json

```

### Example

Ex. using MCP Server via [LangChain](https://github.com/patharanordev/learn-langchain-langgraph/blob/main/workflows/mcp_integration/handler.py) without any description on target table (need to describe something before your question):

```sh
================================ Human Message =================================

From dbo.NOTIFICATION in master database, which customer id who did not read notification yet?
================================== Ai Message ==================================

[
    {
        'type': 'text', 
        'text': 'To get the customer IDs that have unread notifications in the dbo.NOTIFICATION table, we can run the following SQL query using the run_safe_diagnostic tool:'
    }, {
        'type': 'tool_use', 
        'name': 'run_safe_diagnostic', 
        'input': {
            'db': 'master', 
            'sql': 'SELECT DISTINCT CUST_ID \nFROM dbo.NOTIFICATION\nWHERE IS_READ = 0;'
        }, 
        'id': 'tooluse_CBvB-H5VRP-x-XnGoATY2g'
    }
]
Tool Calls:
run_safe_diagnostic (tooluse_CBvB-H5VRP-x-XnGoATY2g)
Call ID: tooluse_CBvB-H5VRP-x-XnGoATY2g
Args:
    db: master
    sql: SELECT DISTINCT CUST_ID
FROM dbo.NOTIFICATION
WHERE IS_READ = 0;
================================= Tool Message =================================
Name: run_safe_diagnostic

[
{
    "CUST_ID": "lj2koe562"
}
]
================================== Ai Message ==================================

This query selects the distinct CUST_ID values from the NOTIFICATION table where the IS_READ column is 0, indicating the notification has not been read yet.

The result shows that the customer with ID "lj2koe562" has an unread notification in this table.
```

## Development

- ✅ Transport selection
  - ✅ Local communication
  - ✅ Remote communication
- ⬜ Message handling
  - ⬜ Request processing
  - ⬜ Progress reporting
  - ⬜ Error management
- ⬜ Security considerations
  - ✅ Transport security
  - ⬜ Message validation
  - ⬜ Resource protection
  - ⬜ Error handling
- ⬜ Debugging and monitoring
  - ⬜ Logging
  - ⬜ Diagnostics
  - ⬜ Testing
