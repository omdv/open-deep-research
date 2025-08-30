"""Helper functions for the Deep Research agent."""

import os
from datetime import datetime
from typing import Optional

from langchain_core.runnables import RunnableConfig


def get_today_str() -> str:
  """Get today's date as a formatted string."""
  return datetime.now().strftime("%Y-%m-%d")


def get_api_key_for_model(
  model_name: str,
  config: RunnableConfig = None,
) -> Optional[str]:
  """Get API key for a specific model provider."""
  # Extract provider from model name (e.g., "openai:gpt-4" -> "openai")
  provider = model_name.split(":")[0] if ":" in model_name else model_name

  # Map providers to environment variable names
  provider_key_mapping = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
  }

  env_var = provider_key_mapping.get(provider.lower())
  if env_var:
    return os.getenv(env_var)

  return None
