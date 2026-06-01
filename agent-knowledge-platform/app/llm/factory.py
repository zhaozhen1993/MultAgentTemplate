"""LLM factory: unified interface for creating LLM instances."""

import importlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM instances across different providers.

    Supports: deepseek, qwen (通义千问), ernie (文心一言)
    All providers use OpenAI-compatible API format.
    """

    PROVIDERS = {
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-chat",
            "type": "openai_compatible",
        },
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "default_model": "qwen-plus",
            "type": "openai_compatible",
        },
        "deepseek-coder": {
            "base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-coder",
            "type": "openai_compatible",
        },
    }

    @classmethod
    def create(
        cls,
        provider: str = None,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        temperature: float = 0.7,
        **kwargs,
    ):
        """Create an LLM instance.

        Args:
            provider: Provider name (deepseek/qwen/ernie)
            model: Model name (defaults to provider's default)
            api_key: API key (defaults to settings)
            base_url: API base URL (defaults to provider's URL)
            temperature: Sampling temperature
            **kwargs: Additional parameters passed to ChatOpenAI

        Returns:
            LangChain ChatModel instance
        """
        from langchain_openai import ChatOpenAI
        from app.config import settings

        provider = provider or settings.LLM_PROVIDER
        api_key = api_key or settings.LLM_API_KEY
        base_url = base_url or settings.LLM_BASE_URL

        provider_config = cls.PROVIDERS.get(provider)

        if provider_config and provider_config["type"] == "openai_compatible":
            model = model or provider_config["default_model"]
            base_url = base_url or provider_config["base_url"]

            logger.info(f"Creating LLM: provider={provider}, model={model}, base_url={base_url}")

            return ChatOpenAI(
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                **kwargs,
            )
        else:
            # Try special adapter
            return cls._create_special(provider, model, api_key, temperature, **kwargs)

    @classmethod
    def _create_special(
        cls,
        provider: str,
        model: str = None,
        api_key: str = None,
        temperature: float = 0.7,
        **kwargs,
    ):
        """Create LLM using special adapters for non-OpenAI-compatible providers."""
        adapter_map = {
            "ernie": "app.llm.ernie",
        }

        module_path = adapter_map.get(provider)
        if module_path:
            try:
                module = importlib.import_module(module_path)
                return module.create_llm(
                    model=model,
                    api_key=api_key,
                    temperature=temperature,
                    **kwargs,
                )
            except ImportError as e:
                raise ImportError(
                    f"Provider '{provider}' requires additional dependencies: {e}"
                )

        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Supported providers: {list(cls.PROVIDERS.keys())}"
        )

    @classmethod
    def list_providers(cls) -> list:
        """List available LLM providers."""
        return [
            {
                "name": name,
                "default_model": config.get("default_model"),
                "type": config.get("type"),
            }
            for name, config in cls.PROVIDERS.items()
        ]
