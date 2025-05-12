from fastmcp import FastMCP
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine import reflection
from urllib.parse import quote_plus
from starlette.requests import Request
from starlette.responses import JSONResponse
from models.app_transport import AppTransport
from configs.settings import Settings
import asyncio
import json

settings = Settings()
mcp = FastMCP(
    name=settings.app_name,
    instructions=settings.app_instructions
)

def get_connection(db):
    conn_str = (
        f"mssql+aioodbc://{settings.db_uid}:{quote_plus(settings.db_pwd)}@{settings.db_host},{settings.db_port}/{db}"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        f"&Encrypt={settings.encrypt}"
        f"&TrustServerCertificate={settings.trust_server_certificate}"
    )
        
    print("Connection string:", conn_str)
        
    engine = create_async_engine(conn_str, echo=True)
    
    return engine
    
async def query_table_schema(engine, schema: str, table: str):
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table
        """), {"schema": schema, "table": table})

        rows = result.mappings().all()
        return json.dumps([dict(row) for row in rows]) 

async def query_tables_in_schema(engine, schema: str = "dbo"):
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = :schema
        """), {"schema": schema})

        rows = result.scalars().all()
        return rows
    
async def query_table_row_counts(engine):
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT 
                SCHEMA_NAME(t.schema_id) AS schema_name,
                t.name AS table_name,
                SUM(p.rows) AS row_count
            FROM 
                sys.tables AS t
            JOIN 
                sys.partitions AS p ON t.object_id = p.object_id
            WHERE 
                p.index_id IN (0, 1)
            GROUP BY 
                SCHEMA_NAME(t.schema_id), t.name
            ORDER BY 
                row_count DESC
        """))
        return [dict(row._mapping) for row in result]
    
async def query_missing_indexes(engine):
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT 
                DB_NAME(database_id) AS database_name,
                OBJECT_NAME(mid.object_id, database_id) AS table_name,
                migs.avg_total_user_cost * migs.avg_user_impact * (migs.user_seeks + migs.user_scans) AS improvement_score,
                mid.equality_columns, mid.inequality_columns, mid.included_columns
            FROM 
                sys.dm_db_missing_index_group_stats migs
            JOIN 
                sys.dm_db_missing_index_groups mig ON mig.index_group_handle = migs.group_handle
            JOIN 
                sys.dm_db_missing_index_details mid ON mig.index_handle = mid.index_handle
            WHERE 
                database_id = DB_ID()
            ORDER BY 
                improvement_score DESC
        """))
        return [dict(row._mapping) for row in result]
    
async def query_index_usage_stats(engine):
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT 
                OBJECT_NAME(i.object_id) AS table_name,
                i.name AS index_name,
                s.user_seeks, s.user_scans, s.user_lookups, s.user_updates
            FROM 
                sys.indexes i
            LEFT JOIN 
                sys.dm_db_index_usage_stats s ON i.object_id = s.object_id AND i.index_id = s.index_id
            WHERE 
                OBJECTPROPERTY(i.object_id, 'IsUserTable') = 1
        """))
        return [dict(row._mapping) for row in result]
    
async def query_top_expensive_queries(engine):
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT TOP 10
                qs.total_elapsed_time / qs.execution_count AS avg_time,
                qs.execution_count,
                qs.total_logical_reads,
                SUBSTRING(st.text, qs.statement_start_offset/2 + 1,
                    (CASE 
                        WHEN qs.statement_end_offset = -1 THEN LEN(CONVERT(NVARCHAR(MAX), st.text)) * 2
                        ELSE qs.statement_end_offset 
                    END - qs.statement_start_offset)/2 + 1) AS query_text
            FROM 
                sys.dm_exec_query_stats qs
            CROSS APPLY 
                sys.dm_exec_sql_text(qs.sql_handle) st
            ORDER BY 
                avg_time DESC
        """))
        return [dict(row._mapping) for row in result]
    
async def query_table_io_stats(engine):
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT 
                OBJECT_NAME(s.object_id) AS table_name,
                i.name AS index_name,
                i.type_desc AS index_type,
                s.user_seeks, s.user_scans, s.user_lookups, s.user_updates
            FROM 
                sys.dm_db_index_usage_stats s
            JOIN 
                sys.indexes i ON i.object_id = s.object_id AND i.index_id = s.index_id
            WHERE 
                database_id = DB_ID()
        """))
        return [dict(row._mapping) for row in result]
    
async def query_top_waits(engine):
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT 
                wait_type, 
                wait_time_ms / 1000.0 AS wait_time_sec,
                100.0 * wait_time_ms / SUM(wait_time_ms) OVER() AS pct,
                signal_wait_time_ms / 1000.0 AS signal_wait_sec
            FROM 
                sys.dm_os_wait_stats
            WHERE 
                wait_type NOT IN (
                    'CLR_SEMAPHORE','LAZYWRITER_SLEEP','RESOURCE_QUEUE','SLEEP_TASK','SLEEP_SYSTEMTASK',
                    'SQLTRACE_BUFFER_FLUSH','WAITFOR','LOGMGR_QUEUE','CHECKPOINT_QUEUE','REQUEST_FOR_DEADLOCK_SEARCH',
                    'XE_TIMER_EVENT','BROKER_TO_FLUSH','BROKER_TASK_STOP','CLR_MANUAL_EVENT','CLR_AUTO_EVENT',
                    'DISPATCHER_QUEUE_SEMAPHORE','FT_IFTS_SCHEDULER_IDLE_WAIT','XE_DISPATCHER_WAIT','XE_DISPATCHER_JOIN',
                    'WAIT_XACT_OWN_TRANSACTION'
                )
            ORDER BY 
                wait_time_ms DESC
        """))
        return [dict(row._mapping) for row in result]
    
async def exec_safe_diagnostic(engine, sql: str):
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            result = await conn.execute(text(sql))
            rows = result.fetchall()
            await trans.rollback()  # Rollback to prevent any changes
            return [dict(row._mapping) for row in rows]
        except Exception as e:
            await trans.rollback()
            raise e
        
# ------------------------------------------------------
    
@mcp.tool()
async def get_table_schema(db:str, table: str, db_schema: str="dbo") -> list:
    """
    Get the schema of a SQL Server table by connecting to SQLServer database.
    """
    result = []
    engine = get_connection(db)
    try:
        result = await query_table_schema(engine, db_schema, table)
    finally:
        await engine.dispose()
        
    return result

@mcp.tool()
async def get_table_names(db:str, db_schema: str="dbo") -> list:
    """
    Get/Scan table names in specific database.
    """
    columns = []
    engine = get_connection(db)
    try:
        columns = await query_tables_in_schema(engine, db_schema)
        for col in columns:
            print(col)
    finally:
        await engine.dispose()
        
    return columns

@mcp.tool()
async def get_table_row_counts(db:str) -> list:
    """
    Get table row counts in specific database.
    """
    columns = []
    engine = get_connection(db)
    try:
        columns = await query_table_row_counts(engine)
        for col in columns:
            print(col)
    finally:
        await engine.dispose()
        
    return columns

@mcp.tool()
async def get_missing_indexes(db:str) -> list:
    """
    Get missing indexes in specific database.
    """
    columns = []
    engine = get_connection(db)
    try:
        columns = await query_missing_indexes(engine)
        for col in columns:
            print(col)
    finally:
        await engine.dispose()
        
    return columns

@mcp.tool()
async def get_index_usage_stats(db:str) -> list:
    """
    Get index usage stats in specific database.
    """
    columns = []
    engine = get_connection(db)
    try:
        columns = await query_index_usage_stats(engine)
        for col in columns:
            print(col)
    finally:
        await engine.dispose()
        
    return columns

@mcp.tool()
async def get_top_expensive_queries(db:str) -> list:
    """
    Get top expensive queries in specific database.
    """
    columns = []
    engine = get_connection(db)
    try:
        columns = await query_top_expensive_queries(engine)
        for col in columns:
            print(col)
    finally:
        await engine.dispose()
        
    return columns

@mcp.tool()
async def get_table_io_stats(db:str) -> list:
    """
    Get table IO stats in specific database.
    """
    columns = []
    engine = get_connection(db)
    try:
        columns = await query_table_io_stats(engine)
        for col in columns:
            print(col)
    finally:
        await engine.dispose()
        
    return columns

@mcp.tool()
async def get_top_waits(db:str) -> list:
    """
    Get top waits in specific database.
    """
    columns = []
    engine = get_connection(db)
    try:
        columns = await query_top_waits(engine)
        for col in columns:
            print(col)
    finally:
        await engine.dispose()
        
    return columns

@mcp.tool()
async def run_safe_diagnostic(db:str, sql: str) -> list:
    """
    Executes a **read-only** SQL query in a safe transaction that is always rolled back.

    Args:
        db (str): The database name.
        sql (str): The SQL statement to be executed. Should be SELECT or any diagnostic statement.

    Returns:
        list: A list of rows (as dictionaries) returned by the SQL query.
    """
    columns = []
    engine = get_connection(db)
    try:
        columns = await exec_safe_diagnostic(engine, sql)
        for col in columns:
            print(col)
    finally:
        await engine.dispose()
        
    return columns

# ------------------------------------------------------

@mcp.resource("data://config")
def get_config():
    """
    Get the configuration.
    """
    # masking password
    config = settings.copy()
    config.db_pwd = "******"
    
    return config.dict()

async def poc():
    db = settings.db_name
    engine = get_connection(db)
    try:
        # result = await get_table_schema(db, table="KMA_MST_NOTIFICATION", db_schema="dbo")
        # result = await get_table_names(db, db_schema="dbo")
        # result = await get_table_row_counts(db)
        # result = await get_missing_indexes(db)
        # result = await get_index_usage_stats(db)
        # result = await get_top_expensive_queries(db)
        # result = await get_table_io_stats(db)
        # result = await get_top_waits(db)
        result = await run_safe_diagnostic(db, sql="SELECT * FROM KMA_MST_NOTIFICATION")
        print(result)
    finally:
        await engine.dispose()
        

@mcp.custom_route(path="/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """
    Health check endpoint.
    """
    return JSONResponse({"status": "ok"})
    
if __name__ == "__main__":
    
    if settings.is_env == "poc":
        asyncio.run(poc())
    else:
        print("Settings:", settings)
        transport = AppTransport(settings.app_transport)
        if transport == AppTransport.STDIO:
            mcp.run(transport=settings.app_transport)
        elif transport == AppTransport.STREAM:
            mcp.run(
                transport=settings.app_transport, 
                host=settings.app_host, 
                port=settings.app_port, 
                path=settings.app_path,
                log_level=settings.app_log_level
            )
        elif transport == AppTransport.SSE:
            mcp.run(
                transport=settings.app_transport, 
                host=settings.app_host, 
                port=settings.app_port, 
                path=settings.app_path,
                # message_path=settings.app_message_path,
                log_level=settings.app_log_level
            )
        else:
            raise ValueError(f"Unsupported transport: {settings.app_transport}")
