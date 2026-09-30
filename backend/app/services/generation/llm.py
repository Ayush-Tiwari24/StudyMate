"""
StudyMate RAG — LLM Factory

Returns an OpenAI or Ollama chat model based on configuration.
Supports both streaming and non-streaming modes.
"""

from functools import lru_cache

from app.core.config import settings
from app.core.logger import logger


@lru_cache(maxsize=1)
def get_llm(streaming: bool = True):
    """
    Create and cache an LLM instance based on the configured provider.

    Args:
        streaming: Whether to enable streaming mode

    Returns:
        A LangChain chat model (ChatOpenAI or ChatOllama).
    """
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        logger.info(f"Using OpenAI LLM: {settings.openai_model}")
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            streaming=streaming,
        )

    elif settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        logger.info(f"Using Ollama LLM: {settings.ollama_model}")
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.llm_temperature,
            num_predict=settings.llm_max_tokens,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


def get_llm_for_rewrite():
    """
    Get a non-streaming LLM for the question rewrite step.
    Uses the same provider but without streaming.
    """
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.0,  # Deterministic rewriting
            max_tokens=200,
            streaming=False,
        )
    elif settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.0,
            num_predict=200,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
