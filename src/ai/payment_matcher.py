import json
from src.ai.openai_client import OpenAIClient


class PaymentMatcher:
    """請求書データと入金データのマッチング案をAIで生成"""

    def __init__(self, client=None):
        self.client = client or OpenAIClient()

    def match(self, invoices: list, payments: list) -> list:
        """
        invoices: List[dict]
        payments: List[dict]
        return: List[dict] (各要素: invoice_id, payment_id, match_type, confidence_score, match_amount, status)
        """
        system_prompt = (
            "あなたは日本の経理担当AIです。請求書データと入金データを照合し、マッチング結果を出力してください。\n"
            "完全一致・部分一致・ファジーマッチの3種類で判定し、出力はJSON配列で、各要素に次のキーを含めてください: "
            "invoice_id, payment_id, match_type, confidence_score, match_amount, status。")
        user_prompt = (
            f"請求書データ:\n{json.dumps(invoices, ensure_ascii=False)}\n入金データ:\n{json.dumps(payments, ensure_ascii=False)}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = self.client.chat(messages)
        content = response["choices"][0]["message"]["content"]
        try:
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            json_str = content[json_start:json_end]
            return json.loads(json_str)
        except Exception:
            return [{"error": "AI出力パース失敗", "raw": content}]
