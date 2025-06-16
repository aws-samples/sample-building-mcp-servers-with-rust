#!/usr/bin/env python3
"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

A simple RDS MCP server implementation in Python.
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/tmp/rds_operator.log"),
        logging.StreamHandler(sys.stderr)
    ]
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
            "list_instances": {
                "description": "List RDS instances in a region",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "region": {
                            "type": "string",
                            "description": "AWS region to list RDS instances from"
                        }
                    },
                    "required": ["region"]
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
                    "name": "rds-python",
                    "version": "1.0.0",
                    "instructions": "A simple RDS server"
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
            if tool_name == "list_instances":
                result = await self.list_instances(arguments.get("region", ""))
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
            else:
                return self.error_response(request_id, -32602, f"Tool not implemented: {tool_name}")
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return self.error_response(request_id, -32603, f"Tool execution error: {str(e)}")
    
    async def list_instances(self, region: str) -> Dict[str, List[Dict[str, Any]]]:
        """List RDS instances in the specified region."""
        logger.info(f"Listing RDS instances in region: {region}")
        
        try:
            # Create RDS client for the specified region
            if region and region.strip():
                rds_client = boto3.client('rds', region_name=region)
            else:
                rds_client = boto3.client('rds')
            
            # List RDS instances
            response = rds_client.describe_db_instances()
            
            # Extract instance information
            instances = []
            for instance in response.get('DBInstances', []):
                instance_info = {
                    "identifier": instance.get('DBInstanceIdentifier', ''),
                    "engine": instance.get('Engine'),
                    "status": instance.get('DBInstanceStatus'),
                    "endpoint": instance.get('Endpoint', {}).get('Address') if instance.get('Endpoint') else None
                }
                instances.append(instance_info)
            
            logger.info(f"Successfully listed {len(instances)} RDS instances")
            return {"instances": instances}
        except ClientError as e:
            logger.error(f"Error listing RDS instances: {e}")
            raise
    
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


class RDSServer(MCPServer):
    """RDS MCP Server."""
    
    def __init__(self):
        super().__init__()
        logger.info("RDS MCP Server initialized")


async def main():
    """Main server loop."""
    logger.info("Starting RDS MCP server")
    
    server = RDSServer()
    
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
