#!/usr/bin/env python3
"""
AIワークフローテストスイート
"""

import unittest
import json
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ai.openai_client import OpenAIClient
from src.ai.invoice_draft_generator import InvoiceDraftGenerator
from src.ai.payment_matcher import PaymentMatcher

class TestOpenAIClient(unittest.TestCase):
    """OpenAI APIラッパーのテスト"""
    
    def setUp(self):
        self.client = OpenAIClient(api_key="test_key", base_url="https://test.openrouter.ai/api/v1")
    
    @patch('requests.post')
    def test_chat_success(self, mock_post):
        """チャットAPI呼び出しの成功テスト"""
        # モックレスポンスの設定
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"work_description": "テスト業務", "notes": "テスト備考"}'
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
        self.assertEqual(result["choices"][0]["message"]["content"], 
                        '{"work_description": "テスト業務", "notes": "テスト備考"}')
        mock_post.assert_called_once()

class TestInvoiceDraftGenerator(unittest.TestCase):
    """請求書ドラフト生成AIのテスト"""
    
    def setUp(self):
        self.generator = InvoiceDraftGenerator()
    
    @patch.object(OpenAIClient, 'chat')
    def test_generate_draft_success(self, mock_chat):
        """ドラフト生成の成功テスト"""
        # モックレスポンスの設定
        mock_chat.return_value = {
            "choices": [{
                "message": {
                    "content": '{"work_description": "システム開発業務", "notes": "月次保守作業"}'
                }
            }]
        }
        
        # テストデータ
        project_info = {
            "client_name": "テスト株式会社",
            "project_name": "テストプロジェクト",
            "billing_amount": 500000,
            "pm_name": "田中太郎"
        }
        
        # テスト実行
        result = self.generator.generate_draft(project_info)
        
        # 検証
        self.assertEqual(result["work_description"], "システム開発業務")
        self.assertEqual(result["notes"], "月次保守作業")
        mock_chat.assert_called_once()
    
    @patch.object(OpenAIClient, 'chat')
    def test_generate_draft_parse_error(self, mock_chat):
        """JSONパースエラーのテスト"""
        # 不正なJSONレスポンス
        mock_chat.return_value = {
            "choices": [{
                "message": {
                    "content": "不正なJSONレスポンス"
                }
            }]
        }
        
        project_info = {
            "client_name": "テスト株式会社",
            "project_name": "テストプロジェクト",
            "billing_amount": 500000,
            "pm_name": "田中太郎"
        }
        
        # テスト実行
        result = self.generator.generate_draft(project_info)
        
        # 検証
        self.assertEqual(result["work_description"], "AI出力パース失敗")
        self.assertEqual(result["notes"], "不正なJSONレスポンス")

class TestPaymentMatcher(unittest.TestCase):
    """入金マッチングAIのテスト"""
    
    def setUp(self):
        self.matcher = PaymentMatcher()
    
    @patch.object(OpenAIClient, 'chat')
    def test_match_success(self, mock_chat):
        """マッチングの成功テスト"""
        # モックレスポンスの設定
        mock_chat.return_value = {
            "choices": [{
                "message": {
                    "content": '''[
                        {
                            "invoice_id": "INV_001",
                            "payment_id": "PAY_001",
                            "match_type": "exact",
                            "confidence_score": 1.0,
                            "match_amount": 300000,
                            "status": "confirmed"
                        }
                    ]'''
                }
            }]
        }
        
        # テストデータ
        invoices = [
            {
                "invoice_id": "INV_001",
                "client_name": "テスト株式会社",
                "billing_amount": 300000
            }
        ]
        
        payments = [
            {
                "payment_id": "PAY_001",
                "client_name": "テスト株式会社",
                "payment_amount": 300000
            }
        ]
        
        # テスト実行
        result = self.matcher.match(invoices, payments)
        
        # 検証
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["invoice_id"], "INV_001")
        self.assertEqual(result[0]["payment_id"], "PAY_001")
        self.assertEqual(result[0]["match_type"], "exact")
        self.assertEqual(result[0]["confidence_score"], 1.0)
        mock_chat.assert_called_once()
    
    @patch.object(OpenAIClient, 'chat')
    def test_match_parse_error(self, mock_chat):
        """JSONパースエラーのテスト"""
        # 不正なJSONレスポンス
        mock_chat.return_value = {
            "choices": [{
                "message": {
                    "content": "不正なJSONレスポンス"
                }
            }]
        }
        
        invoices = [{"invoice_id": "INV_001"}]
        payments = [{"payment_id": "PAY_001"}]
        
        # テスト実行
        result = self.matcher.match(invoices, payments)
        
        # 検証
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["error"], "AI出力パース失敗")
        self.assertEqual(result[0]["raw"], "不正なJSONレスポンス")

class TestIntegration(unittest.TestCase):
    """統合テスト"""
    
    def test_ai_workflow_integration(self):
        """AIワークフロー統合テスト"""
        # 請求書ドラフト生成AIのテスト
        draft_generator = InvoiceDraftGenerator()
        self.assertIsNotNone(draft_generator)
        
        # 入金マッチングAIのテスト
        payment_matcher = PaymentMatcher()
        self.assertIsNotNone(payment_matcher)
        
        # OpenAI APIクライアントのテスト
        openai_client = OpenAIClient()
        self.assertIsNotNone(openai_client)

def run_tests():
    """テストスイートを実行"""
    # テストスイートの作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストケースの追加
    suite.addTests(loader.loadTestsFromTestCase(TestOpenAIClient))
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceDraftGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestPaymentMatcher))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # テストの実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果の表示
    print(f"\n{'='*50}")
    print("AI WORKFLOW TEST SUMMARY")
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