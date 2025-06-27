import requests
from config.settings import settings


class OpenAIClient:
    """OpenRouter経由でOpenAI API (GPT-4o)を利用するラッパー"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = base_url or getattr(
            settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        self.model = model or getattr(
            settings, 'OPENROUTER_MODEL', 'openai/gpt-4o')

    def chat(self, messages, temperature=0.2, max_tokens=1024):
        """
        Chat形式でAPIを呼び出す
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
