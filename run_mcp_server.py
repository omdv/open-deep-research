"""Simple script to run the MCP server for financial APIs."""

import logging
import os
import sys

import uvicorn

from open_deep_research.mcp_server import app

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


if __name__ == "__main__":
  logging.info("Starting Financial MCP Server...")
  logging.info("Available tools:")
  logging.info(
    "- get_company_profile: Get company profile using Financial Modeling Prep API",
  )
  logging.info("")
  logging.info("Required environment variable:")
  logging.info("- FMP_API_KEY: Your Financial Modeling Prep API key")
  logging.info("")
  logging.info("Server will be available at: http://127.0.0.1:8000")
  logging.info("Tools endpoint: http://127.0.0.1:8000/tools/<tool_name>")

  uvicorn.run(app, host="127.0.0.1", port=8000)
