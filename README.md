# MCP Integration Examples

This project demonstrates different implementations of the Model Context Protocol (MCP).

## Project Structure

- `/custom_mcp`: A custom implementation of MCP with LLM integration
  - Standalone calculator server with add and subtract operations
  - LLM agent that connects directly to the MCP server over HTTP
  - No dependency on official MCP SDK

- `/sdk_mcp`: An implementation using the official MCP Python SDK
  - Calculator server with add, subtract, multiply, and divide operations
  - LLM agent that uses the MCP client from the SDK
  - Uses the abstractions and utilities provided by the SDK

## Documentation

- [custom_mcp/README.md](custom_mcp/README.md) - Details on the custom implementation
- [sdk_mcp/README.md](sdk_mcp/README.md) - Details on the SDK-based implementation

## Setup

1. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

2. Set up your DeepSeek API key:
   - Copy `.env.example` to `.env`
   - Add your DeepSeek API key to the `.env` file

## Running the Examples

### Custom MCP Implementation

1. Start the custom MCP calculator server (in one terminal):
   ```
   python custom_mcp/calculator_server.py
   ```

2. Run the custom LLM agent in another terminal:
   ```
   python custom_mcp/llm_agent.py
   ```

### SDK-based MCP Implementation

1. Start the SDK-based MCP calculator server (in one terminal):
   ```
   python sdk_mcp/calculator_server.py
   ```

2. Run the SDK-based LLM agent in another terminal:
   ```
   python sdk_mcp/llm_agent.py
   ```

## Example Queries

For both implementations, you can try queries like:
- "What is 145 plus 237?"
- "Subtract 50 from 100"
- "What is 25 multiplied by 4?" (SDK implementation only)
- "Divide 100 by 8" (SDK implementation only)
- Regular questions that don't need tools

## Implementation Comparison

| Feature | Custom MCP | SDK-based MCP |
|---------|------------|---------------|
| Code complexity | Higher (handles protocol details) | Lower (abstractions from SDK) |
| Tools | Add, Subtract | Add, Subtract, Multiply, Divide |
| Port | 8000 | 8001 |
| External dependencies | None for MCP, but requires httpx | MCP Python SDK + httpx |
| Protocol compliance | Manual implementation | Managed by SDK |

## Command Line Options

Both LLM agents support these command line options:

- `--input` or `-i`: Process a single input and exit (e.g., `python sdk_mcp/llm_agent.py -i "5+4"`)
- `--server` or `-s`: Specify the MCP server URL
- `--test-api` or `-t`: Test the DeepSeek API connection and exit
