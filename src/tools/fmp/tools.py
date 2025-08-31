"""Financial Modeling Prep API tools for Open Deep Research."""

import json
import logging
from datetime import datetime
from typing import List, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from .client import FMPClient, FMPError

logger = logging.getLogger(__name__)


def _format_fmp_response(
  data: dict | list,
  symbol: str,
  endpoint_name: str,
  api_endpoint: str,
) -> str:
  """Format FMP API response with citation-friendly source attribution.

  Args:
      data: The JSON data from FMP API
      symbol: Stock symbol (if applicable)
      endpoint_name: Human-readable endpoint name
      api_endpoint: Actual API endpoint path

  Returns:
      Formatted string with data and inline citations
  """
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
  base_url = "https://financialmodelingprep.com/api/v3"
  full_url = f"{base_url}{api_endpoint}"

  # Create citation-friendly format
  source_title = f"Financial Modeling Prep - {endpoint_name}"
  if symbol:
    source_title += f" ({symbol})"
  source_title += f" - Retrieved {timestamp}"

  return f"""{json.dumps(data, indent=2)}

Source: {source_title}: {full_url}"""


def _get_fmp_client() -> FMPClient:
  """Get FMP client instance."""
  try:
    return FMPClient()
  except ValueError:
    logger.exception("Failed to initialize FMP client")
    raise


# Company Information Tools
@tool(
  description="Get comprehensive company profile information including CEO, market cap, industry, sector, and business description",
)
async def get_company_profile(
  symbol: str, _: RunnableConfig = None,
) -> str:
  """Get comprehensive company profile information.

  Args:
      symbol: Stock symbol (e.g., AAPL, GOOGL, MSFT)
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string with company profile data
  """
  logger.info("Getting company profile for %s", symbol)

  try:
    client = _get_fmp_client()
    company = await client.get_company_profile(symbol)

    return _format_fmp_response(
      data=company,
      symbol=symbol,
      endpoint_name="Company Profile",
      api_endpoint=f"/profile/{symbol}",
    )

  except FMPError:
    logger.exception("FMP API error for %s", symbol)
    return f"Error getting company profile for {symbol}"
  except Exception:
    logger.exception("Unexpected error for %s", symbol)
    return f"Error getting company profile for {symbol}"


# Stock Quote Tools


@tool(
  description="Get stock quote with price, volume, P/E ratio, market cap, year high/low for stocks and indices. Use ^ prefix for major indices (^GSPC, ^IXIC, ^DJI, ^VIX, ^SPX)",
)
async def get_stock_quote(
  symbol: str,
  _: RunnableConfig = None,
) -> str:
  """Get stock quote with detailed information for stocks and indices.

  Args:
      symbol: Stock or index symbol (e.g., AAPL, GOOGL, MSFT, ^SPX, ^DJI, ^VIX)
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string with stock quote data
  """
  logger.info("Getting quote for %s", symbol)

  try:
    client = _get_fmp_client()
    quote = await client.get_quote(symbol)

    return _format_fmp_response(
      data=quote,
      symbol=symbol,
      endpoint_name="Stock Quote",
      api_endpoint=f"/quote/{symbol}",
    )

  except FMPError:
    return f"Error getting quote for {symbol}"
  except Exception:
    logger.exception("Unexpected error for %s", symbol)
    return f"Error getting quote for {symbol}"

@tool(
  description="Get historical end-of-day price data for stocks and indices - useful for daily price analysis and long-term chart patterns. Use ^ prefix for major indices (^DJI, ^VIX, ^SPX). Use ^GSPC for ^SPX.",
)
async def get_eod_quotes(
  symbol: str,
  from_date: Optional[str] = None,
  to_date: Optional[str] = None,
  _: RunnableConfig = None,
) -> str:
  """Get historical end-of-day quotes for stocks and indices.

  Args:
      symbol: Stock or index symbol (e.g., AAPL, SPY, QQQ, DIA, IWM, VTI, ^GSPC, ^IXIC, ^DJI, ^VIX, ^SPX)
      from_date: Start date in YYYY-MM-DD format (optional)
      to_date: End date in YYYY-MM-DD format (optional)
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string with historical end-of-day price data
  """
  logger.info("Getting end-of-day quotes for %s", symbol)

  try:
    client = _get_fmp_client()
    chart_data = await client.get_eod_quotes(symbol, from_date, to_date)

    # Build endpoint URL with parameters for the stable endpoint
    endpoint = f"/stable/historical-price-eod/light?symbol={symbol}"
    if from_date or to_date:
      params = []
      if from_date:
        params.append(f"from={from_date}")
      if to_date:
        params.append(f"to={to_date}")
      endpoint += f"&{'&'.join(params)}"

    return _format_fmp_response(
      data=chart_data,
      symbol=symbol,
      endpoint_name="End-of-Day Quotes",
      api_endpoint=endpoint,
    )

  except FMPError:
    return f"Error getting end-of-day quotes for {symbol}"
  except Exception:
    return f"Error getting end-of-day quotes for {symbol}"


# Economic Data Tools


@tool(
  description="Get economic calendar events like CPI, GDP, Fed meetings, and other market-moving events for specific date ranges",
)
async def get_economic_events(
  from_date: str,
  to_date: str,
  impact: Optional[List[str]] = None,
  countries: Optional[List[str]] = None,
  config: RunnableConfig = None,
) -> str:
  """Get economic events for a given date range.

  Args:
      from_date: Start date in YYYY-MM-DD format
      to_date: End date in YYYY-MM-DD format (max 30 days from start)
      impact: List of impact levels to filter by (High, Medium, Low)
      countries: List of country codes to filter by (US, EA, etc.)
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string containing economic events
  """
  logger.info("Getting economic events from %s to %s", from_date, to_date)

  try:
    client = _get_fmp_client()
    events = await client.get_economic_events(
      from_date,
      to_date,
      impact=impact,
      countries=countries,
    )

    return _format_fmp_response(
      data=events,
      symbol="",
      endpoint_name="Economic Calendar Events",
      api_endpoint=f"/api/v3/economic_calendar?from={from_date}&to={to_date}",
    )

  except FMPError:
    return "Error getting economic events"
  except Exception:
    return "Error getting economic events"


@tool(
  description="Get current US Treasury rates for various maturities (1m, 3m, 6m, 1y, 2y, 5y, 10y, 30y) for the past 30 days",
)
async def get_treasury_rates(_: RunnableConfig = None) -> str:
  """Get US Treasury rates for the past 30 days.

  Args:
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string containing treasury rates data
  """
  logger.info("Getting treasury rates")

  try:
    client = _get_fmp_client()
    rates = await client.get_treasury_rates()

    return _format_fmp_response(
      data=rates,
      symbol="",
      endpoint_name="US Treasury Rates",
      api_endpoint="/treasury",
    )

  except FMPError:
    return "Error getting treasury rates"
  except Exception:
    return "Error getting treasury rates"


# Financial Statements Tools


@tool(
  description="Get company income statement data including revenue, gross profit, operating income, and net income for multiple periods",
)
async def get_income_statement(
  symbol: str,
  period: str = "annual",
  limit: int = 5,
  _: RunnableConfig = None,
) -> str:
  """Get income statement data for a company.

  Args:
      symbol: Stock symbol (e.g., AAPL, GOOGL, MSFT)
      period: "annual" or "quarter"
      limit: Number of periods to retrieve (default 5)
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string with income statement data
  """
  logger.info("Getting income statement for %s", symbol)

  try:
    client = _get_fmp_client()
    statements = await client.get_income_statement(symbol, period, limit)

    return _format_fmp_response(
      data=statements,
      symbol=symbol,
      endpoint_name=f"Income Statement ({period})",
      api_endpoint=f"/income-statement/{symbol}?period={period}&limit={limit}",
    )

  except FMPError:
    return f"Error getting income statement for {symbol}"
  except Exception:
    return f"Error getting income statement for {symbol}"


@tool(
  description="Get company balance sheet data including total assets, liabilities, equity, and cash positions",
)
async def get_balance_sheet(
  symbol: str,
  period: str = "annual",
  limit: int = 5,
  _: RunnableConfig = None,
) -> str:
  """Get balance sheet data for a company.

  Args:
      symbol: Stock symbol (e.g., AAPL, GOOGL, MSFT)
      period: "annual" or "quarter"
      limit: Number of periods to retrieve (default 5)
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string with balance sheet data
  """
  logger.info("Getting balance sheet for %s", symbol)

  try:
    client = _get_fmp_client()
    statements = await client.get_balance_sheet(symbol, period, limit)

    return _format_fmp_response(
      data=statements,
      symbol=symbol,
      endpoint_name=f"Balance Sheet ({period})",
      api_endpoint=f"/balance-sheet-statement/{symbol}?period={period}&limit={limit}",
    )

  except FMPError:
    return f"Error getting balance sheet for {symbol}"
  except Exception:
    return f"Error getting balance sheet for {symbol}"


@tool(
  description="Get company cash flow statement including operating, investing, and financing cash flows plus free cash flow",
)
async def get_cash_flow(
  symbol: str,
  period: str = "annual",
  limit: int = 5,
  _: RunnableConfig = None,
) -> str:
  """Get cash flow statement data for a company.

  Args:
      symbol: Stock symbol (e.g., AAPL, GOOGL, MSFT)
      period: "annual" or "quarter"
      limit: Number of periods to retrieve (default 5)
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string with cash flow statement data
  """
  logger.info("Getting cash flow for %s", symbol)

  try:
    client = _get_fmp_client()
    statements = await client.get_cash_flow(symbol, period, limit)

    return _format_fmp_response(
      data=statements,
      symbol=symbol,
      endpoint_name=f"Cash Flow Statement ({period})",
      api_endpoint=f"/cash-flow-statement/{symbol}?period={period}&limit={limit}",
    )

  except FMPError:
    return f"Error getting cash flow for {symbol}"
  except Exception:
    return f"Error getting cash flow for {symbol}"


# Key Metrics and Ratios


@tool(
  description="Get key financial metrics including P/E ratio, ROE, ROA, debt ratios, and market valuation metrics",
)
async def get_key_metrics(
  symbol: str,
  period: str = "annual",
  limit: int = 5,
  _: RunnableConfig = None,
) -> str:
  """Get key financial metrics for a company.

  Args:
      symbol: Stock symbol (e.g., AAPL, GOOGL, MSFT)
      period: "annual" or "quarter"
      limit: Number of periods to retrieve (default 5)
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string with key metrics data
  """
  logger.info("Getting key metrics for %s", symbol)

  try:
    client = _get_fmp_client()
    metrics = await client.get_key_metrics(symbol, period, limit)

    return _format_fmp_response(
      data=metrics,
      symbol=symbol,
      endpoint_name=f"Key Financial Metrics ({period})",
      api_endpoint=f"/key-metrics/{symbol}?period={period}&limit={limit}",
    )

  except FMPError:
    return f"Error getting key metrics for {symbol}"
  except Exception:
    return f"Error getting key metrics for {symbol}"


# Search Tools


@tool(
  description="Search for stock symbols by company name - useful when you need to find the ticker symbol for a company",
)
async def search_stock_symbols(
  query: str,
  limit: int = 10,
  _: RunnableConfig = None,
) -> str:
  """Search for stock symbols by company name or partial match.

  Args:
      query: Company name or partial name to search for
      limit: Maximum number of results to return (default 10)
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string with search results
  """
  logger.info("Searching symbols for query: %s", query)

  try:
    client = _get_fmp_client()
    results = await client.search_symbols(query, limit)

    return _format_fmp_response(
      data=results,
      symbol="",
      endpoint_name="Symbol Search",
      api_endpoint=f"/stable/search-symbol?query={query}&limit={limit}",
    )

  except FMPError:
    return "Error searching symbols"
  except Exception:
    return "Error searching symbols"


@tool(
  description="Get recent news articles about specific stocks - useful for current events. Will not work for indices.",
)
async def get_stock_news(
  symbols: Optional[List[str]] = None,
  limit: int = 20,
  _: RunnableConfig = None,
) -> str:
  """Get recent stock news articles.

  Args:
      symbols: List of stock symbols to filter news (optional)
      limit: Maximum number of articles to return (default 20)
      config: Runtime configuration (unused but kept for consistency)

  Returns:
      JSON string with news articles
  """
  symbols_str = ", ".join(symbols) if symbols else "general"
  logger.info("Getting stock news for symbols: %s", symbols_str)

  try:
    client = _get_fmp_client()
    news = await client.get_stock_news(symbols, limit)

    symbols_param = ",".join(symbols) if symbols else ""
    return _format_fmp_response(
      data=news,
      symbol=symbols_param,
      endpoint_name="Stock News",
      api_endpoint=f"/stable/news/stock?symbols={symbols_param}&limit={limit}"
      if symbols
      else f"/stable/news/stock?limit={limit}",
    )

  except FMPError:
    return "Error getting stock news"
  except Exception:
    return "Error getting stock news"
