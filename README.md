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

[{'type': 'text', 'text': 'To get the list of customer IDs that have unread notifications in the dbo.NOTIFICATION table, we can run the following SQL query using the run_safe_diagnostic tool:'}, {'type': 'tool_use', 'name': 'run_safe_diagnostic', 'input': {'db': 'master', 'sql': 'SELECT DISTINCT CUSTOMER_ID \nFROM dbo.NOTIFICATION\nWHERE IS_READ = 0;'}, 'id': 'tooluse_l_vou1pPTHWRresWHCqnvg'}]
Tool Calls:
  run_safe_diagnostic (tooluse_l_vou1pPTHWRresWHCqnvg)
 Call ID: tooluse_l_vou1pPTHWRresWHCqnvg
  Args:
    db: master
    sql: SELECT DISTINCT CUSTOMER_ID
FROM dbo.NOTIFICATION
WHERE IS_READ = 0;
================================= Tool Message =================================
Name: run_safe_diagnostic

Error: ToolException('Error executing tool run_safe_diagnostic: (pyodbc.ProgrammingError) (\'42S22\', "[42S22] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Invalid column name \'CUSTOMER_ID\'. (207) (SQLExecDirectW)")\n[SQL: SELECT DISTINCT CUSTOMER_ID \nFROM dbo.NOTIFICATION\nWHERE IS_READ = 0;]\n(Background on this error at: https://sqlalche.me/e/20/f405)')
 Please fix your mistakes.
================================== Ai Message ==================================

[{'type': 'text', 'text': 'Oops, it seems the dbo.NOTIFICATION table does not have a CUSTOMER_ID column. Let me check the table schema first:'}, {'type': 'tool_use', 'name': 'get_table_schema', 'input': {'db': 'master', 'table': 'NOTIFICATION'}, 'id': 'tooluse_Ik7C2avnR4uDyb1ZpDGxCw'}]
Tool Calls:
  get_table_schema (tooluse_Ik7C2avnR4uDyb1ZpDGxCw)
 Call ID: tooluse_Ik7C2avnR4uDyb1ZpDGxCw
  Args:
    db: master
    table: NOTIFICATION
================================= Tool Message =================================
Name: get_table_schema

[{"COLUMN_NAME": "NOTI_ID", "DATA_TYPE": "bigint", "IS_NULLABLE": "NO"}, {"COLUMN_NAME": "CUST_ID", "DATA_TYPE": "varchar", "IS_NULLABLE": "YES"}, {"COLUMN_NAME": "SUBJECT_TH", "DATA_TYPE": "varchar", "IS_NULLABLE": "YES"}, {"COLUMN_NAME": "SUBJECT_EN", "DATA_TYPE": "varchar", "IS_NULLABLE": "YES"}, ..., {"COLUMN_NAME": "IMAGE_ACTION_2", "DATA_TYPE": "varchar", "IS_NULLABLE": "YES"}]
================================== Ai Message ==================================

[{'type': 'text', 'text': "Ah I see, the customer ID column is named CUST_ID. Let's try the query again with the correct column name:"}, {'type': 'tool_use', 'name': 'run_safe_diagnostic', 'input': {'db': 'master', 'sql': 'SELECT DISTINCT CUST_ID\nFROM dbo.NOTIFICATION  \nWHERE IS_READ = 0;'}, 'id': 'tooluse_625QEvaeSjeynA9raV4K6g'}]
Tool Calls:
  run_safe_diagnostic (tooluse_625QEvaeSjeynA9raV4K6g)
 Call ID: tooluse_625QEvaeSjeynA9raV4K6g
  Args:
    db: master
    sql: SELECT DISTINCT CUST_ID
FROM dbo.NOTIFICATION
WHERE IS_READ = 0;
================================= Tool Message =================================
Name: run_safe_diagnostic

[
  {
    "cpu_time": 2,
    "logical_reads": 651,
    "rows": [
      {
        "CUST_ID": "lj2koe562"
      }
    ]
  }
]
================================== Ai Message ==================================

The query returns a list of distinct CUST_ID values from the NOTIFICATION table where the IS_READ column is 0, indicating unread notifications.

Based on the result, the customer ID "lj2koe562" has unread notifications in this table.
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
