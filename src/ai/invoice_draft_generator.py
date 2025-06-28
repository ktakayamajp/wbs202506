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
        
        try:
            response = self.client.chat(messages)
            
            # レスポンスの構造を確認
            if not isinstance(response, dict):
                print(f"予期しないレスポンス形式: {type(response)}")
                return {"work_description": "APIレスポンス形式エラー", "notes": str(response)}
            
            # choicesキーの存在を確認
            if "choices" not in response:
                print(f"APIレスポンスにchoicesキーがありません: {response}")
                return {"work_description": "APIレスポンスエラー", "notes": str(response)}
            
            if not response["choices"] or len(response["choices"]) == 0:
                print("APIレスポンスのchoicesが空です")
                return {"work_description": "APIレスポンスが空", "notes": "choicesが空です"}
            
            # メッセージの存在を確認
            if "message" not in response["choices"][0]:
                print(f"APIレスポンスにmessageキーがありません: {response['choices'][0]}")
                return {"work_description": "APIレスポンスエラー", "notes": "messageキーがありません"}
            
            # コンテンツの存在を確認
            if "content" not in response["choices"][0]["message"]:
                print(f"APIレスポンスにcontentキーがありません: {response['choices'][0]['message']}")
                return {"work_description": "APIレスポンスエラー", "notes": "contentキーがありません"}
            
            content = response["choices"][0]["message"]["content"]
            
            try:
                # 余計なテキストが混じる場合も考慮
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start == -1 or json_end == 0:
                    print(f"JSONが見つかりません: {content}")
                    return {"work_description": "JSONパース失敗", "notes": content}
                
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"JSONデコードエラー: {e}, コンテンツ: {content}")
                return {"work_description": "JSONデコード失敗", "notes": content}
            except Exception as e:
                print(f"予期しないエラー: {e}, コンテンツ: {content}")
                return {"work_description": "予期しないエラー", "notes": content}
                
        except Exception as e:
            print(f"API呼び出しエラー: {e}")
            return {"work_description": "API呼び出し失敗", "notes": str(e)}
