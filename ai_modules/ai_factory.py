import os
from .providers.openai_p import OpenAIProvider
from .providers.anthropic_p import AnthropicProvider
from .providers.gemini_p import GeminiProvider
from .providers.groq_p import GroqProvider
from .providers.openrouter_p import OpenRouterProvider

class AIFactory:
    @staticmethod
    def get_provider(provider_name: str = None):
        if not provider_name:
            provider_name = os.getenv("ACTIVE_AI_PROVIDER", "Groq")
            
        p_name = provider_name.strip().lower()
        if p_name == "openai":
            return OpenAIProvider()
        elif p_name == "anthropic":
            return AnthropicProvider()
        elif p_name == "gemini":
            return GeminiProvider()
        elif p_name == "groq":
            return GroqProvider()
        elif p_name == "openrouter":
            return OpenRouterProvider()
        else:
            raise ValueError(f"指定されたAIプロバイダ '{provider_name}' は存在しません。")