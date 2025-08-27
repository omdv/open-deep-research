# Simplified Open Deep Research Setup

This is a simplified version of Open Deep Research that removes Supabase authentication and uses only the core implementation in `src/open_deep_research/` with a simple MCP server for financial APIs.

## Quick Start

### 1. Install Dependencies
```bash
uv sync
```

### 2. Set Environment Variables
Create a `.env` file with:
```bash
# Required for research
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Required for financial MCP server
FMP_API_KEY=your_financial_modeling_prep_api_key_here

# Optional: Other model providers
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. Start the MCP Server (Terminal 1)
```bash
python run_mcp_server.py
```
This will start the financial MCP server at http://127.0.0.1:8000

### 4. Start the Research Agent (Terminal 2)
```bash
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
```

## What Was Simplified

### Removed:
- Supabase authentication and database
- Complex MCP authentication flows
- Security directory and auth handlers
- Legacy implementations (`src/legacy/`)
- Complex token management

### Kept:
- Core research workflow (`src/open_deep_research/`)
- Tavily search integration
- Multiple model provider support
- Evaluation framework
- Simple MCP server for financial data

## Architecture

### Core Components:
- `src/open_deep_research/deep_researcher.py` - Main LangGraph workflow
- `src/open_deep_research/configuration.py` - Simplified configuration
- `src/open_deep_research/utils.py` - Simplified utilities without authentication
- `src/open_deep_research/mcp_server.py` - Simple financial MCP server

### MCP Server:
- **Tool**: `get_company_profile(symbol: str)` - Get company information
- **API**: Financial Modeling Prep (requires FMP_API_KEY)
- **Endpoint**: http://127.0.0.1:8000/tools/get_company_profile

## Configuration

The agent is configured to use:
- **MCP URL**: http://127.0.0.1:8000 (local MCP server)
- **MCP Tools**: ["get_company_profile"]
- **Search API**: Tavily (default)
- **Models**: OpenAI GPT models (configurable)

## Usage Example

1. Start both servers as described above
2. Go to LangGraph Studio UI
3. Ask: "Research Apple Inc's financial performance and recent developments"
4. The agent will use both Tavily search and the financial MCP tool to provide comprehensive research

## API Keys Required

### Financial Modeling Prep API
- Get your free API key at: https://financialmodelingprep.com/developer/docs
- Add to `.env` as `FMP_API_KEY=your_key_here`

### Tavily Search API  
- Get your free API key at: https://tavily.com/
- Add to `.env` as `TAVILY_API_KEY=your_key_here`

### OpenAI API
- Get your API key at: https://platform.openai.com/api-keys
- Add to `.env` as `OPENAI_API_KEY=your_key_here`

## Testing the MCP Server

You can test the MCP server directly:
```bash
curl -X POST http://127.0.0.1:8000/tools/get_company_profile \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

This should return Apple's company profile information.