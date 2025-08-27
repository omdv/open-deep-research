"""Simple MCP server for Financial Modeling Prep API using FastAPI-MCP."""

import logging
import os
import ssl

import aiohttp
from fastapi import APIRouter, FastAPI
from fastapi_mcp import FastApiMCP

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Financial Modeling Prep API Key from environment
FMP_API_KEY = os.getenv("FMP_API_KEY")

# Initialize FastAPI app
app = FastAPI(title="Financial MCP Server", version="1.0.0")

# Create router for financial tools
financial_router = APIRouter(prefix="/financial", tags=["financial"])


@financial_router.get(
  "/company_profile",
  operation_id="get_company_profile",
  response_model=str,
)
async def get_company_profile(symbol: str) -> str:
  """Get company profile information using Financial Modeling Prep API.

  Args:
      symbol: Stock symbol (e.g., AAPL, GOOGL, MSFT)
  """
  logger.info(f"🔧 MCP TOOL CALLED: get_company_profile for symbol: {symbol}")

  if not FMP_API_KEY:
    logger.error("FMP_API_KEY not configured")
    return "Error: FMP_API_KEY not configured"

  url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}"
  params = {"apikey": FMP_API_KEY}

  # Create SSL context that doesn't verify certificates
  ssl_context = ssl.create_default_context()
  ssl_context.check_hostname = False
  ssl_context.verify_mode = ssl.CERT_NONE

  # Create connector with SSL context
  connector = aiohttp.TCPConnector(ssl=ssl_context)

  async with aiohttp.ClientSession(connector=connector) as session:
    try:
      async with session.get(url, params=params) as response:
        if response.status != 200:
          return f"Error: HTTP {response.status}"

        data = await response.json()

        if not data:
          return f"No company profile found for {symbol}"

        if isinstance(data, list) and len(data) > 0:
          company = data[0]
        elif isinstance(data, dict):
          company = data
        else:
          return f"Invalid data format received for {symbol}"

        mkt_cap = company.get("mktCap")
        mkt_cap_str = f"${mkt_cap:,}" if mkt_cap else "N/A"

        return f"""Company Profile for {symbol}:
Company Name: {company.get("companyName", "N/A")}
Symbol: {company.get("symbol", "N/A")}
Price: ${company.get("price", "N/A")}
Beta: {company.get("beta", "N/A")}
Market Cap: {mkt_cap_str}
Last Dividend: ${company.get("lastDiv", "N/A")}
Range: ${company.get("range", "N/A")}
Changes: {company.get("changes", "N/A")}%
Industry: {company.get("industry", "N/A")}
Sector: {company.get("sector", "N/A")}
Country: {company.get("country", "N/A")}
CEO: {company.get("ceo", "N/A")}
Website: {company.get("website", "N/A")}
Description: {company.get("description", "N/A")[:300]}...
Exchange: {company.get("exchangeShortName", "N/A")}
Full-time Employees: {company.get("fullTimeEmployees", "N/A")}"""

    except Exception as e:
      return f"Error fetching company profile: {e!s}"


# Include the router in the app
app.include_router(financial_router)


@app.get("/")
def read_root() -> dict:
  """Return the root endpoint."""
  return {
    "message": "Welcome to the Financial MCP Server",
    "docs": "/docs",
    "financial_endpoints": "/financial",
  }


# Create MCP server and mount it to FastAPI
mcp = FastApiMCP(app)
mcp.mount()

if __name__ == "__main__":
  import uvicorn

  uvicorn.run(app, host="127.0.0.1", port=8000)
