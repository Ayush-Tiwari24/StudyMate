"""
Unit tests for LLM configuration, reasoning effort, and token limits.
"""

from app.core.config import settings
from app.services.generation.llm import get_llm, get_llm_for_rewrite


def test_llm_config_token_limits():
    """Verify settings token limits and defaults."""
    assert settings.llm_max_tokens == 1500
    assert settings.rewrite_max_tokens == 200
    assert settings.groq_reasoning_effort in ("low", "medium", "high", "none")


def test_groq_llm_has_reasoning_effort_and_timeout():
    """Verify reasoning_effort and request timeout are passed to ChatOpenAI when provider is groq."""
    llm = get_llm(streaming=False, provider="groq", model_name="openai/gpt-oss-20b")
    # ChatOpenAI stores reasoning_effort and request_timeout
    assert getattr(llm, "reasoning_effort", None) == settings.groq_reasoning_effort or "low"
    assert getattr(llm, "request_timeout", None) == settings.llm_request_timeout
    assert llm.max_tokens == 1500


def test_groq_rewrite_llm_has_reasoning_effort_and_rewrite_tokens():
    """Verify rewrite LLM configures rewrite_max_tokens and reasoning_effort."""
    rewrite_llm = get_llm_for_rewrite(provider="groq", model_name="openai/gpt-oss-20b")
    assert getattr(rewrite_llm, "reasoning_effort", None) == settings.groq_reasoning_effort or "low"
    assert rewrite_llm.max_tokens == settings.rewrite_max_tokens
    assert getattr(rewrite_llm, "max_retries", None) == 1
