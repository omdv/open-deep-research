"""Financial Modeling Prep API client."""

import logging
import os
import ssl
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class FMPError(Exception):
  """Custom exception for FMP API errors."""

  def __init__(self, status_code: int, message: str = ""):
    self.status_code = status_code
    self.message = message
    super().__init__(f"FMP API error {status_code}: {message}")


class FMPClient:
  """Financial Modeling Prep API client."""

  def __init__(self, api_key: Optional[str] = None):
    """Initialize the FMP client."""
    self.api_key = api_key or os.getenv("FMP_API_KEY")
    if not self.api_key:
      raise ValueError(
        "FMP_API_KEY must be provided or set as environment variable",
      )

    self.base_url = "https://financialmodelingprep.com/api/v3"
    self.timeout = 30

  async def _make_request(
    self,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
  ) -> Any:
    """Make an HTTP request to the FMP API."""
    url = f"{self.base_url}/{endpoint.lstrip('/')}"
    request_params = {"apikey": self.api_key}
    if params:
      request_params.update(params)

    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(connector=connector) as session:
      try:
        async with session.get(
          url,
          params=request_params,
          timeout=self.timeout,
        ) as response:
          if response.status not in [200, 201]:
            error_text = await response.text()
            raise FMPError(response.status, error_text)

          data = await response.json()
          if not data and response.status == 200:
            raise FMPError(404, "No data found")

          return data
      except aiohttp.ClientError as e:
        raise FMPError(500, str(e))

  # Company Profile and Information
  async def get_company_profile(self, symbol: str) -> Dict[str, Any]:
    """Get company profile information."""
    data = await self._make_request(f"profile/{symbol}")
    return data[0] if isinstance(data, list) and data else data

  # Stock Quotes
  async def get_full_quote(self, symbol: str) -> Dict[str, Any]:
    """Get full stock quote with detailed information."""
    data = await self._make_request(f"quote/{symbol}")
    return data[0] if isinstance(data, list) and data else data

  async def get_short_quote(self, symbol: str) -> Dict[str, Any]:
    """Get short stock quote with basic price and volume."""
    data = await self._make_request(f"quote-short/{symbol}")
    return data[0] if isinstance(data, list) and data else data

  # Economic Data
  async def get_economic_events(
    self,
    from_date: str,
    to_date: str,
    impact: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,
  ) -> List[Dict[str, Any]]:
    """Get economic events for a date range."""
    # Validate date range (max 30 days)
    from_dt = datetime.strptime(from_date, "%Y-%m-%d")
    to_dt = datetime.strptime(to_date, "%Y-%m-%d")

    if (to_dt - from_dt).days > 30:
      to_date = (from_dt + timedelta(days=30)).strftime("%Y-%m-%d")
      logger.warning(
        f"Date range limited to 30 days, adjusted to: {from_date} to {to_date}",
      )

    params = {"from": from_date, "to": to_date}
    data = await self._make_request("economic_calendar", params)

    # Filter by impact and countries if provided
    if impact or countries:
      impact = impact or ["High", "Medium"]
      countries = countries or ["US", "EA"]

      filtered_data = [
        event
        for event in data
        if event.get("impact") in impact and event.get("country") in countries
      ]
      return filtered_data

    return data

  async def get_treasury_rates(self) -> List[Dict[str, Any]]:
    """Get treasury rates for the past 30 days."""
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # Use the stable endpoint for treasury rates
    url = "https://financialmodelingprep.com/stable/treasury-rates"
    params = {"from": from_date, "to": to_date, "apikey": self.api_key}

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(connector=connector) as session:
      async with session.get(
        url,
        params=params,
        timeout=self.timeout,
      ) as response:
        if response.status not in [200, 201]:
          raise FMPError(response.status, await response.text())
        return await response.json()

  # Financial Statements
  async def get_income_statement(
    self,
    symbol: str,
    period: str = "annual",
    limit: int = 5,
  ) -> List[Dict[str, Any]]:
    """Get income statement data."""
    params = {"period": period, "limit": str(limit)}
    return await self._make_request(f"income-statement/{symbol}", params)

  async def get_balance_sheet(
    self,
    symbol: str,
    period: str = "annual",
    limit: int = 5,
  ) -> List[Dict[str, Any]]:
    """Get balance sheet data."""
    params = {"period": period, "limit": str(limit)}
    return await self._make_request(f"balance-sheet-statement/{symbol}", params)

  async def get_cash_flow(
    self,
    symbol: str,
    period: str = "annual",
    limit: int = 5,
  ) -> List[Dict[str, Any]]:
    """Get cash flow statement data."""
    params = {"period": period, "limit": str(limit)}
    return await self._make_request(f"cash-flow-statement/{symbol}", params)

  # Key Metrics
  async def get_key_metrics(
    self,
    symbol: str,
    period: str = "annual",
    limit: int = 5,
  ) -> List[Dict[str, Any]]:
    """Get key financial metrics."""
    params = {"period": period, "limit": str(limit)}
    return await self._make_request(f"key-metrics/{symbol}", params)

  async def get_financial_ratios(
    self,
    symbol: str,
    period: str = "annual",
    limit: int = 5,
  ) -> List[Dict[str, Any]]:
    """Get financial ratios."""
    params = {"period": period, "limit": str(limit)}
    return await self._make_request(f"ratios/{symbol}", params)

  # Market Data
  async def get_historical_price(
    self,
    symbol: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
  ) -> List[Dict[str, Any]]:
    """Get historical price data."""
    params = {}
    if from_date:
      params["from"] = from_date
    if to_date:
      params["to"] = to_date

    return await self._make_request(f"historical-price-full/{symbol}", params)

  # Analyst Estimates
  async def get_analyst_estimates(
    self,
    symbol: str,
    period: str = "annual",
    limit: int = 5,
  ) -> List[Dict[str, Any]]:
    """Get analyst estimates."""
    params = {"period": period, "limit": str(limit)}
    return await self._make_request(f"analyst-estimates/{symbol}", params)

  # News and Events
  async def get_stock_news(
    self,
    symbols: Optional[List[str]] = None,
    limit: int = 50,
  ) -> List[Dict[str, Any]]:
    """Get stock news."""
    params = {"limit": str(limit)}
    if symbols:
      params["tickers"] = ",".join(symbols)

    return await self._make_request("stock_news", params)

  # Symbol Search
  async def search_symbols(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for stock symbols."""
    params = {"query": query, "limit": str(limit)}
    return await self._make_request("search", params)

  async def get_symbol_list(self) -> List[Dict[str, Any]]:
    """Get list of all available symbols."""
    return await self._make_request("stock/list")
