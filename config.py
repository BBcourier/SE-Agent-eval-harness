import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str


def load_llm_config():
    load_dotenv()

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")

    missing = []

    if not api_key:
        missing.append("LLM_API_KEY")

    if not base_url:
        missing.append("LLM_BASE_URL")

    if not model:
        missing.append("LLM_MODEL")

    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required environment variables: {missing_text}")

    return LLMConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


if __name__ == "__main__":
    config = load_llm_config()

    print("LLM configuration loaded successfully.")
    print(f"base_url: {config.base_url}")
    print(f"model: {config.model}")