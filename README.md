# MCP Integration Examples

This project demonstrates different implementations of the Model Context Protocol (MCP).

## Project Structure

- `/custom_mcp`: A custom implementation of MCP with LLM integration
  - Standalone calculator server with add and subtract operations
  - LLM agent that connects directly to the MCP server over HTTP
  - No dependency on official MCP SDK

## Custom MCP Implementation

See the [custom_mcp/README.md](custom_mcp/README.md) for details on the custom implementation.

### Setup and Usage

1. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

2. Set up your DeepSeek API key:
   - Copy `.env.example` to `.env`
   - Add your DeepSeek API key to the `.env` file

3. Start the MCP calculator server (in one terminal):
   ```
   python custom_mcp/calculator_server.py
   ```

4. Run the LLM agent in another terminal:
   ```
   python custom_mcp/llm_agent.py
   ```

5. Enter requests and see the agent use tools as needed
   - Try asking "What is 145 plus 237?"
   - Try asking "Subtract 50 from 100"
   - Try normal questions that don't need tools

## Command Line Options

The LLM agent supports several command line options:

- `--input` or `-i`: Process a single input and exit (e.g., `python custom_mcp/llm_agent.py -i "5+4"`)
- `--server` or `-s`: Specify the MCP server URL (default: http://localhost:8000)
- `--test-api` or `-t`: Test the DeepSeek API connection and exit

## Implementation Details

The custom MCP implementation shows the core flows of an MCP system:

1. **Standalone Components**: Server and agent run independently and communicate via HTTP
2. **Tool Discovery**: The agent discovers tools from the server via standard MCP methods
3. **LLM Integration**: Tool descriptions are formatted and included in the prompt to the LLM
4. **Tool Execution**: When the LLM decides to use a tool, the agent executes it via HTTP
5. **Response Handling**: Tool results are fed back to the LLM for interpretation

This implementation follows the MCP protocol specification while maintaining clear separation between components. 
