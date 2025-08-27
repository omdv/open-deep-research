#!/usr/bin/env python3
"""Test script for FMP client (bypassing LangChain tools)."""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from open_deep_research.tools.fmp.client import FMPClient


async def test_client():
  """Test FMP client directly."""

  # Check if API key is set
  if not os.getenv("FMP_API_KEY"):
    print("❌ FMP_API_KEY environment variable not set!")
    print("Set it with: export FMP_API_KEY='your_api_key_here'")
    return

  print("🧪 Testing FMP Client...")
  print("=" * 50)

  try:
    client = FMPClient()
    symbol = "AAPL"

    # Test 1: Company Profile
    print("\n🔧 Testing Company Profile...")
    profile = await client.get_company_profile(symbol)
    print("✅ Company Profile: SUCCESS")
    print(f"📄 Company: {profile.get('companyName')} ({profile.get('symbol')})")
    print(f"📄 Industry: {profile.get('industry')}")
    print(
      f"📄 Market Cap: ${profile.get('mktCap'):,}" if profile.get("mktCap") else "N/A",
    )

    # Test 2: Stock Quote
    print(f"\n🔧 Testing Stock Quote for {symbol}...")
    quote = await client.get_full_quote(symbol)
    print("✅ Stock Quote: SUCCESS")
    print(f"📄 Price: ${quote.get('price')}")
    print(f"📄 Change: {quote.get('change')} ({quote.get('changesPercentage')}%)")

    # Test 3: Short Quote
    print(f"\n🔧 Testing Short Quote for {symbol}...")
    short_quote = await client.get_short_quote(symbol)
    print("✅ Short Quote: SUCCESS")
    print(
      f"📄 Price: ${short_quote.get('price')}, Volume: {short_quote.get('volume'):,}",
    )

    # Test 4: Symbol Search
    print("\n🔧 Testing Symbol Search...")
    search_results = await client.search_symbols("Apple", 3)
    print("✅ Symbol Search: SUCCESS")
    for i, result in enumerate(search_results[:3], 1):
      print(f"📄 {i}. {result.get('name')} ({result.get('symbol')})")

    # Test 5: Income Statement
    print(f"\n🔧 Testing Income Statement for {symbol}...")
    income = await client.get_income_statement(symbol, "annual", 2)
    print("✅ Income Statement: SUCCESS")
    if income:
      latest = income[0]
      print(f"📄 Latest Period: {latest.get('date')}")
      print(
        f"📄 Revenue: ${latest.get('revenue'):,}" if latest.get("revenue") else "N/A",
      )
      print(
        f"📄 Net Income: ${latest.get('netIncome'):,}"
        if latest.get("netIncome")
        else "N/A",
      )

    # Test 6: Treasury Rates
    print("\n🔧 Testing Treasury Rates...")
    rates = await client.get_treasury_rates()
    print("✅ Treasury Rates: SUCCESS")
    if rates and len(rates) > 0:
      latest_rate = rates[0]
      print(f"📄 Date: {latest_rate.get('date')}")
      print(
        f"📄 1Y: {latest_rate.get('year1')}%, 10Y: {latest_rate.get('year10')}%",
      )

    # Test 7: Economic Events (past 7 days)
    print("\n🔧 Testing Economic Events...")
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    events = await client.get_economic_events(
      week_ago.strftime("%Y-%m-%d"),
      today.strftime("%Y-%m-%d"),
      impact=["High"],
      countries=["US"],
    )
    print("✅ Economic Events: SUCCESS")
    print(f"📄 Found {len(events)} high-impact US events in the past week")
    for event in events[:3]:
      print(
        f"📄 {event.get('date')}: {event.get('event')} ({event.get('impact')})",
      )

    # Test 8: Stock News
    print("\n🔧 Testing Stock News...")
    news = await client.get_stock_news([symbol], 3)
    print("✅ Stock News: SUCCESS")
    print(f"📄 Found {len(news)} news articles for {symbol}")
    for i, article in enumerate(news[:3], 1):
      print(f"📄 {i}. {article.get('title', 'No title')[:60]}...")

  except Exception as e:
    print(f"❌ Test failed: {e!s}")
    import traceback

    traceback.print_exc()

  print("\n" + "=" * 50)
  print("🎉 FMP Client testing complete!")


if __name__ == "__main__":
  asyncio.run(test_client())
