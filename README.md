## MCP Sample

A Rust implementation of Model Context Protocol (MCP) servers for extending AI assistant capabilities.

## Overview

This project provides sample MCP servers that can be used with Amazon Q or other MCP-compatible AI assistants. The servers implement various functionalities:

- **Calculator Server**: Performs basic arithmetic operations
- **RDS Server**: Interacts with Amazon RDS instances
- **S3 Server**: Manages Amazon S3 buckets and objects
- **PostgreSQL Server**: Connects to PostgreSQL databases and executes queries

## Prerequisites

- Rust and Cargo
- AWS credentials configured for RDS and S3 operations
- An MCP-compatible AI assistant (like Amazon Q)

## Installation

Clone the repository and build the project:

```bash
git clone <repository-url>
cd sample-building-mcp-servers-with-rust
# install pip
sudo yum install -y python3-pip
# install dependencies
python3 -m pip install boto3 asyncpq
```

### Integration with Amazon Q CLI

To integrate these MCP servers with Amazon Q CLI or other MCP-compatible clients, add a configuration like this to your `.amazon-q.json` file:

```json
{
  "mcpServers": {
    "calculator-python": {
      "command": "python3",
      "args": ["/path/to/mcp-sample-servers-rust/src/calculator_server.py"]
    },
    "s3-python": {
      "command": "python3",
      "args": ["/path/to/mcp-sample-servers-rust/src/s3_server.py"]
    },
    "rds-python": {
      "command": "python3",
      "args": ["/path/to/mcp-sample-servers-rust/src/rds_server.py"]
    },
    "postgresql-python": {
      "command": "python3",
      "args": [
        "/path/to/mcp-sample-servers-rust/src/postgresql_server.py",
        "postgresql://postgres:<DB-PASSWORD>@<DB-ENDPOINT>.com:5432/demo"
      ]
    }
  }
}
```

Replace `/path/to/mcp-sample-servers-rust/` with the actual path to your built binaries. Once configured, Amazon Q will be able to use these servers to extend its capabilities.

## Server Descriptions

### Calculator Server

Provides basic arithmetic operations like addition and subtraction.

### RDS Server

Lists and manages Amazon RDS instances in specified regions.

### S3 Server

Manages S3 buckets and objects, including listing buckets by region.

### PostgreSQL Server

Connects to PostgreSQL databases and executes read-only queries, lists tables, and provides schema information.
