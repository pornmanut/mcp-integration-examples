#!/usr/bin/env python3
"""
LLM Agent with MCP Integration

This agent uses an LLM (DeepSeek) to interact with MCP tools.
It connects directly to the MCP server via HTTP,
discovers tools, formats them for the LLM, and executes them based on LLM responses.
"""

import json
import os
import re
import sys
import argparse
from typing import Any, Dict, List, Optional, Union

import dotenv
import httpx


class LLMAgent:
    """An agent that uses an LLM to work with MCP tools."""

    def __init__(self, mcp_server_url: str, api_key: str, model: str = "deepseek-chat"):
        """
        Initialize the LLM agent.
        
        Args:
            mcp_server_url: The URL of the MCP server
            api_key: The DeepSeek API key
            model: The DeepSeek model to use
        """
        self.mcp_server_url = mcp_server_url
        self.api_key = api_key
        self.model = model
        self.tools = []
        self.messages = []
        self.system_prompt = ""
    
    async def initialize_connection(self) -> Dict[str, Any]:
        """
        Initialize the connection to the MCP server.
        
        Returns:
            The server capabilities
        """
        try:
            # Make an initialize request to the MCP server
            request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0",
                    "clientInfo": {
                        "name": "LLM Agent",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": True,
                        "resources": False,
                        "prompts": False
                    }
                },
                "id": "init-1"
            }
            
            response = await self._send_mcp_request(request)
            print(f"Connected to MCP server: {response.get('serverInfo', {}).get('name', 'Unknown')}")
            return response
        except Exception as e:
            print(f"Error initializing connection: {e}")
            raise
    
    async def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Discover tools from the MCP server and format them for the LLM.
        
        Returns:
            The discovered tools
        """
        try:
            # Make a tools/list request to the MCP server
            request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": "list-1"
            }
            
            self.tools = await self._send_mcp_request(request)
            
            # Create the system prompt with tool descriptions
            tools_description = self._format_tools_for_llm()
            self.system_prompt = (
                "You are a helpful assistant with access to the following tools:\n\n"
                f"{tools_description}\n\n"
                "To use a tool, include a JSON block anywhere in your response like this:\n"
                "```json\n"
                "{\n"
                '  "tool": "tool_name",\n'
                '  "parameters": {\n'
                '    "param1": value1,\n'
                '    "param2": value2\n'
                "  }\n"
                "}\n"
                "```\n\n"
                "IMPORTANT RULES:\n"
                "1. You can explain your reasoning, but ALWAYS use tools for operations - NEVER perform calculations yourself\n"
                "2. Use ONE tool call per response\n"
                "3. After receiving a tool result, ALWAYS make the next tool call if more operations remain\n"
                "4. Only provide a final answer after ALL operations have been performed using tools\n\n"
                "For multi-step tasks:\n"
                "1. First explain which step you're on and what you're doing (e.g., 'Step 1: I'll add these numbers')\n"
                "2. Then include the JSON block to call the appropriate tool\n"
                "3. For each step, explain what you're doing and why\n"
                "4. Only provide a final answer when the entire task is complete\n\n"
                "For example, to calculate '5+10-3':\n"
                "Step a: I'll add 5 and 10\n"
                "```json\n"
                "{\n"
                '  "tool": "add",\n'
                '  "parameters": {\n'
                '    "a": 5,\n'
                '    "b": 10\n'
                "  }\n"
                "}\n"
                "```\n\n"
                "After receiving result 15:\n"
                "Step b: Now I'll subtract 3 from the result 15\n"
                "```json\n"
                "{\n"
                '  "tool": "subtract",\n'
                '  "parameters": {\n'
                '    "a": 15,\n'
                '    "b": 3\n'
                "  }\n"
                "}\n"
                "```\n\n"
                "After receiving result 12:\n"
                "The result of 5+10-3 is 12.\n\n"
                "Remember to use tools for EVERY operation, no matter how simple it seems."
            )
            
            # Initialize the conversation with the system prompt
            self.messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            return self.tools
        except Exception as e:
            print(f"Error discovering tools: {e}")
            raise
    
    def _format_tools_for_llm(self) -> str:
        """
        Format tools into a string description for the LLM.
        
        Returns:
            A formatted string describing all tools
        """
        descriptions = []
        
        for tool in self.tools:
            # Format basic tool info
            desc = f"Tool: {tool['name']}\n"
            desc += f"Description: {tool['description']}\n"
            desc += "Parameters:\n"
            
            # Format parameters
            if 'parameters_schema' in tool and 'properties' in tool['parameters_schema']:
                properties = tool['parameters_schema']['properties']
                required = tool['parameters_schema'].get('required', [])
                
                for param_name, param_info in properties.items():
                    param_desc = f"  - {param_name}"
                    if param_name in required:
                        param_desc += " (required)"
                    param_desc += f": {param_info.get('description', 'No description')}"
                    param_desc += f" (type: {param_info.get('type', 'any')})"
                    desc += param_desc + "\n"
            
            descriptions.append(desc)
        
        return "\n".join(descriptions)
    
    async def process_user_input(self, user_input: str) -> str:
        """
        Process user input through the LLM and execute any requested tools.
        
        Args:
            user_input: The user's input text
            
        Returns:
            The final response for the user
        """
        # Add user input to the conversation
        self.messages.append({"role": "user", "content": user_input})
        
        # Get initial response from LLM
        return await self._process_llm_response()
    
    async def _process_llm_response(self) -> str:
        """
        Process an LLM response, handling any tool calls and subsequent steps.
        
        Returns:
            The final response for the user
        """
        # Get response from LLM
        llm_response = await self._get_llm_response()
        
        # Check if the response contains a tool call
        tool_call = self._parse_tool_call(llm_response)
        
        if tool_call:
            tool_name = tool_call.get("tool")
            parameters = tool_call.get("parameters", {})
            
            # Add the complete LLM response to conversation history
            self.messages.append({"role": "assistant", "content": llm_response})
            
            # Find the tool ID from the name
            tool_id = None
            for tool in self.tools:
                if tool["name"] == tool_name:
                    tool_id = tool["id"]
                    break
            
            if tool_id:
                try:
                    # Execute the tool
                    print(f"Executing tool: {tool_name} with parameters: {parameters}")
                    result = await self._execute_tool(tool_id, parameters)
                    
                    # Add the tool result to the conversation
                    # Use a format that encourages the LLM to continue its reasoning
                    self.messages.append({"role": "system", "content": f"Tool result: {result}"})
                    
                    # Process next step (which might be another tool call or a final response)
                    return await self._process_llm_response()
                    
                except Exception as e:
                    error_message = f"Error executing tool: {str(e)}"
                    print(error_message)
                    
                    # Add the error to the conversation
                    self.messages.append({"role": "system", "content": f"Error executing tool '{tool_name}': {error_message}"})
                    
                    # Get the final response from the LLM
                    final_response = await self._get_llm_response()
                    
                    # Add the final response to conversation history
                    self.messages.append({"role": "assistant", "content": final_response})
                    
                    return final_response
            else:
                error_message = f"Unknown tool: {tool_name}"
                print(error_message)
                
                # Add the error to the conversation
                self.messages.append({"role": "system", "content": f"Unknown tool '{tool_name}'. Available tools: {', '.join(tool['name'] for tool in self.tools)}"})
                
                # Get the final response from the LLM
                final_response = await self._get_llm_response()
                
                # Add the final response to conversation history
                self.messages.append({"role": "assistant", "content": final_response})
                
                return final_response
        else:
            # If no tool call, add the response to history and return it
            self.messages.append({"role": "assistant", "content": llm_response})
            return llm_response
    
    async def _get_llm_response(self) -> str:
        """
        Get a response from the LLM without modifying the conversation history.
        
        Returns:
            The LLM's response text
        
        Raises:
            Exception: If there's an error communicating with the LLM
        """
        url = "https://api.deepseek.com/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": self.messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        print(f"Sending request to LLM: {json.dumps(payload, indent=2, default=str)}")
        print(f"API Key (first 5 chars): {self.api_key[:5]}...")
        print(f"Request URL: {url}")
        
        try:
            print("Creating httpx client...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    print("Sending POST request to LLM...")
                    response = await client.post(url, json=payload, headers=headers)
                    print(f"Response status code: {response.status_code}")
                    print(f"Response headers: {response.headers}")
                    
                    # Try to print response body regardless of status code
                    try:
                        response_json = response.json()
                        print(f"Response body: {json.dumps(response_json, indent=2)}")
                    except Exception as e:
                        print(f"Failed to parse response as JSON: {e}")
                        print(f"Raw response text: {response.text}")
                    
                    # Now raise for non-200 status
                    response.raise_for_status()
                    
                    data = response.json()
                    print(f"Received response from LLM: {json.dumps(data, indent=2)}")
                    
                    message = data.get("choices", [{}])[0].get("message", {})
                    content = message.get("content", "")
                    
                    # Do NOT add to conversation history - let the caller handle it
                    return content
                except httpx.HTTPStatusError as e:
                    print(f"HTTP error: {e}")
                    print(f"Error details: {e.response.text}")
                    raise Exception(f"LLM API error: {e.response.status_code} - {e.response.text}")
                except httpx.RequestError as e:
                    print(f"Request error: {e}")
                    print(f"Error type: {type(e)}")
                    print(f"Error details: {e.__dict__}")
                    raise Exception(f"LLM API request failed: {str(e)}")
                except Exception as e:
                    print(f"Unexpected error in HTTP request: {str(e)}")
                    print(f"Error type: {type(e)}")
                    import traceback
                    traceback.print_exc()
                    raise Exception(f"Unexpected error when calling LLM API: {str(e)}")
        except Exception as e:
            print(f"Outer exception in _get_llm_response: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to communicate with LLM API: {str(e)}")
    
    async def _send_mcp_request(self, request: Dict[str, Any]) -> Any:
        """
        Send a request to the MCP server.
        
        Args:
            request: The JSON-RPC request to send
            
        Returns:
            The result from the server
            
        Raises:
            Exception: If there's an error communicating with the server
        """
        try:
            print(f"Sending request to MCP server: {json.dumps(request, indent=2)}")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.mcp_server_url, json=request)
                response.raise_for_status()
                
                data = response.json()
                print(f"Received response from MCP server: {json.dumps(data, indent=2)}")
                
                if "error" in data:
                    error = data["error"]
                    raise Exception(f"MCP server error: {error.get('message')} (code: {error.get('code')})")
                
                return data.get("result", {})
        except Exception as e:
            print(f"Error communicating with MCP server: {e}")
            raise
    
    async def _execute_tool(self, tool_id: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a tool on the MCP server.
        
        Args:
            tool_id: The ID of the tool to execute
            parameters: The tool parameters
            
        Returns:
            The result of the tool execution
        """
        request = {
            "jsonrpc": "2.0",
            "method": "tools/execute",
            "params": {
                "tool_id": tool_id,
                "parameters": parameters
            },
            "id": f"exec-{tool_id}"
        }
        
        return await self._send_mcp_request(request)
    
    def _parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse a tool call from the LLM response.
        
        Args:
            text: The LLM response text
            
        Returns:
            A dictionary with tool and parameters, or None if no tool call found
        """
        # Method 1: Look for JSON in code blocks with json tag
        json_matches = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
        for json_text in json_matches:
            try:
                data = json.loads(json_text)
                if isinstance(data, dict) and "tool" in data and "parameters" in data:
                    return data
            except json.JSONDecodeError:
                continue
        
        # Method 2: Look for JSON in code blocks without language tag
        json_matches = re.findall(r"```\n(.*?)\n```", text, re.DOTALL)
        for json_text in json_matches:
            try:
                data = json.loads(json_text)
                if isinstance(data, dict) and "tool" in data and "parameters" in data:
                    return data
            except json.JSONDecodeError:
                continue
        
        # Method 3: Check if the entire response is a JSON object
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "tool" in data and "parameters" in data:
                return data
        except json.JSONDecodeError:
            pass
        
        # Method 4: Look for JSON structure with both "tool" and "parameters" keys
        # This regex tries to find a JSON object that contains both required keys
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*"tool"\s*:\s*"[^"]*"(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*"parameters"\s*:\s*\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
        json_matches = re.findall(json_pattern, text)
        
        for json_text in json_matches:
            try:
                data = json.loads(json_text)
                if isinstance(data, dict) and "tool" in data and "parameters" in data:
                    return data
            except json.JSONDecodeError:
                continue
        
        # Method 5: Last resort - try to find a simpler pattern and parse it
        simple_pattern = r'(\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^}]+\}\s*\})'
        simple_matches = re.findall(simple_pattern, text)
        
        for json_text in simple_matches:
            try:
                data = json.loads(json_text)
                if isinstance(data, dict) and "tool" in data and "parameters" in data:
                    return data
            except json.JSONDecodeError:
                continue
        
        return None


async def main():
    """Main entry point for the LLM agent."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LLM Agent with MCP integration")
    parser.add_argument('--input', '-i', type=str, help='One-time input to process')
    parser.add_argument('--server', '-s', type=str, default="http://localhost:8000", 
                      help='MCP server URL (default: http://localhost:8000)')
    parser.add_argument('--test-api', '-t', action='store_true', 
                      help='Test the DeepSeek API connection only')
    args = parser.parse_args()
    
    # Load environment variables
    dotenv.load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set")
        sys.exit(1)
    
    # Test API connection if requested
    if args.test_api:
        await test_api_connection(api_key)
        return
    
    try:
        # Initialize the agent
        print(f"Initializing LLM agent with MCP server at {args.server}")
        agent = LLMAgent(args.server, api_key)
        
        # Initialize the connection
        print("Connecting to MCP server...")
        server_info = await agent.initialize_connection()
        print(f"Connected to server: {server_info.get('serverInfo', {}).get('name')}")
        
        # Discover tools
        print("Discovering tools...")
        tools = await agent.discover_tools()
        print(f"Discovered {len(tools)} tools")
        
        if args.input:
            # Process one-time input
            print(f"Processing input: {args.input}")
            response = await agent.process_user_input(args.input)
            print(f"\nAssistant: {response}")
        else:
            # Start interactive loop
            print("\nLLM Agent ready for interaction. Type 'exit' to quit.")
            while True:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                print("Processing...")
                response = await agent.process_user_input(user_input)
                print(f"\nAssistant: {response}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


async def test_api_connection(api_key: str):
    """Test the connection to the DeepSeek API."""
    print("====== TESTING DEEPSEEK API CONNECTION ======")
    url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello!"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    try:
        print("Testing API connectivity...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            print(f"Response status: {response.status_code}")
            
            try:
                data = response.json()
                print(f"Response data: {json.dumps(data, indent=2)}")
                print("API connection successful!")
            except:
                print(f"Raw response: {response.text}")
    except Exception as e:
        print(f"API test error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 
