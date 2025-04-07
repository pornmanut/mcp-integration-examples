# Custom MCP Implementation

This directory contains a custom implementation of the Model Context Protocol (MCP).

## Components

- `calculator_server.py`: A standalone MCP server that provides calculator tools and listens on HTTP.
- `llm_agent.py`: An agent that uses an LLM (DeepSeek) to interact with MCP tools, connecting directly to the MCP server via HTTP.

## Usage

### Calculator Server

Run the calculator server:

```bash
python calculator_server.py
```

This will start an MCP server on localhost:8000 with the following calculator tools:
- `calculator:add` - Add two numbers together
- `calculator:subtract` - Subtract the second number from the first

### LLM Agent

Run the LLM agent to interact with the calculator:

```bash
python llm_agent.py
```

The agent will:
1. Connect to the MCP server
2. Discover available tools
3. Allow users to input queries
4. Process these through an LLM
5. Execute any requested tools and return results

This implementation demonstrates how to create a custom MCP server and client without relying on the official MCP SDK. 
