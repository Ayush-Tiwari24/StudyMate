"""
StudyMate RAG — LLM Factory

Returns a Groq, OpenAI, or Ollama chat model based on configuration.
Supports both streaming and non-streaming modes.
"""

from functools import lru_cache

from app.core.config import settings
from app.core.logger import logger


def get_llm(
    streaming: bool = True,
    provider: str | None = None,
    model_name: str | None = None,
    temperature: float | None = None,
):
    """
    Create an LLM instance based on the configured provider or user preferences.

    Args:
        streaming: Whether to enable streaming mode
        provider: Optional provider override ("groq" | "openai" | "ollama")
        model_name: Optional model name override
        temperature: Optional temperature override

    Returns:
        A LangChain chat model.
    """
    provider = provider or settings.llm_provider
    temp = temperature if temperature is not None else settings.llm_temperature

    if provider == "groq":
        from langchain_openai import ChatOpenAI

        model = model_name or settings.groq_model
        api_key = settings.groq_api_key or settings.openai_api_key
        logger.info(f"Using Groq LLM: {model} (temp={temp})")
        return ChatOpenAI(
            model=model,
            base_url=settings.groq_base_url,
            api_key=api_key or "dummy_groq_key",
            temperature=temp,
            max_tokens=settings.llm_max_tokens,
            streaming=streaming,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        model = model_name or settings.openai_model
        logger.info(f"Using OpenAI LLM: {model} (temp={temp})")
        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            temperature=temp,
            max_tokens=settings.llm_max_tokens,
            streaming=streaming,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        model = model_name or settings.ollama_model
        logger.info(f"Using Ollama LLM: {model} (temp={temp})")
        return ChatOllama(
            model=model,
            base_url=settings.ollama_base_url,
            temperature=temp,
            num_predict=settings.llm_max_tokens,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_llm_for_rewrite(
    provider: str | None = None,
    model_name: str | None = None,
):
    """
    Get a non-streaming LLM for the question rewrite step.
    Uses user provider/model or falls back to system configuration.
    """
    provider = provider or settings.llm_provider

    if provider == "groq":
        from langchain_openai import ChatOpenAI

        model = model_name or settings.groq_model
        api_key = settings.groq_api_key or settings.openai_api_key
        return ChatOpenAI(
            model=model,
            base_url=settings.groq_base_url,
            api_key=api_key or "dummy_groq_key",
            temperature=0.0,
            max_tokens=200,
            streaming=False,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        model = model_name or settings.openai_model
        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            temperature=0.0,  # Deterministic rewriting
            max_tokens=200,
            streaming=False,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        model = model_name or settings.ollama_model
        return ChatOllama(
            model=model,
            base_url=settings.ollama_base_url,
            temperature=0.0,
            num_predict=200,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
