import requests
import json
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
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            # HTTPエラーの確認
            response.raise_for_status()
            
            # JSONレスポンスの解析
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                print(f"JSONデコードエラー: {e}")
                print(f"レスポンス内容: {response.text}")
                raise Exception(f"APIレスポンスのJSON解析に失敗: {e}")
            
            # レスポンスの基本構造を確認
            if not isinstance(response_data, dict):
                raise Exception(f"予期しないレスポンス形式: {type(response_data)}")
            
            # エラーレスポンスの確認
            if "error" in response_data:
                error_msg = response_data["error"]
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get("message", str(error_msg))
                raise Exception(f"APIエラー: {error_msg}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"HTTPリクエストエラー: {e}")
            raise Exception(f"API呼び出しに失敗: {e}")
        except Exception as e:
            print(f"予期しないエラー: {e}")
            raise
