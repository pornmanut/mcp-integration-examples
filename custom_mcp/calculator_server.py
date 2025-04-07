#!/usr/bin/env python3
"""
Simple MCP Calculator Server

This is a standalone MCP server that provides calculator tools and listens on HTTP.
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List

# Server configuration
HOST = "localhost"
PORT = 8000
SERVER_NAME = "MCP Calculator Server"
SERVER_VERSION = "1.0.0"

class MCPTool:
    """Represents a tool exposed by the MCP server."""
    
    def __init__(self, tool_id, name, description, handler_func):
        self.id = tool_id
        self.name = name
        self.description = description
        self.handler = handler_func
        
    def to_dict(self):
        """Convert the tool to its dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number"
                    }
                },
                "required": ["a", "b"]
            },
            "return_schema": {
                "type": "number",
                "description": "The calculation result"
            }
        }

class MCPCalculatorServer:
    """A simple MCP server that provides calculator functionality."""
    
    def __init__(self):
        """Initialize the calculator server."""
        # Register the tools
        self.tools = {}
        self.register_tool(
            "calculator:add",
            "add",
            "Add two numbers together",
            self.add
        )
        self.register_tool(
            "calculator:subtract",
            "subtract",
            "Subtract the second number from the first",
            self.subtract
        )
        
    def register_tool(self, tool_id, name, description, handler):
        """Register a new tool with the server."""
        self.tools[tool_id] = MCPTool(tool_id, name, description, handler)
        
    def add(self, params):
        """Add two numbers."""
        if "a" not in params or "b" not in params:
            raise ValueError("Missing required parameters: 'a' and 'b'")
            
        a = params["a"]
        b = params["b"]
        result = a + b
        print(f"[DEBUG] Addition: {a} + {b} = {result}", file=sys.stderr)
        return result
        
    def subtract(self, params):
        """Subtract b from a."""
        if "a" not in params or "b" not in params:
            raise ValueError("Missing required parameters: 'a' and 'b'")
            
        a = params["a"]
        b = params["b"]
        result = a - b
        print(f"[DEBUG] Subtraction: {a} - {b} = {result}", file=sys.stderr)
        return result
    
    def handle_initialize(self):
        """Handle an initialize request."""
        return {
            "protocolVersion": "1.0",
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION
            },
            "capabilities": {
                "tools": True,
                "resources": False,
                "prompts": False
            }
        }
    
    def handle_list_tools(self):
        """Handle a tools/list request."""
        print(f"[DEBUG] Tools Discovery - Returning {len(self.tools)} tools", file=sys.stderr)
        for tool_id, tool in self.tools.items():
            print(f"[DEBUG]   - {tool_id}: {tool.description}", file=sys.stderr)
            
        return [tool.to_dict() for tool in self.tools.values()]
    
    def handle_execute_tool(self, params):
        """Handle a tools/execute request."""
        tool_id = params.get("tool_id")
        if not tool_id:
            raise ValueError("Missing required parameter: tool_id")
            
        if tool_id not in self.tools:
            raise ValueError(f"Unknown tool: {tool_id}")
            
        tool_params = params.get("parameters", {})
        print(f"[DEBUG] Executing tool: {tool_id}", file=sys.stderr)
        print(f"[DEBUG] Parameters: {json.dumps(tool_params)}", file=sys.stderr)
        
        result = self.tools[tool_id].handler(tool_params)
        print(f"[DEBUG] Result: {result}", file=sys.stderr)
        return result

class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP server."""
    
    server_instance = MCPCalculatorServer()
    
    def do_POST(self):
        """Handle POST requests."""
        # Get content length
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_error(400, "Missing request body")
            return
            
        # Read and parse request body
        request_body = self.rfile.read(content_length).decode('utf-8')
        try:
            request = json.loads(request_body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON in request body")
            return
            
        # Extract request information
        jsonrpc = request.get("jsonrpc")
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Log the request
        print(f"\n[DEBUG] === NEW REQUEST ===", file=sys.stderr)
        print(f"[DEBUG] Method: {method}", file=sys.stderr)
        print(f"[DEBUG] ID: {request_id}", file=sys.stderr)
        print(f"[DEBUG] Params: {json.dumps(params)}", file=sys.stderr)
        
        # Validate basic JSON-RPC structure
        if jsonrpc != "2.0" or not method:
            self.send_json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request"
                },
                "id": request_id
            })
            return
            
        # Process the request
        try:
            result = None
            
            if method == "initialize":
                result = self.server_instance.handle_initialize()
            elif method == "tools/list":
                result = self.server_instance.handle_list_tools()
            elif method == "tools/execute":
                result = self.server_instance.handle_execute_tool(params)
            else:
                self.send_json_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    },
                    "id": request_id
                })
                return
                
            # Send success response
            response = {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
            self.send_json_response(response)
            
        except Exception as e:
            # Send error response
            error_message = str(e)
            print(f"[DEBUG] Error: {error_message}", file=sys.stderr)
            self.send_json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {error_message}"
                },
                "id": request_id
            })
            
        print(f"[DEBUG] === END REQUEST ===\n", file=sys.stderr)
            
    def send_json_response(self, response_obj):
        """Send a JSON response to the client."""
        response_str = json.dumps(response_obj)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_str)))
        self.end_headers()
        self.wfile.write(response_str.encode('utf-8'))
        print(f"[DEBUG] Response: {response_str}", file=sys.stderr)
            
def main():
    """Main entry point for the calculator server."""
    server_address = (HOST, PORT)
    
    print("\n========================================", file=sys.stderr)
    print(f"{SERVER_NAME} starting on http://{HOST}:{PORT}", file=sys.stderr)
    print(f"Version: {SERVER_VERSION}", file=sys.stderr)
    print("Available tools:", file=sys.stderr)
    print("  - calculator:add - Add two numbers together", file=sys.stderr)
    print("  - calculator:subtract - Subtract the second number from the first", file=sys.stderr)
    print("========================================\n", file=sys.stderr)
    
    try:
        httpd = HTTPServer(server_address, MCPRequestHandler)
        print("Server is running. Press Ctrl+C to stop.", file=sys.stderr)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down...", file=sys.stderr)
        httpd.server_close()
        print("Server stopped.", file=sys.stderr)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
        
if __name__ == "__main__":
    main() 
