#!/usr/bin/env python3
"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

A simple PostgreSQL MCP server implementation in Python.
"""

import asyncio
import json
import sys
import logging
import os
from typing import Any, Dict, List, Optional

import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/tmp/postgresql_operator.log"),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


class MCPServer:
    """Base MCP Server implementation."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.tools = {}
        self.setup_tools()

    def setup_tools(self):
        """Setup available tools."""
        self.tools = {
            "list_tables": {
                "description": "List tables in the PostgreSQL database",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            "get_table_schema": {
                "description": "Get schema for a specific table",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to get schema for"
                        }
                    },
                    "required": ["table_name"]
                }
            },
            "query": {
                "description": "Run a read-only SQL query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL query to execute (read-only)"
                        }
                    },
                    "required": ["sql"]
                }
            }
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.info(f"Received request: method={method}, id={request_id}")

        try:
            if method == "initialize":
                return await self.handle_initialize(request_id, params)
            elif method == "tools/list":
                return await self.handle_tools_list(request_id)
            elif method == "tools/call":
                return await self.handle_tools_call(request_id, params)
            else:
                logger.error(f"Method not found: {method}")
                return self.error_response(request_id, -32601, f"Method not found: {method}")
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self.error_response(request_id, -32603, str(e))

    async def handle_initialize(self, request_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request."""
        logger.info("Handling initialize request")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "postgresql-python",
                    "version": "1.0.0",
                    "instructions": "A PostgreSQL database server"
                }
            }
        }

    async def handle_tools_list(self, request_id: int) -> Dict[str, Any]:
        """Handle tools list request."""
        logger.info("Handling tools/list request")
        tools_list = []
        for name, tool_info in self.tools.items():
            tools_list.append({
                "name": name,
                "description": tool_info["description"],
                "inputSchema": tool_info["inputSchema"]
            })

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools_list
            }
        }

    async def handle_tools_call(self, request_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"Handling tools/call request for tool: {tool_name} with arguments: {arguments}")

        if tool_name not in self.tools:
            return self.error_response(request_id, -32602, f"Unknown tool: {tool_name}")

        try:
            result = None
            if tool_name == "list_tables":
                result = await self.list_tables()
            elif tool_name == "get_table_schema":
                table_name = arguments.get("table_name")
                if not table_name:
                    return self.error_response(request_id, -32602, "Missing required parameter: table_name")
                result = await self.get_table_schema(table_name)
            elif tool_name == "query":
                sql = arguments.get("sql")
                if not sql:
                    return self.error_response(request_id, -32602, "Missing required parameter: sql")
                result = await self.query(sql)
            else:
                return self.error_response(request_id, -32602, f"Tool not implemented: {tool_name}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result)
                        }
                    ]
                }
            }
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return self.error_response(request_id, -32603, f"Tool execution error: {str(e)}")

    async def get_connection(self):
        """Get a PostgreSQL connection."""
        try:
            # Parse and fix the connection string to handle special characters in password
            import urllib.parse

            # Parse the connection string
            parts = self.connection_string.split('@')
            if len(parts) != 2:
                logger.error("Invalid connection string format")
                raise ValueError("Invalid connection string format")

            auth_part = parts[0]
            host_part = parts[1]

            # Split auth part to get username and password
            auth_parts = auth_part.split('://')
            if len(auth_parts) != 2:
                logger.error("Invalid connection string format in auth part")
                raise ValueError("Invalid connection string format in auth part")

            protocol = auth_parts[0]
            user_pass = auth_parts[1]

            # Split username and password
            user_pass_parts = user_pass.split(':')
            if len(user_pass_parts) != 2:
                logger.error("Invalid username/password format")
                raise ValueError("Invalid username/password format")

            username = user_pass_parts[0]
            password = user_pass_parts[1]

            # Reconstruct the connection string with properly encoded password
            # Use asyncpg's direct parameter approach instead of URL
            user = username
            password = password
            host, port_db = host_part.split(':')
            port, database = port_db.split('/')

            # Connect with individual parameters instead of connection string
            conn = await asyncpg.connect(
                user=user,
                password=password,
                host=host,
                port=port,
                database=database
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def list_tables(self) -> Dict[str, List[Dict[str, str]]]:
        """List tables in the PostgreSQL database."""
        logger.info("Listing tables in PostgreSQL database...")

        try:
            conn = await self.get_connection()
            try:
                rows = await conn.fetch(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )

                tables = []
                for row in rows:
                    tables.append({"table_name": row["table_name"]})

                logger.info(f"Successfully listed {len(tables)} tables")
                return {"tables": tables}
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return {"tables": []}

    async def get_table_schema(self, table_name: str) -> Dict[str, List[Dict[str, str]]]:
        """Get schema for a specific table."""
        logger.info(f"Getting schema for table: {table_name}...")

        try:
            conn = await self.get_connection()
            try:
                rows = await conn.fetch(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = $1",
                    table_name
                )

                columns = []
                for row in rows:
                    columns.append({
                        "column_name": row["column_name"],
                        "data_type": row["data_type"]
                    })

                logger.info(f"Successfully retrieved schema for table {table_name} with {len(columns)} columns")
                return {"columns": columns}
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error getting table schema: {e}")
            return {"columns": []}

    async def query(self, sql: str) -> Dict[str, List[Dict[str, Any]]]:
        """Run a read-only SQL query."""
        logger.info(f"Executing SQL query: {sql}...")

        try:
            conn = await self.get_connection()
            try:
                # Start a read-only transaction
                await conn.execute("BEGIN TRANSACTION READ ONLY")
                try:
                    rows = await conn.fetch(sql)

                    # Convert rows to JSON-serializable format
                    result_rows = []
                    for row in rows:
                        json_row = {}
                        for key, value in row.items():
                            # Handle different data types
                            if isinstance(value, (str, int, float, bool)) or value is None:
                                json_row[key] = value
                            else:
                                # Convert other types to string
                                json_row[key] = str(value)
                        result_rows.append(json_row)

                    logger.info(f"Query executed successfully with {len(result_rows)} rows")
                    return {"rows": result_rows}
                finally:
                    # Always rollback to ensure we don't modify data
                    await conn.execute("ROLLBACK")
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {"rows": []}

    def error_response(self, request_id: int, code: int, message: str) -> Dict[str, Any]:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }


class PostgreSQLServer(MCPServer):
    """PostgreSQL MCP Server."""

    def __init__(self, connection_string: str):
        super().__init__(connection_string)
        logger.info("PostgreSQL MCP Server initialized")


async def main():
    """Main server loop."""
    # Get connection string from command line arguments
    if len(sys.argv) < 2:
        logger.error("Please provide a PostgreSQL connection string as a command-line argument")
        print("Usage: python postgresql_server.py <connection_string>", file=sys.stderr)
        sys.exit(1)

    connection_string = sys.argv[1]
    logger.info(f"Starting PostgreSQL MCP server with connection string: {connection_string}")

    server = PostgreSQLServer(connection_string)

    try:
        while True:
            # Read from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = await server.handle_request(request)

                # Write response to stdout
                print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                print(json.dumps(error_response), flush=True)

    except KeyboardInterrupt:
        logger.info("Server shutting down")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.exception("Exception details:")


if __name__ == "__main__":
    asyncio.run(main())
