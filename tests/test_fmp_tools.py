#!/usr/bin/env python3
"""Test script for FMP tools."""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from open_deep_research.tools.fmp.tools import (
  get_balance_sheet,
  get_cash_flow,
  get_company_profile,
  get_economic_events,
  get_full_stock_quote,
  get_income_statement,
  get_key_metrics,
  get_short_stock_quote,
  get_stock_news,
  get_treasury_rates,
  search_stock_symbols,
)


async def test_tools():
  """Test all FMP tools."""

  # Check if API key is set
  if not os.getenv("FMP_API_KEY"):
    print("❌ FMP_API_KEY environment variable not set!")
    print("Set it with: export FMP_API_KEY='your_api_key_here'")
    return

  print("🧪 Testing FMP Tools...")
  print("=" * 50)

  # Test symbol for testing
  symbol = "AAPL"

  tests = [
    ("Company Profile", get_company_profile, [symbol]),
    ("Full Stock Quote", get_full_stock_quote, [symbol]),
    ("Short Stock Quote", get_short_stock_quote, [symbol]),
    ("Search Symbols", search_stock_symbols, ["Apple"]),
    ("Stock News", get_stock_news, [None, 5]),  # General news, limit 5
    ("Income Statement", get_income_statement, [symbol, "annual", 2]),
    ("Balance Sheet", get_balance_sheet, [symbol, "annual", 2]),
    ("Cash Flow", get_cash_flow, [symbol, "annual", 2]),
    ("Key Metrics", get_key_metrics, [symbol, "annual", 2]),
    ("Treasury Rates", get_treasury_rates, []),
  ]

  # Test economic events (last 7 days)
  today = datetime.now()
  week_ago = today - timedelta(days=7)
  tests.append(
    (
      "Economic Events",
      get_economic_events,
      [week_ago.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")],
    ),
  )

  for test_name, tool_func, args in tests:
    print(f"\n🔧 Testing {test_name}...")
    try:
      # Use proper LangChain tool invocation
      if args:
        if len(args) == 1:
          result = await tool_func.ainvoke(
            {"symbol": args[0]}
            if test_name not in ["Search Symbols", "Economic Events"]
            else {"query": args[0]}
            if test_name == "Search Symbols"
            else {"from_date": args[0], "to_date": args[1]}
            if len(args) > 1
            else {},
          )
        elif len(args) == 2 and test_name == "Economic Events":
          result = await tool_func.ainvoke(
            {"from_date": args[0], "to_date": args[1]},
          )
        elif len(args) == 2 and test_name == "Stock News":
          result = await tool_func.ainvoke(
            {"symbols": args[0], "limit": args[1]},
          )
        elif len(args) == 3:
          result = await tool_func.ainvoke(
            {"symbol": args[0], "period": args[1], "limit": args[2]},
          )
        else:
          result = await tool_func.ainvoke({})
      else:
        result = await tool_func.ainvoke({})
      print(f"✅ {test_name}: SUCCESS")

      # Pretty print JSON if possible
      if result.startswith("Error"):
        print(f"❌ Result: {result}")
      else:
        # Try to extract and format JSON
        try:
          if " is " in result:
            json_part = result.split(" is ", 1)[1].rstrip(".")
            parsed = json.loads(json_part)
            print(
              f"📄 Sample data: {json.dumps(parsed, indent=2)[:300]}...",
            )
          else:
            parsed = json.loads(result)
            print(
              f"📄 Sample data: {json.dumps(parsed, indent=2)[:300]}...",
            )
        except:
          print(f"📄 Raw result: {result[:200]}...")

    except Exception as e:
      print(f"❌ {test_name}: FAILED - {e!s}")

  print("\n" + "=" * 50)
  print("🎉 FMP Tools testing complete!")


if __name__ == "__main__":
  asyncio.run(test_tools())
