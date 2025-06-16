#!/usr/bin/env python3
"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

A simple calculator MCP server implementation in Python.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
import logging

# Configure logging to stderr (similar to the Rust implementation)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class MCPServer:
    """Base MCP Server implementation."""
    
    def __init__(self):
        self.tools = {}
        self.setup_tools()
    
    def setup_tools(self):
        """Setup available tools."""
        self.tools = {
            "sum": {
                "description": "Calculate the sum of two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "integer",
                            "description": "the left hand side number"
                        },
                        "b": {
                            "type": "integer", 
                            "description": "the right hand side number"
                        }
                    },
                    "required": ["a", "b"]
                }
            },
            "sub": {
                "description": "Calculate the difference of two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "integer",
                            "description": "the left hand side number"
                        },
                        "b": {
                            "type": "integer",
                            "description": "the right hand side number"
                        }
                    },
                    "required": ["a", "b"]
                }
            }
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                return await self.handle_initialize(request_id, params)
            elif method == "tools/list":
                return await self.handle_tools_list(request_id)
            elif method == "tools/call":
                return await self.handle_tools_call(request_id, params)
            else:
                return self.error_response(request_id, -32601, f"Method not found: {method}")
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self.error_response(request_id, -32603, str(e))
    
    async def handle_initialize(self, request_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "calculator-server",
                    "version": "1.0.0",
                    "instructions": "A simple calculator"
                }
            }
        }
    
    async def handle_tools_list(self, request_id: int) -> Dict[str, Any]:
        """Handle tools list request."""
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
        
        if tool_name not in self.tools:
            return self.error_response(request_id, -32602, f"Unknown tool: {tool_name}")
        
        try:
            if tool_name == "sum":
                result = self.sum(arguments.get("a"), arguments.get("b"))
            elif tool_name == "sub":
                result = self.sub(arguments.get("a"), arguments.get("b"))
            else:
                return self.error_response(request_id, -32602, f"Tool not implemented: {tool_name}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": str(result)
                        }
                    ]
                }
            }
        except Exception as e:
            return self.error_response(request_id, -32603, f"Tool execution error: {str(e)}")
    
    def sum(self, a: int, b: int) -> str:
        """Calculate the sum of two numbers."""
        if a is None or b is None:
            raise ValueError("Both a and b must be provided")
        return str(a + b)
    
    def sub(self, a: int, b: int) -> int:
        """Calculate the difference of two numbers."""
        if a is None or b is None:
            raise ValueError("Both a and b must be provided")
        return a - b
    
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


class CalculatorServer(MCPServer):
    """Calculator MCP Server."""
    
    def __init__(self):
        super().__init__()
        logger.info("Calculator MCP Server initialized")


async def main():
    """Main server loop."""
    logger.info("Starting MCP server")
    
    server = CalculatorServer()
    
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


if __name__ == "__main__":
    asyncio.run(main())
