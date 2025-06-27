import json
from src.ai.openai_client import OpenAIClient


class InvoiceDraftGenerator:
    """プロジェクト情報から請求書ドラフト（業務内容・備考）をAIで生成"""

    def __init__(self, client=None):
        self.client = client or OpenAIClient()

    def generate_draft(self, project_info: dict) -> dict:
        """
        project_info: {
            'client_name': str,
            'project_name': str,
            'billing_amount': int,
            'pm_name': str
        }
        return: {'work_description': str, 'notes': str}
        """
        system_prompt = (
            "あなたは日本のIT企業の経理担当AIです。与えられたプロジェクト情報から、請求書ドラフト（業務内容・備考）を日本語で簡潔に生成してください。\n"
            "出力は必ずJSON形式で、次のキーを含めてください: work_description, notes。")
        user_prompt = (
            f"プロジェクト情報:\n- クライアント名: {project_info.get('client_name')}\n- プロジェクト名: {project_info.get('project_name')}\n- 請求金額: {project_info.get('billing_amount')}円\n- PM: {project_info.get('pm_name')}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = self.client.chat(messages)
        # レスポンスからJSON部分を抽出
        content = response["choices"][0]["message"]["content"]
        try:
            # 余計なテキストが混じる場合も考慮
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            json_str = content[json_start:json_end]
            return json.loads(json_str)
        except Exception:
            return {"work_description": "AI出力パース失敗", "notes": content}
