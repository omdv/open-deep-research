"""Simplified utility functions for the Deep Research agent."""

from typing import List, Optional

import aiohttp
from langchain_core.messages import (
  AIMessage,
  MessageLikeRepresentation,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool, tool
from open_deep_research.configuration import Configuration, SearchAPI
from open_deep_research.state import ResearchComplete

##########################
# Financial Modeling Prep Tools
##########################
# Import all FMP tools from the tools package
from open_deep_research.tools.fmp.tools import (
  get_balance_sheet,
  get_cash_flow,
  get_company_profile,
  get_economic_events,
  get_stock_quote,
  get_income_statement,
  get_key_metrics,
  get_eod_quotes,
  get_stock_news,
  get_treasury_rates,
)

##########################
# Search Tools
##########################
from open_deep_research.tools.tavily.tools import tavily_search

##########################
# MCP Utils (Simplified)
##########################


async def simple_mcp_tool_call(tool_name: str, args: dict, mcp_url: str) -> str:
  """Make a simple HTTP call to MCP server tool.

  Args:
      tool_name: Name of the tool to call
      args: Arguments for the tool
      mcp_url: Base URL of the MCP server

  Returns:
      Tool result as string
  """
  try:
    async with aiohttp.ClientSession() as session:
      # Map tool names to actual endpoints
      endpoint_map = {
        "get_company_profile": "/financial/company_profile",
      }

      if tool_name in endpoint_map:
        tool_url = f"{mcp_url.rstrip('')}{endpoint_map[tool_name]}"
        # Use GET for FastAPI endpoints with query parameters
        params = args
        async with session.get(tool_url, params=params) as response:
          if response.status == 200:
            result = await response.text()
            return result
          return f"Error calling tool {tool_name}: HTTP {response.status}"
      else:
        return f"Unknown tool: {tool_name}"

  except Exception as e:
    return f"Error calling tool {tool_name}: {e!s}"


async def load_simple_mcp_tools(
  config: RunnableConfig,
  existing_tool_names: set[str],
) -> list[BaseTool]:
  """Load simple MCP tools using direct HTTP calls.

  Args:
      config: Runtime configuration containing MCP server details
      existing_tool_names: Set of tool names already in use to avoid conflicts

  Returns:
      List of simple MCP tools
  """
  configurable = Configuration.from_runnable_config(config)

  if not configurable.mcp_config or not configurable.mcp_config.url:
    return []

  mcp_url = configurable.mcp_config.url
  tools = []

  # Create simple tools for each configured tool
  for tool_name in configurable.mcp_config.tools or []:
    if tool_name in existing_tool_names:
      continue

    # Create a simple tool that calls the MCP server
    async def make_tool_func(name):
      async def tool_func(**kwargs):
        return await simple_mcp_tool_call(name, kwargs, mcp_url)

      return tool_func

    tool_func = await make_tool_func(tool_name)

    tool = StructuredTool.from_function(
      func=tool_func,
      name=tool_name,
      description=f"Financial tool: {tool_name}",
      coroutine=tool_func,
    )

    tools.append(tool)

  return tools


##########################
# Utility Functions
##########################


@tool()
def think_tool(reflection: str) -> str:
  """Record thoughts and reasoning during research.

  Args:
      reflection: Your thoughts, reasoning, or planning notes

  Returns:
      Confirmation that the reflection was recorded
  """
  return f"Reflection recorded: {reflection}"


def get_model_token_limit(model_name: str) -> Optional[int]:
  """Get the token limit for a specific model."""
  # Simple model token limits mapping
  model_limits = {
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4.1": 128000,
    "gpt-4.1-mini": 128000,
    "gpt-5": 200000,
    "claude-3-haiku": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-opus": 200000,
    "claude-sonnet-4": 200000,
  }

  # Extract model name without provider prefix
  clean_model = model_name.split(":")[-1] if ":" in model_name else model_name

  return model_limits.get(clean_model)


def is_token_limit_exceeded(error: Exception, model_name: str) -> bool:
  """Check if an error indicates token limit was exceeded."""
  error_str = str(error).lower()
  token_limit_indicators = [
    "token limit",
    "context length",
    "maximum context",
    "too many tokens",
    "context window",
  ]

  return any(indicator in error_str for indicator in token_limit_indicators)


def remove_up_to_last_ai_message(
  messages: List[MessageLikeRepresentation],
) -> List[MessageLikeRepresentation]:
  """Remove messages from the beginning up to (and including) the last AI message."""
  # Find the index of the last AI message
  last_ai_index = -1
  for i in range(len(messages) - 1, -1, -1):
    if isinstance(messages[i], AIMessage):
      last_ai_index = i
      break

  # If no AI message found, return original messages
  if last_ai_index == -1:
    return messages

  # Return messages after the last AI message
  return messages[last_ai_index + 1 :]


def get_notes_from_tool_calls(messages: List[MessageLikeRepresentation]) -> List[str]:
  """Extract notes from think_tool calls and research findings from ConductResearch tool messages."""
  notes = []

  for message in messages:
    # Extract think_tool reflections
    if hasattr(message, "tool_calls") and message.tool_calls:
      for tool_call in message.tool_calls:
        if tool_call.get("name") == "think_tool":
          args = tool_call.get("args", {})
          if "reflection" in args:
            notes.append(args["reflection"])

    # Extract ConductResearch findings from ToolMessage responses
    if hasattr(message, "name") and message.name == "ConductResearch":
      if hasattr(message, "content") and message.content:
        # This contains the compressed research findings
        notes.append(str(message.content))

  return notes


def openai_websearch_called(message: AIMessage) -> bool:
  """Check if OpenAI native web search was called in a message."""
  # Check if the message content contains web search indicators
  content = str(message.content) if message.content else ""
  return "web_search" in content.lower() or "searching the web" in content.lower()


def anthropic_websearch_called(message: AIMessage) -> bool:
  """Check if Anthropic native web search was called in a message."""
  # Similar check for Anthropic web search patterns
  content = str(message.content) if message.content else ""
  return "web search" in content.lower() or "searched for" in content.lower()


##########################
# Main Tool Loading Function
##########################


async def get_all_tools(config: RunnableConfig) -> List[BaseTool]:
  """Get all available tools based on configuration."""
  configurable = Configuration.from_runnable_config(config)
  tools = []
  existing_tool_names = set()

  # Add think_tool for strategic planning
  tools.append(think_tool)
  existing_tool_names.add("think_tool")

  # Add ResearchComplete tool for signaling completion
  tools.append(ResearchComplete)
  existing_tool_names.add("ResearchComplete")

  # Add search tools based on configuration
  if configurable.search_api == SearchAPI.TAVILY:
    tools.append(tavily_search)
    existing_tool_names.add("tavily_search")

  # Add Financial Modeling Prep tools
  fmp_tools = [
    get_company_profile,
    get_stock_quote,
    get_eod_quotes,
    get_economic_events,
    get_treasury_rates,
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
    get_key_metrics,
    get_stock_news,
  ]

  for fmp_tool in fmp_tools:
    tools.append(fmp_tool)
    existing_tool_names.add(fmp_tool.name)

  return tools
