#!/usr/bin/env python3
"""
OpenAI APIラッパーテストスイート
"""

import unittest
import json
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ai.openai_client import OpenAIClient

class TestOpenAIClient(unittest.TestCase):
    """OpenAI APIラッパーのテスト"""
    
    def setUp(self):
        self.test_api_key = "test_api_key_12345"
        self.test_base_url = "https://test.openrouter.ai/api/v1"
        self.test_model = "openai/gpt-4o"
        self.client = OpenAIClient(
            api_key=self.test_api_key,
            base_url=self.test_base_url,
            model=self.test_model
        )
    
    def test_initialization(self):
        """初期化テスト"""
        self.assertEqual(self.client.api_key, self.test_api_key)
        self.assertEqual(self.client.base_url, self.test_base_url)
        self.assertEqual(self.client.model, self.test_model)
    
    def test_initialization_with_defaults(self):
        """デフォルト値での初期化テスト"""
        with patch('src.ai.openai_client.settings') as mock_settings:
            mock_settings.OPENROUTER_API_KEY = "default_key"
            mock_settings.OPENROUTER_BASE_URL = "https://default.openrouter.ai/api/v1"
            mock_settings.OPENROUTER_MODEL = "openai/gpt-4o"
            
            client = OpenAIClient()
            self.assertEqual(client.api_key, "default_key")
            self.assertEqual(client.base_url, "https://default.openrouter.ai/api/v1")
            self.assertEqual(client.model, "openai/gpt-4o")
    
    @patch('requests.post')
    def test_chat_success(self, mock_post):
        """チャットAPI呼び出しの成功テスト"""
        # モックレスポンスの設定
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "テストレスポンス"
                }
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # テスト実行
        messages = [
            {"role": "system", "content": "テストシステムプロンプト"},
            {"role": "user", "content": "テストユーザーメッセージ"}
        ]
        result = self.client.chat(messages)
        
        # 検証
        self.assertIn("choices", result)
        self.assertEqual(result["choices"][0]["message"]["content"], "テストレスポンス")
        
        # API呼び出しの検証
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # URLの検証
        self.assertEqual(call_args[0][0], f"{self.test_base_url}/chat/completions")
        
        # ヘッダーの検証
        headers = call_args[1]["headers"]
        self.assertEqual(headers["Authorization"], f"Bearer {self.test_api_key}")
        self.assertEqual(headers["Content-Type"], "application/json")
        
        # ペイロードの検証
        payload = call_args[1]["json"]
        self.assertEqual(payload["model"], self.test_model)
        self.assertEqual(payload["messages"], messages)
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["max_tokens"], 1024)
    
    @patch('requests.post')
    def test_chat_with_custom_parameters(self, mock_post):
        """カスタムパラメータでのチャットAPI呼び出しテスト"""
        # モックレスポンスの設定
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "テスト"}}]}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # テスト実行
        messages = [{"role": "user", "content": "テスト"}]
        result = self.client.chat(messages, temperature=0.5, max_tokens=2048)
        
        # 検証
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertEqual(payload["temperature"], 0.5)
        self.assertEqual(payload["max_tokens"], 2048)
    
    @patch('requests.post')
    def test_chat_api_error(self, mock_post):
        """APIエラーのテスト"""
        # HTTPエラーのシミュレーション
        mock_post.side_effect = Exception("API Error")
        
        messages = [{"role": "user", "content": "テスト"}]
        
        # 例外が発生することを確認
        with self.assertRaises(Exception):
            self.client.chat(messages)
    
    @patch('requests.post')
    def test_chat_http_error(self, mock_post):
        """HTTPエラーのテスト"""
        # HTTP 400エラーのシミュレーション
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 400 Bad Request")
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "テスト"}]
        
        # 例外が発生することを確認
        with self.assertRaises(Exception):
            self.client.chat(messages)
    
    def test_chat_timeout(self):
        """タイムアウトのテスト"""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Timeout")
            
            messages = [{"role": "user", "content": "テスト"}]
            
            with self.assertRaises(Exception):
                self.client.chat(messages)
    
    def test_chat_empty_messages(self):
        """空のメッセージ配列のテスト"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"choices": [{"message": {"content": "テスト"}}]}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # 空のメッセージ配列
            result = self.client.chat([])
            
            # APIは呼び出されるが、空のメッセージ配列が渡される
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            self.assertEqual(payload["messages"], [])
    
    def test_chat_large_messages(self):
        """大きなメッセージのテスト"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"choices": [{"message": {"content": "テスト"}}]}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # 大きなメッセージ
            large_content = "テスト" * 1000
            messages = [{"role": "user", "content": large_content}]
            
            result = self.client.chat(messages)
            
            # APIが呼び出されることを確認
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            self.assertEqual(payload["messages"], messages)

class TestOpenAIClientIntegration(unittest.TestCase):
    """統合テスト"""
    
    def test_client_creation_with_settings(self):
        """設定ファイルを使用したクライアント作成テスト"""
        with patch('src.ai.openai_client.settings') as mock_settings:
            mock_settings.OPENROUTER_API_KEY = "integration_test_key"
            mock_settings.OPENROUTER_BASE_URL = "https://integration.openrouter.ai/api/v1"
            mock_settings.OPENROUTER_MODEL = "openai/gpt-4o"
            
            client = OpenAIClient()
            self.assertEqual(client.api_key, "integration_test_key")
            self.assertEqual(client.base_url, "https://integration.openrouter.ai/api/v1")
            self.assertEqual(client.model, "openai/gpt-4o")
    
    def test_client_creation_with_partial_settings(self):
        """部分的な設定でのクライアント作成テスト"""
        with patch('src.ai.openai_client.settings') as mock_settings:
            # 一部の設定のみ提供
            mock_settings.OPENROUTER_API_KEY = "partial_key"
            # 他の設定はデフォルト値を使用
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            mock_settings.OPENROUTER_MODEL = "openai/gpt-4o"
            
            client = OpenAIClient()
            self.assertEqual(client.api_key, "partial_key")
            # デフォルト値が使用されることを確認
            self.assertEqual(client.base_url, "https://openrouter.ai/api/v1")
            self.assertEqual(client.model, "openai/gpt-4o")

def run_tests():
    """テストスイートを実行"""
    # テストスイートの作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストケースの追加
    suite.addTests(loader.loadTestsFromTestCase(TestOpenAIClient))
    suite.addTests(loader.loadTestsFromTestCase(TestOpenAIClientIntegration))
    
    # テストの実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果の表示
    print(f"\n{'='*50}")
    print("OPENAI CLIENT TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 