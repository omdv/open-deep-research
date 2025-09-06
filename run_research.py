"""Simple CLI runner for Open Deep Research."""

import asyncio
import sys
from datetime import datetime

from rich.console import Console

from src.configuration import Configuration
from src.deep_researcher import deep_researcher


async def main() -> None:
  """Main function to run the research."""
  console = Console()

  query = " ".join(sys.argv[1:])  # Join all arguments in case query has spaces
  console.print(f"Starting research on: {query}")
  console.print("This may take several minutes...")

  try:
    config = Configuration()

    # Convert enum to string value for serialization
    config_dict = config.model_dump()
    if "search_api" in config_dict:
      config_dict["search_api"] = config_dict["search_api"].value if hasattr(config_dict["search_api"], 'value') else config_dict["search_api"]

    result = await deep_researcher.ainvoke(
      {"messages": [{"role": "user", "content": query}]},
      config={"configurable": config_dict},
    )

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_report_{timestamp}.md"

    # Save report
    with open(filename, "w", encoding="utf-8") as f:
      f.write(result["final_report"])

    console.print(f"✅ Research completed! Report saved to: {filename}")

  except Exception as e:
    console.print(f"❌ Error during research: {str(e)}")
    sys.exit(1)


if __name__ == "__main__":
  asyncio.run(main())
