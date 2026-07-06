import os
import requests
from .base import BaseAIProvider

class AnthropicProvider(BaseAIProvider):
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
        self.url = "https://api.anthropic.com/v1/messages"

    def ask_assignment(self, prompt: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
            "system": "You must output your response as a valid JSON object containing a single key 'assigned_name'. Do not include any other text.",
            "temperature": 0.1
        }
        response = requests.post(self.url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result["content"][0]["text"]