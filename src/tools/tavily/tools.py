"""Tavily search tools for Open Deep Research."""

import asyncio
import logging
import os
from typing import Annotated, Dict, List, Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from open_deep_research.configuration import Configuration
from open_deep_research.helpers import get_api_key_for_model, get_today_str
from open_deep_research.prompts import summarize_webpage_prompt
from open_deep_research.state import Summary
from tavily import AsyncTavilyClient

logger = logging.getLogger(__name__)


TAVILY_SEARCH_DESCRIPTION = (
  "A search engine optimized for comprehensive, accurate, and trusted results. "
  "Useful for when you need to answer questions about current events."
)


@tool(description=TAVILY_SEARCH_DESCRIPTION)
async def tavily_search(
  queries: List[str],
  max_results: Annotated[int, InjectedToolArg] = 5,
  topic: Annotated[
    Literal["general", "news", "finance"],
    InjectedToolArg,
  ] = "general",
  config: RunnableConfig = None,
) -> str:
  """Fetch and summarize search results from Tavily search API.

  Args:
      queries: List of search queries to execute
      max_results: Maximum number of results to return per query
      topic: Topic filter for search results (general, news, or finance)
      config: Runtime configuration for API keys and model settings

  Returns:
      Formatted string containing summarized search results
  """
  # Add logging to see when tool is called
  print(f"🔍 TAVILY TOOL CALLED: Searching for queries: {queries}")
  logger.info(f"Tavily Tool called with queries: {queries}")

  # Step 1: Execute search queries asynchronously
  search_results = await tavily_search_async(
    queries,
    max_results=max_results,
    topic=topic,
    include_raw_content=True,
    config=config,
  )

  # Step 2: Deduplicate results by URL to avoid processing the same content multiple times
  unique_results = {}
  for response in search_results:
    for result in response["results"]:
      url = result["url"]
      if url not in unique_results:
        unique_results[url] = {**result, "query": response["query"]}

  # Step 3: Set up the summarization model with configuration
  configurable = Configuration.from_runnable_config(config)

  # Character limit to stay within model token limits (configurable)
  max_char_to_include = configurable.max_content_length

  # Initialize summarization model with retry logic
  model_api_key = get_api_key_for_model(configurable.summarization_model, config)
  summarization_model = (
    init_chat_model(
      model=configurable.summarization_model,
      max_tokens=configurable.summarization_model_max_tokens,
      api_key=model_api_key,
      tags=["langsmith:nostream"],
    )
    .with_structured_output(Summary)
    .with_retry(
      stop_after_attempt=configurable.max_structured_output_retries,
    )
  )

  # Step 4: Create summarization tasks (skip empty content)
  async def noop():
    """No-op function for results without raw content."""
    return

  summarization_tasks = [
    summarization_model.ainvoke(
      [
        HumanMessage(
          content=summarize_webpage_prompt.format(
            webpage_content=result.get("raw_content", "")[:max_char_to_include],
            date=get_today_str(),
          ),
        ),
      ],
    )
    if result.get("raw_content")
    else noop()
    for result in unique_results.values()
  ]

  # Step 5: Execute all summarization tasks concurrently
  summaries = await asyncio.gather(*summarization_tasks)

  # Step 6: Format and return results
  formatted_results = []
  for result, summary in zip(unique_results.values(), summaries, strict=False):
    if summary is None:
      # Use basic result info when no raw content is available
      formatted_result = f"Title: {result.get('title', 'No title')}\n"
      formatted_result += f"URL: {result.get('url', 'No URL')}\n"
      formatted_result += f"Content: {result.get('content', 'No content available')}\n"
    else:
      # Use AI-generated summary
      formatted_result = f"Title: {result.get('title', 'No title')}\n"
      formatted_result += f"URL: {result.get('url', 'No URL')}\n"
      formatted_result += f"Summary: {summary.summary}\n"
      formatted_result += f"Key Excerpts: {summary.key_excerpts}\n"

    formatted_results.append(formatted_result)

  return "\n" + "\n---\n".join(formatted_results)


async def tavily_search_async(
  queries: List[str],
  max_results: int = 5,
  topic: Literal["general", "news", "finance"] = "general",
  include_raw_content: bool = True,
  config: RunnableConfig = None,
) -> List[Dict]:
  """Execute multiple Tavily search queries asynchronously."""
  api_key = os.getenv("TAVILY_API_KEY")
  if not api_key:
    return [
      {
        "query": query,
        "results": [
          {
            "title": "Error",
            "content": "TAVILY_API_KEY not found",
            "url": "",
          },
        ],
      }
      for query in queries
    ]

  tavily = AsyncTavilyClient(api_key=api_key)

  # Create search tasks for all queries
  search_tasks = [
    tavily.search(
      query=query,
      max_results=max_results,
      topic=topic,
      include_raw_content=include_raw_content,
    )
    for query in queries
  ]

  try:
    # Execute all searches concurrently
    results = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Process results and handle exceptions
    formatted_results = []
    for query, result in zip(queries, results, strict=False):
      if isinstance(result, Exception):
        # Handle search errors gracefully
        formatted_results.append(
          {
            "query": query,
            "results": [
              {
                "title": "Search Error",
                "content": f"Error searching for '{query}': {result!s}",
                "url": "",
              },
            ],
          },
        )
      else:
        # Add query context to successful results
        formatted_results.append(
          {
            "query": query,
            "results": result.get("results", []),
          },
        )

    return formatted_results

  except Exception as e:
    # Fallback for unexpected errors
    return [
      {
        "query": query,
        "results": [{"title": "Error", "content": str(e), "url": ""}],
      }
      for query in queries
    ]
